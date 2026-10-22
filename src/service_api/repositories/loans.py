from uuid import UUID

from service_api.models.loans import (
    CreateLoanRepaymentRequest,
    CreatePolicyLoanRequest,
    LoanRepayment,
    PolicyLoan,
)
from service_api.services.database import DatabaseService


class PolicyLoanNotFoundError(Exception):
    pass


class PolicyLoanClosedError(Exception):
    pass


class RepaymentExceedsBalanceError(Exception):
    pass


class PolicyLoanRepository:
    def __init__(self, database: DatabaseService) -> None:
        self._database = database

    async def create_loan(self, request: CreatePolicyLoanRequest) -> PolicyLoan:
        insert_loan_query = """
            INSERT INTO lending.policy_loan (
                borrower_name,
                principal_cents,
                annual_interest_rate_basis_points,
                disbursed_at
            )
            VALUES ($1, $2, $3, $4)
            RETURNING
                uid,
                borrower_name,
                (
                    annual_interest_rate_basis_points::numeric / 10000
                )::numeric(5, 4) AS annual_interest_rate,
                disbursed_at,
                status
        """
        insert_disbursement_query = """
            INSERT INTO lending.loan_transaction (
                policy_loan_uid,
                transaction_type,
                amount_cents,
                effective_at
            )
            VALUES ($1, 'DISBURSEMENT', $2, $3)
        """

        async with (
            self._database.acquire() as connection,
            connection.transaction(),
        ):
            row = await connection.fetchrow(
                insert_loan_query,
                request.borrower_name,
                request.principal_cents,
                request.annual_interest_rate_basis_points,
                request.disbursed_at,
            )
            await connection.execute(
                insert_disbursement_query,
                row["uid"],
                request.principal_cents,
                request.disbursed_at,
            )

        return PolicyLoan.model_validate(
            {
                **dict(row),
                "principal_balance_cents": request.principal_cents,
                "interest_balance_cents": 0,
            }
        )

    async def list_loans(self) -> list[PolicyLoan]:
        query = """
            SELECT
                loan.uid,
                loan.borrower_name,
                (
                    loan.annual_interest_rate_basis_points::numeric / 10000
                )::numeric(5, 4) AS annual_interest_rate,
                loan.disbursed_at,
                loan.status,
                COALESCE(
                    SUM(transaction.amount_cents) FILTER (
                        WHERE transaction.transaction_type = 'DISBURSEMENT'
                    ),
                    0
                )::bigint - COALESCE(
                    SUM(transaction.principal_applied_cents) FILTER (
                        WHERE transaction.transaction_type = 'REPAYMENT'
                    ),
                    0
                )::bigint AS principal_balance_cents,
                COALESCE(
                    SUM(transaction.amount_cents) FILTER (
                        WHERE transaction.transaction_type = 'INTEREST_ACCRUAL'
                    ),
                    0
                )::bigint - COALESCE(
                    SUM(transaction.interest_applied_cents) FILTER (
                        WHERE transaction.transaction_type = 'REPAYMENT'
                    ),
                    0
                )::bigint AS interest_balance_cents
            FROM lending.policy_loan AS loan
            LEFT JOIN lending.loan_transaction AS transaction
                ON transaction.policy_loan_uid = loan.uid
            GROUP BY loan.uid
            ORDER BY loan.disbursed_at, loan.uid
        """
        async with self._database.acquire() as connection:
            rows = await connection.fetch(query)

        return [PolicyLoan.model_validate(dict(row)) for row in rows]

    async def create_repayment(
        self,
        loan_uid: UUID,
        request: CreateLoanRepaymentRequest,
    ) -> LoanRepayment:
        lock_loan_query = """
            SELECT status
            FROM lending.policy_loan
            WHERE uid = $1
            FOR UPDATE
        """
        get_balances_query = """
            SELECT
                COALESCE(
                    SUM(amount_cents) FILTER (
                        WHERE transaction_type = 'DISBURSEMENT'
                    ),
                    0
                )::bigint - COALESCE(
                    SUM(principal_applied_cents) FILTER (
                        WHERE transaction_type = 'REPAYMENT'
                    ),
                    0
                )::bigint AS principal_balance_cents,
                COALESCE(
                    SUM(amount_cents) FILTER (
                        WHERE transaction_type = 'INTEREST_ACCRUAL'
                    ),
                    0
                )::bigint - COALESCE(
                    SUM(interest_applied_cents) FILTER (
                        WHERE transaction_type = 'REPAYMENT'
                    ),
                    0
                )::bigint AS interest_balance_cents
            FROM lending.loan_transaction
            WHERE policy_loan_uid = $1
        """
        insert_repayment_query = """
            INSERT INTO lending.loan_transaction (
                policy_loan_uid,
                transaction_type,
                amount_cents,
                interest_applied_cents,
                principal_applied_cents,
                effective_at
            )
            VALUES ($1, 'REPAYMENT', $2, $3, $4, now())
        """
        close_loan_query = """
            UPDATE lending.policy_loan
            SET status = 'CLOSED'
            WHERE uid = $1
        """

        async with (
            self._database.acquire() as connection,
            connection.transaction(),
        ):
            loan = await connection.fetchrow(lock_loan_query, loan_uid)
            if loan is None:
                raise PolicyLoanNotFoundError
            if loan["status"] == "CLOSED":
                raise PolicyLoanClosedError

            balances = await connection.fetchrow(get_balances_query, loan_uid)
            principal_balance = balances["principal_balance_cents"]
            interest_balance = balances["interest_balance_cents"]
            outstanding_balance = principal_balance + interest_balance
            if request.amount_cents > outstanding_balance:
                raise RepaymentExceedsBalanceError

            interest_applied = min(request.amount_cents, interest_balance)
            principal_applied = request.amount_cents - interest_applied
            remaining_balance = outstanding_balance - request.amount_cents

            await connection.execute(
                insert_repayment_query,
                loan_uid,
                request.amount_cents,
                interest_applied,
                principal_applied,
            )
            if remaining_balance == 0:
                await connection.execute(close_loan_query, loan_uid)

        return LoanRepayment(
            amount_applied_to_interest_cents=interest_applied,
            amount_applied_to_principal_cents=principal_applied,
            remaining_balance_cents=remaining_balance,
        )

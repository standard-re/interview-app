from service_api.models.loans import CreatePolicyLoanRequest, PolicyLoan
from service_api.services.database import DatabaseService


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
                disbursed_at
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
                COALESCE(
                    SUM(transaction.amount_cents) FILTER (
                        WHERE transaction.transaction_type = 'DISBURSEMENT'
                    ),
                    0
                )::bigint AS principal_balance_cents,
                COALESCE(
                    SUM(transaction.amount_cents) FILTER (
                        WHERE transaction.transaction_type = 'INTEREST_ACCRUAL'
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

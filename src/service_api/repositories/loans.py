from service_api.models.loans import PolicyLoan
from service_api.services.database import DatabaseService


class PolicyLoanRepository:
    def __init__(self, database: DatabaseService) -> None:
        self._database = database

    async def list_loans(self) -> list[PolicyLoan]:
        query = """
            SELECT
                loan.uid,
                loan.policy_number,
                loan.borrower_name,
                loan.annual_interest_rate,
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

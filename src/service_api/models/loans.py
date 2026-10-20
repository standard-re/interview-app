from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PolicyLoan(BaseModel):
    uid: UUID
    policy_number: str
    borrower_name: str
    annual_interest_rate: Decimal
    disbursed_at: datetime
    principal_balance_cents: int
    interest_balance_cents: int

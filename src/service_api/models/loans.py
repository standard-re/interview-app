from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints


class CreatePolicyLoanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    borrower_name: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
            pattern=r"^[^\x00]*$",
        ),
    ]
    principal_cents: int = Field(
        strict=True,
        gt=0,
        le=9_223_372_036_854_775_807,
    )
    annual_interest_rate: Decimal = Field(
        ge=0,
        le=Decimal("0.1000"),
        max_digits=5,
        decimal_places=4,
    )
    disbursed_at: AwareDatetime

    @property
    def annual_interest_rate_basis_points(self) -> int:
        return int(self.annual_interest_rate * 10_000)


class PolicyLoanStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class PolicyLoan(BaseModel):
    uid: UUID
    borrower_name: str
    annual_interest_rate: Decimal
    disbursed_at: datetime
    principal_balance_cents: int
    interest_balance_cents: int
    status: PolicyLoanStatus


class CreateLoanRepaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_cents: int = Field(
        strict=True,
        gt=0,
        le=9_223_372_036_854_775_807,
    )


class LoanRepayment(BaseModel):
    amount_applied_to_interest_cents: int
    amount_applied_to_principal_cents: int
    remaining_balance_cents: int

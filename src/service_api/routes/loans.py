from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from service_api.auth import verify_api_key
from service_api.dependencies import get_policy_loan_repository
from service_api.models.loans import (
    CreateLoanRepaymentRequest,
    CreatePolicyLoanRequest,
    LoanRepayment,
    PolicyLoan,
)
from service_api.repositories.loans import (
    PolicyLoanClosedError,
    PolicyLoanNotFoundError,
    PolicyLoanRepository,
    RepaymentExceedsBalanceError,
)

router = APIRouter(
    dependencies=[Depends(verify_api_key)],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden"},
    },
)


@router.post(
    "/loans",
    operation_id="create_policy_loan",
    status_code=status.HTTP_201_CREATED,
)
async def create_policy_loan(
    request: CreatePolicyLoanRequest,
    repository: Annotated[
        PolicyLoanRepository,
        Depends(get_policy_loan_repository),
    ],
) -> PolicyLoan:
    return await repository.create_loan(request)


@router.get("/loans", operation_id="list_policy_loans")
async def list_policy_loans(
    repository: Annotated[
        PolicyLoanRepository,
        Depends(get_policy_loan_repository),
    ],
) -> list[PolicyLoan]:
    return await repository.list_loans()


@router.post(
    "/loans/{loan_uid}/repayments",
    operation_id="create_loan_repayment",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Loan not found"},
        status.HTTP_409_CONFLICT: {"description": "Repayment conflict"},
    },
)
async def create_loan_repayment(
    loan_uid: UUID,
    request: CreateLoanRepaymentRequest,
    repository: Annotated[
        PolicyLoanRepository,
        Depends(get_policy_loan_repository),
    ],
) -> LoanRepayment:
    try:
        return await repository.create_repayment(loan_uid, request)
    except PolicyLoanNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy loan not found",
        ) from error
    except PolicyLoanClosedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Policy loan is closed",
        ) from error
    except RepaymentExceedsBalanceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repayment amount exceeds the outstanding balance",
        ) from error

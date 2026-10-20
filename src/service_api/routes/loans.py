from typing import Annotated

from fastapi import APIRouter, Depends, status

from service_api.auth import verify_api_key
from service_api.dependencies import get_policy_loan_repository
from service_api.models.loans import CreatePolicyLoanRequest, PolicyLoan
from service_api.repositories.loans import PolicyLoanRepository

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

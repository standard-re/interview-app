from typing import Annotated

from fastapi import APIRouter, Depends

from service_api.auth import verify_api_key
from service_api.dependencies import get_policy_loan_repository
from service_api.models.loans import PolicyLoan
from service_api.repositories.loans import PolicyLoanRepository

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/loans", operation_id="list_policy_loans")
async def list_policy_loans(
    repository: Annotated[
        PolicyLoanRepository,
        Depends(get_policy_loan_repository),
    ],
) -> list[PolicyLoan]:
    return await repository.list_loans()

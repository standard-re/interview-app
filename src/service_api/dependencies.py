from functools import lru_cache

from service_api.config import get_settings
from service_api.repositories.loans import PolicyLoanRepository
from service_api.services.database import DatabaseService


@lru_cache
def get_database_service() -> DatabaseService:
    return DatabaseService(get_settings().database_url)


def get_policy_loan_repository() -> PolicyLoanRepository:
    return PolicyLoanRepository(get_database_service())


async def startup_services() -> None:
    await get_database_service().connect()


async def cleanup_services() -> None:
    await get_database_service().close()

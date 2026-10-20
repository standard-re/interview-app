from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from service_api.app import create_app
from service_api.config import Settings, get_settings
from service_api.dependencies import get_policy_loan_repository
from service_api.models.loans import PolicyLoan


@pytest.mark.asyncio
async def test_version_returns_release_metadata_without_authentication() -> None:
    settings = Settings(commit="test-commit", release="test-release")
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"commit": "test-commit", "release": "test-release"}


@pytest.mark.asyncio
async def test_loans_requires_api_key() -> None:
    loan = PolicyLoan(
        uid=UUID("00000000-0000-0000-0000-000000000001"),
        policy_number="POL-100001",
        borrower_name="Avery Morgan",
        annual_interest_rate=Decimal("0.0450"),
        disbursed_at=datetime(2026, 1, 1, tzinfo=UTC),
        principal_balance_cents=2500000,
        interest_balance_cents=6468,
    )

    class FakePolicyLoanRepository:
        async def list_loans(self) -> list[PolicyLoan]:
            return [loan]

    settings = Settings(api_key="test-key")
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_policy_loan_repository] = FakePolicyLoanRepository

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        unauthorized_response = await client.get("/loans")
        authorized_response = await client.get(
            "/loans",
            headers={"X-API-Key": "test-key"},
        )

    assert unauthorized_response.status_code == 401
    assert authorized_response.status_code == 200
    assert authorized_response.json() == [loan.model_dump(mode="json")]

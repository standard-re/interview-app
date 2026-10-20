from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from service_api.app import create_app
from service_api.config import Settings, get_settings
from service_api.dependencies import get_policy_loan_repository
from service_api.models.loans import CreatePolicyLoanRequest, PolicyLoan


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
        borrower_name="Avery Morgan",
        annual_interest_rate=Decimal("0.1000"),
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


@pytest.mark.asyncio
async def test_create_loan_returns_created_loan() -> None:
    loan = PolicyLoan(
        uid=UUID("00000000-0000-0000-0000-000000000001"),
        borrower_name="Avery Morgan",
        annual_interest_rate=Decimal("0.0450"),
        disbursed_at=datetime(2026, 1, 1, tzinfo=UTC),
        principal_balance_cents=2500000,
        interest_balance_cents=0,
    )
    received_requests: list[CreatePolicyLoanRequest] = []

    class FakePolicyLoanRepository:
        async def create_loan(
            self,
            request: CreatePolicyLoanRequest,
        ) -> PolicyLoan:
            received_requests.append(request)
            return loan

    settings = Settings(api_key="test-key")
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_policy_loan_repository] = FakePolicyLoanRepository

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/loans",
            headers={"X-API-Key": "test-key"},
            json={
                "borrower_name": "  Avery Morgan  ",
                "principal_cents": 2500000,
                "annual_interest_rate": "0.1000",
                "disbursed_at": "2026-01-01T00:00:00Z",
            },
        )

    assert response.status_code == 201
    assert response.json() == loan.model_dump(mode="json")
    assert received_requests == [
        CreatePolicyLoanRequest(
            borrower_name="Avery Morgan",
            principal_cents=2500000,
            annual_interest_rate=Decimal("0.1000"),
            disbursed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    ]
    assert received_requests[0].annual_interest_rate_basis_points == 1000


@pytest.mark.asyncio
async def test_create_loan_rejects_invalid_request() -> None:
    class FakePolicyLoanRepository:
        async def create_loan(
            self,
            request: CreatePolicyLoanRequest,
        ) -> PolicyLoan:
            raise AssertionError(f"Unexpected repository call: {request}")

    settings = Settings(api_key="test-key")
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_policy_loan_repository] = FakePolicyLoanRepository

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/loans",
            headers={"X-API-Key": "test-key"},
            json={
                "borrower_name": " ",
                "principal_cents": 0,
                "annual_interest_rate": "0.04501",
                "disbursed_at": "2026-01-01",
                "policy_number": "POL-100001",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_loan_rejects_interest_rate_above_ten_percent() -> None:
    class FakePolicyLoanRepository:
        async def create_loan(
            self,
            request: CreatePolicyLoanRequest,
        ) -> PolicyLoan:
            raise AssertionError(f"Unexpected repository call: {request}")

    settings = Settings(api_key="test-key")
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_policy_loan_repository] = FakePolicyLoanRepository

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/loans",
            headers={"X-API-Key": "test-key"},
            json={
                "borrower_name": "Avery Morgan",
                "principal_cents": 2500000,
                "annual_interest_rate": "0.1001",
                "disbursed_at": "2026-01-01T00:00:00Z",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "less_than_equal"
    assert response.json()["detail"][0]["loc"] == [
        "body",
        "annual_interest_rate",
    ]


def test_loan_endpoints_document_authentication_errors() -> None:
    schema = create_app().openapi()

    for method in ("get", "post"):
        responses = schema["paths"]["/loans"][method]["responses"]
        assert responses["401"]["description"] == "Unauthorized"
        assert responses["403"]["description"] == "Forbidden"


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"principal_cents": True},
        {"principal_cents": "2500000"},
        {"principal_cents": 2500000.0},
        {"principal_cents": 9_223_372_036_854_775_808},
        {"borrower_name": "Avery\x00Morgan"},
    ],
)
def test_create_loan_rejects_values_postgres_cannot_store(
    invalid_fields: dict[str, object],
) -> None:
    valid_fields = {
        "borrower_name": "Avery Morgan",
        "principal_cents": 2500000,
        "annual_interest_rate": "0.0450",
        "disbursed_at": "2026-01-01T00:00:00Z",
    }

    with pytest.raises(ValidationError):
        CreatePolicyLoanRequest.model_validate(valid_fields | invalid_fields)

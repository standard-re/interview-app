from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast
from uuid import UUID

import pytest

from service_api.models.loans import CreateLoanRepaymentRequest
from service_api.repositories.loans import (
    PolicyLoanRepository,
    RepaymentExceedsBalanceError,
)
from service_api.services.database import DatabaseService


class FakeConnection:
    def __init__(self, rows: list[dict[str, Any] | None]) -> None:
        self.rows = rows
        self.executions: list[tuple[str, tuple[object, ...]]] = []

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None]:
        yield

    async def fetchrow(self, query: str, *args: object) -> dict[str, Any] | None:
        return self.rows.pop(0)

    async def execute(self, query: str, *args: object) -> None:
        self.executions.append((query, args))


class FakeDatabase:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[FakeConnection]:
        yield self.connection


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "amount_cents",
        "expected_interest",
        "expected_principal",
        "expected_remaining",
        "expected_execution_count",
    ),
    [
        (5000, 5000, 0, 1005000, 1),
        (15000, 10000, 5000, 995000, 1),
        (1010000, 10000, 1000000, 0, 2),
    ],
)
async def test_create_repayment_applies_interest_before_principal(
    amount_cents: int,
    expected_interest: int,
    expected_principal: int,
    expected_remaining: int,
    expected_execution_count: int,
) -> None:
    connection = FakeConnection(
        [
            {"status": "OPEN"},
            {
                "principal_balance_cents": 1000000,
                "interest_balance_cents": 10000,
            },
        ]
    )
    database = FakeDatabase(connection)
    repository = PolicyLoanRepository(cast(DatabaseService, database))
    loan_uid = UUID("00000000-0000-0000-0000-000000000001")

    repayment = await repository.create_repayment(
        loan_uid,
        CreateLoanRepaymentRequest(amount_cents=amount_cents),
    )

    assert repayment.amount_applied_to_interest_cents == expected_interest
    assert repayment.amount_applied_to_principal_cents == expected_principal
    assert repayment.remaining_balance_cents == expected_remaining
    assert len(connection.executions) == expected_execution_count
    assert connection.executions[0][1] == (
        loan_uid,
        amount_cents,
        expected_interest,
        expected_principal,
    )
    assert "VALUES ($1, 'REPAYMENT', $2, $3, $4, now())" in connection.executions[0][0]
    if expected_remaining == 0:
        assert "SET status = 'CLOSED'" in connection.executions[1][0]


@pytest.mark.asyncio
async def test_create_repayment_rejects_amount_above_balance() -> None:
    connection = FakeConnection(
        [
            {"status": "OPEN"},
            {
                "principal_balance_cents": 1000000,
                "interest_balance_cents": 10000,
            },
        ]
    )
    database = FakeDatabase(connection)
    repository = PolicyLoanRepository(cast(DatabaseService, database))

    with pytest.raises(RepaymentExceedsBalanceError):
        await repository.create_repayment(
            UUID("00000000-0000-0000-0000-000000000001"),
            CreateLoanRepaymentRequest(amount_cents=1010001),
        )

    assert connection.executions == []

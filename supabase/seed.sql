INSERT INTO lending.policy_loan (
    uid,
    borrower_name,
    principal_cents,
    annual_interest_rate_basis_points,
    disbursed_at
)
VALUES
    (
        '10000000-0000-0000-0000-000000000001',
        'Avery Morgan',
        2500000,
        450,
        '2026-09-01 12:00:00+00'
    ),
    (
        '10000000-0000-0000-0000-000000000002',
        'Jordan Lee',
        5000000,
        575,
        '2026-09-08 12:00:00+00'
    ),
    (
        '10000000-0000-0000-0000-000000000003',
        'Riley Chen',
        8000000,
        625,
        '2026-09-15 12:00:00+00'
    ),
    (
        '10000000-0000-0000-0000-000000000004',
        'Cameron Ellis',
        1800000,
        400,
        '2026-08-01 12:00:00+00'
    );

INSERT INTO lending.loan_transaction (
    policy_loan_uid,
    transaction_type,
    amount_cents,
    effective_at
)
SELECT
    uid,
    'DISBURSEMENT',
    principal_cents,
    disbursed_at
FROM lending.policy_loan;

INSERT INTO lending.loan_transaction (
    policy_loan_uid,
    transaction_type,
    amount_cents,
    effective_at
)
SELECT
    loan.uid,
    'INTEREST_ACCRUAL',
    floor(
        loan.principal_cents
        * loan.annual_interest_rate_basis_points
        / 10000.0
        / 365
    )::bigint,
    accrual.effective_at
FROM lending.policy_loan AS loan
CROSS JOIN LATERAL generate_series(
    loan.disbursed_at + interval '1 day',
    loan.disbursed_at + interval '21 days',
    interval '1 day'
) AS accrual(effective_at);

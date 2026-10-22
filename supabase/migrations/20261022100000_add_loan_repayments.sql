ALTER TYPE lending.loan_transaction_type RENAME TO loan_transaction_type_old;

CREATE TYPE lending.loan_transaction_type AS ENUM (
    'DISBURSEMENT',
    'INTEREST_ACCRUAL',
    'REPAYMENT'
);

ALTER TABLE lending.loan_transaction
ALTER COLUMN transaction_type TYPE lending.loan_transaction_type
USING transaction_type::text::lending.loan_transaction_type;

DROP TYPE lending.loan_transaction_type_old;

CREATE TYPE lending.policy_loan_status AS ENUM ('OPEN', 'CLOSED');

ALTER TABLE lending.policy_loan
ADD COLUMN status lending.policy_loan_status NOT NULL DEFAULT 'OPEN';

ALTER TABLE lending.loan_transaction
ADD COLUMN interest_applied_cents bigint,
ADD COLUMN principal_applied_cents bigint,
ADD CONSTRAINT loan_transaction_repayment_allocation_check CHECK (
    (
        transaction_type = 'REPAYMENT'
        AND interest_applied_cents IS NOT NULL
        AND principal_applied_cents IS NOT NULL
        AND interest_applied_cents >= 0
        AND principal_applied_cents >= 0
        AND interest_applied_cents + principal_applied_cents = amount_cents
    )
    OR (
        transaction_type <> 'REPAYMENT'
        AND interest_applied_cents IS NULL
        AND principal_applied_cents IS NULL
    )
);

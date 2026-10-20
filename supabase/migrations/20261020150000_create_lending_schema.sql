CREATE SCHEMA lending;

CREATE TYPE lending.loan_transaction_type AS ENUM (
    'DISBURSEMENT',
    'INTEREST_ACCRUAL'
);

CREATE TABLE lending.policy_loan (
    uid uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_number text NOT NULL,
    borrower_name text NOT NULL,
    principal_cents bigint NOT NULL CHECK (principal_cents > 0),
    annual_interest_rate numeric(5, 4) NOT NULL CHECK (annual_interest_rate >= 0),
    disbursed_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE lending.loan_transaction (
    uid uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_loan_uid uuid NOT NULL REFERENCES lending.policy_loan (uid),
    transaction_type lending.loan_transaction_type NOT NULL,
    amount_cents bigint NOT NULL CHECK (amount_cents > 0),
    effective_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX loan_transaction_policy_loan_uid_effective_at_idx
ON lending.loan_transaction (policy_loan_uid, effective_at);

CREATE FUNCTION lending.set_last_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.last_updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER set_policy_loan_last_updated_at
BEFORE UPDATE ON lending.policy_loan
FOR EACH ROW
EXECUTE FUNCTION lending.set_last_updated_at();

CREATE TRIGGER set_loan_transaction_last_updated_at
BEFORE UPDATE ON lending.loan_transaction
FOR EACH ROW
EXECUTE FUNCTION lending.set_last_updated_at();

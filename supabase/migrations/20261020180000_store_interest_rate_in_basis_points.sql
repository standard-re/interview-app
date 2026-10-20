ALTER TABLE lending.policy_loan
DROP CONSTRAINT policy_loan_annual_interest_rate_check;

ALTER TABLE lending.policy_loan
ALTER COLUMN annual_interest_rate TYPE integer
USING round(annual_interest_rate * 10000)::integer;

ALTER TABLE lending.policy_loan
RENAME COLUMN annual_interest_rate TO annual_interest_rate_basis_points;

ALTER TABLE lending.policy_loan
ADD CONSTRAINT policy_loan_annual_interest_rate_basis_points_nonnegative
CHECK (annual_interest_rate_basis_points >= 0);

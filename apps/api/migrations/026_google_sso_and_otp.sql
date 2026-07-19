-- 026_google_sso_and_otp.sql
-- Google Sign-In (link an existing user to their Google account) + email
-- one-time-code login. Both are alternative login paths for an EXISTING
-- user (matched by email) -- neither can self-provision a brand new
-- org/user, consistent with this app's existing "no self-serve
-- registration beyond POST /auth/signup" design.

ALTER TABLE users ADD COLUMN google_sub VARCHAR(255) UNIQUE;

CREATE TABLE otp_codes (
    otp_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    code_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    consumed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_otp_codes_email ON otp_codes(email);

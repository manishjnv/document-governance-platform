-- 022_review_risk_model.sql
-- Redesigned risk score: was a flat additive sum capped at 100 that
-- saturated to 100 for almost any real document with several critical
-- findings, giving customers no way to tell a "somewhat risky" document
-- from an "extremely risky" one. New model uses a saturating curve and
-- breaks risk down per review axis (Scope/Delivery/Commercial/Security/
-- Governance/Legal/Compliance) instead of one blended number.

ALTER TABLE reviews ADD COLUMN risk_breakdown JSONB;

COMMENT ON COLUMN reviews.risk_breakdown IS
  'Per-axis risk score (0-100 each), e.g. {"Legal": 62, "Commercial": 30, ...}. Null for reviews scored before this column existed.';

-- Per-org override of a risk-severity weight (app/scoring/algorithm.py
-- DocumentScorer.RISK_SEVERITY_WEIGHTS), same pattern as org_scoring_weights.
CREATE TABLE org_risk_weights (
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    severity VARCHAR(20) NOT NULL,
    weight DECIMAL(6,2) NOT NULL CHECK (weight >= 0),
    PRIMARY KEY (org_id, severity)
);

COMMENT ON TABLE org_risk_weights IS 'Per-org override of a risk-severity weight. Absent row = platform default weight.';

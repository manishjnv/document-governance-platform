-- 034: mitre_connections — encrypted-at-rest SIEM connection storage
-- (MITRE Phase 13b, docs/planning/MITRE_SIEM_INTEGRATION_PLAN.md §2.1).
--
-- Stores per-org SIEM connection parameters so pulls can run without
-- re-entering the secret (and, in 13c, on a schedule). The secret is
-- AES-256-GCM ciphertext (nonce || ct||tag) produced by
-- app/mitre/connectors/vault.py with a master key from the SIEM_CRED_KEY
-- env var; key_version enables rotation by re-encryption. config holds
-- ONLY non-secret parameters (validated per connector). The secret is
-- write-only through the API: never returned, never logged, never in
-- reports/exports/LLM payloads.
--
-- Apply to ALL of (no migration runner exists — RCA #3/#11/#12/#13):
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_dev  < apps/api/migrations/034_mitre_connections.sql
--   docker exec -i edgp-postgres psql -U edgp_user -d edgp_test < apps/api/migrations/034_mitre_connections.sql
--   docker exec -i scopewise-postgres psql -U scopewise_user -d scopewise_prod < apps/api/migrations/034_mitre_connections.sql
-- New table only — test_insights_extra.py's hand-rolled fixture is
-- untouched. The platform CHECK is mirrored as an ORM CheckConstraint in
-- app/models/mitre_connection.py (5th sync point: keep in lockstep).

CREATE TABLE IF NOT EXISTS mitre_connections (
    connection_id UUID PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    platform VARCHAR(30) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    secret_ciphertext BYTEA NOT NULL,
    key_version INTEGER NOT NULL DEFAULT 1,
    created_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT ck_mitre_connections_platform CHECK (platform IN ('sentinel'))
);

CREATE INDEX IF NOT EXISTS ix_mitre_connections_org
    ON mitre_connections (org_id) WHERE deleted_at IS NULL;

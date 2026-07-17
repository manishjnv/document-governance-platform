-- =====================================================================
-- EDGP Phase 2 — Fine-Grained Access Control
-- Ref: T-2056 (document-level RBAC), T-2057 (delegation / temporary
--      access grants), T-2058 (access expiry), T-2059 (access audit
--      trail), T-2060 (IP whitelisting, optional feature)
-- Target: PostgreSQL 16
--
-- Depends on:
--   - organizations table (org_id FK)
--   - users table (user_id FK)
-- =====================================================================

-- Per-resource access grant. A grant is delegated access to a single
-- (resource_type, resource_id) for one user at one permission level.
-- Revoked or expired grants are hard-deleted (see
-- app/compliance/access_control.py) -- never soft-deleted, so there is no
-- deleted_at column here.
CREATE TABLE resource_grants (
  grant_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id               UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  resource_type        VARCHAR(50) NOT NULL CHECK (resource_type IN ('document', 'review')),
  resource_id          UUID NOT NULL,
  grantee_user_id      UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  permission           VARCHAR(50) NOT NULL CHECK (permission IN ('view', 'comment', 'edit', 'approve')),
  granted_by_user_id   UUID REFERENCES users(user_id) ON DELETE SET NULL,
  expires_at           TIMESTAMPTZ,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  -- Grants are created once and later deleted (revoke/expire), never
  -- patched -- but the model uses the shared TimestampMixin (created_at +
  -- updated_at) for consistency with every other mixin-based table, so the
  -- column exists here to match.
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE resource_grants IS
  'Fine-grained per-resource access grants (T-2056). expires_at implements temporary delegation (T-2057/T-2058). Revoked/expired rows are hard-deleted, never soft-deleted.';

CREATE INDEX idx_resource_grants_grantee_user_id ON resource_grants (grantee_user_id);
CREATE INDEX idx_resource_grants_resource ON resource_grants (resource_type, resource_id);

-- Org-level IP allowlist (T-2060). Opt-in: an org with zero rows here has
-- not enabled IP restriction at all (see is_ip_allowed()), so this table
-- starting empty for every org is the correct default, not a gap.
CREATE TABLE ip_allowlist (
  entry_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id        UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  cidr          VARCHAR(43) NOT NULL,
  description   VARCHAR(255),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE ip_allowlist IS
  'Org-level allowed CIDR ranges (T-2060, opt-in). Zero rows for an org means IP restriction is off for that org.';

CREATE INDEX idx_ip_allowlist_org_id ON ip_allowlist (org_id);

-- =====================================================================
-- EDGP Phase 2 Wave 2 — Teams
-- Ref: T-2071 (team creation), T-2072 (member roles), T-2073 (invitations),
--      T-2074 (activity feed), T-2075 (team settings)
-- Target: PostgreSQL 16
--
-- Depends on: organizations, users (both in 001_init_schema.sql). Reuses
-- 001's set_updated_at() trigger function — not redefined here.
-- =====================================================================


-- =====================================================================
-- teams — a named group of users within an org
-- =====================================================================
CREATE TABLE teams (
  team_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  name        VARCHAR(255) NOT NULL,
  description TEXT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  deleted_at  TIMESTAMPTZ NULL
);
COMMENT ON TABLE teams IS
  'A named group of users within an org (T-2071). Soft-deletable.';

CREATE UNIQUE INDEX uq_teams_org_name_active
  ON teams (org_id, name) WHERE deleted_at IS NULL;
CREATE INDEX idx_teams_org_active ON teams (org_id) WHERE deleted_at IS NULL;

CREATE TRIGGER trg_teams_updated_at
  BEFORE UPDATE ON teams
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =====================================================================
-- team_members — org user's membership + role on a team
-- =====================================================================
CREATE TABLE team_members (
  member_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id    UUID NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
  user_id    UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  role       VARCHAR(50) NOT NULL DEFAULT 'member',
  created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

  CONSTRAINT ck_team_members_role CHECK (role IN ('lead', 'member')),
  CONSTRAINT uq_team_members_team_user UNIQUE (team_id, user_id)
);
COMMENT ON TABLE team_members IS
  'Membership + role of a user on a team (T-2072). No soft delete -- removing a member deletes the row.';

CREATE INDEX idx_team_members_team_id ON team_members (team_id);
CREATE INDEX idx_team_members_user_id ON team_members (user_id);


-- =====================================================================
-- team_invitations — pending invite to join a team, by email + token
-- =====================================================================
CREATE TABLE team_invitations (
  invitation_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id            UUID NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
  invited_email      VARCHAR(255) NOT NULL,
  invited_by_user_id UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
  status             VARCHAR(50) NOT NULL DEFAULT 'pending',
  token              VARCHAR(255) NOT NULL,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  expires_at         TIMESTAMPTZ NOT NULL,

  CONSTRAINT ck_team_invitations_status CHECK (status IN ('pending', 'accepted', 'expired')),
  CONSTRAINT uq_team_invitations_token UNIQUE (token)
);
COMMENT ON TABLE team_invitations IS
  'Pending/accepted/expired invite to join a team (T-2073). No email is sent -- caller/frontend delivers the link carrying `token`.';

CREATE INDEX idx_team_invitations_team_id ON team_invitations (team_id);
CREATE INDEX idx_team_invitations_email ON team_invitations (invited_email);

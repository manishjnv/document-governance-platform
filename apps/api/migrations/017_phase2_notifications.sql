-- =====================================================================
-- EDGP Phase 2 — Notifications & Preferences
-- Ref: T-2076 (notification data model), T-2080 (notification preferences)
-- Target: PostgreSQL 16
--
-- Depends on:
--   - organizations table (org_id FK)
--   - users table (user_id FK)
-- =====================================================================

-- Notifications: REST-pollable real-time event store
-- T-2076 note: WebSocket real-time push is out of scope (no WS server infra
-- in this repo) — this is the REST-pollable notification store; wire
-- Socket.io/starlette websockets here if that lands later.
CREATE TABLE notifications (
  notif_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id               UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  user_id              UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  type                 VARCHAR(50) NOT NULL,
  content              TEXT NOT NULL,
  read                 BOOLEAN NOT NULL DEFAULT FALSE,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE notifications IS
  'REST-pollable notification store for real-time and async alerts. No soft delete — hard lifecycle.';

CREATE INDEX idx_notifications_user_id_read_created
  ON notifications (user_id, read, created_at DESC);


-- Notification preferences: per-user delivery settings
CREATE TABLE notification_preferences (
  user_id              UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
  org_id               UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  email_enabled        BOOLEAN NOT NULL DEFAULT TRUE,
  in_app_enabled       BOOLEAN NOT NULL DEFAULT TRUE,
  digest_frequency     VARCHAR(20) NOT NULL DEFAULT 'daily'
    CHECK (digest_frequency IN ('realtime', 'daily', 'weekly', 'never')),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE notification_preferences IS
  'User-scoped delivery preferences. One row per user. Soft defaults on insert if missing.';

CREATE INDEX idx_notification_preferences_org_id
  ON notification_preferences (org_id);

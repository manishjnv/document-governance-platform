-- =====================================================================
-- Fix: search_history / saved_searches missing updated_at
-- Ref: T-2005
--
-- 005_phase2_search_history.sql only gave both tables created_at, but
-- their ORM models (app/models/search_history.py) use TimestampMixin,
-- which declares both created_at AND updated_at as NOT NULL columns.
-- Every INSERT the app runs asks Postgres to RETURN updated_at, which
-- 005 never created -- UndefinedColumnError on every write. Add the
-- column + the same set_updated_at() trigger every other table uses
-- (001_init_schema.sql defines the function; not redefined here).
-- =====================================================================

ALTER TABLE search_history
  ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp();

ALTER TABLE saved_searches
  ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp();

CREATE TRIGGER trg_saved_searches_updated_at
  BEFORE UPDATE ON saved_searches
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

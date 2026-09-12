-- Platform admin can grant a free-tier org a fixed number of interactive
-- runs (review trigger / MITRE assessment run); each consumes one, at zero
-- the org is gated again. Paid tiers and platform admins ignore this.
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS run_allowance INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN organizations.run_allowance IS
    'Remaining free-tier interactive runs (review trigger / MITRE assessment run) granted by a platform admin. Decremented by one per run; 0 means gated unless tier is pro/enterprise or caller is a platform admin.';

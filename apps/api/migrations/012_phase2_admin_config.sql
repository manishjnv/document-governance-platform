-- =====================================================================
-- EDGP Phase 2 Wave 2 — Admin customization config tables
-- Ref: T-2091 (custom rules mgmt), T-2092 (AI agent config),
--      T-2093 (scoring weight customization), T-2094 (document type
--      customization), T-2095 (field mappings)
-- Target: PostgreSQL 16
--
-- Five small per-org config tables, each PK'd on (org_id, key). No
-- soft-delete: these are keyed config rows, not user-facing records —
-- absence of a row just means "use the platform default" (see
-- app/admin/customization.py for the default-merge logic).
-- =====================================================================

-- T-2091: enable/disable a built-in rule (app/rules/builtin.py rule_id) per org
CREATE TABLE org_rule_config (
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    rule_id VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (org_id, rule_id)
);

-- T-2092: enable/disable an AI reviewer agent (app/ai/agent.py ReviewAgent.name) per org
CREATE TABLE org_agent_config (
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (org_id, agent_name)
);

-- T-2093: per-org scoring category weight override (app/scoring/algorithm.py DocumentScorer.WEIGHTS)
CREATE TABLE org_scoring_weights (
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,
    weight DECIMAL(5,2) NOT NULL DEFAULT 1.0 CHECK (weight >= 0),
    PRIMARY KEY (org_id, category)
);

-- T-2094: org-defined custom document types (beyond the built-in "SOW")
CREATE TABLE org_document_types (
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    type_name VARCHAR(50) NOT NULL,
    PRIMARY KEY (org_id, type_name)
);

-- T-2095: map a source document field to a scoring category
CREATE TABLE org_field_mappings (
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    source_field VARCHAR(100) NOT NULL,
    target_category VARCHAR(50) NOT NULL,
    PRIMARY KEY (org_id, source_field)
);

COMMENT ON TABLE org_rule_config IS 'Per-org override: is built-in rule_id enabled? Absent row = enabled (default).';
COMMENT ON TABLE org_agent_config IS 'Per-org override: is AI reviewer agent_name enabled? Absent row = enabled (default).';
COMMENT ON TABLE org_scoring_weights IS 'Per-org override of a scoring category weight. Absent row = platform default weight.';
COMMENT ON TABLE org_document_types IS 'Org-defined custom document types, additive to the built-in set.';
COMMENT ON TABLE org_field_mappings IS 'Org-defined mapping of a source document field to a scoring category.';

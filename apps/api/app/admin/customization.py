"""Per-org admin customization config: rules, agents, scoring weights,
document types, field mappings.

T-2091: Custom rules management (enable/disable built-in rules per org)
T-2092: AI agent configuration (enable/disable agents per org)
T-2093: Scoring weight customization
T-2094: Document type customization
T-2095: Field mappings

Raw sqlalchemy.text() queries against the five small keyed-config tables
from migrations/012_phase2_admin_config.sql, matching the pattern
app/compliance/retention.py used for organizations.audit_retention_days
-- no ORM models needed for tables this small.

ponytail: this module only reads/writes the config rows. Nothing in the
rule engine (app/rules/*), scoring algorithm (app/scoring/algorithm.py),
or AI orchestrator (app/ai/orchestrator.py) reads these tables yet -- see
the router/test report for the full "not wired up" caveat.
"""

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import CommercialReviewer, DeliveryReviewer, ScopeReviewer, SecurityReviewer
from app.rules.builtin import get_builtin_rules
from app.scoring.algorithm import DocumentScorer

logger = logging.getLogger(__name__)

# Real built-in rule IDs (app/rules/builtin.py) -- validated against, not invented.
VALID_RULE_IDS = {rule["rule_id"] for rule in get_builtin_rules()}

# Real AI reviewer agent names (app/ai/agent.py). Note: only 4 concrete
# ReviewAgent subclasses exist in this codebase today (Scope, Delivery,
# Commercial, Security) despite orchestrator commit messages referencing
# "5 specialized reviewers" -- validating against what actually exists.
VALID_AGENT_NAMES = {
    cls().name
    for cls in (ScopeReviewer, DeliveryReviewer, CommercialReviewer, SecurityReviewer)
}

# Real scoring categories (app/scoring/algorithm.py DocumentScorer.WEIGHTS).
VALID_SCORING_CATEGORIES = set(DocumentScorer.WEIGHTS.keys())


# ---------------------------------------------------------------------------
# T-2091: rule config
# ---------------------------------------------------------------------------


async def get_rule_config(db: AsyncSession, org_id: UUID) -> dict[str, bool]:
    """All built-in rule_ids -> enabled. Defaults to True unless the org
    has an explicit override row."""
    result = await db.execute(
        text("SELECT rule_id, enabled FROM org_rule_config WHERE org_id = :org_id"),
        {"org_id": org_id},
    )
    overrides = {row[0]: row[1] for row in result.all()}
    return {rule_id: overrides.get(rule_id, True) for rule_id in sorted(VALID_RULE_IDS)}


async def set_rule_enabled(db: AsyncSession, org_id: UUID, rule_id: str, enabled: bool) -> None:
    """Raises ValueError if rule_id isn't a real built-in rule."""
    if rule_id not in VALID_RULE_IDS:
        raise ValueError(f"Unknown rule_id: {rule_id!r}")

    await db.execute(
        text(
            """
            INSERT INTO org_rule_config (org_id, rule_id, enabled)
            VALUES (:org_id, :rule_id, :enabled)
            ON CONFLICT (org_id, rule_id) DO UPDATE SET enabled = :enabled
            """
        ),
        {"org_id": org_id, "rule_id": rule_id, "enabled": enabled},
    )
    await db.commit()


# ---------------------------------------------------------------------------
# T-2092: agent config
# ---------------------------------------------------------------------------


async def get_agent_config(db: AsyncSession, org_id: UUID) -> dict[str, bool]:
    """All real agent names -> enabled. Defaults to True unless overridden."""
    result = await db.execute(
        text("SELECT agent_name, enabled FROM org_agent_config WHERE org_id = :org_id"),
        {"org_id": org_id},
    )
    overrides = {row[0]: row[1] for row in result.all()}
    return {name: overrides.get(name, True) for name in sorted(VALID_AGENT_NAMES)}


async def set_agent_enabled(db: AsyncSession, org_id: UUID, agent_name: str, enabled: bool) -> None:
    """Raises ValueError if agent_name isn't a real ReviewAgent."""
    if agent_name not in VALID_AGENT_NAMES:
        raise ValueError(f"Unknown agent_name: {agent_name!r}")

    await db.execute(
        text(
            """
            INSERT INTO org_agent_config (org_id, agent_name, enabled)
            VALUES (:org_id, :agent_name, :enabled)
            ON CONFLICT (org_id, agent_name) DO UPDATE SET enabled = :enabled
            """
        ),
        {"org_id": org_id, "agent_name": agent_name, "enabled": enabled},
    )
    await db.commit()


# ---------------------------------------------------------------------------
# T-2093: scoring weights
# ---------------------------------------------------------------------------


async def get_scoring_weights(db: AsyncSession, org_id: UUID) -> dict[str, float]:
    """All real scoring categories -> weight. Defaults to the platform
    weight (DocumentScorer.WEIGHTS) unless the org has overridden it."""
    result = await db.execute(
        text("SELECT category, weight FROM org_scoring_weights WHERE org_id = :org_id"),
        {"org_id": org_id},
    )
    overrides = {row[0]: float(row[1]) for row in result.all()}
    return {
        category: overrides.get(category, DocumentScorer.WEIGHTS[category])
        for category in sorted(VALID_SCORING_CATEGORIES)
    }


async def set_scoring_weight(db: AsyncSession, org_id: UUID, category: str, weight: float) -> None:
    """Raises ValueError if category isn't a real scoring category or weight < 0."""
    if category not in VALID_SCORING_CATEGORIES:
        raise ValueError(f"Unknown scoring category: {category!r}")
    if weight < 0:
        raise ValueError(f"weight must be >= 0, got {weight}")

    await db.execute(
        text(
            """
            INSERT INTO org_scoring_weights (org_id, category, weight)
            VALUES (:org_id, :category, :weight)
            ON CONFLICT (org_id, category) DO UPDATE SET weight = :weight
            """
        ),
        {"org_id": org_id, "category": category, "weight": weight},
    )
    await db.commit()


# ---------------------------------------------------------------------------
# T-2094: document types
# ---------------------------------------------------------------------------


async def get_document_types(db: AsyncSession, org_id: UUID) -> list[str]:
    """Org's custom document types. No built-in defaults -- purely additive,
    org-owned rows (the platform's only built-in type today is "SOW", which
    app/rules/builtin.py hardcodes independently of this table)."""
    result = await db.execute(
        text(
            "SELECT type_name FROM org_document_types WHERE org_id = :org_id ORDER BY type_name"
        ),
        {"org_id": org_id},
    )
    return [row[0] for row in result.all()]


async def add_document_type(db: AsyncSession, org_id: UUID, type_name: str) -> None:
    """Idempotent: adding an existing type_name is a no-op."""
    await db.execute(
        text(
            """
            INSERT INTO org_document_types (org_id, type_name)
            VALUES (:org_id, :type_name)
            ON CONFLICT (org_id, type_name) DO NOTHING
            """
        ),
        {"org_id": org_id, "type_name": type_name},
    )
    await db.commit()


async def remove_document_type(db: AsyncSession, org_id: UUID, type_name: str) -> None:
    """Idempotent: removing a non-existent type_name is a no-op."""
    await db.execute(
        text(
            "DELETE FROM org_document_types WHERE org_id = :org_id AND type_name = :type_name"
        ),
        {"org_id": org_id, "type_name": type_name},
    )
    await db.commit()


# ---------------------------------------------------------------------------
# T-2095: field mappings
# ---------------------------------------------------------------------------


async def get_field_mappings(db: AsyncSession, org_id: UUID) -> dict[str, str]:
    """Org's source_field -> target_category mappings."""
    result = await db.execute(
        text(
            "SELECT source_field, target_category FROM org_field_mappings WHERE org_id = :org_id"
        ),
        {"org_id": org_id},
    )
    return {row[0]: row[1] for row in result.all()}


async def set_field_mapping(
    db: AsyncSession, org_id: UUID, source_field: str, target_category: str
) -> None:
    """Raises ValueError if target_category isn't a real scoring category."""
    if target_category not in VALID_SCORING_CATEGORIES:
        raise ValueError(f"Unknown scoring category: {target_category!r}")

    await db.execute(
        text(
            """
            INSERT INTO org_field_mappings (org_id, source_field, target_category)
            VALUES (:org_id, :source_field, :target_category)
            ON CONFLICT (org_id, source_field) DO UPDATE SET target_category = :target_category
            """
        ),
        {"org_id": org_id, "source_field": source_field, "target_category": target_category},
    )
    await db.commit()


async def remove_field_mapping(db: AsyncSession, org_id: UUID, source_field: str) -> None:
    """Idempotent: removing a non-existent source_field is a no-op."""
    await db.execute(
        text(
            "DELETE FROM org_field_mappings WHERE org_id = :org_id AND source_field = :source_field"
        ),
        {"org_id": org_id, "source_field": source_field},
    )
    await db.commit()

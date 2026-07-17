"""Rule engine for document validation.

T-501-T-512: Configuration-driven rule system (no hardcoded logic)
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class RuleSeverity(str, Enum):
    """Rule severity levels."""

    CRITICAL = "critical"
    MAJOR = "major"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class RuleViolation:
    """A rule violation found during validation."""

    rule_id: str
    rule_name: str
    severity: RuleSeverity
    description: str
    evidence: Optional[str] = None
    recommendation: Optional[str] = None


@dataclass
class Rule:
    """
    A validation rule.

    T-501: Design rule format (JSON schema friendly)
    """

    rule_id: str
    name: str
    description: str
    document_types: list[str]  # SOW, Proposal, etc. or ["*"] for all
    severity: RuleSeverity
    check_type: str  # section_presence, word_count, keyword, conditional, regex
    params: dict[str, Any]  # Check-specific parameters
    recommendation: str


class RuleExecutor:
    """
    Execute validation rules against documents.

    T-503: Implement rule executor
    """

    def __init__(self):
        self.rules: list[Rule] = []

    def register_rule(self, rule: Rule):
        """Register a rule."""
        self.rules.append(rule)
        logger.info(f"Registered rule: {rule.rule_id} ({rule.name})")

    async def validate(
        self,
        document_text: str,
        document_type: str,
        sections: Optional[dict[str, str]] = None,
        enabled_rule_ids: Optional[set[str]] = None,
    ) -> list[RuleViolation]:
        """
        Validate document against all applicable rules.

        enabled_rule_ids: T-2091 per-org rule enable/disable
        (app/admin/customization.py). None means unrestricted (all rules).

        Returns list of violations found.
        """
        violations = []

        for rule in self.rules:
            if enabled_rule_ids is not None and rule.rule_id not in enabled_rule_ids:
                continue

            # Check if rule applies to this document type
            if rule.document_types and document_type not in rule.document_types and "*" not in rule.document_types:
                continue

            try:
                # Execute rule based on type
                if rule.check_type == "section_presence":
                    violation = self._check_section_presence(rule, sections or {})

                elif rule.check_type == "word_count":
                    violation = self._check_word_count(rule, sections or {}, document_text)

                elif rule.check_type == "keyword":
                    violation = self._check_keyword(rule, document_text)

                elif rule.check_type == "conditional":
                    violation = self._check_conditional(rule, document_text, sections or {})

                elif rule.check_type == "regex":
                    violation = self._check_regex(rule, document_text)

                else:
                    logger.warning(f"Unknown rule type: {rule.check_type}")
                    continue

                if violation:
                    violations.append(violation)

            except Exception as e:
                logger.error(f"Error executing rule {rule.rule_id}: {e}")
                continue

        return violations

    def _check_section_presence(self, rule: Rule, sections: dict) -> Optional[RuleViolation]:
        """
        T-505: Section presence check
        Verify that required sections exist in document.
        """
        required_sections = rule.params.get("required_sections", [])

        for section in required_sections:
            if section.lower() not in [s.lower() for s in sections.keys()]:
                return RuleViolation(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    description=rule.description,
                    evidence=f"Missing section: '{section}'",
                    recommendation=rule.recommendation,
                )

        return None

    def _check_word_count(
        self, rule: Rule, sections: dict, full_text: str
    ) -> Optional[RuleViolation]:
        """
        T-506: Word count check
        Verify sections have minimum word count.
        """
        required_sections = rule.params.get("required_sections", [])
        min_words = rule.params.get("min_words", 50)

        for section in required_sections:
            section_text = sections.get(section.lower(), "")
            word_count = len(section_text.split())

            if word_count < min_words:
                return RuleViolation(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    description=rule.description,
                    evidence=f"'{section}' has only {word_count} words (minimum {min_words})",
                    recommendation=rule.recommendation,
                )

        return None

    def _check_keyword(self, rule: Rule, document_text: str) -> Optional[RuleViolation]:
        """
        T-508: Keyword check
        Verify document contains required keywords.
        """
        keywords = rule.params.get("keywords", [])
        text_lower = document_text.lower()

        for keyword in keywords:
            if keyword.lower() not in text_lower:
                return RuleViolation(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    description=rule.description,
                    evidence=f"Missing keyword: '{keyword}'",
                    recommendation=rule.recommendation,
                )

        return None

    def _check_conditional(
        self, rule: Rule, document_text: str, sections: dict
    ) -> Optional[RuleViolation]:
        """
        T-507: Conditional check
        E.g., "if SOW > $100K, then delay clause required"
        """
        condition = rule.params.get("condition")
        required_field = rule.params.get("required_field")

        if not condition or not required_field:
            return None

        # Simple conditional: check if condition matches, then verify required field
        if condition.lower() in document_text.lower():
            field_text = sections.get(required_field.lower(), "")
            if not field_text or len(field_text.split()) < 10:
                return RuleViolation(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    description=rule.description,
                    evidence=f"Condition met but '{required_field}' is missing or incomplete",
                    recommendation=rule.recommendation,
                )

        return None

    def _check_regex(self, rule: Rule, document_text: str) -> Optional[RuleViolation]:
        """
        T-508: Regex pattern check
        Verify document matches or doesn't match patterns.
        """
        pattern = rule.params.get("pattern")
        should_match = rule.params.get("should_match", True)

        if not pattern:
            return None

        try:
            matches = bool(re.search(pattern, document_text, re.IGNORECASE))

            if should_match and not matches:
                return RuleViolation(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    description=rule.description,
                    evidence=f"Pattern not found: {pattern}",
                    recommendation=rule.recommendation,
                )
            elif not should_match and matches:
                return RuleViolation(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    description=rule.description,
                    evidence=f"Pattern found but should not be present: {pattern}",
                    recommendation=rule.recommendation,
                )

        except re.error as e:
            logger.error(f"Invalid regex in rule {rule.rule_id}: {e}")

        return None


# Global rule executor instance
_executor: Optional[RuleExecutor] = None


async def get_rule_executor() -> RuleExecutor:
    """Get or create global rule executor."""
    global _executor
    if _executor is None:
        _executor = RuleExecutor()
        await _load_builtin_rules(_executor)
    return _executor


async def _load_builtin_rules(executor: RuleExecutor):
    """
    T-504: Load built-in rules (20 core SOW rules)
    """
    from app.rules.builtin import get_builtin_rules

    for rule_dict in get_builtin_rules():
        rule = Rule(
            rule_id=rule_dict["rule_id"],
            name=rule_dict["name"],
            description=rule_dict["description"],
            document_types=rule_dict.get("document_types", ["*"]),
            severity=RuleSeverity(rule_dict["severity"]),
            check_type=rule_dict["check_type"],
            params=rule_dict.get("params", {}),
            recommendation=rule_dict.get("recommendation", ""),
        )
        executor.register_rule(rule)

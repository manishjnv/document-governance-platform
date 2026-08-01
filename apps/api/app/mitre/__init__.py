"""MITRE ATT&CK coverage-assessment module (isolated from the review pipeline).

Phase 0 surface: pinned ATT&CK dataset access (attack_data), pure
applicability filtering (applicability), and pure coverage computation
(coverage). No DB, no API, no LLM calls at this layer.
"""

"""Suggest missing sections based on document type and parsed sections.

T-2033: Missing section detection
"""

import logging

logger = logging.getLogger(__name__)

# ponytail: domain-derived checklists per document type. Swap for a data-driven
# inventory (e.g., scraped from past documents) once T-2031's pipeline has
# outcome labels — for now, these are reasonable defaults.
SECTION_CHECKLISTS = {
    "SOW": ["scope", "deliverables", "payment terms", "timeline", "acceptance criteria"],
    "Proposal": ["executive summary", "approach", "pricing", "timeline", "terms"],
    "Contract": [
        "parties",
        "recitals",
        "definitions",
        "scope of work",
        "payment terms",
        "term and termination",
        "confidentiality",
        "indemnification",
        "liability",
    ],
    "NDA": [
        "parties",
        "definition of confidential information",
        "permitted use",
        "obligations",
        "term",
        "return of information",
    ],
}


def suggest_missing_sections(document_type: str, parsed_sections: dict) -> list[str]:
    """
    Suggest sections missing from a document based on its type.

    Args:
        document_type: Document type (e.g., "SOW", "Proposal", "Contract", "NDA")
        parsed_sections: Dict of section names found in the document
                        (key: section name, value: any truthy value)

    Returns:
        List of section names from the checklist that were NOT found
    """
    # Normalize document_type case
    doc_type_normalized = document_type.strip() if document_type else ""

    # Get checklist for this type, default to empty if unknown
    checklist = SECTION_CHECKLISTS.get(doc_type_normalized, [])

    if not checklist:
        logger.debug(f"No section checklist for document type: {doc_type_normalized}")
        return []

    # Normalize parsed_sections keys to lowercase for comparison
    found_sections_lower = {k.lower() for k in (parsed_sections or {}).keys()}

    # Find missing sections: case-insensitive substring match
    # (e.g., "payment terms" matches "Payment Terms and Conditions")
    missing = []
    for section in checklist:
        section_lower = section.lower()
        # Check if any found section contains this checklist item
        if not any(section_lower in found_lower for found_lower in found_sections_lower):
            missing.append(section)

    logger.debug(
        f"Document type {doc_type_normalized}: checklist={checklist}, "
        f"missing={missing}"
    )

    return missing

"""PII detection and masking utilities.

T-2049: PII detection & masking
- Regex-based detection of emails, phone numbers, SSN, credit card patterns
- Masking detected PII with type-appropriate redaction markers
"""

import re
from typing import Any


def detect_pii(text: str) -> list[dict[str, Any]]:
    """
    Detect personally identifiable information in text.

    Regex patterns for:
    - Email addresses
    - US-style phone numbers (XXX-XXX-XXXX, (XXX) XXX-XXXX, etc.)
    - SSN-like patterns (XXX-XX-XXXX)
    - Credit card-like patterns (13-19 digits, optional separators)

    Args:
        text: Text to scan for PII

    Returns:
        List of dicts with keys: type, match, start, end
        Empty list if no PII detected
    """
    if not text:
        return []

    findings = []

    # Email pattern (simple but effective)
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    for match in re.finditer(email_pattern, text):
        findings.append(
            {
                "type": "email",
                "match": match.group(),
                "start": match.start(),
                "end": match.end(),
            }
        )

    # US phone number patterns
    # Handles: XXX-XXX-XXXX, (XXX) XXX-XXXX, XXX.XXX.XXXX, +1-XXX-XXX-XXXX, etc.
    phone_pattern = r"(\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b"
    for match in re.finditer(phone_pattern, text):
        findings.append(
            {
                "type": "phone",
                "match": match.group(),
                "start": match.start(),
                "end": match.end(),
            }
        )

    # SSN pattern (XXX-XX-XXXX)
    ssn_pattern = r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b"
    for match in re.finditer(ssn_pattern, text):
        findings.append(
            {
                "type": "ssn",
                "match": match.group(),
                "start": match.start(),
                "end": match.end(),
            }
        )

    # Credit card pattern (13-19 digits, optional separators)
    # Simplified: 4-4-4-4 digits (Visa/Mastercard style) or continuous 13-19 digits
    cc_pattern = r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,19}\b"
    for match in re.finditer(cc_pattern, text):
        match_text = match.group()
        # Filter out non-card-like patterns (e.g., too many common digits)
        digits_only = re.sub(r"\D", "", match_text)
        if len(digits_only) >= 13 and len(digits_only) <= 19:
            findings.append(
                {
                    "type": "credit_card",
                    "match": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                }
            )

    # Sort by position to avoid overlaps during masking
    findings.sort(key=lambda x: x["start"])

    return findings


def mask_pii(text: str) -> str:
    """
    Mask detected PII in text with redaction markers.

    Replaces each detected span with [TYPE REDACTED] (uppercase type name).
    Handles overlapping matches by processing in order from start.

    Args:
        text: Text to mask

    Returns:
        Text with PII replaced by type-appropriate markers
    """
    if not text:
        return text

    findings = detect_pii(text)
    if not findings:
        return text

    # Build replacement text, handling overlaps by tracking offset
    result_parts = []
    last_end = 0

    for finding in findings:
        start, end = finding["start"], finding["end"]

        # Skip if this finding overlaps with previous (shouldn't happen if sorted)
        if start < last_end:
            continue

        # Add unmasked text before this finding
        result_parts.append(text[last_end:start])

        # Add redaction marker
        pii_type = finding["type"].upper()
        result_parts.append(f"[{pii_type} REDACTED]")

        last_end = end

    # Add remaining text after last finding
    result_parts.append(text[last_end:])

    return "".join(result_parts)

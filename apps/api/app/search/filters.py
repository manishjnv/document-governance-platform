"""Filter validation logic. T-2014: Client and server-side validation of filter criteria."""

from app.models.enums import DocumentType


def validate_filters(filters: dict) -> list[str]:
    """
    Validate filter dictionary against allowed criteria.

    Returns:
        List of human-readable error strings. Empty list if valid.
    """
    errors = []

    # ponytail: simple validation, add structured error codes if needed later
    if not isinstance(filters, dict):
        errors.append("filters must be a dictionary")
        return errors

    # Validate date_from and date_to
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")

    if date_from and date_to:
        if date_from > date_to:
            errors.append("date_from must be on or before date_to")

    # Validate document_type
    document_type = filters.get("document_type")
    if document_type:
        valid_types = [dt.value for dt in DocumentType]
        if document_type not in valid_types:
            errors.append(f"document_type must be one of: {', '.join(valid_types)}")

    # Validate score range
    score_min = filters.get("score_min")
    score_max = filters.get("score_max")

    if score_min is not None and score_max is not None:
        if score_min > score_max:
            errors.append("score_min must be less than or equal to score_max")

    # Validate score bounds
    if score_min is not None and (score_min < 0 or score_min > 100):
        errors.append("score_min must be between 0 and 100")

    if score_max is not None and (score_max < 0 or score_max > 100):
        errors.append("score_max must be between 0 and 100")

    return errors

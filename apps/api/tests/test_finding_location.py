"""_locate_finding tiers: exact/normalized, sentence, 8-word shingle --
and never a false anchor from a short generic phrase."""

from app.routers.reviews import _locate_finding

_SECTIONS = [
    {
        "heading": "5. Service Levels",
        "content": (
            "Critical incidents are acknowledged within 15 minutes.\n"
            "The platform availability commitment is 99.9% measured monthly "
            "across all in-scope services and reported quarterly.\n"
        ),
        "page_number": 2,
    },
    {
        "heading": "11. Commercial Model",
        "content": "A fixed monthly fee applies, invoiced monthly in arrears.\n",
        "page_number": 3,
    },
]
_DOC = " ".join(s["content"] for s in _SECTIONS)


def test_exact_quote_locates_with_page():
    ref, page = _locate_finding(
        "Critical incidents are acknowledged within 15 minutes.", _DOC, _SECTIONS
    )
    assert ref == "5. Service Levels (p.2)"
    assert page == 2


def test_case_and_whitespace_differences_still_match():
    ref, page = _locate_finding(
        "critical incidents   are ACKNOWLEDGED within\n15 minutes", _DOC, _SECTIONS
    )
    assert page == 2


def test_partially_paraphrased_evidence_matches_via_sentence_or_shingle():
    # First sentence invented, second is a verbatim quote.
    ref, page = _locate_finding(
        "The SLA lacks resolution commitments. The platform availability "
        "commitment is 99.9% measured monthly across all in-scope services "
        "and reported quarterly.",
        _DOC,
        _SECTIONS,
    )
    assert page == 2


def test_generic_short_phrase_gets_no_anchor():
    ref, page = _locate_finding("monthly", _DOC, _SECTIONS)
    assert ref is None and page is None


def test_fully_paraphrased_evidence_gets_no_anchor():
    ref, page = _locate_finding(
        "Vendor should define an escalation matrix with named levels and owners.",
        _DOC,
        _SECTIONS,
    )
    assert ref is None and page is None

"""Tests for document-type auto-detection (app/parser.py).

RFP support (docs/planning/4_AI_AGENT_SPECS.md, 2026-07-17): a real bug was
found and fixed during adversarial review -- the SOW check ran before the
RFP check, so an RFP that mentions "Statement of Work" as boilerplate (the
deliverable the awarded vendor will produce) was silently misclassified as
SOW, routing it through the wrong ReviewAgent branch and rule set with no
exception raised.
"""

from app.parser import DocumentType, DocxParser, PdfParser

_RFP_WITH_SOW_BOILERPLATE = """
REQUEST FOR PROPOSAL

We are requesting proposals for cloud migration services. The selected
vendor shall produce a Statement of Work within 10 business days of award,
detailing the full scope of the engagement.
"""

_PLAIN_SOW = "STATEMENT OF WORK\n\nThis SOW covers cloud migration services."

_PLAIN_RFP = "REQUEST FOR PROPOSAL\n\nWe are soliciting bids for cloud migration services."


class TestDocxParserTypeDetection:
    def test_rfp_mentioning_statement_of_work_is_not_misclassified_as_sow(self):
        assert DocxParser._detect_type(_RFP_WITH_SOW_BOILERPLATE) == DocumentType.RFP

    def test_plain_sow_still_detected(self):
        assert DocxParser._detect_type(_PLAIN_SOW).value == "SOW"

    def test_plain_rfp_still_detected(self):
        assert DocxParser._detect_type(_PLAIN_RFP).value == "RFP"


class TestPdfParserTypeDetection:
    def test_rfp_mentioning_statement_of_work_is_not_misclassified_as_sow(self):
        assert PdfParser._detect_type(_RFP_WITH_SOW_BOILERPLATE).value == "RFP"

    def test_plain_sow_still_detected(self):
        assert PdfParser._detect_type(_PLAIN_SOW).value == "SOW"

    def test_plain_rfp_still_detected(self):
        assert PdfParser._detect_type(_PLAIN_RFP).value == "RFP"

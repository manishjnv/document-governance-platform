"""Document parsing for DOCX and PDF files."""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Document types recognized by parser."""

    SOW = "SOW"
    PROPOSAL = "Proposal"
    PROJECT_PLAN = "ProjectPlan"
    HLD = "HLD"
    LLD = "LLD"
    SOP = "SOP"
    SLA = "SLA"
    SECURITY = "Security"
    OTHER = "Other"


@dataclass
class ParsedSection:
    """A section extracted from document."""

    heading: str
    level: int  # 1=H1, 2=H2, etc.
    content: str
    page_number: Optional[int] = None
    start_offset: int = 0
    end_offset: int = 0


@dataclass
class ParseResult:
    """Result from parsing a document."""

    status: str  # success | partial | failed
    raw_text: str
    sections: list[ParsedSection]
    page_count: int
    detected_type: Optional[DocumentType] = None
    language: str = "en"
    error_message: Optional[str] = None
    tokens_estimated: int = 0


class DocxParser:
    """Parse DOCX files."""

    @staticmethod
    async def parse(file_content: bytes) -> ParseResult:
        """Parse DOCX file."""
        try:
            from docx import Document
            from docx.enum.style import WD_STYLE_TYPE

            doc = Document(file_content)
            raw_text = []
            sections = []
            page_count = 1  # DOCX doesn't have built-in page info

            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue

                raw_text.append(text)

                # Detect heading level
                level = 0
                if para.style and para.style.name.startswith("Heading"):
                    # Extract number from "Heading 1", "Heading 2", etc.
                    try:
                        level = int(para.style.name.split()[-1])
                    except (IndexError, ValueError):
                        level = 0

                # If it's a heading, create a section
                if level > 0:
                    sections.append(
                        ParsedSection(
                            heading=text,
                            level=level,
                            content="",  # Will be filled as we parse
                        )
                    )
                elif sections:
                    # Add to last section's content
                    sections[-1].content += text + "\n"

            # Combine text
            full_text = "\n".join(raw_text)

            # Estimate tokens (rough: 1 token ≈ 4 chars)
            tokens = len(full_text) // 4

            # Detect document type
            detected_type = DocxParser._detect_type(full_text)

            return ParseResult(
                status="success",
                raw_text=full_text,
                sections=sections,
                page_count=page_count,
                detected_type=detected_type,
                tokens_estimated=tokens,
            )

        except Exception as e:
            logger.error(f"DOCX parsing error: {e}")
            return ParseResult(
                status="failed",
                raw_text="",
                sections=[],
                page_count=0,
                error_message=str(e),
            )

    @staticmethod
    def _detect_type(text: str) -> DocumentType:
        """Detect document type from content."""
        text_lower = text.lower()

        # Simple pattern matching (can be improved with ML later)
        if "statement of work" in text_lower or "sow" in text_lower:
            return DocumentType.SOW
        elif "proposal" in text_lower:
            return DocumentType.PROPOSAL
        elif "project plan" in text_lower:
            return DocumentType.PROJECT_PLAN
        elif "high level design" in text_lower or "hld" in text_lower:
            return DocumentType.HLD
        elif "low level design" in text_lower or "lld" in text_lower:
            return DocumentType.LLD
        elif "standard operating procedure" in text_lower or "sop" in text_lower:
            return DocumentType.SOP
        elif "service level agreement" in text_lower or "sla" in text_lower:
            return DocumentType.SLA
        elif "security" in text_lower:
            return DocumentType.SECURITY

        return DocumentType.OTHER


class PdfParser:
    """Parse PDF files."""

    @staticmethod
    async def parse(file_content: bytes) -> ParseResult:
        """Parse PDF file."""
        try:
            from pypdf import PdfReader
            from io import BytesIO

            pdf = PdfReader(BytesIO(file_content))
            page_count = len(pdf.pages)
            raw_text = []
            sections = []

            # Extract text from all pages
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                raw_text.append(f"--- Page {page_num} ---\n{text}")

                # Try to detect sections by font size changes (simplified)
                # In a real implementation, use advanced PDF analysis
                lines = text.split("\n")
                for line in lines:
                    line = line.strip()
                    if len(line) > 5 and len(line) < 100:  # Heuristic for headings
                        if line.isupper() or (line[0].isupper() and len(line.split()) < 10):
                            sections.append(
                                ParsedSection(
                                    heading=line,
                                    level=1,
                                    content="",
                                    page_number=page_num,
                                )
                            )

            full_text = "\n".join(raw_text)
            tokens = len(full_text) // 4

            # Detect document type
            detected_type = PdfParser._detect_type(full_text)

            return ParseResult(
                status="success" if full_text else "partial",
                raw_text=full_text,
                sections=sections,
                page_count=page_count,
                detected_type=detected_type,
                tokens_estimated=tokens,
            )

        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            return ParseResult(
                status="failed",
                raw_text="",
                sections=[],
                page_count=0,
                error_message=str(e),
            )

    @staticmethod
    def _detect_type(text: str) -> DocumentType:
        """Detect document type from content."""
        text_lower = text.lower()

        if "statement of work" in text_lower or "sow" in text_lower:
            return DocumentType.SOW
        elif "proposal" in text_lower:
            return DocumentType.PROPOSAL
        elif "project plan" in text_lower:
            return DocumentType.PROJECT_PLAN
        elif "high level design" in text_lower or "hld" in text_lower:
            return DocumentType.HLD
        elif "low level design" in text_lower or "lld" in text_lower:
            return DocumentType.LLD
        elif "standard operating procedure" in text_lower or "sop" in text_lower:
            return DocumentType.SOP
        elif "service level agreement" in text_lower or "sla" in text_lower:
            return DocumentType.SLA
        elif "security" in text_lower:
            return DocumentType.SECURITY

        return DocumentType.OTHER


async def parse_document(
    file_content: bytes, file_type: str
) -> ParseResult:
    """
    Parse document based on file type.

    T-313-T-320: Main parsing pipeline
    """
    file_type = file_type.lower()

    if file_type in ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        return await DocxParser.parse(file_content)

    elif file_type in ("pdf", "application/pdf"):
        return await PdfParser.parse(file_content)

    else:
        return ParseResult(
            status="failed",
            raw_text="",
            sections=[],
            page_count=0,
            error_message=f"Unsupported file type: {file_type}",
        )

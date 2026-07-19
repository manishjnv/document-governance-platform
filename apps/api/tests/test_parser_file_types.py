"""Tests for the new file-type parsers: CSV (stdlib), .xlsx (openpyxl),
.xls (xlrd), and .doc (antiword, exercised via its not-installed failure
path in this dev environment -- the success path is covered on the CI/prod
image where antiword is actually present). Multi-sheet coverage matters:
Excel workbooks with multiple tabs must all be captured, not just the first.
"""

from io import BytesIO

import pytest

from app.parser import CsvParser, DocParser, ExcelParser, XlsParser, parse_document


class TestCsvParser:
    async def test_parses_rows_into_text(self):
        content = b"name,role\nAlice,admin\nBob,viewer\n"
        result = await CsvParser.parse(content)
        assert result.status == "success"
        assert "Alice" in result.raw_text
        assert "admin" in result.raw_text

    async def test_empty_csv_is_partial(self):
        result = await CsvParser.parse(b"")
        assert result.status == "partial"


class TestExcelParser:
    def _workbook_bytes(self, sheet_data: dict[str, list[list]]) -> bytes:
        from openpyxl import Workbook

        wb = Workbook()
        wb.remove(wb.active)
        for name, rows in sheet_data.items():
            ws = wb.create_sheet(title=name)
            for row in rows:
                ws.append(row)
        buf = BytesIO()
        wb.save(buf)
        return buf.getvalue()

    async def test_single_sheet(self):
        content = self._workbook_bytes({"Sheet1": [["a", "b"], [1, 2]]})
        result = await ExcelParser.parse(content)
        assert result.status == "success"
        assert "Sheet1" in result.raw_text

    async def test_multiple_sheets_all_captured(self):
        """Every tab must show up in raw_text/sections, not just the first."""
        content = self._workbook_bytes(
            {
                "Summary": [["total", 100]],
                "Details": [["line item", "amount"], ["widget", 50]],
                "Notes": [["remember to review section 4"]],
            }
        )
        result = await ExcelParser.parse(content)
        assert result.status == "success"
        assert {s.heading for s in result.sections} == {"Summary", "Details", "Notes"}
        assert "widget" in result.raw_text
        assert "review section 4" in result.raw_text
        assert result.page_count == 3


class TestXlsParser:
    async def test_invalid_bytes_fails_gracefully(self):
        result = await XlsParser.parse(b"not a real xls file")
        assert result.status == "failed"
        assert result.error_message


class TestDocParser:
    async def test_missing_antiword_fails_gracefully(self):
        """In this dev environment antiword isn't installed -- confirms the
        graceful-failure path rather than an unhandled crash. The success
        path (antiword actually extracting text) runs on the prod image,
        which installs antiword via Dockerfile.prod."""
        result = await DocParser.parse(b"fake doc bytes")
        assert result.status == "failed"
        assert result.error_message


class TestParseDocumentDispatch:
    async def test_dispatches_csv_by_extension_alias(self):
        result = await parse_document(b"a,b\n1,2\n", "csv")
        assert result.status == "success"

    async def test_dispatches_xlsx_by_mime_type(self):
        from openpyxl import Workbook

        wb = Workbook()
        wb.active.append(["x", "y"])
        buf = BytesIO()
        wb.save(buf)

        result = await parse_document(
            buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        assert result.status == "success"

    async def test_unsupported_type_fails(self):
        result = await parse_document(b"data", "application/zip")
        assert result.status == "failed"

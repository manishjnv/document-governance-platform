"""Ingest unit tests for the MITRE assessment module (Phase 1).

Fixture files are built in-memory with openpyxl / plain CSV — no checked-in
binaries. (.xls reading via xlrd is untested here: no xls writer is
installed; the code path is symmetric with xlsx.)
"""

import io

import pytest
from openpyxl import Workbook

from app.mitre import ingest
from app.mitre.ingest import IngestError, parse_use_case_file, parse_environment_file


def _xlsx(rows, sheet_name="Sheet1", extra_sheets=()) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    for row in rows:
        ws.append(row)
    for name, extra_rows in extra_sheets:
        extra = wb.create_sheet(name)
        for row in extra_rows:
            extra.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


TEMPLATE_HEADERS = [
    "Use Case Name", "MITRE Technique(s)", "Detection Logic",
    "Description", "Log Source", "Status",
]


def test_template_layout_happy_path():
    content = _xlsx([
        TEMPLATE_HEADERS,
        ["Suspicious PowerShell", "T1059.001", "process where ...", "PS abuse", "Sysmon", "Enabled"],
        ["RDP Brute Force", "T1110, T1021.001", "auth failures > 20", "", "WinEventLog", "Disabled"],
        ["Untagged rule", "", "some query", "", "", "Enabled"],
    ])
    parsed = parse_use_case_file(content, "xlsx")
    assert parsed["row_count"] == 3
    assert set(parsed["columns"]) == {"name", "tags", "logic", "description", "log_source", "enabled"}
    r1, r2, r3 = parsed["rows"]
    assert r1 == {
        "row_ref": "Sheet1:2", "name": "Suspicious PowerShell",
        "description": "PS abuse", "log_source": "Sysmon", "enabled": True,
        "tags": ["T1059.001"], "logic": "process where ...",
    }
    assert r2["tags"] == ["T1110", "T1021.001"]
    assert r2["enabled"] is False
    assert r3["tags"] == [] and r3["enabled"] is True


def test_messy_headers_detected_below_title_rows():
    content = _xlsx([
        ["SOC Detection Inventory — Export 2026"],
        [],
        ["Rule", "TTPs", "Query", "State"],
        ["Kerberoasting watch", "t1558.003", "spn requests...", "active"],
    ])
    parsed = parse_use_case_file(content, "xlsx")
    assert parsed["row_count"] == 1
    row = parsed["rows"][0]
    assert row["row_ref"] == "Sheet1:4"
    assert row["tags"] == ["T1558.003"]  # lowercase tag normalized
    assert row["enabled"] is True


def test_csv_happy_path():
    content = "Rule Name,MITRE ID,Status\r\nDNS tunnel detect,T1071.004,enabled\r\n".encode()
    parsed = parse_use_case_file(content, "csv")
    assert parsed["row_count"] == 1
    assert parsed["rows"][0]["row_ref"] == "csv:2"
    assert parsed["rows"][0]["tags"] == ["T1071.004"]


def test_empty_file_rejected():
    with pytest.raises(IngestError, match="empty"):
        parse_use_case_file(b"", "xlsx")


def test_no_name_column_rejected_pointing_at_template():
    content = _xlsx([["foo", "bar"], ["a", "b"]])
    with pytest.raises(IngestError, match="template"):
        parse_use_case_file(content, "xlsx")


def test_row_cap_enforced():
    lines = ["Rule Name,MITRE ID"] + [f"rule {i},T1059" for i in range(ingest.MAX_USE_CASE_ROWS + 1)]
    with pytest.raises(IngestError, match="row limit|5,000"):
        parse_use_case_file("\n".join(lines).encode(), "csv")


def test_pdf_docx_rejected_with_phase2_message():
    for file_type in ("pdf", "docx"):
        with pytest.raises(IngestError, match="XLSX template"):
            parse_use_case_file(b"%PDF-1.4 whatever", file_type)


def test_environment_workbook_parsing():
    content = _xlsx(
        [["Platform"], ["Windows Server 2019"], ["Ubuntu Linux"], ["Azure AD"],
         ["AWS"], ["OT/SCADA network"], ["Cisco IOS switches"], ["SAP ERP"]],
        sheet_name="Assets",
        extra_sheets=[("Log Sources", [["Source"], ["Sysmon"], ["CloudTrail"]])],
    )
    parsed = parse_environment_file(content, "xlsx")
    env = parsed["environment"]
    assert env["inventory_provided"] is True
    assert set(env["platforms"]) == {"Windows", "Linux", "Identity Provider", "IaaS", "Network Devices"}
    assert env["has_ics_assets"] is True          # OT/SCADA row
    assert env["has_managed_mobile"] is False
    assert parsed["log_sources"] == ["Sysmon", "CloudTrail"]
    assert parsed["sheets_found"] == {"assets": "Assets", "log_sources": "Log Sources"}
    # missing sheets + unmapped assets become assumption lines
    assert any("Security Tooling" in a for a in parsed["assumptions"])
    assert any("Crown Jewels" in a for a in parsed["assumptions"])
    assert any("SAP ERP" in a for a in parsed["assumptions"])


def test_environment_mobile_detection_and_missing_assets_sheet():
    content = _xlsx(
        [["Source"], ["Sysmon"]],
        sheet_name="Log Sources",
        extra_sheets=[("Tooling", [["Tool"], ["Intune MDM"], ["CrowdStrike EDR"]])],
    )
    parsed = parse_environment_file(content, "xlsx")
    assert parsed["environment"]["inventory_provided"] is False
    assert any("Assets" in a for a in parsed["assumptions"])

    content = _xlsx([["Asset"], ["Android"], ["iPhone fleet"]], sheet_name="Assets")
    parsed = parse_environment_file(content, "xlsx")
    env = parsed["environment"]
    assert set(env["platforms"]) == {"Android", "iOS"}
    assert env["has_managed_mobile"] is True


def test_environment_must_be_excel():
    with pytest.raises(IngestError, match="Excel"):
        parse_environment_file(b"a,b,c", "csv")


# ---------------------------------------------------------------------------
# workbook-wide budgets (2026-08-01 adversarial review, blocking finding #2)
# ---------------------------------------------------------------------------


def test_workbook_sheet_cap():
    wb = Workbook()
    for i in range(ingest.MAX_SHEETS + 1):
        wb.create_sheet(f"extra{i}")
    buf = io.BytesIO()
    wb.save(buf)
    with pytest.raises(IngestError, match="sheets"):
        ingest._xlsx_grids(buf.getvalue())


def test_workbook_cumulative_row_cap():
    wb = Workbook()
    half = ingest.MAX_TOTAL_ROWS // 2 + 100
    for title in ("a", "b"):
        ws = wb.create_sheet(title)
        for _ in range(half):
            ws.append(["x"])
    buf = io.BytesIO()
    wb.save(buf)
    with pytest.raises(IngestError, match="overall limit"):
        ingest._xlsx_grids(buf.getvalue())


def test_workbook_row_width_cap():
    wb = Workbook()
    wb.active.append(["c"] * (ingest.MAX_ROW_CELLS + 1))
    buf = io.BytesIO()
    wb.save(buf)
    with pytest.raises(IngestError, match="wider than"):
        ingest._xlsx_grids(buf.getvalue())


# --- Phase 9: column override + preview headers/samples ---

def test_column_override_replaces_detection():
    content = _xlsx([
        ["Rule Name", "Ref Codes", "Query"],
        ["Encoded PowerShell", "T1059.001", "proc = powershell"],
    ])
    auto = parse_use_case_file(content, "xlsx")
    assert "tags" not in auto["columns"]  # 'Ref Codes' isn't a synonym
    assert auto["headers"] == ["Rule Name", "Ref Codes", "Query"]
    assert auto["sample_rows"] == [["Encoded PowerShell", "T1059.001", "proc = powershell"]]

    overridden = parse_use_case_file(
        content, "xlsx", column_override={"name": 0, "tags": 1, "logic": 2}
    )
    assert overridden["columns"] == {"name": 0, "tags": 1, "logic": 2}
    assert overridden["rows"][0]["tags"] == ["T1059.001"]
    assert overridden["rows"][0]["logic"] == "proc = powershell"


def test_column_override_validation_errors():
    content = _xlsx([["Rule Name", "Ref Codes"], ["r1", "T1110"]])
    for bad, needle in [
        ({"name": 5}, "out of range"),
        ({"name": True}, "out of range"),          # bools are not indexes
        ({"nope": 0, "name": 1}, "Unknown field"),
        ({"tags": 1}, "name column is required"),
        ({}, "non-empty object"),
        ({"name": 0, "tags": 0}, "one field"),
    ]:
        with pytest.raises(IngestError, match=needle):
            parse_use_case_file(content, "xlsx", column_override=bad)


def test_csv_grid_enforces_row_and_width_caps():
    wide = ("name," + ",".join(["x"] * ingest.MAX_ROW_CELLS)).encode()
    with pytest.raises(IngestError, match="wider than"):
        ingest._csv_grid(wide)
    tall = ("name\n" + "r\n" * (ingest.MAX_TOTAL_ROWS + 1)).encode()
    with pytest.raises(IngestError, match="overall limit"):
        ingest._csv_grid(tall)


# --- Phase 6: widened header/sheet/platform synonym sets ---

def test_splunk_style_headers_detected():
    content = _xlsx([
        ["Correlation Search Name", "ATT&CK ID", "SPL Query", "Objective", "Deployment Status", "Source Type"],
        ["Encoded PowerShell", "T1059.001", "| tstats ...", "catch encodedcommand", "Enabled", "wineventlog"],
    ])
    parsed = parse_use_case_file(content, "xlsx")
    assert set(parsed["columns"]) == {"name", "tags", "logic", "description", "enabled", "log_source"}
    row = parsed["rows"][0]
    assert row["name"] == "Encoded PowerShell"
    assert row["tags"] == ["T1059.001"]
    assert row["enabled"] is True
    assert row["log_source"] == "wineventlog"


def test_sentinel_style_headers_detected():
    content = _xlsx([
        ["Analytic Name", "MITRE_TTP", "KQL Query", "Is_Enabled", "Log_Type"],
        ["OAuth consent grant", "T1528", "AuditLogs | where ...", "true", "AuditLogs"],
    ])
    parsed = parse_use_case_file(content, "xlsx")
    assert set(parsed["columns"]) == {"name", "tags", "logic", "enabled", "log_source"}
    assert parsed["rows"][0]["tags"] == ["T1528"]
    assert parsed["rows"][0]["enabled"] is True


def test_widened_environment_sheet_and_platform_synonyms():
    content = _xlsx(
        [["Asset"], ["Palo Alto firewalls"], ["SUSE Linux estate"], ["AKS clusters"],
         ["Duo MFA"], ["iPadOS tablets"], ["Modbus PLC network"]],
        sheet_name="Asset List",
        extra_sheets=[
            ("SIEM Sources", [["Source"], ["Sysmon"]]),
            ("Security Products", [["Tool"], ["CrowdStrike"]]),
            ("High Value Assets", [["Item"], ["Payment gateway"]]),
        ],
    )
    parsed = parse_environment_file(content, "xlsx")
    assert set(parsed["sheets_found"]) == {"assets", "log_sources", "tooling", "crown_jewels"}
    env = parsed["environment"]
    assert set(env["platforms"]) == {
        "Network Devices", "Linux", "Containers", "Identity Provider", "iOS",
    }
    assert env["has_managed_mobile"] is True   # iPadOS fleet
    assert env["has_ics_assets"] is True       # Modbus marker
    assert parsed["tooling"] == ["CrowdStrike"]
    assert parsed["crown_jewels"] == ["Payment gateway"]

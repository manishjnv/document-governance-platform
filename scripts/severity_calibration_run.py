"""Legal severity calibration: run LegalReviewer over the real sample set and
build the SME worksheet pack.

    python scripts/severity_calibration_run.py --run     # calls OpenRouter, writes raw/*.json
    python scripts/severity_calibration_run.py --build   # builds the XLSX from raw/*.json
    python scripts/severity_calibration_run.py           # both

OPENROUTER_API_KEY must be the ScopeWise key (the one in the VPS .env), never
the personal tooling key -- see memory `openrouter-key-identity`. Inject it
per-process; this script never prints it. No product code is modified: the
agent's OpenRouter adapter is wrapped at runtime only to capture usage and
the generation id for cost lookup.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))
os.chdir(API)  # settings reads apps/api/.env when present

OUT = ROOT / "docs" / "planning" / "severity_calibration"
RAW = OUT / "raw"
SAMPLE = ROOT / "docs" / "sample"

# (path, document_type, why it is in the set)
DOCS = [
    (SAMPLE / "Real_Federal_Contracts" / "USCIS_70SBUR18C00000017.pdf", "SOW", "Real awarded US federal contract (USCIS reading room), Work Statement pp. 3-14"),
    (SAMPLE / "Real_Federal_Contracts" / "USCIS_70SBUR19P00000128.pdf", "SOW", "Real awarded US federal contract (USCIS reading room)"),
    (SAMPLE / "Real_Federal_Contracts" / "USCIS_HSHQDC-13-D-E2075.pdf", "SOW", "Real IDIQ / unified services contract (USCIS reading room)"),
    (SAMPLE / "Real_Federal_Contracts" / "USCIS_HSSCCG-05-Q-0020.pdf", "RFP", "Real RFQ (USCIS reading room) -- exercises the RFP prompt branch"),
    (SAMPLE / "SOW_Sample" / "SOC_SOW_Testing.docx", "SOW", "Commercial-style SOC services SOW; has the 29-row hand-labeled ground truth"),
    (SAMPLE / "SOW_Sample" / "aws_examples_sows.pdf", "SOW", "Public AWS example SOWs (commercial, non-customer)"),
]

SEVERITY_RANK = {"critical": 4, "major": 3, "medium": 2, "low": 1, "info": 0}
PENALTY = {"critical": 25, "major": 15, "medium": 8, "low": 4, "info": 0}


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()


# ---------------------------------------------------------------- run ------

async def _review_one(path: Path, doc_type: str, key: str) -> dict:
    import httpx

    from app.ai import agent as agent_mod
    from app.parser import parse_document

    parsed = await parse_document(path.read_bytes(), path.suffix.lstrip("."))
    if parsed.status == "failed" or len(parsed.raw_text) < 500:
        return {"document": path.name, "error": f"parse {parsed.status}: {parsed.error_message}", "findings": []}

    captured: list[dict] = []
    orig_create = agent_mod._OpenRouterMessages.create

    def create(self, model, max_tokens, temperature, system, messages):
        resp = self._client.chat.completions.create(
            model=model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "system", "content": system}, *messages],
        )
        u = getattr(resp, "usage", None)
        captured.append({
            "id": resp.id, "model": resp.model,
            "prompt_tokens": getattr(u, "prompt_tokens", None),
            "completion_tokens": getattr(u, "completion_tokens", None),
        })
        return agent_mod._OpenRouterMessage(resp.choices[0].message.content)

    agent_mod._OpenRouterMessages.create = create  # runtime wrap only; restored below
    try:
        reviewer = agent_mod.LegalReviewer()
        await reviewer.initialize()
        result = await reviewer.review(parsed.raw_text, doc_type)
    finally:
        agent_mod._OpenRouterMessages.create = orig_create

    # cost per generation from OpenRouter's generation endpoint (needs a moment to settle)
    async with httpx.AsyncClient(timeout=30) as client:
        for c in captured:
            for _ in range(5):
                r = await client.get("https://openrouter.ai/api/v1/generation", params={"id": c["id"]},
                                     headers={"Authorization": f"Bearer {key}"})
                if r.status_code == 200:
                    d = r.json().get("data", {})
                    c["cost_usd"] = d.get("total_cost")
                    c["native_tokens_prompt"] = d.get("native_tokens_prompt")
                    c["native_tokens_completion"] = d.get("native_tokens_completion")
                    break
                await asyncio.sleep(2)

    findings = result.get("findings", []) if isinstance(result, dict) else []
    for i, f in enumerate(findings, 1):
        f["_anchor"] = _anchor(f.get("evidence") or "", parsed)
    return {
        "document": path.name, "document_type": doc_type, "path": str(path.relative_to(ROOT)),
        "parse": {"status": parsed.status, "chars": len(parsed.raw_text), "pages": parsed.page_count, "sections": len(parsed.sections)},
        "model_used": result.get("_model_used") if isinstance(result, dict) else None,
        "calls": captured,
        "cost_usd": sum((c.get("cost_usd") or 0) for c in captured),
        "overall_confidence": result.get("overall_confidence") if isinstance(result, dict) else None,
        "legal_terms": result.get("legal_terms") if isinstance(result, dict) else None,
        "findings": findings,
        "raw_response": result.get("raw_response") if isinstance(result, dict) else None,
    }


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _anchor(evidence: str, parsed) -> dict:
    """Locate the quoted evidence in the parsed sections -> heading + page.
    Uses the first 60 normalised characters; falls back to a 25-char probe."""
    ev = _norm(evidence)
    if not ev:
        return {"section": None, "page": None, "located": False}
    for probe in (ev[:60], ev[:25]):
        if len(probe) < 12:
            continue
        for s in parsed.sections:
            if probe in _norm(s.content) or probe in _norm(s.heading):
                return {"section": s.heading[:120], "page": s.page_number, "located": True}
        pos = _norm(parsed.raw_text).find(probe)
        if pos >= 0 and parsed.page_count:
            page = int(pos / max(1, len(parsed.raw_text)) * parsed.page_count) + 1
            return {"section": None, "page": page, "located": True, "page_estimated": True}
    return {"section": None, "page": None, "located": False}


async def run_all(key: str) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(3)

    async def one(path, doc_type, why):
        async with sem:
            print(f"reviewing {path.name} ({doc_type}) ...", flush=True)
            res = await _review_one(path, doc_type, key)
            res["why_in_set"] = why
            res["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="minutes")
            res["git_sha"] = git_sha()
            (RAW / f"{path.stem}.legal.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
            print(f"  {path.name}: {len(res['findings'])} findings, model {res.get('model_used')}, ${res.get('cost_usd', 0):.4f}", flush=True)

    await asyncio.gather(*(one(*d) for d in DOCS))


# -------------------------------------------------------------- build ------

def build_pack() -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    from app.mitre.report_xlsx import _guard  # reuse the house formula-injection guard

    BRAND = "0057B8"
    white_bold = Font(bold=True, color="FFFFFF")
    thin = Side(style="thin", color="D0D7E2")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    sev_fill = {"critical": "F8D7DA", "major": "FDE2C8", "medium": "FFF3CD", "low": "E2F0D9", "info": "EEF2F7"}

    raws = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RAW.glob("*.legal.json"))]
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sha = raws[0]["git_sha"] if raws else git_sha()
    models = sorted({r.get("model_used") or "?" for r in raws})
    total_cost = sum(r.get("cost_usd") or 0 for r in raws)

    wb = Workbook()

    def sheet(title, headers, widths, first=False):
        ws = wb.active if first else wb.create_sheet()
        ws.title = title
        ws.append([_guard(h) for h in headers])
        for c in ws[1]:
            c.font, c.fill, c.border = white_bold, PatternFill("solid", fgColor=BRAND), border
            c.alignment = Alignment(vertical="center", wrap_text=True)
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A2"
        return ws

    # --- Read Me
    rm = wb.active
    rm.title = "Read Me"
    rm.column_dimensions["A"].width = 110
    lines = [
        ("Legal severity calibration -- SME worksheet", True),
        (f"Generated {date} from git {sha}; LegalReviewer model(s) per audit trail: {', '.join(models)}; via OpenRouter; total spend ${total_cost:.4f}.", False),
        ("", False),
        ("WHAT THIS IS", True),
        ("Every finding the LegalReviewer agent produced on six real (non-synthetic, non-customer) documents, with the severity it assigned. You rate each one; the Findings sheet is the only sheet you need to edit.", False),
        ("", False),
        ("THE 30-MINUTE PROCEDURE", True),
        ("1. Open the Findings sheet. Work top to bottom; each row is one finding with its quoted evidence, section and page.", False),
        ("2. In column 'SME severity' pick critical / major / medium / low / info (dropdown). 'info' means: not a risk worth a finding.", False),
        ("3. Column 'Agree?' is Yes if your rating equals the system's, otherwise No (dropdown). If you think the finding itself is wrong (not a real issue), pick 'Not a finding'.", False),
        ("4. Comment only where you disagree, one line: why the system is too high or too low.", False),
        ("5. Question A (answer on this sheet, cell A24): the RFQ document has no executed terms yet. Should missing legal-term DISCLOSURE in an RFP be one tier below the same gap in an unsigned SOW? Yes / No / Depends (say on what).", False),
        ("6. Question B (cell A26): SCORING_METHODOLOGY.md defines no per-level meaning for the four labels. In one line each, what should critical / major / medium / low mean for a contract finding?", False),
        ("7. Save as-is (same file name) and send it back. A script reads it; do not add or reorder columns.", False),
        ("", False),
        ("HOW THE SYSTEM USES SEVERITY (verbatim from docs/planning/SCORING_METHODOLOGY.md, 'Finding Severity')", True),
        ("What it measures: how serious the reviewing agent (or rule) judged a single finding to be.", False),
        ("Honest status: this is the weakest-grounded part of the system today. Severity is assigned by LLM judgment with no external validation yet -- tracked as an open item in docs/planning/LEGAL_SEVERITY_CALIBRATION.md, which needs a legal SME to compare the system's severity judgments against real risk assessment before it can be trusted at face value. Until that sign-off lands, treat severity labels as a reasonable first pass, not a certified rating.", False),
        ("The risk-model weights and the finding-severity scoring penalties intentionally use the same relative ordering (critical > major > medium > low) so severity means the same thing everywhere in the product, even while the underlying severity judgment itself is still pending calibration.", False),
        ("Operational meaning today (score points a finding removes from its category): critical -25, major -15, medium -8, low -4, info 0. So one 'critical' legal finding is the difference between a green and a yellow category.", False),
        ("", False),
        ("Note: the four labels have no written per-level definition anywhere in the repo. That is deliberate honesty, not an omission of this pack; Question B asks you to supply them.", False),
        ("", False),
        ("Question A answer:", True),
        ("", False),
        ("Question B answer:", True),
        ("", False),
    ]
    for text, bold in lines:
        rm.append([text])
        cell = rm.cell(row=rm.max_row, column=1)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        if bold:
            cell.font = Font(bold=True, size=12 if rm.max_row == 1 else 11)

    # --- Documents
    ds = sheet("Documents", ["Document", "Type", "Why it is in the set", "Pages", "Chars parsed", "Findings", "Model used", "Cost (USD)"], [40, 8, 70, 8, 12, 10, 26, 12])
    for r in raws:
        ds.append([_guard(r["document"]), r.get("document_type"), _guard(r.get("why_in_set", "")), r.get("parse", {}).get("pages"), r.get("parse", {}).get("chars"), len(r["findings"]), r.get("model_used"), round(r.get("cost_usd") or 0, 4)])

    # --- Findings
    headers = ["ID", "Document", "Doc type", "Finding type", "System severity", "Confidence", "Evidence (quoted)", "Description", "Recommendation", "Section", "Page", "SME severity", "Agree?", "SME comment"]
    fs = sheet("Findings", headers, [7, 30, 8, 30, 14, 11, 60, 50, 45, 30, 7, 14, 14, 50])
    dv_sev = DataValidation(type="list", formula1='"critical,major,medium,low,info"', allow_blank=True)
    dv_agree = DataValidation(type="list", formula1='"Yes,No,Not a finding"', allow_blank=True)
    fs.add_data_validation(dv_sev); fs.add_data_validation(dv_agree)
    n = 0
    for r in raws:
        for f in r["findings"]:
            n += 1
            a = f.get("_anchor", {})
            sev = str(f.get("severity", "")).lower()
            page = a.get("page")
            page_txt = f"~{page}" if page and a.get("page_estimated") else page
            fs.append([f"L{n:03d}", _guard(r["document"]), r.get("document_type"), _guard(f.get("type", "")), sev,
                       f.get("confidence"), _guard(f.get("evidence", "")), _guard(f.get("description", "")), _guard(f.get("recommendation", "")),
                       _guard(a.get("section") or ("not located" if not a.get("located") else "")), page_txt, None, None, None])
            row = fs.max_row
            for c in fs[row]:
                c.alignment = Alignment(wrap_text=True, vertical="top"); c.border = border
            if sev in sev_fill:
                fs.cell(row=row, column=5).fill = PatternFill("solid", fgColor=sev_fill[sev])
            for col in (12, 13, 14):
                fs.cell(row=row, column=col).fill = PatternFill("solid", fgColor="FFFBE6")
    if n:
        dv_sev.add(f"L2:L{n + 1}"); dv_agree.add(f"M2:M{n + 1}")
    fs.auto_filter.ref = f"A1:N{max(n + 1, 2)}"

    # --- Summary (severity distribution per document + per finding type)
    sm = sheet("Summary", ["Document", "critical", "major", "medium", "low", "info", "Total", "Weighted penalty pts"], [40, 10, 10, 10, 10, 10, 8, 20])
    for r in raws:
        counts = {k: 0 for k in SEVERITY_RANK}
        for f in r["findings"]:
            counts[str(f.get("severity", "")).lower()] = counts.get(str(f.get("severity", "")).lower(), 0) + 1
        sm.append([_guard(r["document"]), counts["critical"], counts["major"], counts["medium"], counts["low"], counts["info"], len(r["findings"]), sum(PENALTY.get(k, 0) * v for k, v in counts.items())])
    sm.append([])
    sm.append(["Finding type", "critical", "major", "medium", "low", "info", "Total", "Typical (mode)"])
    for c in sm[sm.max_row]:
        c.font = white_bold; c.fill = PatternFill("solid", fgColor=BRAND)
    by_type: dict[str, dict] = {}
    for r in raws:
        for f in r["findings"]:
            t = f.get("type", "?"); s = str(f.get("severity", "")).lower()
            by_type.setdefault(t, {k: 0 for k in SEVERITY_RANK})
            by_type[t][s] = by_type[t].get(s, 0) + 1
    for t, counts in sorted(by_type.items()):
        total = sum(counts.values())
        mode = max(counts, key=lambda k: (counts[k], SEVERITY_RANK[k]))
        sm.append([_guard(t), counts["critical"], counts["major"], counts["medium"], counts["low"], counts["info"], total, mode])

    wb.properties.creator = "ScopeWise"
    wb.properties.title = "Legal severity calibration -- SME worksheet"
    out = OUT / f"LEGAL_SEVERITY_SME_PACK_{date}.xlsx"
    wb.save(out)
    print(f"wrote {out} ({n} findings across {len(raws)} documents, ${total_cost:.4f})")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--build", action="store_true")
    args = ap.parse_args()
    do_run = args.run or not (args.run or args.build)
    do_build = args.build or not (args.run or args.build)
    if do_run:
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            sys.exit("OPENROUTER_API_KEY not set (inject the ScopeWise key per-process)")
        asyncio.run(run_all(key))
    if do_build:
        build_pack()

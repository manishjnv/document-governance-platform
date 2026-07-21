"""Report generation for document governance.

T-610: Executive summary generator
T-611: Scorecard section with 7 category scores
T-612: Risk heatmap visual
T-616: HTML report template
T-617: PDF export
"""

import logging
from datetime import datetime
from html import escape

from app.scoring.algorithm import CATEGORY_GUIDANCE

logger = logging.getLogger(__name__)

BRAND_BLUE = "#0057B8"
BRAND_BLUE_DARK = "#003D82"


def _esc(value) -> str:
    """Escape before interpolating into the report HTML -- findings and
    filenames come from uploaded documents/agent output, not from us, so
    treat them as untrusted (stored-XSS risk otherwise: a malicious
    filename or clause quoted verbatim as `evidence` would otherwise
    execute in any org member's browser who opens this report)."""
    return escape(str(value)) if value is not None else ""


class ReportGenerator:
    """Generate HTML and PDF reports from scoring results."""

    async def generate_html_report(
        self,
        doc_id: str,
        filename: str,
        scoring_result,
        review_findings: list,
        doc_meta: dict | None = None,
        findings_count: dict | None = None,
        sections: list | None = None,
        rule_gaps: list | None = None,
    ) -> str:
        """
        T-616: Generate HTML report template.

        Returns HTML string with all sections: header/stats, executive
        summary, scorecard, document X-ray, findings, risk heatmap.

        doc_meta: document_type/version/page_count/project_name/reviewed_at
        for the stats strip. findings_count: severity -> count. sections:
        doc.parsed_sections (Document X-ray "sections found"). rule_gaps:
        findings with finding_source == "rule" (Document X-ray "gaps").
        All optional so an old caller without the new context still gets a
        report, just without those sections.
        """
        logger.info(f"Generating HTML report for {doc_id}")

        html = self._build_html_skeleton(doc_id, filename, doc_meta or {})
        html += self._build_executive_summary(scoring_result, findings_count or {})
        html += self._build_scorecard(scoring_result)
        html += self._build_document_xray(sections or [], rule_gaps or [])
        html += self._build_findings_section(review_findings)
        html += self._build_risk_heatmap(scoring_result)
        html += self._build_footer()

        return html

    def _build_html_skeleton(self, doc_id: str, filename: str, doc_meta: dict) -> str:
        """T-616: HTML skeleton with styles + branded header/stats strip."""
        stats = [
            ("Document Type", doc_meta.get("document_type")),
            ("Version", f"v{doc_meta['version']}" if doc_meta.get("version") else None),
            ("Pages", doc_meta.get("page_count")),
            ("Project", doc_meta.get("project_name")),
            ("Reviewed", doc_meta.get("reviewed_at")),
        ]
        stats_html = "".join(
            f'<div class="stat"><span class="stat-label">{_esc(label)}</span>'
            f'<span class="stat-value">{_esc(value)}</span></div>'
            for label, value in stats
            if value
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Review Report - {_esc(filename)}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}

        .container {{
            max-width: 900px;
            margin: 20px auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        .header {{
            background: {BRAND_BLUE};
            color: white;
            padding: 32px 40px;
        }}

        .header .brand {{
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            opacity: 0.85;
            margin-bottom: 14px;
        }}

        .header h1 {{
            font-size: 26px;
            word-break: break-word;
        }}

        .header p {{
            font-size: 13px;
            opacity: 0.85;
            margin-top: 4px;
        }}

        .stats-strip {{
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            margin-top: 20px;
            padding-top: 16px;
            border-top: 1px solid rgba(255,255,255,0.25);
        }}

        .stat {{
            display: flex;
            flex-direction: column;
        }}

        .stat-label {{
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            opacity: 0.75;
        }}

        .stat-value {{
            font-size: 14px;
            font-weight: 600;
        }}

        .content {{
            padding: 40px;
        }}

        section {{
            margin-bottom: 40px;
        }}

        section h2 {{
            font-size: 24px;
            border-bottom: 3px solid {BRAND_BLUE};
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}

        .summary-box {{
            background: #eef4fc;
            border-left: 4px solid {BRAND_BLUE};
            padding: 20px;
            border-radius: 4px;
            margin-bottom: 20px;
        }}

        .findings-count-strip {{
            display: flex;
            gap: 12px;
            margin: 16px 0;
        }}

        .count-tile {{
            flex: 1;
            text-align: center;
            padding: 10px;
            border-radius: 6px;
            background: #f9f9f9;
            border: 1px solid #e0e0e0;
        }}

        .count-tile .n {{
            font-size: 22px;
            font-weight: bold;
        }}

        .count-tile .label {{
            font-size: 11px;
            text-transform: uppercase;
            color: #666;
        }}

        .top-risks {{
            margin-top: 16px;
        }}

        .top-risks ul {{
            margin-left: 20px;
            margin-top: 8px;
        }}

        .score-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .score-card {{
            background: #f9f9f9;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}

        .score-card h3 {{
            font-size: 14px;
            text-transform: uppercase;
            color: #666;
            margin-bottom: 10px;
        }}

        .score-value {{
            font-size: 36px;
            font-weight: bold;
            margin: 10px 0;
        }}

        .score-value.green {{
            color: #27ae60;
        }}

        .score-value.yellow {{
            color: #f39c12;
        }}

        .score-value.red {{
            color: #e74c3c;
        }}

        .score-guidance {{
            font-size: 12px;
            color: #555;
            margin-top: 8px;
            text-align: left;
        }}

        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 10px;
        }}

        .progress-fill {{
            height: 100%;
            border-radius: 4px;
        }}

        .progress-fill.green {{
            background: #27ae60;
        }}

        .progress-fill.yellow {{
            background: #f39c12;
        }}

        .progress-fill.red {{
            background: #e74c3c;
        }}

        .xray-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-top: 16px;
        }}

        .xray-grid h4 {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #666;
            margin-bottom: 8px;
        }}

        .xray-grid ul {{
            list-style: none;
            font-size: 13px;
        }}

        .xray-grid li {{
            padding: 4px 0;
            border-bottom: 1px solid #eee;
        }}

        .xray-grid li.gap {{
            color: #c0392b;
        }}

        .findings-list {{
            list-style: none;
        }}

        .finding {{
            background: #fafafa;
            border-left: 4px solid #e74c3c;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 4px;
        }}

        .finding.critical {{
            border-left-color: #e74c3c;
            background: #ffe5e5;
        }}

        .finding.major {{
            border-left-color: #f39c12;
            background: #fff5e5;
        }}

        .finding.medium {{
            border-left-color: #3498db;
            background: #e5f2ff;
        }}

        .finding.low {{
            border-left-color: #27ae60;
            background: #e5ffe5;
        }}

        .finding-title {{
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .finding-location {{
            display: inline-block;
            font-size: 11px;
            font-weight: 600;
            color: {BRAND_BLUE_DARK};
            background: rgba(0,87,184,0.08);
            padding: 2px 8px;
            border-radius: 10px;
            margin-bottom: 8px;
        }}

        .finding-desc {{
            font-size: 14px;
            margin-bottom: 5px;
        }}

        .finding-rec {{
            font-size: 12px;
            color: #666;
            font-style: italic;
        }}

        .heatmap {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 10px;
            margin-top: 20px;
        }}

        .heatmap-cell {{
            text-align: center;
            padding: 15px;
            border-radius: 4px;
            color: white;
            font-weight: bold;
        }}

        .heatmap-cell.green {{
            background: #27ae60;
        }}

        .heatmap-cell.yellow {{
            background: #f39c12;
        }}

        .heatmap-cell.red {{
            background: #e74c3c;
        }}

        .footer {{
            background: #f5f5f5;
            padding: 20px 40px;
            text-align: center;
            font-size: 12px;
            color: #666;
            border-top: 1px solid #e0e0e0;
        }}

        .footer-text {{
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="brand">ScopeWise</div>
            <h1>{_esc(filename)}</h1>
            <p>Document Review Report &middot; Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            {f'<div class="stats-strip">{stats_html}</div>' if stats_html else ''}
        </div>
        <div class="content">
"""

    def _build_executive_summary(self, scoring_result, findings_count: dict) -> str:
        """T-610: Executive summary -- score, risk, narrative summary, a
        findings-count strip, top risk areas (from risk_breakdown), and
        recommended next steps -- all in one pass (previously split across
        two methods that callers had to remember to both invoke, and the
        PDF export path didn't, silently dropping next steps from PDFs)."""
        overall_score = scoring_result.overall_score
        risk_score = scoring_result.risk_score

        score_status = "green" if overall_score >= 80 else ("yellow" if overall_score >= 60 else "red")
        risk_status = "red" if risk_score > 70 else ("yellow" if risk_score > 40 else "green")

        count_tiles = "".join(
            f'<div class="count-tile"><div class="n">{findings_count.get(sev, 0)}</div>'
            f'<div class="label">{sev}</div></div>'
            for sev in ("critical", "major", "medium", "low", "info")
        )

        top_risks = sorted(
            (scoring_result.risk_breakdown or {}).items(), key=lambda kv: kv[1], reverse=True
        )[:3]
        top_risks_html = ""
        if top_risks:
            items = "".join(f"<li>{_esc(axis)} -- {score:.0f}%</li>" for axis, score in top_risks)
            top_risks_html = f"""
                <div class="top-risks">
                    <h3>Top Risk Areas:</h3>
                    <ul>{items}</ul>
                </div>
"""

        steps_html = "".join(
            f"                        <li style='margin-bottom: 8px;'>{_esc(step)}</li>\n"
            for step in scoring_result.next_steps
        )

        return f"""
            <section>
                <h2>Executive Summary</h2>
                <div class="summary-box">
                    <p><strong>Overall Score:</strong> <span class="score-value {score_status}">{overall_score:.0f}/100</span></p>
                    <p><strong>Risk Level:</strong> <span class="score-value {risk_status}">{risk_score:.0f}%</span></p>
                    <p style="margin-top: 15px;">{_esc(scoring_result.summary)}</p>
                </div>
                <div class="findings-count-strip">{count_tiles}</div>
                {top_risks_html}
                <div>
                    <h3>Recommended Next Steps:</h3>
                    <ul style="margin-left: 20px; margin-top: 10px;">
{steps_html}
                    </ul>
                </div>
            </section>
"""

    def _build_scorecard(self, scoring_result) -> str:
        """T-611: Scorecard with 7 category scores + a one-line, actionable
        guidance per category so a reader knows what to fix, not just the
        number. Green categories get an affirmative note instead of a
        generic "add more" nudge."""
        html = """
            <section>
                <h2>Scorecard</h2>
                <div class="score-grid">
"""

        for category_name, category_score in scoring_result.category_scores.items():
            score = category_score.score
            status = category_score.status
            progress_pct = int(score)

            if status == "green":
                guidance = "On track -- no major gaps found in this area."
            else:
                guidance = CATEGORY_GUIDANCE.get(category_name, "Review this area for gaps.")
                matched = len(category_score.findings or [])
                if matched:
                    guidance += f" ({matched} related finding{'s' if matched != 1 else ''})"

            html += f"""
                    <div class="score-card">
                        <h3>{_esc(category_name)}</h3>
                        <div class="progress-bar">
                            <div class="progress-fill {status}" style="width: {progress_pct}%"></div>
                        </div>
                        <div class="score-value {status}">{score:.0f}</div>
                        <p style="font-size: 12px; color: #666;">of {category_score.max_points}</p>
                        <p class="score-guidance">{_esc(guidance)}</p>
                    </div>
"""

        html += """
                </div>
            </section>
"""
        return html

    def _build_document_xray(self, sections: list, rule_gaps: list) -> str:
        """Document sections found + rule-engine gaps, at a glance -- the
        same "Document X-Ray" view already shown on the results page,
        added here since a downloaded report is the one artifact meant to
        stand on its own without the app open next to it."""
        if not sections and not rule_gaps:
            return ""

        section_items = "".join(
            f"<li>{_esc(s.get('heading', 'Untitled section'))}</li>" for s in sections
        ) or "<li>No sections detected.</li>"

        gap_items = "".join(
            f"<li class='gap'>{_esc(g.get('title') or g.get('description', 'Gap'))}</li>"
            for g in rule_gaps
        ) or "<li>None -- passes all rule checks.</li>"

        return f"""
            <section>
                <h2>Document X-Ray</h2>
                <div class="xray-grid">
                    <div>
                        <h4>Sections Found ({len(sections)})</h4>
                        <ul>{section_items}</ul>
                    </div>
                    <div>
                        <h4>Gaps Detected ({len(rule_gaps)})</h4>
                        <ul>{gap_items}</ul>
                    </div>
                </div>
            </section>
"""

    def _build_findings_section(self, findings: list) -> str:
        """Build findings section, tagged with section name + page number
        (finding["section_ref"], e.g. "Payment Terms (p.4)") so a reader
        can find the clause in the source document without re-searching."""
        if not findings:
            return """
            <section>
                <h2>Findings</h2>
                <p>No findings reported.</p>
            </section>
"""

        html = """
            <section>
                <h2>Findings</h2>
                <ul class="findings-list">
"""

        for finding in findings:
            severity = finding.get("severity", "medium").lower()
            title = finding.get("title") or finding.get("description", "Finding")
            description = finding.get("description", "")
            recommendation = finding.get("recommendation", "")
            evidence = finding.get("evidence", "")
            section_ref = finding.get("section_ref", "")

            html += f"""
                    <li class="finding {severity}">
"""
            if section_ref:
                html += f'                        <div class="finding-location">&#128205; {_esc(section_ref)}</div>\n'

            html += f'                        <div class="finding-title">[{_esc(severity.upper())}] {_esc(title)}</div>\n'

            if description:
                html += f'                        <div class="finding-desc">{_esc(description)}</div>\n'

            if evidence:
                html += f'                        <div class="finding-desc"><strong>Evidence:</strong> {_esc(evidence)}</div>\n'

            if recommendation:
                html += f'                        <div class="finding-rec"><strong>Recommendation:</strong> {_esc(recommendation)}</div>\n'

            html += "                    </li>\n"

        html += """
                </ul>
            </section>
"""
        return html

    def _build_risk_heatmap(self, scoring_result) -> str:
        """T-612: Risk heatmap visual."""
        html = """
            <section>
                <h2>Risk Heatmap</h2>
                <p>Category-by-category risk assessment:</p>
                <div class="heatmap">
"""

        for category_name, category_score in scoring_result.category_scores.items():
            status = category_score.status
            score = int(category_score.score)

            html += f"""
                    <div class="heatmap-cell {status}">
                        <div>{_esc(category_name.title())}</div>
                        <div style="font-size: 18px; margin-top: 5px;">{score}</div>
                    </div>
"""

        html += """
                </div>
            </section>
"""
        return html

    def _build_footer(self) -> str:
        """Build footer."""
        return """
        </div>
        <div class="footer">
            <div class="footer-text">
                ScopeWise -- Document Governance Platform
            </div>
            <div class="footer-text">
                This report was automatically generated by ScopeWise.
            </div>
        </div>
    </div>
</body>
</html>
"""

    async def generate_pdf_report(
        self,
        html_content: str,
        filename: str,
    ) -> bytes:
        """
        T-617: PDF export.

        xhtml2pdf (pure Python, wraps reportlab -- no system libs like
        weasyprint's Pango/Cairo needed) renders the SAME html_content the
        HTML report already produces.

        xhtml2pdf's CSS support doesn't include Grid/Flexbox (used by
        `.score-grid`/`.heatmap`/`.xray-grid` in the HTML template) --
        those sections degrade to stacked blocks in the PDF rather than a
        grid layout. Content and data are unaffected; only that specific
        visual layout.
        """
        import io

        from xhtml2pdf import pisa

        logger.info(f"PDF export requested for {filename}")

        output = io.BytesIO()
        result = pisa.CreatePDF(src=html_content, dest=output)

        if result.err:
            logger.error(f"PDF generation failed for {filename}: {result.err} error(s)")
            raise RuntimeError(f"PDF generation failed with {result.err} error(s)")

        return output.getvalue()

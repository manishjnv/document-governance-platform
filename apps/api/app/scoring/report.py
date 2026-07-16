"""Report generation for document governance.

T-610: Executive summary generator
T-611: Scorecard section with 7 category scores
T-612: Risk heatmap visual
T-616: HTML report template
T-617: PDF export (placeholder)
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate HTML and PDF reports from scoring results."""

    async def generate_html_report(
        self,
        doc_id: str,
        filename: str,
        scoring_result,
        review_findings: list,
    ) -> str:
        """
        T-616: Generate HTML report template.

        Returns HTML string with all sections: executive summary, scorecard, findings, risk heatmap.
        """
        logger.info(f"Generating HTML report for {doc_id}")

        # Build HTML
        html = self._build_html_skeleton(doc_id, filename)
        html += self._build_executive_summary(scoring_result)
        html += self._build_scorecard(scoring_result)
        html += self._build_findings_section(review_findings)
        html += self._build_risk_heatmap(scoring_result)
        html += self._build_footer()

        return html

    def _build_html_skeleton(self, doc_id: str, filename: str) -> str:
        """T-616: HTML skeleton with styles."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Review Report - {filename}</title>
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}

        .header p {{
            font-size: 16px;
            opacity: 0.9;
        }}

        .content {{
            padding: 40px;
        }}

        section {{
            margin-bottom: 40px;
        }}

        section h2 {{
            font-size: 24px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}

        .summary-box {{
            background: #f0f4ff;
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 4px;
            margin-bottom: 20px;
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
            transition: all 0.3s ease;
        }}

        .score-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border-color: #667eea;
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
            transition: width 0.3s ease;
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
            <h1>Document Review Report</h1>
            <p>{filename}</p>
            <p style="font-size: 12px; margin-top: 10px;">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <div class="content">
"""

    def _build_executive_summary(self, scoring_result) -> str:
        """T-610: Executive summary section."""
        overall_score = scoring_result.overall_score
        risk_score = scoring_result.risk_score

        score_status = "green" if overall_score >= 80 else ("yellow" if overall_score >= 60 else "red")
        risk_status = "red" if risk_score > 70 else ("yellow" if risk_score > 40 else "green")

        return f"""
            <section>
                <h2>Executive Summary</h2>
                <div class="summary-box">
                    <p><strong>Overall Score:</strong> <span class="score-value {score_status}">{overall_score}/100</span></p>
                    <p><strong>Risk Level:</strong> <span class="score-value {risk_status}">{risk_score:.0f}%</span></p>
                    <p style="margin-top: 15px;">{scoring_result.summary}</p>
                </div>
                <div>
                    <h3>Recommended Next Steps:</h3>
                    <ul style="margin-left: 20px; margin-top: 10px;">
"""

    def _continue_summary(self, scoring_result) -> str:
        """Continue executive summary with next steps."""
        html = ""
        for step in scoring_result.next_steps:
            html += f"                        <li style='margin-bottom: 8px;'>{step}</li>\n"

        html += """
                    </ul>
                </div>
            </section>
"""
        return html

    def _build_scorecard(self, scoring_result) -> str:
        """T-611: Scorecard with 7 category scores."""
        html = """
            <section>
                <h2>Scorecard</h2>
                <div class="score-grid">
"""

        for category_name, category_score in scoring_result.category_scores.items():
            score = category_score.score
            status = category_score.status
            progress_pct = int(score)

            html += f"""
                    <div class="score-card">
                        <h3>{category_name}</h3>
                        <div class="progress-bar">
                            <div class="progress-fill {status}" style="width: {progress_pct}%"></div>
                        </div>
                        <div class="score-value {status}">{score:.0f}</div>
                        <p style="font-size: 12px; color: #666;">of {category_score.max_points}</p>
                    </div>
"""

        html += """
                </div>
            </section>
"""
        return html

    def _build_findings_section(self, findings: list) -> str:
        """Build findings section."""
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

            html += f"""
                    <li class="finding {severity}">
                        <div class="finding-title">[{severity.upper()}] {title}</div>
"""

            if description:
                html += f"                        <div class=\"finding-desc\">{description}</div>\n"

            if evidence:
                html += f"                        <div class=\"finding-desc\"><strong>Evidence:</strong> {evidence}</div>\n"

            if recommendation:
                html += f"                        <div class=\"finding-rec\"><strong>Recommendation:</strong> {recommendation}</div>\n"

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
                        <div>{category_name.title()}</div>
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
                Enterprise Document Governance Platform (EDGP)
            </div>
            <div class="footer-text">
                This report was automatically generated by the EDGP system.
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
        T-617: PDF export with reportlab/weasyprint.

        For now, returns HTML as bytes. In production, use weasyprint:
        from weasyprint import HTML
        return HTML(string=html_content).write_pdf()
        """
        logger.info(f"PDF export requested for {filename}")
        # Placeholder: in production, use weasyprint or reportlab
        return html_content.encode("utf-8")

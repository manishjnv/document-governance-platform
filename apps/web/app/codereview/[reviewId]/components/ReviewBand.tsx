'use client';

import { KpiTile } from '@/components/app';
import { CodeReviewReport, Severity, deriveHeadline } from '../../lib';

/** Executive band: 5 stat tiles + a derived one-line headline. Matches the
 * MITRE ExecutiveBand tile pattern (tinted number, muted label, tooltip). */
export function ReviewBand({
  report,
  onSelectSeverity,
}: {
  report: CodeReviewReport;
  onSelectSeverity: (severity: Severity) => void;
}) {
  const c = report.counts.by_severity;
  const fp = report.metrics.false_positive_count;
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        <KpiTile label="Total findings" value={report.counts.total} tip="All findings reported for this scan." />
        <KpiTile
          label="Critical"
          value={c.critical ?? 0}
          tone="crit"
          tip="Critical-severity findings. Click to filter the table."
          onClick={() => onSelectSeverity('critical')}
        />
        <KpiTile
          label="High"
          value={c.high ?? 0}
          tone="high"
          tip="High-severity findings. Click to filter the table."
          onClick={() => onSelectSeverity('high')}
        />
        <KpiTile
          label="Exploit chains"
          value={report.chains.length}
          tip="Findings the scanner linked into a multi-step attack path."
        />
        <KpiTile
          label="Verifier false positives"
          value={fp ?? 0}
          tone="grey"
          tip="Findings the AI verifier marked as false positive."
        />
      </div>
      <p className="text-xs text-muted-foreground">{deriveHeadline(report)}</p>
    </div>
  );
}

'use client';

import { KpiTile, type KpiTone } from '@/components/app';
import { CodeReviewReport, FIX_FILTER_ORDER, FixFilter, Severity, deriveHeadline, matchesFix } from '../../lib';

const FIX_TONE: Record<FixFilter, KpiTone> = {
  fixed: 'ok',
  broke_tests: 'crit',
  patch_rejected: 'high',
  needs_review: 'med',
  not_fixed: 'grey',
  not_attempted: 'grey',
};

/** Executive band: 5 stat tiles + a derived one-line headline. Matches the
 * MITRE ExecutiveBand tile pattern (tinted number, muted label, tooltip). */
export function ReviewBand({
  report,
  onSelectSeverity,
  fix,
  onSelectFix,
}: {
  report: CodeReviewReport;
  onSelectSeverity: (severity: Severity) => void;
  /** Fix-status cards, shown for fix-mode scan runs only. */
  fix?: FixFilter | null;
  onSelectFix?: (fix: FixFilter | null) => void;
}) {
  const showFix = report.run_extras?.mode === 'fix' && onSelectFix;
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
      {showFix && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {FIX_FILTER_ORDER.map(({ key, label, tip }) => (
            <KpiTile
              key={key}
              label={label}
              value={report.findings.filter((f) => matchesFix(f, key)).length}
              tone={FIX_TONE[key]}
              tip={`${tip} Click to filter the table.`}
              active={fix === key}
              onClick={() => onSelectFix(fix === key ? null : key)}
            />
          ))}
        </div>
      )}
      <p className="text-xs text-muted-foreground [overflow-wrap:anywhere]">{deriveHeadline(report)}</p>
    </div>
  );
}

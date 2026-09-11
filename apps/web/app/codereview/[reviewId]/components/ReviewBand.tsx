'use client';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { CodeReviewReport, Severity, deriveHeadline } from '../../lib';

function Tile({
  value,
  label,
  tip,
  accent,
  onClick,
}: {
  value: string | number;
  label: string;
  tip: string;
  accent?: string;
  onClick?: () => void;
}) {
  const content = (
    <div className="rounded-md border p-3.5 text-center">
      <div className={cn('text-2xl font-bold leading-tight', accent)}>{value}</div>
      <div className="text-[11px] text-muted-foreground">{label}</div>
    </div>
  );
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        {onClick ? (
          <button
            type="button"
            onClick={onClick}
            className="w-full transition-colors hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md"
          >
            {content}
          </button>
        ) : (
          <div className="cursor-default">{content}</div>
        )}
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">{tip}</TooltipContent>
    </Tooltip>
  );
}

/** Executive band: 5 stat tiles + a derived one-line headline. Copies the
 * MITRE ExecutiveBand tile pattern (tinted number, muted label, tooltip). */
export function ReviewBand({
  report,
  onSelectSeverity,
}: {
  report: CodeReviewReport;
  onSelectSeverity: (severity: Severity) => void;
}) {
  const c = report.counts.by_severity;
  const tp = report.metrics.true_positive_count;
  const fp = report.metrics.false_positive_count;
  return (
    <div className="space-y-1.5">
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
        <Tile value={report.counts.total} label="Total findings" tip="All findings reported for this scan." />
        <Tile
          value={c.critical ?? 0}
          label="Critical"
          accent="text-rose-700"
          tip="Critical-severity findings. Click to filter the table."
          onClick={() => onSelectSeverity('critical')}
        />
        <Tile
          value={c.high ?? 0}
          label="High"
          accent="text-orange-600"
          tip="High-severity findings. Click to filter the table."
          onClick={() => onSelectSeverity('high')}
        />
        <Tile value={report.chains.length} label="Exploit chains" tip="Findings the scanner linked into a multi-step attack path." />
        <Tile
          value={fp ?? 0}
          label="Verifier false positives"
          accent="text-muted-foreground"
          tip="Findings the AI verifier marked as false positive."
        />
      </div>
      <p className="text-xs text-muted-foreground">{deriveHeadline(report)}</p>
    </div>
  );
}

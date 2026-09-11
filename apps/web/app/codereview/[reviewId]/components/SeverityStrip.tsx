'use client';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { CodeReviewFinding, FindingFilter, SEVERITY_META, SEVERITY_ORDER, Severity, filterFindings } from '../../lib';

/** Toggle chip strip for severity. Counts reflect the current search/class/
 * verdict filter (severity key omitted so counts show what selecting each
 * chip would produce). */
export function SeverityStrip({
  findings,
  filter,
  severity,
  onChange,
}: {
  findings: CodeReviewFinding[];
  filter: Omit<FindingFilter, 'severity'>;
  severity: Severity | null;
  onChange: (severity: Severity | null) => void;
}) {
  const base = filterFindings(findings, filter);
  const totalCount = base.length;

  const Chip = ({
    label,
    count,
    active,
    tip,
    onClick,
    chipClass,
  }: {
    label: string;
    count: number;
    active: boolean;
    tip: string;
    onClick: () => void;
    chipClass?: string;
  }) => (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={onClick}
          className={cn(
            'rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors',
            chipClass ?? 'bg-muted text-muted-foreground border-border',
            !active && 'opacity-70',
            active && 'ring-2 ring-primary/40 border-primary'
          )}
        >
          {label} {count}
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">{tip}</TooltipContent>
    </Tooltip>
  );

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <Chip label="All" count={totalCount} active={severity === null} tip="Show every severity." onClick={() => onChange(null)} />
      {SEVERITY_ORDER.map((s) => (
        <Chip
          key={s}
          label={SEVERITY_META[s].label}
          count={base.filter((f) => f.severity === s).length}
          active={severity === s}
          chipClass={SEVERITY_META[s].chip}
          tip={`Show only ${SEVERITY_META[s].label.toLowerCase()}-severity findings.`}
          onClick={() => onChange(severity === s ? null : s)}
        />
      ))}
    </div>
  );
}

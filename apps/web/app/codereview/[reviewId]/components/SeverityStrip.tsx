'use client';

import { Chip, type ChipTone } from '@/components/app';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { CodeReviewFinding, FindingFilter, SEVERITY_META, SEVERITY_ORDER, Severity, filterFindings } from '../../lib';

const SEV_TONE: Record<Severity, ChipTone> = {
  critical: 'crit',
  high: 'high',
  medium: 'med',
  low: 'low',
  info: 'info',
};

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

  const StripChip = ({
    label,
    count,
    active,
    tip,
    tone,
    dot,
    onClick,
  }: {
    label: string;
    count: number;
    active: boolean;
    tip: string;
    tone: ChipTone;
    dot?: boolean;
    onClick: () => void;
  }) => (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={onClick}
          className={cn(
            'rounded-full transition-opacity',
            !active && 'opacity-70 hover:opacity-100',
            active && 'ring-2 ring-primary/40'
          )}
        >
          <Chip tone={tone} dot={dot}>
            {label} {count}
          </Chip>
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">{tip}</TooltipContent>
    </Tooltip>
  );

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <StripChip
        label="All"
        count={totalCount}
        active={severity === null}
        tone="neutral"
        tip="Show every severity."
        onClick={() => onChange(null)}
      />
      {SEVERITY_ORDER.map((s) => (
        <StripChip
          key={s}
          label={SEVERITY_META[s].label}
          count={base.filter((f) => f.severity === s).length}
          active={severity === s}
          tone={SEV_TONE[s]}
          dot
          tip={`Show only ${SEVERITY_META[s].label.toLowerCase()}-severity findings.`}
          onClick={() => onChange(severity === s ? null : s)}
        />
      ))}
    </div>
  );
}

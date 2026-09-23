'use client';

import { Chip, type ChipTone } from '@/components/app';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import {
  CodeReviewFinding,
  FIX_FILTER_ORDER,
  FindingFilter,
  FixFilter,
  SEVERITY_META,
  SEVERITY_ORDER,
  Severity,
  filterFindings,
  matchesFix,
} from '../../lib';

const SEV_TONE: Record<Severity, ChipTone> = {
  critical: 'crit',
  high: 'high',
  medium: 'med',
  low: 'low',
  info: 'info',
};

function StripChip({
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
}) {
  return (
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
}

/** Toggle chip strip for severity. Counts reflect the current search/class/
 * verdict filter (severity key omitted so counts show what selecting each
 * chip would produce). */
export function SeverityStrip({
  findings,
  filter,
  severity,
  onChange,
  fix,
  onFixChange,
}: {
  findings: CodeReviewFinding[];
  filter: Omit<FindingFilter, 'severity'>;
  severity: Severity | null;
  onChange: (severity: Severity | null) => void;
  /** Fix-status chips (fix-mode scan runs only); omit onFixChange to hide them. */
  fix?: FixFilter | null;
  onFixChange?: (fix: FixFilter | null) => void;
}) {
  const base = filterFindings(findings, filter);
  // fix chip counts follow every other filter, severity included, but not the fix filter itself
  const fixBase = filterFindings(findings, { ...filter, severity, fix: null });
  const totalCount = base.length;


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
      {onFixChange && (
        <>
          <span className="mx-1.5 h-4 w-px bg-border" aria-hidden="true" />
          <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Fix</span>
          {FIX_FILTER_ORDER.map(({ key, label, tip }) => (
            <StripChip
              key={key}
              label={label}
              count={fixBase.filter((f) => matchesFix(f, key)).length}
              active={fix === key}
              tone={key === 'broke_tests' ? 'crit' : key === 'fixed' ? 'ok' : key === 'patch_rejected' ? 'high' : key === 'needs_review' ? 'med' : 'neutral'}
              tip={tip}
              onClick={() => onFixChange(fix === key ? null : key)}
            />
          ))}
        </>
      )}
    </div>
  );
}

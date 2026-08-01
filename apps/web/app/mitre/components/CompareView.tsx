'use client';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { AssessmentListItem, CompareEntry, CompareResult, DOMAIN_LABELS, STATE_META, fmtDate } from '../lib';

function DeltaChip({
  value,
  label,
  goodWhenUp,
  suffix = '',
  tip,
}: {
  value: number;
  label: string;
  goodWhenUp: boolean;
  suffix?: string;
  tip: string;
}) {
  const improved = value === 0 ? null : goodWhenUp === value > 0;
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <div className="cursor-default rounded-md bg-muted/40 px-3 py-2 text-center">
          <div
            className={cn(
              'text-lg font-bold leading-tight',
              improved === true && 'text-emerald-600',
              improved === false && 'text-rose-600'
            )}
          >
            {value > 0 ? '▲ +' : value < 0 ? '▼ ' : '— '}
            {value !== 0 && `${value}${suffix}`}
          </div>
          <div className="text-[11px] text-muted-foreground">{label}</div>
        </div>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">{tip}</TooltipContent>
    </Tooltip>
  );
}

function EntryList({
  title,
  blurb,
  entries,
  accent,
  onSelectTechnique,
}: {
  title: string;
  blurb: string;
  entries: CompareEntry[];
  accent: string;
  onSelectTechnique: (techniqueId: string) => void;
}) {
  return (
    <div className="min-w-0 rounded-md bg-muted/30 p-3">
      <Tooltip delayDuration={150}>
        <TooltipTrigger asChild>
          <h4 className={cn('cursor-default text-sm font-semibold', accent)}>
            {title} ({entries.length})
          </h4>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs text-xs">{blurb}</TooltipContent>
      </Tooltip>
      <div className="mt-2 max-h-72 space-y-1 overflow-y-auto pr-1">
        {entries.map((entry) => (
          <button
            key={entry.technique_id}
            type="button"
            onClick={() => onSelectTechnique(entry.technique_id)}
            className="block w-full rounded bg-background px-2 py-1.5 text-left text-xs transition-colors hover:bg-primary/5"
          >
            <span className="font-medium">{entry.technique_id}</span>{' '}
            <span className="text-muted-foreground">{entry.name}</span>
            <span className="mt-0.5 block text-[10px] text-muted-foreground">
              {STATE_META[entry.from]?.label ?? entry.from} → {STATE_META[entry.to]?.label ?? entry.to}
            </span>
          </button>
        ))}
        {entries.length === 0 && <p className="text-xs text-muted-foreground">None.</p>}
      </div>
    </div>
  );
}

/** Trend view between this run and an older completed run. Improvement is
 * MORE coverage: green up-arrows for covered/strict, red for not-covered
 * rising. Fetching happens in the page; this panel is props-only. */
export function CompareView({
  options,
  selectedId,
  onSelect,
  result,
  loading,
  error,
  onSelectTechnique,
}: {
  options: AssessmentListItem[];
  selectedId: string;
  onSelect: (id: string) => void;
  result: CompareResult | null;
  loading: boolean;
  error: string;
  onSelectTechnique: (techniqueId: string) => void;
}) {
  const changedTactics = (result?.tactic_deltas ?? []).filter((t) => t.delta !== 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="compare-with" className="text-sm font-medium">
          Compare with
        </label>
        <select
          id="compare-with"
          value={selectedId}
          onChange={(e) => onSelect(e.target.value)}
          // max-w-full: a select's intrinsic width follows its widest option
          // and would otherwise force horizontal overflow on mobile
          className="max-w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="">Select an earlier completed run…</option>
          {options.map((o) => (
            <option key={o.assessment_id} value={o.assessment_id}>
              {o.name} — {fmtDate(o.completed_at)} ({o.strict_pct}%)
            </option>
          ))}
        </select>
        {loading && <span className="text-xs text-muted-foreground">Comparing…</span>}
      </div>

      {options.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Nothing to compare against yet — run a second assessment later to see your
          coverage trend.
        </p>
      )}
      {error && (
        <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {result && !loading && (
        <>
          <p className="text-xs text-muted-foreground">
            {result.current.name} ({fmtDate(result.current.completed_at)}) vs{' '}
            {result.baseline.name} ({fmtDate(result.baseline.completed_at)})
          </p>
          {result.attack_version_mismatch && (
            <p className="rounded-md bg-amber-50 p-3 text-xs text-amber-800">
              These runs used different ATT&CK versions ({result.current.attack_version} vs{' '}
              {result.baseline.attack_version}) — techniques that exist in only one version
              are left out of this comparison.
            </p>
          )}

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            <DeltaChip value={result.overall_delta.strict_pct ?? 0} label="Coverage %" goodWhenUp suffix=" pts"
              tip="Change in strict coverage percentage since the older run. Up (green) is better." />
            <DeltaChip value={result.overall_delta.weighted_pct ?? 0} label="Weighted %" goodWhenUp suffix=" pts"
              tip="Change in weighted coverage (partial counts as half)." />
            <DeltaChip value={result.overall_delta.covered ?? 0} label="Covered" goodWhenUp
              tip="Change in the number of covered techniques." />
            <DeltaChip value={result.overall_delta.not_covered ?? 0} label="Not covered" goodWhenUp={false}
              tip="Change in the number of uncovered techniques. Down (green) is better." />
            <DeltaChip value={result.overall_delta.not_applicable ?? 0} label="N/A" goodWhenUp={false}
              tip="Change in not-applicable techniques (environment or exclusion changes)." />
          </div>

          <div>
            <h4 className="mb-1 text-sm font-semibold">Tactics that moved</h4>
            {changedTactics.length === 0 ? (
              <p className="text-xs text-muted-foreground">No per-tactic changes.</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {changedTactics
                  .slice()
                  .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
                  .map((t) => (
                    <Tooltip key={`${t.domain}:${t.id}`} delayDuration={150}>
                      <TooltipTrigger asChild>
                        <span
                          className={cn(
                            'cursor-default rounded-full border px-2 py-0.5 text-[11px] font-medium',
                            t.delta > 0
                              ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                              : 'border-rose-200 bg-rose-50 text-rose-800'
                          )}
                        >
                          {t.name} {t.delta > 0 ? '▲' : '▼'} {Math.abs(t.delta)} pts
                        </span>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs text-xs">
                        {DOMAIN_LABELS[t.domain] ?? t.domain} / {t.name}: {t.baseline_strict_pct}% →{' '}
                        {t.current_strict_pct}% strict coverage.
                      </TooltipContent>
                    </Tooltip>
                  ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <EntryList
              title="Newly covered"
              blurb="Techniques you can detect now but couldn't in the older run."
              entries={result.newly_covered}
              accent="text-emerald-700"
              onSelectTechnique={onSelectTechnique}
            />
            <EntryList
              title="Regressed"
              blurb="Covered in the older run but not now — e.g. a rule was disabled or removed."
              entries={result.regressed}
              accent="text-rose-700"
              onSelectTechnique={onSelectTechnique}
            />
            <EntryList
              title="N/A changed"
              blurb="Techniques that entered or left the applicable set — usually an environment or scope-exclusion change, not a detection change."
              entries={result.na_changed}
              accent="text-muted-foreground"
              onSelectTechnique={onSelectTechnique}
            />
          </div>
        </>
      )}
    </div>
  );
}

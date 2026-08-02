'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import {
  FEASIBILITY_META,
  Gap,
  STRENGTH_META,
  STRENGTH_TIP,
  Summary,
  TIER_TIPS,
  TechniqueResult,
  strengthBucket,
} from '../lib';

const INITIAL_ROWS = 50;

/** Dot + text instead of filled pills — denser and less "generated"-looking
 * (house UI taste: data-dense, no pill soup). Meaning stays on hover. */
function Dot({ className }: { className: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn('inline-block h-2 w-2 shrink-0 rounded-full', className)}
    />
  );
}

const TIER_WORDS: Record<number, { word: string; dot: string }> = {
  1: { word: 'Critical', dot: 'bg-rose-500' },
  2: { word: 'High', dot: 'bg-amber-500' },
  3: { word: 'Medium', dot: 'bg-sky-500' },
};

function TierBadge({ tier }: { tier: number }) {
  const meta = TIER_WORDS[tier];
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <span className="inline-flex cursor-default items-center gap-1.5 whitespace-nowrap text-xs">
          {meta ? (
            <>
              <Dot className={meta.dot} />P{tier} · {meta.word}
            </>
          ) : (
            <span className="text-muted-foreground">Unranked</span>
          )}
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">{TIER_TIPS[tier] ?? TIER_TIPS[4]}</TooltipContent>
    </Tooltip>
  );
}

const FEAS_DOTS: Record<string, string> = {
  short: 'bg-emerald-500',
  mid: 'bg-sky-500',
  long: 'bg-slate-400',
};
/** What the bucket means in action terms — "Short term" alone says little. */
const FEAS_WORDS: Record<string, string> = {
  short: 'Build now',
  mid: 'Onboard logs first',
  long: 'New capability',
};

function FeasibilityBadge({ gap }: { gap: Gap }) {
  const meta = FEASIBILITY_META[gap.feasibility];
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <span className="inline-flex cursor-default items-center gap-1.5 text-xs">
          <Dot className={FEAS_DOTS[gap.feasibility]} />
          <span>
            {FEAS_WORDS[gap.feasibility]}
            {gap.feasibility === 'short' && gap.via && (
              <span className="block text-[10px] leading-tight text-muted-foreground">
                via {gap.via}
              </span>
            )}
          </span>
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">
        {meta.label} — {meta.tip}
        {gap.via && ` (${gap.via})`}
      </TooltipContent>
    </Tooltip>
  );
}

/** Ranked gap table + short/mid/long roadmap, with the narrative's
 * AI-vs-template provenance surfaced. */
export function GapsRoadmap({
  summary,
  techniques,
  onSelectTechnique,
}: {
  summary: Summary;
  techniques: TechniqueResult[];
  onSelectTechnique: (techniqueId: string) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const narrative = summary.narrative;
  const gaps = showAll ? summary.gaps : summary.gaps.slice(0, INITIAL_ROWS);
  // Phase 12: partial gaps carry a detection-strength score (from
  // technique_results) — not covered gaps have nothing to score.
  const strengthById = new Map(
    techniques
      .filter((t) => typeof t.strength === 'number')
      .map((t) => [t.technique_id, t.strength as number])
  );

  const tacticName = (gap: Gap) => {
    const domain = summary.domains[gap.domain];
    return gap.tactics
      .map((id) => domain?.tactics.find((t) => t.id === id)?.name ?? id)
      .join(', ');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold">Gaps, ranked by priority</h3>
        <Tooltip delayDuration={150}>
          <TooltipTrigger asChild>
            <span
              className={cn(
                'inline-flex cursor-default items-center rounded-full border px-2 py-0.5 text-[11px] font-medium',
                narrative.generated_by === 'ai'
                  ? 'bg-violet-100 text-violet-800 border-violet-200'
                  : 'bg-muted text-muted-foreground border-transparent'
              )}
            >
              {narrative.generated_by === 'ai' ? 'AI-written text' : 'Standard text'}
            </span>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs text-xs">
            {narrative.generated_by === 'ai'
              ? `Recommendation wording was AI-generated${narrative.model_used ? ` (${narrative.model_used})` : ''}. All numbers come from computed results, never from the AI.`
              : 'The AI narrative was unavailable for this run, so recommendations use standard template wording. All numbers are computed either way.'}
          </TooltipContent>
        </Tooltip>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="h-8 w-8 px-2 text-[11px]">#</TableHead>
              <TableHead className="h-8 px-2 text-[11px]">Technique</TableHead>
              <TableHead className="hidden h-8 px-2 text-[11px] md:table-cell">Tactic</TableHead>
              <TableHead className="h-8 px-2 text-[11px]">
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span className="cursor-default underline decoration-dotted underline-offset-2">
                      Priority
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">
                    How commonly attackers use this technique in real intrusions,
                    from independent threat reports: P1 near-universal, P2 very
                    common, P3 common. A violet dot means it is also tied to your
                    declared industry or threat actors.
                  </TooltipContent>
                </Tooltip>
              </TableHead>
              <TableHead className="hidden h-8 px-2 text-[11px] lg:table-cell">
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span className="cursor-default underline decoration-dotted underline-offset-2">
                      Strength
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">{STRENGTH_TIP}</TooltipContent>
                </Tooltip>
              </TableHead>
              <TableHead className="h-8 px-2 text-[11px]">
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span className="cursor-default underline decoration-dotted underline-offset-2">
                      Feasibility
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">
                    How soon you could realistically build this detection: build
                    now = the needed logs are already onboarded; onboard first =
                    your existing tooling can provide them; new capability =
                    nothing you own produces this telemetry yet.
                  </TooltipContent>
                </Tooltip>
              </TableHead>
              <TableHead className="h-8 min-w-[280px] px-2 text-[11px]">Recommendation</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {gaps.map((gap) => (
              <TableRow key={gap.technique_id}>
                <TableCell className="px-2 py-1.5 text-[11px] text-muted-foreground">
                  {gap.rank}
                </TableCell>
                <TableCell className="px-2 py-1.5">
                  <button
                    type="button"
                    onClick={() => onSelectTechnique(gap.technique_id)}
                    className="whitespace-nowrap text-left text-xs font-medium text-primary hover:underline"
                  >
                    {gap.technique_id}
                  </button>{' '}
                  <span className="text-xs text-muted-foreground">{gap.name}</span>
                </TableCell>
                <TableCell className="hidden px-2 py-1.5 text-xs text-muted-foreground md:table-cell">
                  {tacticName(gap)}
                </TableCell>
                <TableCell className="whitespace-nowrap px-2 py-1.5">
                  <span className="inline-flex items-center gap-1.5">
                    <TierBadge tier={gap.tier} />
                    {gap.threat_relevance && gap.threat_relevance.length > 0 && (
                      <Tooltip delayDuration={150}>
                        <TooltipTrigger asChild>
                          <span className="inline-flex cursor-default items-center gap-1 text-[11px] text-violet-700">
                            <Dot className="bg-violet-500" />
                            Threat
                          </span>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs text-xs">
                          Prioritized for your declared threat profile (
                          {gap.threat_relevance.join(', ')}): these threats are
                          publicly reported to use this technique. Affects ordering
                          only — never the coverage score.
                        </TooltipContent>
                      </Tooltip>
                    )}
                  </span>
                </TableCell>
                <TableCell className="hidden whitespace-nowrap px-2 py-1.5 lg:table-cell">
                  {strengthById.has(gap.technique_id) ? (
                    <span
                      className="inline-flex cursor-default items-center gap-1.5 text-xs"
                      title={STRENGTH_TIP}
                    >
                      <Dot
                        className={
                          {
                            strong: 'bg-emerald-500',
                            moderate: 'bg-amber-500',
                            weak: 'bg-rose-500',
                          }[strengthBucket(strengthById.get(gap.technique_id)!)]
                        }
                      />
                      {strengthById.get(gap.technique_id)} ·{' '}
                      {STRENGTH_META[strengthBucket(strengthById.get(gap.technique_id)!)].label}
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell className="px-2 py-1.5">
                  <FeasibilityBadge gap={gap} />
                </TableCell>
                <TableCell className="px-2 py-1.5 text-xs leading-snug">
                  {narrative.gap_recommendations[gap.technique_id] ?? gap.hint}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {summary.gaps.length > INITIAL_ROWS && (
        <Button variant="outline" size="sm" onClick={() => setShowAll((v) => !v)}>
          {showAll ? 'Show top 50 only' : `Show all ${summary.gaps.length} gaps`}
        </Button>
      )}

      {/* grid-cols-1 matters: minmax(0,1fr) lets the track shrink below the
          nowrap (truncate) items' intrinsic width on mobile */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        {(['short', 'mid', 'long'] as const).map((bucket) => {
          const meta = FEASIBILITY_META[bucket];
          const items = summary.roadmap[bucket] ?? [];
          return (
            <div key={bucket} className="rounded-md bg-muted/30 p-3">
              <div className="mb-1 flex items-center gap-2">
                <span className="text-sm font-semibold">{meta.label}</span>
                <span className="text-[11px] text-muted-foreground">
                  {bucket === 'short' ? '0–3 months' : bucket === 'mid' ? '3–9 months' : '9–18 months'}
                  {' · '}
                  {items.length} item{items.length === 1 ? '' : 's'}
                </span>
              </div>
              <p className="mb-2 text-xs text-muted-foreground">
                {narrative.roadmap_prose[bucket]}
              </p>
              <div className="max-h-64 space-y-1 overflow-y-auto pr-1">
                {items.map((gap) => (
                  <button
                    key={gap.technique_id}
                    type="button"
                    onClick={() => onSelectTechnique(gap.technique_id)}
                    title={gap.hint}
                    className="block w-full truncate rounded bg-background px-2 py-1 text-left text-xs transition-colors hover:bg-primary/5"
                  >
                    <span className="font-medium">{gap.technique_id}</span>{' '}
                    <span className="text-muted-foreground">{gap.name}</span>
                  </button>
                ))}
                {items.length === 0 && (
                  <p className="text-xs text-muted-foreground">Nothing in this bucket.</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

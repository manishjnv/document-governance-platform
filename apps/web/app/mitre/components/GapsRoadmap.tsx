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

function TierBadge({ tier }: { tier: number }) {
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <span
          className={cn(
            'inline-flex cursor-default items-center rounded-full border px-2 py-0.5 text-[11px] font-medium',
            tier === 1 && 'bg-rose-100 text-rose-800 border-rose-200',
            tier === 2 && 'bg-amber-100 text-amber-800 border-amber-200',
            tier === 3 && 'bg-sky-100 text-sky-800 border-sky-200',
            tier >= 4 && 'bg-muted text-muted-foreground border-transparent'
          )}
        >
          {tier >= 4 ? '—' : `P${tier}`}
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">{TIER_TIPS[tier] ?? TIER_TIPS[4]}</TooltipContent>
    </Tooltip>
  );
}

function FeasibilityBadge({ gap }: { gap: Gap }) {
  const meta = FEASIBILITY_META[gap.feasibility];
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <span
          className={cn(
            'inline-flex cursor-default items-center rounded-full border px-2 py-0.5 text-[11px] font-medium',
            meta.chip
          )}
        >
          {meta.label}
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">
        {meta.tip}
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
              <TableHead className="w-10">#</TableHead>
              <TableHead>Technique</TableHead>
              <TableHead className="hidden md:table-cell">Tactic</TableHead>
              <TableHead>
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span className="cursor-default underline decoration-dotted underline-offset-2">
                      Priority
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">
                    How commonly attackers use this technique in real intrusions,
                    from independent threat reports: P1 near-universal, P2 very
                    common, P3 common, — unranked. A &quot;Threat match&quot; chip
                    means it is also tied to your declared industry or threat
                    actors.
                  </TooltipContent>
                </Tooltip>
              </TableHead>
              <TableHead className="hidden lg:table-cell">
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span className="cursor-default underline decoration-dotted underline-offset-2">
                      Strength
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">{STRENGTH_TIP}</TooltipContent>
                </Tooltip>
              </TableHead>
              <TableHead>
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span className="cursor-default underline decoration-dotted underline-offset-2">
                      Feasibility
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">
                    How soon you could realistically build this detection: short
                    term = the needed logs are already onboarded; mid term = your
                    existing tooling can provide them; long term = needs a new
                    telemetry capability.
                  </TooltipContent>
                </Tooltip>
              </TableHead>
              <TableHead className="min-w-[280px]">Recommendation</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {gaps.map((gap) => (
              <TableRow key={gap.technique_id}>
                <TableCell className="text-xs text-muted-foreground">{gap.rank}</TableCell>
                <TableCell>
                  <button
                    type="button"
                    onClick={() => onSelectTechnique(gap.technique_id)}
                    className="text-left text-sm font-medium text-primary hover:underline"
                  >
                    {gap.technique_id}
                  </button>
                  <div className="text-xs text-muted-foreground">{gap.name}</div>
                </TableCell>
                <TableCell className="hidden text-xs text-muted-foreground md:table-cell">
                  {tacticName(gap)}
                </TableCell>
                <TableCell>
                  <span className="inline-flex flex-wrap items-center gap-1">
                    <TierBadge tier={gap.tier} />
                    {gap.threat_relevance && gap.threat_relevance.length > 0 && (
                      <Tooltip delayDuration={150}>
                        <TooltipTrigger asChild>
                          <span className="inline-flex cursor-default items-center rounded-full border border-violet-200 bg-violet-100 px-2 py-0.5 text-[11px] font-medium text-violet-800">
                            Threat match
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
                <TableCell className="hidden lg:table-cell">
                  {strengthById.has(gap.technique_id) ? (
                    <span
                      className={cn(
                        'inline-flex cursor-default items-center rounded-full border px-2 py-0.5 text-[11px] font-medium',
                        STRENGTH_META[strengthBucket(strengthById.get(gap.technique_id)!)].chip
                      )}
                      title={STRENGTH_TIP}
                    >
                      {strengthById.get(gap.technique_id)}/100
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell>
                  <FeasibilityBadge gap={gap} />
                </TableCell>
                <TableCell className="text-xs leading-snug">
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

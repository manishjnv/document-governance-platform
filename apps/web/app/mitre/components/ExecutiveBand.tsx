'use client';

import { Info } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import {
  Assessment,
  DOMAIN_LABELS,
  STATE_META,
  Summary,
  TechniqueResult,
  fmtDate,
  orderedDomains,
} from '../lib';

/** Phase 14b: how a tile opens the drill-down panel. */
export type DrillHandler = (
  title: string,
  items: TechniqueResult[],
  opts?: { grouped?: boolean; subtitle?: string }
) => void;

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
    <CardContent className="px-3 py-2.5 text-center">
      <div className={cn('text-xl font-bold leading-tight', accent)}>{value}</div>
      <div className="text-[11px] font-medium text-muted-foreground">{label}</div>
    </CardContent>
  );
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        {onClick ? (
          <Card
            role="button"
            tabIndex={0}
            onClick={onClick}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }}
            className="cursor-pointer transition-colors hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {content}
          </Card>
        ) : (
          <Card className="cursor-default">{content}</Card>
        )}
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">
        {tip}
        {onClick ? ' Click to see the techniques behind this number.' : ''}
      </TooltipContent>
    </Tooltip>
  );
}

/** Top band of the results page: headline %, per-domain tiles, state counts,
 * top-5 gaps, run metadata. Data-dense, no hero cards. Phase 14b: every
 * number opens the drill-down panel. */
export function ExecutiveBand({
  assessment,
  summary,
  techniques,
  onSelectTechnique,
  onDrill,
}: {
  assessment: Assessment;
  summary: Summary;
  techniques: TechniqueResult[];
  onSelectTechnique: (techniqueId: string) => void;
  onDrill: DrillHandler;
}) {
  const o = summary.overall;
  const domains = orderedDomains(summary.domains).filter(([, d]) => d.applicable > 0);
  const gated = orderedDomains(summary.domains).filter(([, d]) => d.applicable === 0);
  const topGaps = summary.gaps.slice(0, 5);
  const applicable = techniques.filter((t) => t.state !== 'not_applicable');

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
        <Tile
          value={`${o.strict_pct}%`}
          label="Coverage"
          accent="text-primary"
          tip={`Strict coverage: ${o.covered} of ${o.applicable} applicable techniques have at least one qualifying detection. Weighted coverage (partial counts as half): ${o.weighted_pct}%.`}
          onClick={() =>
            onDrill('All applicable techniques', applicable, {
              grouped: true,
              subtitle: `${o.applicable} techniques apply to your environment, grouped by state.`,
            })
          }
        />
        {domains.map(([key, d]) => (
          <Tile
            key={key}
            value={`${d.strict_pct}%`}
            label={DOMAIN_LABELS[key] ?? key}
            tip={`${DOMAIN_LABELS[key] ?? key}: ${d.covered} of ${d.applicable} applicable techniques covered (weighted ${d.weighted_pct}%).`}
            onClick={() =>
              onDrill(
                `${DOMAIN_LABELS[key] ?? key} techniques`,
                applicable.filter((t) => t.domain === key),
                {
                  grouped: true,
                  subtitle: `${d.applicable} applicable techniques in this matrix, grouped by state.`,
                }
              )
            }
          />
        ))}
        {(['covered', 'partial', 'not_covered', 'not_applicable'] as const).map(
          (state) => (
            <Tile
              key={state}
              value={o[state]}
              label={STATE_META[state].label}
              accent={
                state === 'covered'
                  ? 'text-emerald-600'
                  : state === 'partial'
                    ? 'text-amber-600'
                    : state === 'not_covered'
                      ? 'text-rose-600'
                      : undefined
              }
              tip={STATE_META[state].tip}
              onClick={() =>
                onDrill(
                  `${STATE_META[state].label} techniques (${o[state]})`,
                  techniques.filter((t) => t.state === state),
                  {
                    subtitle:
                      state === 'partial'
                        ? 'Each row shows why it only counts as half-covered.'
                        : undefined,
                  }
                )
              }
            />
          )
        )}
      </div>

      {/* Phase 14b: the plain-words headline + "is this % bad?" context. */}
      <p className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
        Of the {o.applicable} techniques that apply to your environment, your rules
        can detect {o.covered}
        {o.partial > 0 ? ` (plus ${o.partial} partially)` : ''}.
        <Tooltip delayDuration={150}>
          <TooltipTrigger asChild>
            <button
              type="button"
              aria-label={`Is ${o.strict_pct}% bad? Context on this score`}
              className="inline-flex items-center gap-0.5 rounded text-muted-foreground underline decoration-dotted underline-offset-2 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Info size={12} aria-hidden="true" /> Is {o.strict_pct}% bad?
            </button>
          </TooltipTrigger>
          <TooltipContent className="max-w-sm text-xs">
            Probably not as bad as it looks: early SIEM detection programs
            typically start under 10% strict coverage, because ATT&CK counts
            every known attacker technique. The point of this assessment is the
            roadmap — the short-term items raise this number fastest — not the
            grade itself.
          </TooltipContent>
        </Tooltip>
      </p>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {topGaps.length > 0 && (
          <span className="flex flex-wrap items-center gap-1.5">
            <span className="font-medium text-foreground">Top gaps:</span>
            {topGaps.map((g) => (
              <Tooltip key={g.technique_id} delayDuration={150}>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={() => onSelectTechnique(g.technique_id)}
                    className="rounded-full border bg-rose-50 px-2 py-0.5 font-medium text-rose-800 transition-colors hover:bg-rose-100"
                  >
                    {g.technique_id}
                  </button>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs text-xs">
                  {g.name} — {g.hint}
                </TooltipContent>
              </Tooltip>
            ))}
          </span>
        )}
        {gated.map(([key]) => {
          const reason = summary.not_applicable.find((n) => n.domain === key)?.reason;
          return (
            <span key={key}>
              {DOMAIN_LABELS[key] ?? key}: not assessed{reason ? ` — ${reason}` : ''}
            </span>
          );
        })}
        <span className="ml-auto">
          ATT&CK v{assessment.attack_version} · run {fmtDate(assessment.completed_at)}
        </span>
      </div>
    </div>
  );
}

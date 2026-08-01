'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { Assessment, DOMAIN_LABELS, STATE_META, Summary, fmtDate } from '../lib';

function Tile({
  value,
  label,
  tip,
  accent,
}: {
  value: string | number;
  label: string;
  tip: string;
  accent?: string;
}) {
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <Card className="cursor-default">
          <CardContent className="px-3 py-2.5 text-center">
            <div className={cn('text-xl font-bold leading-tight', accent)}>{value}</div>
            <div className="text-[11px] font-medium text-muted-foreground">{label}</div>
          </CardContent>
        </Card>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">{tip}</TooltipContent>
    </Tooltip>
  );
}

/** Top band of the results page: headline %, per-domain tiles, state counts,
 * top-5 gaps, run metadata. Data-dense, no hero cards. */
export function ExecutiveBand({
  assessment,
  summary,
  onSelectTechnique,
}: {
  assessment: Assessment;
  summary: Summary;
  onSelectTechnique: (techniqueId: string) => void;
}) {
  const o = summary.overall;
  const domains = Object.entries(summary.domains).filter(([, d]) => d.applicable > 0);
  const gated = Object.entries(summary.domains).filter(([, d]) => d.applicable === 0);
  const topGaps = summary.gaps.slice(0, 5);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
        <Tile
          value={`${o.strict_pct}%`}
          label="Coverage"
          accent="text-primary"
          tip={`Strict coverage: ${o.covered} of ${o.applicable} applicable techniques have at least one qualifying detection. Weighted coverage (partial counts as half): ${o.weighted_pct}%.`}
        />
        {domains.map(([key, d]) => (
          <Tile
            key={key}
            value={`${d.strict_pct}%`}
            label={DOMAIN_LABELS[key] ?? key}
            tip={`${DOMAIN_LABELS[key] ?? key}: ${d.covered} of ${d.applicable} applicable techniques covered (weighted ${d.weighted_pct}%).`}
          />
        ))}
        <Tile value={o.covered} label="Covered" accent="text-emerald-600" tip={STATE_META.covered.tip} />
        <Tile value={o.partial} label="Partial" accent="text-amber-600" tip={STATE_META.partial.tip} />
        <Tile value={o.not_covered} label="Not covered" accent="text-rose-600" tip={STATE_META.not_covered.tip} />
        <Tile value={o.not_applicable} label="N/A" tip={STATE_META.not_applicable.tip} />
      </div>

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

'use client';

import { useMemo } from 'react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { DOMAIN_LABELS, STATE_META, Summary, TechniqueResult } from '../lib';

/** Navigator-style tactic-column heatmap, plain CSS grid — no charting
 * dependency. Cells use click -> drawer for full detail plus a native
 * `title` hover hint (a Radix tooltip per ~700 cells would be wasteful);
 * shadcn tooltips cover the legend and column headers. */
export function CoverageHeatmap({
  summary,
  techniques,
  onSelectTechnique,
}: {
  summary: Summary;
  techniques: TechniqueResult[];
  onSelectTechnique: (techniqueId: string) => void;
}) {
  const byDomainTactic = useMemo(() => {
    const map = new Map<string, TechniqueResult[]>();
    for (const t of techniques) {
      for (const tacticId of t.tactics) {
        const key = `${t.domain}:${tacticId}`;
        const list = map.get(key) ?? [];
        list.push(t);
        map.set(key, list);
      }
    }
    for (const list of map.values()) {
      list.sort((a, b) => a.technique_id.localeCompare(b.technique_id));
    }
    return map;
  }, [techniques]);

  const activeDomains = Object.entries(summary.domains).filter(([, d]) => d.applicable > 0);

  return (
    <div className="space-y-6">
      {/* Legend */}
      <div className="flex flex-wrap items-center gap-3 text-xs">
        {Object.entries(STATE_META).map(([state, meta]) => (
          <Tooltip key={state} delayDuration={150}>
            <TooltipTrigger asChild>
              <span className="flex cursor-default items-center gap-1.5">
                <span className={cn('h-3 w-3 rounded-sm', meta.cell.split(' ')[0])} />
                {meta.label}
              </span>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs text-xs">{meta.tip}</TooltipContent>
          </Tooltip>
        ))}
        <span className="text-muted-foreground">Click any technique for details.</span>
      </div>

      {activeDomains.map(([domainKey, domain]) => (
        <section key={domainKey}>
          <h3 className="mb-2 text-sm font-semibold">
            {DOMAIN_LABELS[domainKey] ?? domainKey}{' '}
            <span className="font-normal text-muted-foreground">
              — {domain.covered}/{domain.applicable} covered ({domain.strict_pct}%)
            </span>
          </h3>
          <div className="overflow-x-auto rounded-md bg-muted/30 p-2">
            <div
              className="grid gap-2"
              style={{
                gridTemplateColumns: `repeat(${domain.tactics.length}, minmax(148px, 1fr))`,
              }}
            >
              {domain.tactics.map((tactic) => {
                const cells = byDomainTactic.get(`${domainKey}:${tactic.id}`) ?? [];
                return (
                  <div key={tactic.id} className="min-w-0">
                    <Tooltip delayDuration={150}>
                      <TooltipTrigger asChild>
                        <div className="mb-1 cursor-default px-1">
                          <div className="truncate text-xs font-semibold">{tactic.name}</div>
                          <div className="text-[10px] text-muted-foreground">
                            {tactic.covered}/{tactic.applicable} covered
                          </div>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs text-xs">
                        {tactic.name}: {tactic.covered} covered, {tactic.partial} partial,{' '}
                        {tactic.not_covered} not covered, {tactic.not_applicable} not applicable
                        (strict {tactic.strict_pct}%).
                      </TooltipContent>
                    </Tooltip>
                    <div className="flex flex-col gap-1">
                      {cells.map((t) => {
                        const meta = STATE_META[t.state] ?? STATE_META.not_applicable;
                        return (
                          <button
                            key={t.technique_id}
                            type="button"
                            onClick={() => onSelectTechnique(t.technique_id)}
                            title={`${t.technique_id} — ${meta.label}${t.na_reason ? `: ${t.na_reason}` : ''}`}
                            className={cn(
                              'w-full truncate rounded px-1.5 py-1 text-left text-[11px] leading-tight transition-colors',
                              meta.cell,
                              t.technique_id.includes('.') && 'ml-2 w-[calc(100%-0.5rem)]'
                            )}
                          >
                            {t.technique_id}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      ))}
    </div>
  );
}

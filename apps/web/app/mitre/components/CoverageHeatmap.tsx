'use client';

import { useMemo, useRef, useState } from 'react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { DOMAIN_LABELS, STATE_META, STATE_PLAIN, Summary, TechniqueResult } from '../lib';
import type { DrillHandler } from './ExecutiveBand';

/** Navigator-style tactic-column heatmap, plain CSS grid — no charting
 * dependency. Cells show "ID Name" (truncated — no extra area per TTP) and
 * click -> drawer for full detail. Hover context comes from ONE delegated
 * custom tooltip for all ~900 cells (a Radix tooltip per cell would be
 * wasteful): solid background, smooth fade, driven by data-tip attributes.
 * Shadcn tooltips still cover the legend and column headers. */
export function CoverageHeatmap({
  summary,
  techniques,
  onSelectTechnique,
  onDrill,
}: {
  summary: Summary;
  techniques: TechniqueResult[];
  onSelectTechnique: (techniqueId: string) => void;
  onDrill: DrillHandler;
}) {
  // One tooltip for every cell (event delegation on the grid container).
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null);
  const tipTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showTip = (target: Element) => {
    const el = target.closest('[data-tip]') as HTMLElement | null;
    if (!el) {
      setTip(null);
      return;
    }
    const rect = el.getBoundingClientRect();
    if (tipTimer.current) clearTimeout(tipTimer.current);
    tipTimer.current = setTimeout(
      () =>
        setTip({
          x: Math.min(Math.max(rect.left + rect.width / 2, 130), window.innerWidth - 130),
          y: rect.top,
          text: el.dataset.tip ?? '',
        }),
      120
    );
  };
  const hideTip = () => {
    if (tipTimer.current) clearTimeout(tipTimer.current);
    setTip(null);
  };

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
    <div
      className="space-y-6"
      onMouseOver={(e) => showTip(e.target as Element)}
      onMouseOut={hideTip}
    >
      {tip && (
        <div
          role="tooltip"
          className="pointer-events-none fixed z-50 -translate-x-1/2 -translate-y-full whitespace-pre-line rounded-md border bg-popover px-2.5 py-1.5 text-[11px] leading-snug text-popover-foreground shadow-md animate-in fade-in-0 zoom-in-95 duration-150"
          style={{ left: tip.x, top: tip.y - 6, maxWidth: 260 }}
        >
          {tip.text}
        </div>
      )}
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
            <button
              type="button"
              onClick={() =>
                onDrill(
                  `${DOMAIN_LABELS[domainKey] ?? domainKey} techniques`,
                  techniques.filter(
                    (t) => t.domain === domainKey && t.state !== 'not_applicable'
                  ),
                  { grouped: true }
                )
              }
              className="font-normal text-muted-foreground underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              — {domain.covered}/{domain.applicable} covered ({domain.strict_pct}%)
            </button>
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
                        <button
                          type="button"
                          onClick={() =>
                            onDrill(
                              `${tactic.name} — ${DOMAIN_LABELS[domainKey] ?? domainKey}`,
                              cells,
                              { grouped: true }
                            )
                          }
                          className="mb-1 w-full rounded px-1 text-left hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <div className="truncate text-xs font-semibold">{tactic.name}</div>
                          <div className="text-[10px] text-muted-foreground">
                            {tactic.covered}/{tactic.applicable} covered
                          </div>
                        </button>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs text-xs">
                        {tactic.name}: {tactic.covered} covered, {tactic.partial} partial,{' '}
                        {tactic.not_covered} not covered, {tactic.not_applicable} not applicable
                        (strict {tactic.strict_pct}%). Click for the list.
                      </TooltipContent>
                    </Tooltip>
    <div className="flex flex-col gap-1">
                      {cells.map((t) => {
                        const meta = STATE_META[t.state] ?? STATE_META.not_applicable;
                        const detail =
                          t.state === 'not_applicable' && t.na_reason
                            ? t.na_reason
                            : STATE_PLAIN[t.state] ?? meta.label;
                        return (
                          <button
                            key={t.technique_id}
                            type="button"
                            onClick={() => onSelectTechnique(t.technique_id)}
                            data-tip={`${t.technique_id}${t.name ? ` — ${t.name}` : ''}\n${meta.label}: ${detail}. Click for details.`}
                            onFocus={(e) => showTip(e.target as Element)}
                            onBlur={hideTip}
                            className={cn(
                              'w-full truncate rounded px-1.5 py-1 text-left text-[11px] leading-tight transition-colors',
                              meta.cell,
                              t.technique_id.includes('.') && 'ml-2 w-[calc(100%-0.5rem)]'
                            )}
                          >
                            <span className="font-medium">{t.technique_id}</span>
                            {t.name && <span className="opacity-85"> {t.name}</span>}
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

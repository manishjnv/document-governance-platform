'use client';

import { useMemo, useRef, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
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
  // Hover-intent discipline so moving BETWEEN cells never flickers or
  // re-animates: show is debounced only for the FIRST appearance, moving to
  // the next cell just glides the existing tooltip, and hide is delayed so
  // the mouseout->mouseover gap between adjacent cells doesn't unmount it.
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null);
  const showTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Collapsible matrices + legend-as-filter (click a state to show only it).
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [stateFilter, setStateFilter] = useState<Set<string>>(new Set());

  const toggleCollapsed = (domainKey: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(domainKey)) next.delete(domainKey);
      else next.add(domainKey);
      return next;
    });
  const toggleStateFilter = (state: string) =>
    setStateFilter((prev) => {
      const next = new Set(prev);
      if (next.has(state)) next.delete(state);
      else next.add(state);
      return next;
    });

  const showTip = (target: Element) => {
    const el = target.closest('[data-tip]') as HTMLElement | null;
    if (!el) return; // leaving is handled by hideTip's delay, never here
    if (hideTimer.current) clearTimeout(hideTimer.current);
    if (showTimer.current) clearTimeout(showTimer.current);
    const rect = el.getBoundingClientRect();
    const next = {
      x: Math.min(Math.max(rect.left + rect.width / 2, 130), window.innerWidth - 130),
      y: rect.top,
      text: el.dataset.tip ?? '',
    };
    if (tip) setTip(next); // already visible: move instantly, no remount
    else showTimer.current = setTimeout(() => setTip(next), 120);
  };
  const hideTip = () => {
    if (showTimer.current) clearTimeout(showTimer.current);
    hideTimer.current = setTimeout(() => setTip(null), 120);
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
      {/* Legend — each state is also a filter: click to show only it. */}
      <div className="flex flex-wrap items-center gap-3 text-xs">
        {Object.entries(STATE_META).map(([state, meta]) => {
          const active = stateFilter.has(state);
          const dimmed = stateFilter.size > 0 && !active;
          return (
            <Tooltip key={state} delayDuration={150}>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  aria-pressed={active}
                  onClick={() => toggleStateFilter(state)}
                  className={cn(
                    'flex items-center gap-1.5 rounded px-1 py-0.5 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    active && 'bg-muted font-medium',
                    dimmed && 'opacity-40'
                  )}
                >
                  <span className={cn('h-3 w-3 rounded-sm', meta.cell.split(' ')[0])} />
                  {meta.label}
                </button>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs text-xs">
                {meta.tip} Click to show only these techniques.
              </TooltipContent>
            </Tooltip>
          );
        })}
        {stateFilter.size > 0 && (
          <button
            type="button"
            onClick={() => setStateFilter(new Set())}
            className="text-muted-foreground underline decoration-dotted underline-offset-2 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Show all
          </button>
        )}
        <span className="text-muted-foreground">Click any technique for details.</span>
      </div>

      {activeDomains.map(([domainKey, domain]) => (
        <section key={domainKey}>
          <h3 className="mb-2 flex items-center gap-1 text-sm font-semibold">
            <button
              type="button"
              aria-expanded={!collapsed.has(domainKey)}
              onClick={() => toggleCollapsed(domainKey)}
              className="flex items-center gap-1 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {collapsed.has(domainKey) ? (
                <ChevronRight size={14} aria-hidden="true" />
              ) : (
                <ChevronDown size={14} aria-hidden="true" />
              )}
              {DOMAIN_LABELS[domainKey] ?? domainKey}
            </button>{' '}
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
          {!collapsed.has(domainKey) && (
          <div className="overflow-x-auto rounded-md bg-muted/30 p-2">
            <div
              className="grid gap-2"
              style={{
                gridTemplateColumns: `repeat(${domain.tactics.length}, minmax(148px, 1fr))`,
              }}
            >
              {domain.tactics.map((tactic) => {
                const cells = (byDomainTactic.get(`${domainKey}:${tactic.id}`) ?? []).filter(
                  (t) => stateFilter.size === 0 || stateFilter.has(t.state)
                );
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
          )}
        </section>
      ))}

      {/* Rendered LAST: position:fixed takes it out of flow, and being the
          final child means mounting it never shifts the space-y-6 sibling
          margins (as the first child it made the page jump on every hover).
          transition-[left,top] glides it between cells instead of jumping. */}
      {tip && (
        <div
          role="tooltip"
          className="pointer-events-none fixed z-50 -translate-x-1/2 -translate-y-full whitespace-pre-line rounded-md border bg-popover px-2.5 py-1.5 text-[11px] leading-snug text-popover-foreground shadow-md transition-[left,top] duration-100 ease-out animate-in fade-in-0 zoom-in-95"
          style={{ left: tip.x, top: tip.y - 6, maxWidth: 260 }}
        >
          {tip.text}
        </div>
      )}
    </div>
  );
}

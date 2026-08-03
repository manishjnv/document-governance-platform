'use client';

import { useMemo, useRef, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { DOMAIN_LABELS, LogSourceCoverageGroup, STATE_META, STATE_PLAIN, Summary, TechniqueResult, orderedDomains } from '../lib';
import type { DrillHandler } from './ExecutiveBand';

// "PRE" and "None" are ATT&CK's environment-independent markers, not real
// platforms — techniques carrying only those (e.g. Reconnaissance) apply to
// every estate and are never hidden by the platform filter.
const NON_PLATFORMS = new Set(['pre', 'none']);
const realPlatforms = (t: TechniqueResult) =>
  (t.platforms ?? []).filter((p) => !NON_PLATFORMS.has(p.toLowerCase()));

// Navigator-style score gradient for covered cells: darker green = more
// rules map here. One rule = coverage hanging on a single detection.
const DEPTH_CELLS: [string, string][] = [
  ['1 rule', 'bg-emerald-400/75 text-white hover:bg-emerald-500'],
  ['2–3 rules', 'bg-emerald-500/85 text-white hover:bg-emerald-600'],
  ['4+ rules', 'bg-emerald-700/90 text-white hover:bg-emerald-800'],
];
const depthCell = (ruleCount: number) =>
  DEPTH_CELLS[ruleCount <= 1 ? 0 : ruleCount <= 3 ? 1 : 2][1];

/** Navigator-style tactic-column heatmap, plain CSS grid — no charting
 * dependency. Cells show "ID Name" (truncated — no extra area per TTP) and
 * click -> drawer for full detail. Hover context comes from ONE delegated
 * custom tooltip for all ~900 cells (a Radix tooltip per cell would be
 * wasteful): solid background, smooth fade, driven by data-tip attributes.
 * Shadcn tooltips still cover the legend and column headers. */
export function CoverageHeatmap({
  summary,
  techniques,
  logSources,
  onSelectTechnique,
  onDrill,
}: {
  summary: Summary;
  techniques: TechniqueResult[];
  logSources?: LogSourceCoverageGroup[];
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
  // Collapsible matrices + legend-as-filter (click a state to show only it)
  // + Navigator-style platform filter (click a platform chip to show only
  // techniques that can run on it).
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [stateFilter, setStateFilter] = useState<Set<string>>(new Set());
  const [platformFilter, setPlatformFilter] = useState<Set<string>>(new Set());
  // Navigator-style sub-technique roll-up: hide subs, badge parents with
  // "covered/applicable subs". Purely visual — header counts stay truthful.
  const [hideSubs, setHideSubs] = useState(false);

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
  const togglePlatformFilter = (platform: string) =>
    setPlatformFilter((prev) => {
      const next = new Set(prev);
      if (next.has(platform)) next.delete(platform);
      else next.add(platform);
      return next;
    });
  // Log-source lens ("what does our EDR alone cover?"): filter to techniques
  // reached by rules from the selected log source(s). Keyed by display name.
  const [sourceFilter, setSourceFilter] = useState<Set<string>>(new Set());
  const toggleSourceFilter = (source: string) =>
    setSourceFilter((prev) => {
      const next = new Set(prev);
      if (next.has(source)) next.delete(source);
      else next.add(source);
      return next;
    });

  const sourceRowRefs = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const g of logSources ?? []) map.set(g.log_source, new Set(g.row_refs));
    return map;
  }, [logSources]);

  // Platform-agnostic techniques (no real platform tags) always match.
  const matchesPlatform = (t: TechniqueResult) => {
    if (platformFilter.size === 0) return true;
    const plats = realPlatforms(t);
    return plats.length === 0 || plats.some((p) => platformFilter.has(p));
  };
  const matchesSource = (t: TechniqueResult) => {
    if (sourceFilter.size === 0) return true;
    return t.use_case_refs.some((ref) =>
      [...sourceFilter].some((s) => sourceRowRefs.get(s)?.has(ref))
    );
  };
  const lensActive = platformFilter.size > 0 || sourceFilter.size > 0;
  const matchesLens = (t: TechniqueResult) => matchesPlatform(t) && matchesSource(t);

  const countShown = (list: TechniqueResult[]) => {
    let covered = 0;
    let applicable = 0;
    for (const t of list) {
      if (t.state === 'not_applicable') continue;
      applicable += 1;
      if (t.state === 'covered') covered += 1;
    }
    return {
      covered,
      applicable,
      pct: applicable ? Math.round((100 * covered) / applicable) : 0,
    };
  };

  // parent technique id -> covered/applicable among its sub-techniques,
  // for the badge shown when sub-techniques are collapsed.
  const subStats = useMemo(() => {
    const map = new Map<string, { covered: number; applicable: number }>();
    for (const t of techniques) {
      if (!t.technique_id.includes('.')) continue;
      const parent = t.technique_id.split('.')[0];
      const s = map.get(parent) ?? { covered: 0, applicable: 0 };
      if (t.state !== 'not_applicable') {
        s.applicable += 1;
        if (t.state === 'covered') s.covered += 1;
      }
      map.set(parent, s);
    }
    return map;
  }, [techniques]);

  // Per-platform coverage chips, biggest estates first — so a Windows+Linux
  // customer sees their own platforms lead the row.
  const platformStats = useMemo(() => {
    const stats = new Map<string, { covered: number; applicable: number }>();
    for (const t of techniques) {
      if (t.state === 'not_applicable') continue;
      for (const p of realPlatforms(t)) {
        const s = stats.get(p) ?? { covered: 0, applicable: 0 };
        s.applicable += 1;
        if (t.state === 'covered') s.covered += 1;
        stats.set(p, s);
      }
    }
    return [...stats.entries()].sort(
      (a, b) => b[1].applicable - a[1].applicable || a[0].localeCompare(b[0])
    );
  }, [techniques]);

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

  const activeDomains = orderedDomains(summary.domains).filter(([, d]) => d.applicable > 0);

  return (
    <div
      className="space-y-6"
      onMouseOver={(e) => showTip(e.target as Element)}
      onMouseOut={hideTip}
    >
      {/* Platform chips — Navigator-style lens: click to show only techniques
          that can run on that platform. Percentages are per-platform coverage
          (covered / applicable among techniques tagged with that platform). */}
      {platformStats.length > 1 && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-muted-foreground">Runs on:</span>
          {platformStats.map(([platform, s]) => {
            const active = platformFilter.has(platform);
            const dimmed = platformFilter.size > 0 && !active;
            const pct = s.applicable ? Math.round((100 * s.covered) / s.applicable) : 0;
            return (
              <Tooltip key={platform} delayDuration={150}>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-pressed={active}
                    onClick={() => togglePlatformFilter(platform)}
                    className={cn(
                      'flex items-center gap-1 rounded border px-1.5 py-0.5 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      active ? 'border-primary/40 bg-muted font-medium' : 'border-transparent bg-muted/40',
                      dimmed && 'opacity-40'
                    )}
                  >
                    {platform}
                    <span className="text-muted-foreground">{pct}%</span>
                  </button>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs text-xs">
                  {s.covered} of {s.applicable} applicable techniques that can run on{' '}
                  {platform} are covered ({pct}%). Click to show only techniques that can
                  run on {platform}.
                </TooltipContent>
              </Tooltip>
            );
          })}
          {platformFilter.size > 0 && (
            <button
              type="button"
              onClick={() => setPlatformFilter(new Set())}
              className="text-muted-foreground underline decoration-dotted underline-offset-2 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              All platforms
            </button>
          )}
        </div>
      )}
      {/* Log-source chips — "what does this source alone buy you": click to
          show only techniques reached by rules from that log source. */}
      {(logSources?.length ?? 0) > 1 && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-muted-foreground">Detected via:</span>
          {(logSources ?? []).map((g) => {
            const active = sourceFilter.has(g.log_source);
            const dimmed = sourceFilter.size > 0 && !active;
            return (
              <Tooltip key={g.log_source} delayDuration={150}>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleSourceFilter(g.log_source)}
                    className={cn(
                      'flex items-center gap-1 rounded border px-1.5 py-0.5 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      active ? 'border-primary/40 bg-muted font-medium' : 'border-transparent bg-muted/40',
                      dimmed && 'opacity-40'
                    )}
                  >
                    {g.log_source}
                    <span className="text-muted-foreground">
                      {g.rule_count} rule{g.rule_count === 1 ? '' : 's'}
                    </span>
                  </button>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs text-xs">
                  {g.rule_count} detection rule{g.rule_count === 1 ? '' : 's'} use{' '}
                  {g.log_source}, reaching {g.techniques_covered} technique
                  {g.techniques_covered === 1 ? '' : 's'}. Click to show only what this
                  log source detects.
                </TooltipContent>
              </Tooltip>
            );
          })}
          {sourceFilter.size > 0 && (
            <button
              type="button"
              onClick={() => setSourceFilter(new Set())}
              className="text-muted-foreground underline decoration-dotted underline-offset-2 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              All sources
            </button>
          )}
        </div>
      )}
      {lensActive && (
        <p className="text-xs text-muted-foreground">
          Showing techniques
          {platformFilter.size > 0 && <> that can run on {[...platformFilter].join(', ')}</>}
          {platformFilter.size > 0 && sourceFilter.size > 0 && <> and are</>}
          {sourceFilter.size > 0 && <> detected by rules using {[...sourceFilter].join(', ')}</>}
          {' '}— counts update to match.
          {platformFilter.size > 0 &&
            ' Platform-independent techniques (e.g. Reconnaissance) stay visible.'}
        </p>
      )}

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
                  {state === 'covered' ? (
                    <span className="flex h-3 w-[18px] overflow-hidden rounded-sm">
                      {DEPTH_CELLS.map(([label, cls]) => (
                        <span key={label} className={cn('flex-1', cls.split(' ')[0])} />
                      ))}
                    </span>
                  ) : (
                    <span className={cn('h-3 w-3 rounded-sm', meta.cell.split(' ')[0])} />
                  )}
                  {meta.label}
                </button>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs text-xs">
                {meta.tip}
                {state === 'covered' &&
                  ' Darker green = more rules detect it (1, 2–3, 4+); the lightest shade means coverage rests on a single rule.'}{' '}
                Click to show only these techniques.
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
        <Tooltip delayDuration={150}>
          <TooltipTrigger asChild>
            <button
              type="button"
              aria-pressed={hideSubs}
              onClick={() => setHideSubs((v) => !v)}
              className={cn(
                'rounded border px-1.5 py-0.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                hideSubs
                  ? 'border-primary/40 bg-muted font-medium'
                  : 'border-transparent bg-muted/40'
              )}
            >
              {hideSubs ? 'Sub-techniques hidden' : 'Hide sub-techniques'}
            </button>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs text-xs">
            Collapse the matrix to parent techniques only — each parent shows how many
            of its sub-techniques are covered. Coverage counts don&apos;t change.
          </TooltipContent>
        </Tooltip>
        <span className="text-muted-foreground">Click any technique for details.</span>
      </div>

      {activeDomains.map(([domainKey, domain]) => {
        const domainShown = lensActive
          ? countShown(techniques.filter((t) => t.domain === domainKey && matchesLens(t)))
          : null;
        return (
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
                    (t) =>
                      t.domain === domainKey &&
                      t.state !== 'not_applicable' &&
                      matchesLens(t)
                  ),
                  { grouped: true }
                )
              }
              className="font-normal text-muted-foreground underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {domainShown
                ? `— ${domainShown.covered}/${domainShown.applicable} covered (${domainShown.pct}%) with current filters`
                : `— ${domain.covered}/${domain.applicable} covered (${domain.strict_pct}%)`}
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
                const inTactic = byDomainTactic.get(`${domainKey}:${tactic.id}`) ?? [];
                // Platform/log-source lenses narrow what counts; state filter
                // only narrows what's drawn (matching the legend's behavior).
                const platCells = lensActive ? inTactic.filter(matchesLens) : inTactic;
                const tacticShown = lensActive ? countShown(platCells) : null;
                const cells = platCells.filter(
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
                            {(tacticShown ?? tactic).covered}/{(tacticShown ?? tactic).applicable} covered
                          </div>
                        </button>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs text-xs">
                        {tacticShown
                          ? `${tactic.name}: ${tacticShown.covered} of ${tacticShown.applicable} applicable techniques covered (${tacticShown.pct}%) with the current filters. Click for the list.`
                          : `${tactic.name}: ${tactic.covered} covered, ${tactic.partial} partial, ${tactic.not_covered} not covered, ${tactic.not_applicable} not applicable (strict ${tactic.strict_pct}%). Click for the list.`}
                      </TooltipContent>
                    </Tooltip>
    <div className="flex flex-col gap-1">
                      {(hideSubs
                        ? cells.filter((t) => !t.technique_id.includes('.'))
                        : cells
                      ).map((t) => {
                        const meta = STATE_META[t.state] ?? STATE_META.not_applicable;
                        const detail =
                          t.state === 'not_applicable' && t.na_reason
                            ? t.na_reason
                            : STATE_PLAIN[t.state] ?? meta.label;
                        const subs = hideSubs ? subStats.get(t.technique_id) : undefined;
                        const subTip =
                          subs && subs.applicable > 0
                            ? ` ${subs.covered} of ${subs.applicable} sub-techniques covered (hidden).`
                            : '';
                        const ruleCount = t.use_case_refs.length;
                        const depthTip =
                          t.state === 'covered'
                            ? ` ${ruleCount} rule${ruleCount === 1 ? '' : 's'} map${ruleCount === 1 ? 's' : ''} here.`
                            : '';
                        return (
                          <button
                            key={t.technique_id}
                            type="button"
                            onClick={() => onSelectTechnique(t.technique_id)}
                            data-tip={`${t.technique_id}${t.name ? ` — ${t.name}` : ''}\n${meta.label}: ${detail}.${depthTip}${subTip} Click for details.`}
                            onFocus={(e) => showTip(e.target as Element)}
                            onBlur={hideTip}
                            className={cn(
                              'flex w-full items-center gap-1 rounded px-1.5 py-1 text-left text-[11px] leading-tight transition-colors',
                              t.state === 'covered' ? depthCell(ruleCount) : meta.cell,
                              t.technique_id.includes('.') && 'ml-2 w-[calc(100%-0.5rem)]'
                            )}
                          >
                            <span className="min-w-0 flex-1 truncate">
                              <span className="font-medium">{t.technique_id}</span>
                              {t.name && <span className="opacity-85"> {t.name}</span>}
                            </span>
                            {subs && subs.applicable > 0 && (
                              <span className="shrink-0 rounded bg-black/15 px-1 text-[10px] tabular-nums">
                                {subs.covered}/{subs.applicable}
                              </span>
                            )}
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
        );
      })}

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

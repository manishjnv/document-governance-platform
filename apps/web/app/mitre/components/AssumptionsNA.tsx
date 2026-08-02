'use client';

import { useMemo } from 'react';
import { DOMAIN_LABELS, NaEntry, Summary, TechniqueResult } from '../lib';
import type { DrillHandler } from './ExecutiveBand';

/** Phase 14b: rules-by-mapping-status chips ("4 rules AI-tagged" → the
 * affected rules). Keys must exist in summary.counts to render. */
const RULE_COUNT_CHIPS: [string, string][] = [
  ['customer_tagged', 'tagged by you'],
  ['keyword_tagged', 'keyword-matched (no AI)'],
  ['ai_tagged', 'AI-tagged'],
  ['manual', 'reviewer-edited'],
  ['unmapped', 'unmapped'],
  ['invalid', 'with invalid tags'],
];

/** Assumptions list + the N/A appendix grouped by why each technique left
 * the denominator. Grouping keys off the backend's own reason phrasing
 * (derived reasons have fixed shapes; anything else is customer-declared
 * verbatim text). */
const GROUPS = [
  {
    key: 'domain',
    title: 'Whole matrix not applicable',
    blurb: 'These ATT&CK areas don’t apply to your environment at all.',
    match: (r: string) => r.includes('matrix:'),
  },
  {
    key: 'platform',
    title: 'Platform not in your environment',
    blurb: 'These techniques only work on platforms your inventory doesn’t include.',
    match: (r: string) => r.startsWith('targets '),
  },
  {
    key: 'deprecated',
    title: 'Deprecated by MITRE',
    blurb: 'MITRE no longer maintains these techniques, so they aren’t assessed.',
    match: (r: string) => r.startsWith('deprecated in ATT&CK'),
  },
  {
    key: 'customer',
    title: 'Excluded by you',
    blurb: 'You asked us not to assess these — each reason is shown exactly as you gave it.',
    match: () => true, // catch-all: customer-declared verbatim reasons
  },
];

export function AssumptionsNA({
  summary,
  techniques,
  onDrill,
  onDrillRules,
  onSelectTechnique,
}: {
  summary: Summary;
  techniques: TechniqueResult[];
  onDrill: DrillHandler;
  onDrillRules: (status: string | null, title: string) => void;
  onSelectTechnique: (techniqueId: string) => void;
}) {
  const grouped = useMemo(() => {
    const buckets = new Map<string, NaEntry[]>();
    for (const entry of summary.not_applicable) {
      const group = GROUPS.find((g) => g.match(entry.reason ?? ''))!;
      const list = buckets.get(group.key) ?? [];
      list.push(entry);
      buckets.set(group.key, list);
    }
    return buckets;
  }, [summary.not_applicable]);

  // One row per distinct REASON with its techniques as chips — 37 identical
  // "deprecated in ATT&CK v19.1" table rows collapse into one line.
  const byReason = (entries: NaEntry[]) => {
    const map = new Map<string, NaEntry[]>();
    for (const e of entries) {
      const key = e.reason ?? '';
      map.set(key, [...(map.get(key) ?? []), e]);
    }
    return [...map.entries()].sort((a, b) => b[1].length - a[1].length);
  };

  const techniqueByKey = useMemo(
    () => new Map(techniques.map((t) => [`${t.domain}:${t.technique_id}`, t])),
    [techniques]
  );

  const ruleChips = RULE_COUNT_CHIPS.filter(
    ([key]) => (summary.counts?.[key] ?? 0) > 0
  );

  // Phase 14g intake effect: which gaps your industry/actors prioritized.
  const threatIds = useMemo(
    () =>
      new Set(
        summary.gaps
          .filter((g) => (g.threat_relevance?.length ?? 0) > 0)
          .map((g) => g.technique_id)
      ),
    [summary.gaps]
  );

  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-2 text-sm font-semibold">Assumptions made in this assessment</h3>
        <p className="mb-2 text-xs text-muted-foreground">
          Read these before trusting the numbers — they describe what we had to assume or
          could not verify.
        </p>
        {/* Phase 14b: the rule counts behind the tagging assumptions — each
            opens the affected rules. */}
        {ruleChips.length > 0 && (
          <div className="mb-3 flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-muted-foreground">
              Your {summary.counts?.use_cases ?? 0} rules:
            </span>
            {ruleChips.map(([key, label]) => {
              const count = summary.counts[key];
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() =>
                    onDrillRules(
                      key,
                      `${count} rule${count === 1 ? '' : 's'} ${label}`
                    )
                  }
                  className="rounded-full border bg-muted/40 px-2 py-0.5 font-medium transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {count} {label}
                </button>
              );
            })}
            {threatIds.size > 0 && (
              <button
                type="button"
                onClick={() =>
                  onDrill(
                    `${threatIds.size} gaps prioritized by your threat profile`,
                    techniques.filter((t) => threatIds.has(t.technique_id)),
                    {
                      subtitle:
                        'Your declared industry and threat actors lifted these within their priority tier — ordering only, never the coverage score.',
                    }
                  )
                }
                className="rounded-full border border-violet-200 bg-violet-100 px-2 py-0.5 font-medium text-violet-800 transition-colors hover:bg-violet-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {threatIds.size} threat-profile matches
              </button>
            )}
          </div>
        )}
        <div className="grid gap-1.5 lg:grid-cols-2">
          {summary.assumptions.map((assumption, i) => (
            <div
              key={i}
              className="rounded-md border-l-2 border-primary/50 bg-muted/30 px-3 py-1.5 text-xs leading-snug"
            >
              {assumption}
            </div>
          ))}
          {summary.assumptions.length === 0 && (
            <p className="text-sm text-muted-foreground">No assumptions were needed.</p>
          )}
        </div>
      </section>

      <section>
        <h3 className="mb-1 text-sm font-semibold">
          Not-applicable techniques ({summary.not_applicable.length})
        </h3>
        <p className="mb-3 text-xs text-muted-foreground">
          These leave the coverage denominator — the headline percentage makes no claim
          about them. Grouped by reason; click any technique for its details.
        </p>
        <div className="grid gap-3 lg:grid-cols-2">
          {GROUPS.map((group) => {
            const entries = grouped.get(group.key) ?? [];
            if (entries.length === 0) return null;
            return (
              <div key={group.key} className="flex flex-col rounded-md border p-3">
                <div className="mb-0.5 flex items-baseline justify-between gap-2">
                  <h4 className="text-xs font-semibold">{group.title}</h4>
                  <button
                    type="button"
                    onClick={() =>
                      onDrill(
                        `${group.title} (${entries.length})`,
                        entries
                          .map(
                            (e) =>
                              techniqueByKey.get(`${e.domain}:${e.technique_id}`) ?? {
                                technique_id: e.technique_id,
                                domain: e.domain,
                                tactics: [],
                                state: 'not_applicable',
                                na_reason: e.reason,
                                use_case_refs: [],
                              }
                          )
                          .filter((t): t is TechniqueResult => t !== null),
                        { subtitle: group.blurb }
                      )
                    }
                    className="shrink-0 text-[11px] font-medium text-muted-foreground underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {entries.length} techniques
                  </button>
                </div>
                <p className="mb-2 text-[11px] text-muted-foreground">{group.blurb}</p>
                <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
                  {byReason(entries).map(([reason, list]) => (
                    <div key={reason}>
                      <p className="text-[11px] leading-snug text-muted-foreground">
                        {reason}{' '}
                        {list.length > 1 && (
                          <span className="text-muted-foreground/70">({list.length})</span>
                        )}
                      </p>
                      <div className="mt-0.5 flex flex-wrap gap-1">
                        {list.map((e) => (
                          <button
                            key={`${e.domain}:${e.technique_id}`}
                            type="button"
                            onClick={() => onSelectTechnique(e.technique_id)}
                            title={`${DOMAIN_LABELS[e.domain] ?? e.domain} — click for details`}
                            className="rounded border bg-muted/30 px-1.5 py-0.5 text-[10px] font-medium transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          >
                            {e.technique_id}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

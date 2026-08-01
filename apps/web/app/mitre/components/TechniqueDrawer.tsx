'use client';

import { useMemo } from 'react';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { Summary, TechniqueResult, UseCaseItem } from '../lib';
import { StateBadge } from './StateBadge';

/** Slide-over detail for one technique: state, tactics, N/A reason, and the
 * detection rules mapped to it (with confidence + customer/AI source). */
export function TechniqueDrawer({
  techniqueId,
  onClose,
  techniques,
  summary,
  useCases,
  useCasesTruncated,
}: {
  techniqueId: string | null;
  onClose: () => void;
  techniques: TechniqueResult[];
  summary: Summary;
  useCases: UseCaseItem[];
  useCasesTruncated: boolean;
}) {
  const technique = techniques.find((t) => t.technique_id === techniqueId) ?? null;

  const tacticNames = useMemo(() => {
    if (!technique) return [];
    const domain = summary.domains[technique.domain];
    if (!domain) return technique.tactics;
    return technique.tactics.map(
      (id) => domain.tactics.find((t) => t.id === id)?.name ?? id
    );
  }, [technique, summary]);

  const mappedRules = useMemo(() => {
    if (!technique) return [];
    return useCases
      .map((uc) => {
        const mapping = uc.mappings.find((m) => m.technique_id === technique.technique_id);
        return mapping ? { uc, mapping } : null;
      })
      .filter((x): x is { uc: UseCaseItem; mapping: UseCaseItem['mappings'][number] } => x !== null);
  }, [technique, useCases]);

  const gap = technique
    ? summary.gaps.find((g) => g.technique_id === technique.technique_id)
    : null;
  const recommendation = technique
    ? summary.narrative.gap_recommendations[technique.technique_id]
    : null;

  return (
    <Sheet open={techniqueId !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full overflow-y-auto p-5 sm:max-w-md">
        {technique && (
          <>
            <SheetTitle className="flex flex-wrap items-center gap-2 text-base">
              {technique.technique_id}
              <StateBadge state={technique.state} />
            </SheetTitle>
            <div className="mt-1 text-xs text-muted-foreground">
              {tacticNames.join(' · ')}
            </div>

            {technique.na_reason && (
              <div className="mt-4 rounded-md bg-muted/60 p-3 text-sm">
                <div className="mb-1 text-xs font-semibold text-muted-foreground">
                  Why this doesn&apos;t count toward coverage
                </div>
                {technique.na_reason}
              </div>
            )}

            {recommendation && (
              <div className="mt-4 rounded-md bg-sky-50 p-3 text-sm">
                <div className="mb-1 text-xs font-semibold text-sky-800">Recommendation</div>
                {recommendation}
              </div>
            )}
            {!recommendation && gap && (
              <div className="mt-4 rounded-md bg-sky-50 p-3 text-sm">
                <div className="mb-1 text-xs font-semibold text-sky-800">Recommendation</div>
                {gap.hint}
              </div>
            )}

            <div className="mt-5">
              <div className="mb-2 text-xs font-semibold text-muted-foreground">
                Detection rules mapped here ({mappedRules.length})
              </div>
              {mappedRules.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  None of your uploaded rules map to this technique.
                </p>
              )}
              <div className="space-y-2">
                {mappedRules.map(({ uc, mapping }) => (
                  <div key={uc.use_case_id} className="rounded-md border p-2.5 text-sm">
                    <div className="font-medium leading-snug">{uc.name}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-muted-foreground">
                      <span>{uc.enabled === false ? 'Disabled rule' : uc.enabled === true ? 'Enabled' : 'Status unknown'}</span>
                      <span>{mapping.source === 'customer' ? 'Tagged by you' : 'AI-mapped'}</span>
                      <span title="How sure the mapping is (1.0 = your own tag)">
                        confidence {mapping.confidence}
                      </span>
                      {uc.log_source && <span>{uc.log_source}</span>}
                    </div>
                    {mapping.rationale && (
                      <p className="mt-1 text-xs text-muted-foreground">{mapping.rationale}</p>
                    )}
                  </div>
                ))}
              </div>
              {useCasesTruncated && (
                <p className="mt-2 text-[11px] text-muted-foreground">
                  Showing mappings from the first 500 rules only.
                </p>
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

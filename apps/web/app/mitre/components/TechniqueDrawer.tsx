'use client';

import { useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { SOURCE_META, Summary, TechniqueResult, UseCaseItem } from '../lib';
import { StateBadge } from './StateBadge';

/** Slide-over detail for one technique: state, tactics, N/A reason, and the
 * detection rules mapped to it (with confidence + customer/AI source).
 * Admin/reviewer users can correct mappings (Phase 10): remove a wrong
 * mapping from a rule, or map another rule to this technique — the parent
 * page performs the PATCH and refreshes the results. */
export function TechniqueDrawer({
  techniqueId,
  onClose,
  techniques,
  summary,
  useCases,
  useCasesTruncated,
  canEdit,
  onEditMappings,
}: {
  techniqueId: string | null;
  onClose: () => void;
  techniques: TechniqueResult[];
  summary: Summary;
  useCases: UseCaseItem[];
  useCasesTruncated: boolean;
  canEdit: boolean;
  onEditMappings: (useCaseId: string, techniqueIds: string[]) => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState('');
  const [addRuleId, setAddRuleId] = useState('');

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

  const unmappedRules = useMemo(() => {
    if (!technique) return [];
    return useCases.filter(
      (uc) => !uc.mappings.some((m) => m.technique_id === technique.technique_id)
    );
  }, [technique, useCases]);

  const applyEdit = async (useCaseId: string, techniqueIds: string[]) => {
    setSaving(true);
    setEditError('');
    try {
      await onEditMappings(useCaseId, techniqueIds);
      setAddRuleId('');
    } catch (err: any) {
      setEditError(err?.message || 'Could not save the mapping change');
    } finally {
      setSaving(false);
    }
  };

  const removeMapping = (uc: UseCaseItem) =>
    applyEdit(
      uc.use_case_id,
      uc.mappings
        .map((m) => m.technique_id)
        .filter((id) => id !== technique?.technique_id)
    );

  const addMapping = () => {
    const uc = useCases.find((u) => u.use_case_id === addRuleId);
    if (!uc || !technique) return;
    applyEdit(uc.use_case_id, [
      ...uc.mappings.map((m) => m.technique_id),
      technique.technique_id,
    ]);
  };

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
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-medium leading-snug">{uc.name}</div>
                      {canEdit && (
                        <Tooltip delayDuration={150}>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              aria-label={`Remove the ${technique.technique_id} mapping from ${uc.name}`}
                              disabled={saving}
                              onClick={() => removeMapping(uc)}
                              className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:bg-rose-50 hover:text-rose-700 disabled:opacity-50"
                            >
                              <X size={14} aria-hidden="true" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs text-xs">
                            Remove this mapping — the rule&apos;s remaining mappings are
                            kept and coverage is recomputed.
                          </TooltipContent>
                        </Tooltip>
                      )}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-muted-foreground">
                      <span>{uc.enabled === false ? 'Disabled rule' : uc.enabled === true ? 'Enabled' : 'Status unknown'}</span>
                      <Tooltip delayDuration={150}>
                        <TooltipTrigger asChild>
                          <span className="cursor-default underline decoration-dotted underline-offset-2">
                            {(SOURCE_META[mapping.source] ?? SOURCE_META.ai).label}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs text-xs">
                          {(SOURCE_META[mapping.source] ?? SOURCE_META.ai).tip}
                        </TooltipContent>
                      </Tooltip>
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

              {canEdit && unmappedRules.length > 0 && (
                <div className="mt-4 rounded-md border border-dashed p-2.5">
                  <div className="mb-1.5 text-xs font-semibold text-muted-foreground">
                    Map another rule to this technique
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={addRuleId}
                      onChange={(e) => setAddRuleId(e.target.value)}
                      disabled={saving}
                      aria-label="Rule to map to this technique"
                      className="h-8 min-w-0 flex-1 rounded-md border bg-background px-2 text-xs"
                    >
                      <option value="">Choose a rule…</option>
                      {unmappedRules.map((uc) => (
                        <option key={uc.use_case_id} value={uc.use_case_id}>
                          {uc.name}
                        </option>
                      ))}
                    </select>
                    <Button size="sm" variant="outline" disabled={saving || !addRuleId} onClick={addMapping}>
                      Add
                    </Button>
                  </div>
                  <p className="mt-1.5 text-[11px] text-muted-foreground">
                    The edit is recorded as &quot;Edited by reviewer&quot; and the
                    coverage numbers update immediately.
                  </p>
                </div>
              )}
              {editError && (
                <p role="alert" className="mt-2 text-xs text-destructive">
                  {editError}
                </p>
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

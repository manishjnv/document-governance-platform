'use client';

import { useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import {
  SOURCE_META,
  STRENGTH_META,
  STRENGTH_TIP,
  Summary,
  TechniqueExplain,
  TechniqueResult,
  UseCaseItem,
  strengthBucket,
} from '../lib';
import { StateBadge } from './StateBadge';
import { useSheetResize } from './useSheetResize';

/** Slide-over detail for one technique: state, tactics, N/A reason, and the
 * detection rules mapped to it (with confidence + customer/AI source).
 * Admin/reviewer users can correct mappings (Phase 10): remove a wrong
 * mapping from a rule, or map another rule to this technique — the parent
 * page performs the PATCH and refreshes the results. */
export function TechniqueDrawer({
  techniqueId,
  explain,
  onClose,
  techniques,
  summary,
  useCases,
  useCasesTruncated,
  canEdit,
  onEditMappings,
  toolCoverage,
}: {
  techniqueId: string | null;
  /** Phase 14a four-block explanation (null while loading / on fetch failure). */
  explain: TechniqueExplain | null;
  onClose: () => void;
  techniques: TechniqueResult[];
  summary: Summary;
  useCases: UseCaseItem[];
  useCasesTruncated: boolean;
  canEdit: boolean;
  onEditMappings: (useCaseId: string, techniqueIds: string[]) => Promise<void>;
  /** 2026-08-19: tool-native detection credit map (technique id -> tool
   * labels) — shows the MITRE-evaluated note on open/partial techniques. */
  toolCoverage?: Record<string, string[]> | null;
}) {
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState('');
  const [addRuleId, setAddRuleId] = useState('');
  const resize = useSheetResize();

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
      <SheetContent
        side="right"
        style={resize.style}
        className="w-full overflow-y-auto p-5 sm:max-w-md"
      >
        {resize.handle}
        {technique && (
          <>
            <SheetTitle className="flex flex-wrap items-center gap-2 text-base">
              {technique.technique_id}
              <StateBadge state={technique.state} />
              {typeof technique.strength === 'number' && (
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span
                      className={`inline-flex cursor-default items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${STRENGTH_META[strengthBucket(technique.strength)].chip}`}
                    >
                      {STRENGTH_META[strengthBucket(technique.strength)].label} · {technique.strength}/100
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">{STRENGTH_TIP}</TooltipContent>
                </Tooltip>
              )}
            </SheetTitle>
            <div className="mt-1 text-xs text-muted-foreground">
              {tacticNames.join(' · ')}
            </div>
            {technique.strength_rationale && (
              <p className="mt-1 text-xs text-muted-foreground">
                Detection strength: {technique.strength_rationale}
              </p>
            )}

            {(toolCoverage?.[technique.technique_id]?.length ?? 0) > 0 && (
              <div className="mt-3 rounded-md border border-blue-300 bg-blue-50 p-3 text-sm dark:border-blue-900 dark:bg-blue-950/40">
                <div className="mb-1 text-xs font-semibold text-blue-700 dark:text-blue-300">
                  Tool credit — MITRE-evaluated
                </div>
                {toolCoverage![technique.technique_id].join(', ')} was evaluated
                against this technique in MITRE ATT&amp;CK Evaluations
                (evals.mitre.org). Confirm the alert path in your SOC, or build
                the SIEM rule anyway — this never changes the coverage score.
              </div>
            )}

            {technique.na_reason && !explain && (
              <div className="mt-4 rounded-md bg-muted/60 p-3 text-sm">
                <div className="mb-1 text-xs font-semibold text-muted-foreground">
                  Why this doesn&apos;t count toward coverage
                </div>
                {technique.na_reason}
              </div>
            )}

            {/* Phase 14a: the four plain-language blocks (any state). */}
            {explain && (
              <div className="mt-4 space-y-3">
                <div className="rounded-md border p-3 text-sm">
                  <div className="mb-1 text-xs font-semibold text-muted-foreground">
                    What is this?
                  </div>
                  <div className="font-medium leading-snug">{explain.name}</div>
                  {explain.what.definition && (
                    <p className="mt-1">{explain.what.definition}</p>
                  )}
                  {explain.what.attacker_use && (
                    <p className="mt-1 text-muted-foreground">
                      Attackers use this to {explain.what.attacker_use}
                    </p>
                  )}
                </div>

                <div className="rounded-md border p-3 text-sm">
                  <div className="mb-1 text-xs font-semibold text-muted-foreground">
                    {explain.state === 'partial' || explain.state === 'not_covered'
                      ? 'Where is the gap?'
                      : 'Where this fits'}
                  </div>
                  {explain.where.tactics.map(
                    (t) =>
                      t.line && (
                        <p key={t.id} className="leading-snug">
                          This is {/^[aeiou]/i.test(t.name) ? 'an' : 'a'}{' '}
                          <span className="font-medium">{t.name}</span>{' '}
                          technique — {t.line}.
                        </p>
                      )
                  )}
                  {explain.where.via ? (
                    <p className="mt-1 text-muted-foreground">
                      A log source you already collect —{' '}
                      <span className="font-medium">{explain.where.via}</span> —
                      could see this activity.
                    </p>
                  ) : (
                    explain.where.feasibility_hint && (
                      <p className="mt-1 text-muted-foreground">
                        Telemetry: {explain.where.feasibility_hint}.
                      </p>
                    )
                  )}
                  {/* ICS techniques carry a literal "None" platform and PRE is
                      an environment-independent marker — neither is a real
                      platform, so hide them from the display. */}
                  {explain.where.platforms.filter((p) => p !== 'None' && p !== 'PRE')
                    .length > 0 && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Applies to:{' '}
                      {explain.where.platforms
                        .filter((p) => p !== 'None' && p !== 'PRE')
                        .join(', ')}
                    </p>
                  )}
                  {/* Phase 14g: why this technique is in scope for YOU */}
                  {(explain.where.in_scope_because?.length ?? 0) > 0 && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      In scope because of your inventory:{' '}
                      {explain.where.in_scope_because!
                        .map((e) => `'${e.entry}'`)
                        .join(', ')}
                    </p>
                  )}
                </div>

                <div className="rounded-md bg-muted/60 p-3 text-sm">
                  <div className="mb-1 text-xs font-semibold text-muted-foreground">
                    {explain.state === 'covered'
                      ? 'Why this counts as covered'
                      : explain.state === 'not_applicable'
                        ? "Why this doesn't count toward coverage"
                        : 'Why is it a gap?'}
                  </div>
                  {explain.why}
                </div>

                <div className="rounded-md border p-3 text-sm">
                  <div className="mb-1 text-xs font-semibold text-muted-foreground">
                    What would good look like?
                  </div>
                  {explain.good.sketch ? (
                    <p>{explain.good.sketch}</p>
                  ) : (
                    <p className="text-muted-foreground">
                      No curated detection sketch for this technique
                      {explain.where.feasibility_hint
                        ? ` — ${explain.where.feasibility_hint}.`
                        : '.'}
                    </p>
                  )}
                  {explain.good.closest_rule && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Starting point: copy your rule{' '}
                      <span className="font-medium">
                        &apos;{explain.good.closest_rule.rule_name}&apos;
                      </span>{' '}
                      ({explain.good.closest_rule.technique_id}{' '}
                      {explain.good.closest_rule.technique_name}).
                    </p>
                  )}
                  {/* Phase 14g: expected vs actual telemetry */}
                  {(explain.where.expected_telemetry?.length ?? 0) > 0 && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Telemetry ATT&amp;CK expects for this technique:{' '}
                      {explain.where.expected_telemetry!.join(', ')}
                      {explain.where.via
                        ? ` — your '${explain.where.via}' can provide it.`
                        : ' — none of your onboarded log sources matches it yet.'}
                    </p>
                  )}
                  {/* Phase 14h: what does my query actually need, per log source */}
                  {explain.good.telemetry.length > 0 && (
                    <div className="mt-2 space-y-1.5 border-t pt-2">
                      {explain.good.telemetry.map((t) =>
                        t.fields.length > 0 ? (
                          <p key={t.component} className="text-xs">
                            <span className="font-medium">{t.component}:</span>{' '}
                            your query needs {t.fields.join(', ')}. {t.where}
                            <span className="mt-0.5 block text-muted-foreground">
                              {t.gotcha}
                            </span>
                          </p>
                        ) : (
                          <p key={t.component} className="text-xs text-muted-foreground">
                            {t.component}: no curated field guidance for this log source yet.
                          </p>
                        )
                      )}
                    </div>
                  )}
                </div>
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

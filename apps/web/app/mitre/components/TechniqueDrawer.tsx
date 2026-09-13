'use client';

import { useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { AlertBanner, Chip, EmptyState } from '@/components/app';
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

// Tone mapping for the detection-strength Chip — retargeted from
// STRENGTH_META's pre-redesign chip classes (lib.ts) to design tokens.
const STRENGTH_TONE: Record<string, 'ok' | 'med' | 'crit'> = {
  strong: 'ok',
  moderate: 'med',
  weak: 'crit',
};

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
  onAttest,
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
  /** Attest the tool's alert path: counts this technique as covered via a
   * generated tool-attested rule row (admin/reviewer only). */
  onAttest?: (techniqueId: string, tool: string) => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState('');
  const [addRuleId, setAddRuleId] = useState('');
  const [attesting, setAttesting] = useState<string | null>(null);
  const [attestError, setAttestError] = useState('');
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
        grip={resize.handle}
        className="flex w-full flex-col gap-0 p-0 sm:max-w-md"
      >
        {technique && (
          <>
            <div className="border-b border-border px-6 pb-3 pt-4">
              <SheetTitle className="flex flex-wrap items-center gap-2 text-base font-semibold">
                <span className="font-mono">{technique.technique_id}</span>
                <StateBadge state={technique.state} />
                {typeof technique.strength === 'number' && (
                  <Chip
                    tone={STRENGTH_TONE[strengthBucket(technique.strength)]}
                    tip={STRENGTH_TIP}
                  >
                    {STRENGTH_META[strengthBucket(technique.strength)].label} · {technique.strength}/100
                  </Chip>
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
            </div>

            <div className="flex-1 space-y-4 overflow-y-auto px-6 py-4">
            {(toolCoverage?.[technique.technique_id]?.length ?? 0) > 0 && (
              <AlertBanner kind="blue">
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em]">
                  Tool credit — MITRE-evaluated
                </div>
                {toolCoverage![technique.technique_id].join(', ')} was evaluated
                against this technique in MITRE ATT&amp;CK Evaluations
                (evals.mitre.org). Credit alone never changes the coverage
                score — attesting the alert path does.
                {canEdit && onAttest && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {toolCoverage![technique.technique_id].map((tool) => (
                      <button
                        key={tool}
                        type="button"
                        disabled={attesting !== null}
                        onClick={async () => {
                          setAttestError('');
                          setAttesting(tool);
                          try {
                            await onAttest(technique.technique_id, tool);
                          } catch (err) {
                            setAttestError(
                              err instanceof Error ? err.message : 'Attestation failed'
                            );
                          } finally {
                            setAttesting(null);
                          }
                        }}
                        className="rounded-md border border-primary/40 bg-card px-2.5 py-1 text-xs font-medium text-primary transition-colors hover:bg-accent-soft disabled:opacity-50"
                      >
                        {attesting === tool
                          ? 'Attesting…'
                          : `We monitor ${tool}'s alerts — count as covered`}
                      </button>
                    ))}
                  </div>
                )}
                {attestError && <AlertBanner kind="error" className="mt-2">{attestError}</AlertBanner>}
              </AlertBanner>
            )}

            {technique.na_reason && !explain && (
              <div className="rounded-lg border border-border p-3 text-sm">
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">
                  Why this doesn&apos;t count toward coverage
                </div>
                {technique.na_reason}
              </div>
            )}

            {/* Phase 14a: the four plain-language blocks (any state). */}
            {explain && (
              <div className="space-y-3">
                <div className="rounded-lg border border-border p-3 text-sm">
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">
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

                <div className="rounded-lg border border-border p-3 text-sm">
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">
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

                <div className="rounded-lg bg-muted/60 p-3 text-sm">
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">
                    {explain.state === 'covered'
                      ? 'Why this counts as covered'
                      : explain.state === 'not_applicable'
                        ? "Why this doesn't count toward coverage"
                        : 'Why is it a gap?'}
                  </div>
                  {explain.why}
                </div>

                <div className="rounded-lg border border-border p-3 text-sm">
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">
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
              <AlertBanner kind="info">
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em]">Recommendation</div>
                {recommendation}
              </AlertBanner>
            )}
            {!recommendation && gap && (
              <AlertBanner kind="info">
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em]">Recommendation</div>
                {gap.hint}
              </AlertBanner>
            )}

            <div>
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">
                Detection rules mapped here ({mappedRules.length})
              </div>
              {mappedRules.length === 0 && <EmptyState title="None of your uploaded rules map to this technique." />}
              <div className="space-y-2">
                {mappedRules.map(({ uc, mapping }) => (
                  <div key={uc.use_case_id} className="rounded-lg border border-border px-3 py-2 text-[13px]">
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
                              className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:bg-sev-crit-soft hover:text-sev-crit disabled:opacity-50"
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
                      <Chip tone="neutral" xs tip={(SOURCE_META[mapping.source] ?? SOURCE_META.ai).tip}>
                        {(SOURCE_META[mapping.source] ?? SOURCE_META.ai).label}
                      </Chip>
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
                <div className="mt-4 rounded-lg border border-dashed border-line2 p-2.5">
                  <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">
                    Map another rule to this technique
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={addRuleId}
                      onChange={(e) => setAddRuleId(e.target.value)}
                      disabled={saving}
                      aria-label="Rule to map to this technique"
                      className="h-8 min-w-0 flex-1 rounded-md border border-input bg-card px-2 text-xs"
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
                <AlertBanner kind="error" className="mt-2">
                  {editError}
                </AlertBanner>
              )}
            </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

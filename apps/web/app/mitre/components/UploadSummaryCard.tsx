'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, FileSpreadsheet } from 'lucide-react';
import { Assessment, Summary, UseCaseItem } from '../lib';

/** Phase 14g: one parsed environment entry's evidence line. */
interface EnvInterpretation {
  entry: string;
  sheet: string;
  interpretation: string;
}

/** Phase 14d: "What this assessment is based on" — the uploaded files and
 * the numbers derived from them, every number clickable (14b panels).
 * Phase 14g adds the expandable per-entry "how we read your inventory"
 * evidence list when the assessment was created after the parser gained it. */
export function UploadSummaryCard({
  assessment,
  summary,
  useCases,
  onDrillRules,
}: {
  assessment: Assessment;
  summary: Summary;
  useCases: UseCaseItem[];
  onDrillRules: (title: string, rules: UseCaseItem[]) => void;
}) {
  const [envOpen, setEnvOpen] = useState(false);
  const params = (assessment.params ?? {}) as {
    environment?: {
      platforms?: string[];
      has_ics_assets?: boolean;
      has_managed_mobile?: boolean;
      inventory_provided?: boolean;
    };
    environment_lists?: {
      log_sources?: string[];
      tooling?: string[];
      crown_jewels?: string[];
      interpretations?: EnvInterpretation[];
    };
    parse_assumptions?: string[];
  };
  const files = assessment.files ?? [];
  const ucFile = files.find((f) => f.kind === 'use_cases');
  const envFile = files.find((f) => f.kind === 'environment');
  const counts = summary.counts ?? {};
  const disabledRules = useCases.filter((uc) => uc.enabled === false);
  const env = params.environment ?? {};
  const lists = params.environment_lists ?? {};
  const interpretations = lists.interpretations ?? [];
  const unmatchedNote = (params.parse_assumptions ?? []).find((a) =>
    a.startsWith('asset entries not mapped')
  );

  const splitChips: { key: string; label: string; status: string }[] = [
    { key: 'customer_tagged', label: 'tagged by you', status: 'customer_tagged' },
    { key: 'keyword_tagged', label: 'keyword-matched', status: 'keyword_tagged' },
    { key: 'ai_tagged', label: 'AI-tagged', status: 'ai_tagged' },
    { key: 'manual', label: 'reviewer-edited', status: 'manual' },
    { key: 'unmapped', label: 'unmapped', status: 'unmapped' },
    { key: 'invalid', label: 'invalid tags', status: 'invalid' },
  ].filter((c) => (counts[c.key] ?? 0) > 0);

  const chipCls =
    'rounded-full border bg-background px-2 py-0.5 text-[11px] font-medium transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

  return (
    <div className="rounded-md border bg-muted/20 p-3 text-sm">
      <div className="mb-2 text-xs font-semibold text-muted-foreground">
        What this assessment is based on
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <FileSpreadsheet size={14} className="shrink-0 text-muted-foreground" aria-hidden="true" />
            <span className="truncate font-medium">
              {ucFile?.filename ?? 'Detection rules'}
            </span>
            <button
              type="button"
              onClick={() => onDrillRules(`All ${counts.use_cases ?? useCases.length} rules`, useCases)}
              className={chipCls}
            >
              {counts.use_cases ?? useCases.length} rule
              {(counts.use_cases ?? useCases.length) === 1 ? '' : 's'}
            </button>
          </div>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {splitChips.map((c) => (
              <button
                key={c.key}
                type="button"
                onClick={() =>
                  onDrillRules(
                    `${counts[c.key]} rule${counts[c.key] === 1 ? '' : 's'} ${c.label}`,
                    useCases.filter((uc) => uc.mapping_status === c.status)
                  )
                }
                className={chipCls}
              >
                {counts[c.key]} {c.label}
              </button>
            ))}
            {disabledRules.length > 0 && (
              <button
                type="button"
                onClick={() =>
                  onDrillRules(
                    `${disabledRules.length} disabled rule${disabledRules.length === 1 ? '' : 's'}`,
                    disabledRules
                  )
                }
                className={chipCls}
              >
                {disabledRules.length} disabled
              </button>
            )}
          </div>
        </div>

        <div className="min-w-0">
          {envFile ? (
            <>
              <div className="flex flex-wrap items-center gap-1.5">
                <FileSpreadsheet size={14} className="shrink-0 text-muted-foreground" aria-hidden="true" />
                <span className="truncate font-medium">{envFile.filename}</span>
                {env.has_ics_assets && (
                  <span className="rounded-full border px-2 py-0.5 text-[11px]">OT/ICS</span>
                )}
                {env.has_managed_mobile && (
                  <span className="rounded-full border px-2 py-0.5 text-[11px]">Managed mobile</span>
                )}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Platforms: {(env.platforms ?? []).join(', ') || 'none detected'}
                {' · '}
                {(lists.log_sources ?? []).length} log source
                {(lists.log_sources ?? []).length === 1 ? '' : 's'}
                {' · '}
                {(lists.tooling ?? []).length} tooling
                {' · '}
                {(lists.crown_jewels ?? []).length} crown jewel
                {(lists.crown_jewels ?? []).length === 1 ? '' : 's'}
              </p>
              {unmatchedNote && (
                <p className="mt-1 text-xs text-amber-700">{unmatchedNote}</p>
              )}
              {interpretations.length > 0 && (
                <div className="mt-1.5">
                  <button
                    type="button"
                    onClick={() => setEnvOpen((v) => !v)}
                    aria-expanded={envOpen}
                    className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {envOpen ? (
                      <ChevronDown size={13} aria-hidden="true" />
                    ) : (
                      <ChevronRight size={13} aria-hidden="true" />
                    )}
                    How we read your inventory ({interpretations.length} entries)
                  </button>
                  {envOpen && (
                    <ul className="mt-1.5 max-h-56 space-y-1 overflow-y-auto pr-1">
                      {interpretations.map((it, i) => (
                        <li key={i} className="rounded bg-background px-2 py-1 text-xs">
                          <span className="font-medium">{it.entry}</span>{' '}
                          <span className="text-muted-foreground">
                            ({it.sheet}) → {it.interpretation}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </>
          ) : (
            <p className="text-xs text-amber-700">
              No environment workbook was uploaded — the full ATT&CK matrices
              were assessed, so the coverage score is a lower bound.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

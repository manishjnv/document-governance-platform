/**
 * Shared types + display metadata for the MITRE assessment section.
 * Types mirror apps/api/app/mitre/router.py response shapes verbatim.
 * NOT an API client — pages keep their own inline axios calls (house rule).
 */

export interface DomainBrief {
  strict_pct: number | null;
  covered: number | null;
  applicable: number | null;
}

export interface AssessmentListItem {
  assessment_id: string;
  name: string;
  status: string;
  attack_version: string;
  created_at: string | null;
  completed_at: string | null;
  strict_pct: number | null;
  weighted_pct: number | null;
  domains_brief?: Record<string, DomainBrief>;
}

export interface CompareEntry {
  technique_id: string;
  name: string;
  domain: string;
  from: string;
  to: string;
}

export interface CompareResult {
  current: { assessment_id: string; name: string; completed_at: string | null; attack_version: string; strict_pct: number | null };
  baseline: { assessment_id: string; name: string; completed_at: string | null; attack_version: string; strict_pct: number | null };
  attack_version_mismatch: boolean;
  overall_delta: Record<string, number>;
  tactic_deltas: { domain: string; id: string; name: string; current_strict_pct: number; baseline_strict_pct: number; delta: number }[];
  newly_covered: CompareEntry[];
  regressed: CompareEntry[];
  na_changed: CompareEntry[];
}

export interface Rollup {
  covered: number;
  partial: number;
  not_covered: number;
  not_applicable: number;
  applicable: number;
  strict_pct: number;
  weighted_pct: number;
}

export interface TacticRollup extends Rollup {
  id: string;
  shortname: string;
  name: string;
}

export interface DomainSummary extends Rollup {
  tactics: TacticRollup[];
}

export interface Gap {
  technique_id: string;
  name: string;
  domain: string;
  state: string;
  tier: number;
  tactics: string[];
  feasibility: 'short' | 'mid' | 'long';
  via: string | null;
  category: string | null;
  hint: string;
  rank: number;
}

export interface Narrative {
  executive_summary: string;
  gap_recommendations: Record<string, string>;
  roadmap_prose: { short: string; mid: string; long: string };
  generated_by: 'ai' | 'template';
  model_used: string | null;
}

export interface NaEntry {
  technique_id: string;
  domain: string;
  reason: string;
}

export interface Summary {
  overall: Rollup;
  domains: Record<string, DomainSummary>;
  assumptions: string[];
  gaps: Gap[];
  roadmap: { short: Gap[]; mid: Gap[]; long: Gap[] };
  narrative: Narrative;
  not_applicable: NaEntry[];
  applicable_domains: string[];
  counts: Record<string, number>;
}

export interface TechniqueResult {
  technique_id: string;
  domain: string;
  tactics: string[];
  state: string;
  na_reason: string | null;
  use_case_refs: string[];
}

export interface Assessment {
  assessment_id: string;
  name: string;
  status: string;
  attack_version: string;
  params: Record<string, unknown> | null;
  summary: Summary | null;
  technique_results: TechniqueResult[] | null;
  error_message: string | null;
  created_at: string | null;
  completed_at: string | null;
}

export interface UseCaseMapping {
  technique_id: string;
  source: string;
  confidence: number;
  rationale?: string;
}

export interface UseCaseItem {
  use_case_id: string;
  row_ref: string;
  name: string;
  description: string | null;
  log_source: string | null;
  enabled: boolean | null;
  mappings: UseCaseMapping[];
  mapping_status: string;
}

export interface ParsePreview {
  assessment_id: string;
  name: string;
  status: string;
  attack_version: string;
  row_count: number;
  columns: Record<string, number>;
  sheet: string | null;
  headers: string[];
  sample_rows: string[][];
  tagged: number;
  untagged: number;
  invalid: number;
  extraction_pending: boolean;
  environment_provided: boolean;
  environment: {
    platforms: string[];
    has_ics_assets: boolean;
    has_managed_mobile: boolean;
    inventory_provided: boolean;
  };
  sheets_found: Record<string, string>;
  warnings: string[];
  assumptions: string[];
}

/** Plain-English display metadata per technique state. */
export const STATE_META: Record<
  string,
  { label: string; chip: string; cell: string; tip: string }
> = {
  covered: {
    label: 'Covered',
    chip: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    cell: 'bg-emerald-500/85 text-white hover:bg-emerald-600',
    tip: 'At least one enabled detection rule maps here with high confidence.',
  },
  partial: {
    label: 'Partial',
    chip: 'bg-amber-100 text-amber-800 border-amber-200',
    cell: 'bg-amber-400/90 text-amber-950 hover:bg-amber-500',
    tip: 'Only a disabled rule, a lower-confidence AI mapping, or a covered sub-technique reaches this — treat it as half-covered.',
  },
  not_covered: {
    label: 'Not covered',
    chip: 'bg-rose-100 text-rose-800 border-rose-200',
    cell: 'bg-rose-200/80 text-rose-950 hover:bg-rose-300',
    tip: 'No detection rule maps here — this technique is a gap.',
  },
  not_applicable: {
    label: 'N/A',
    chip: 'bg-muted text-muted-foreground border-transparent',
    cell: 'bg-muted/60 text-muted-foreground hover:bg-muted',
    tip: "Doesn't apply to your environment (or was excluded by you), so it doesn't count toward the coverage percentage.",
  },
};

export const FEASIBILITY_META: Record<
  string,
  { label: string; chip: string; tip: string }
> = {
  short: {
    label: 'Short term',
    chip: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    tip: '0–3 months: the log source this detection needs is already onboarded — you can build it now.',
  },
  mid: {
    label: 'Mid term',
    chip: 'bg-sky-100 text-sky-800 border-sky-200',
    tip: '3–9 months: security tooling you already own can provide the needed telemetry — onboard it first, then build the detection.',
  },
  long: {
    label: 'Long term',
    chip: 'bg-slate-100 text-slate-700 border-slate-200',
    tip: '9–18 months: needs a new telemetry capability or bespoke detection engineering.',
  },
};

/** Plain-English display metadata per mapping source (technique drawer). */
export const SOURCE_META: Record<string, { label: string; tip: string }> = {
  customer: {
    label: 'Tagged by you',
    tip: 'This mapping comes from the MITRE technique tag in your uploaded file.',
  },
  keyword: {
    label: 'Matched by rule',
    tip: "The rule's name or logic contains an exact ATT&CK technique name or a well-known attacker tool/command, so it was mapped automatically — no AI involved.",
  },
  ai: {
    label: 'AI-mapped',
    tip: 'An AI model read the rule and suggested this technique — spot-check before relying on it.',
  },
  manual: {
    label: 'Edited by reviewer',
    tip: 'A reviewer manually set this mapping — it overrides the original tag, and coverage was recomputed from it.',
  },
};

export const TIER_TIPS: Record<number, string> = {
  1: 'Priority 1: top-prevalence technique across independent threat reports — near-universal in real intrusions.',
  2: 'Priority 2: very common — a standard part of ransomware and intrusion playbooks.',
  3: 'Priority 3: common supporting behavior seen in many incidents.',
  4: 'Unranked: not on the curated priority list — rank below priority 3.',
};

export const STATUS_META: Record<string, { label: string; chip: string }> = {
  pending: { label: 'Not run yet', chip: 'bg-muted text-muted-foreground border-transparent' },
  running: { label: 'Running', chip: 'bg-sky-100 text-sky-800 border-sky-200' },
  completed: { label: 'Completed', chip: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
  failed: { label: 'Failed', chip: 'bg-rose-100 text-rose-800 border-rose-200' },
};

export const DOMAIN_LABELS: Record<string, string> = {
  enterprise: 'Enterprise',
  ics: 'ICS / OT',
  mobile: 'Mobile',
};

export function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

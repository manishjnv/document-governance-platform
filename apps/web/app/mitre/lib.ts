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
  /** Phase 13d: present when the rules were pulled from a SIEM. */
  siem?: { platform: string | null; trigger: string | null } | null;
}

/** Phase 13d: a saved SIEM connection + pull health (admin view). */
export interface SiemConnection {
  connection_id: string;
  name: string;
  platform: string;
  config: Record<string, string>;
  key_version: number;
  secret_set: boolean;
  schedule_cadence: 'daily' | 'weekly' | null;
  schedule_hour_utc: number | null;
  schedule_weekday: number | null;
  last_scheduled_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  health: {
    last_pull_at: string | null;
    last_status: string | null;
    last_error: string | null;
    scheduled_failure_streak: number;
  };
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
  /** Phase 11: industry/actor labels this gap is relevant to (or absent). */
  threat_relevance?: string[] | null;
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
  /** Phase 12 detection-strength rollup — separate from coverage %. */
  quality?: {
    scored: number;
    avg_strength: number | null;
    strong: number;
    moderate: number;
    weak: number;
  };
  counts: Record<string, number>;
}

export interface TechniqueResult {
  technique_id: string;
  domain: string;
  tactics: string[];
  state: string;
  na_reason: string | null;
  use_case_refs: string[];
  /** Phase 12: 0-100 detection strength (covered/partial with direct rules only). */
  strength?: number | null;
  strength_rationale?: string | null;
  /** Phase 14b: technique name, enriched by the API at read time. */
  name?: string | null;
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

/** Phase 14a: plain-language four-block explanation for one technique. */
export interface TechniqueExplain {
  technique_id: string;
  name: string | null;
  state: string;
  what: { definition: string | null; attacker_use: string | null; curated: boolean };
  where: {
    domain: string;
    tactics: { id: string; name: string; line: string | null }[];
    platforms: string[];
    via: string | null;
    feasibility: string | null;
    feasibility_hint: string | null;
  };
  why: string;
  good: {
    sketch: string | null;
    detection_hint: string | null;
    closest_rule: {
      technique_id: string;
      technique_name: string | null;
      rule_name: string;
    } | null;
  };
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

/** Phase 12 detection-strength buckets. Distinct from coverage: coverage
 * says a rule EXISTS; strength estimates how well it would actually detect. */
export function strengthBucket(score: number): 'strong' | 'moderate' | 'weak' {
  if (score >= 75) return 'strong';
  if (score >= 45) return 'moderate';
  return 'weak';
}

export const STRENGTH_META: Record<string, { label: string; chip: string }> = {
  strong: { label: 'Strong', chip: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
  moderate: { label: 'Moderate', chip: 'bg-amber-100 text-amber-800 border-amber-200' },
  weak: { label: 'Weak', chip: 'bg-rose-100 text-rose-800 border-rose-200' },
};

export const STRENGTH_TIP =
  'Detection strength estimates how well the mapped rules would actually catch this technique (rule provenance, enabled state, and whether the logic references the telemetry the technique expects). It is separate from the coverage % — coverage only says whether a rule exists.';

/** Phase 14b: short plain phrase per state for drill-down list rows. */
export const STATE_PLAIN: Record<string, string> = {
  covered: 'A rule detects this',
  partial: 'Half-covered',
  not_covered: 'No rule detects this',
  not_applicable: "Doesn't apply to your environment",
};

/** Phase 14b: mapping-status in plain words (rule list panel + wizard). */
export const MAPPING_STATUS_PLAIN: Record<string, string> = {
  customer_tagged: 'Tagged by you',
  keyword_tagged: 'Matched by rule keyword',
  ai_tagged: 'AI-mapped — verify',
  manual: 'Edited by reviewer',
  unmapped: 'Not mapped to any technique',
  invalid: 'Tags invalid — treated as untagged',
};

/** Phase 14b: one short client-side why-phrase for a partial technique,
 * derived from the loaded rules (the drawer's explain endpoint stays the
 * authoritative, richer version). */
export function partialWhyBrief(
  useCases: UseCaseItem[],
  techniqueId: string
): string | null {
  const mapped = useCases
    .map((uc) => {
      const m = uc.mappings.find((x) => x.technique_id === techniqueId);
      return m ? { uc, m } : null;
    })
    .filter((x): x is { uc: UseCaseItem; m: UseCaseMapping } => x !== null);
  const disabled = mapped.find(({ uc }) => uc.enabled === false);
  if (disabled) return `rule '${disabled.uc.name}' is disabled`;
  const lowConf = mapped.find(({ m }) => m.confidence > 0 && m.confidence < 0.7);
  if (lowConf) {
    return `AI-tagged at ${Math.round(lowConf.m.confidence * 100)}% — confirm`;
  }
  if (mapped.length === 0) return 'only sub-techniques are covered';
  return null;
}

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

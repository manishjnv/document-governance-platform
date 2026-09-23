/**
 * Shared types + display metadata for the Code Security Review module.
 * Types mirror apps/api/app/codereview/router.py response shapes and
 * docs/planning/CODE_REVIEW_MODULE_REFERENCE.md section 3 verbatim.
 * NOT an API client — pages keep their own inline axios calls (house rule).
 */

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface DuplicateRef {
  file: string;
  line_start: number;
  line_end: number;
}

/** Scanner's own deep-analysis pass on its top findings by CVSS (fix-mode or report-only run). */
export interface FindingDeep {
  root_cause: string;
  gates: { source: string; sink: string; missing_control: string };
  remaining_risks: string[];
  recommendations: string[];
  summary: string;
}

export type FixStatus = 'fixed' | 'patch_rejected' | 'needs_review' | 'not_fixed' | 'not_attempted';
export type FixTests = 'broke_tests' | 'passed' | 'not_tested' | 'no_test_results';

/** Scanner's attempted-fix outcome for one finding (fix-mode run only). */
export interface FindingFix {
  status: FixStatus;
  scanner_verdict: string;
  policy_action: string | null;
  policy_reason: string;
  files: string[];
  patch: string;
  tests: FixTests | null;
  tests_detail: string;
}

export interface CodeReviewFinding {
  idx: number;
  title: string;
  severity: Severity;
  vuln_class: string;
  vuln_class_label: string;
  cwe: string | null;
  cvss_score: number | null;
  cvss_vector: string | null;
  cvss_rating: string | null;
  file: string;
  line_start: number;
  line_end: number;
  confidence: number;
  votes: number;
  verdict: 'TRUE_POSITIVE' | 'FALSE_POSITIVE' | null;
  verdict_confidence: number | null;
  verdict_reason: string;
  description: string;
  impact: string;
  exploit_scenario: string;
  preconditions: string[];
  recommendation: string;
  code_snippet: string;
  exploitability_notes: string;
  verifier_reasoning: string;
  offensive_priority: string | null;
  offensive_reason: string;
  source_ref: string | null;
  sink_ref: string | null;
  duplicates: DuplicateRef[];
  /** Present only for findings the scanner deep-verified (top findings by CVSS). */
  deep?: FindingDeep;
  /** Present only on findings the scanner attempted to fix (fix-mode run). */
  fix?: FindingFix;
}

export interface Chain {
  title: string;
  steps: number[];
  severity: string;
  narrative: string;
}

export interface RunExtrasTests {
  build: 'success' | 'failure' | null;
  suites: number;
  cases: number;
  failures: number;
  errors: number;
  skipped: number;
  failing: { test: string; message: string }[];
  not_run_modules: string[];
}

export interface RunExtrasCoverage {
  coverage_pct: number | null;
  files_in_scope: number | null;
  files_analyzed: number | null;
  chunks: number | null;
  duration_sec?: number | null;
  health: string[];
  threat_model: string;
}

/** Report-level rollup from an uploaded scan-run folder (findings.json/SARIF + triage/finding_case/report.md/JUnit/Maven). */
export interface RunExtras {
  mode: 'fix' | 'report-only' | null;
  deep_verified: number;
  total: number;
  fix_counts: Partial<Record<FixStatus, number>>;
  tests: RunExtrasTests | null;
  coverage: RunExtrasCoverage | null;
}

export interface CodeReviewReport {
  source_format: 'findings' | 'sarif';
  tool: string;
  tool_version: string | null;
  repo_name: string | null;
  git_sha: string | null;
  summary_text: string;
  degraded: boolean;
  degraded_reason: string;
  assumptions: string[];
  counts: {
    total: number;
    by_severity: Record<Severity, number>;
    by_vuln_class: Record<string, number>;
    by_file: Record<string, number>;
  };
  findings: CodeReviewFinding[];
  chains: Chain[];
  dropped_count: number;
  raw_findings_count: number;
  /** Present only when the upload was a whole scan-run folder with extras next to the report. */
  run_extras?: RunExtras;
  metrics: {
    duration_sec: number | null;
    total_files_in_scope: number | null;
    analyzed_files_unique: number | null;
    loc_scanned_by_language: Record<string, number> | null;
    true_positive_count: number | null;
    false_positive_count: number | null;
    total_tokens: number | null;
  };
  manifest: {
    target_git_sha: string | null;
    tool_version?: string | null;
    duration_sec: number | null;
    models: Record<string, { id: string; provider: string }>;
    total_cost_usd: number | null;
    total_tokens: number | null;
  } | null;
}

export interface CodeReviewListItem {
  review_id: string;
  /** Shared read-only demo review (visible to every signed-in user). */
  demo?: boolean;
  /** False when the review belongs to another org (demo) — hide rename/delete. */
  editable?: boolean;
  name: string;
  repo_label: string;
  git_sha: string | null;
  source_format: 'findings' | 'sarif';
  created_at: string | null;
  counts: {
    total: number;
    by_severity: Record<Severity, number>;
  };
}

export interface CodeReviewDetail extends CodeReviewListItem {
  report: CodeReviewReport;
}

export const SEVERITY_META: Record<
  Severity,
  { label: string; chip: string; dot: string; text: string; order: number }
> = {
  critical: { label: 'Critical', chip: 'bg-rose-100 text-rose-800 border-rose-200', dot: 'bg-rose-600', text: 'text-rose-700', order: 0 },
  high: { label: 'High', chip: 'bg-orange-100 text-orange-800 border-orange-200', dot: 'bg-orange-500', text: 'text-orange-600', order: 1 },
  medium: { label: 'Medium', chip: 'bg-amber-100 text-amber-800 border-amber-200', dot: 'bg-amber-500', text: 'text-amber-600', order: 2 },
  low: { label: 'Low', chip: 'bg-emerald-100 text-emerald-800 border-emerald-200', dot: 'bg-emerald-600', text: 'text-emerald-700', order: 3 },
  info: { label: 'Info', chip: 'bg-sky-100 text-sky-800 border-sky-200', dot: 'bg-sky-500', text: 'text-sky-700', order: 4 },
};

export type Verdict = NonNullable<CodeReviewFinding['verdict']>;

export const VERDICT_META: Record<Verdict, { label: string; chip: string; tooltip: string }> = {
  TRUE_POSITIVE: {
    label: 'Confirmed',
    chip: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    tooltip: 'Verifier: true positive',
  },
  FALSE_POSITIVE: {
    label: 'False positive',
    chip: 'bg-muted text-muted-foreground border-border',
    tooltip: 'Verifier: false positive',
  },
};

export const SOURCE_FORMAT_LABEL: Record<CodeReviewReport['source_format'], string> = {
  findings: 'findings.json',
  sarif: 'SARIF',
};

export const FIX_STATUS_META: Record<FixStatus, { label: string }> = {
  fixed: { label: 'Fixed (scanner accepted)' },
  patch_rejected: { label: 'Patch rejected by scanner policy' },
  needs_review: { label: 'Not fixed: needs manual review' },
  not_fixed: { label: 'Not fixed' },
  not_attempted: { label: 'Not attempted (report-only run)' },
};

export const FIX_TESTS_META: Record<FixTests, { label: string }> = {
  broke_tests: { label: 'Fix broke a test' },
  passed: { label: 'Tests passed' },
  not_tested: { label: 'No test results for this code' },
  no_test_results: { label: 'No test results uploaded' },
};

export const DEEP_VERIFIED_LABEL = 'Deep-verified';

/** "<n> of <total> findings were deep-verified…" report-level note, per the contract's exact wording. */
export function deepVerifiedNote(deepVerified: number, total: number): string {
  return `${deepVerified} of ${total} findings were deep-verified by the scanner (its top findings by CVSS); the rest come from the first review pass only.`;
}

export interface FindingFilter {
  severity?: Severity | null;
  klass?: string | null;
  verdict?: Verdict | 'none' | null;
  query?: string;
}

/** Pure filter used by the results table, chains tab and prev/next navigation. */
export function filterFindings(findings: CodeReviewFinding[], f: FindingFilter): CodeReviewFinding[] {
  const q = (f.query ?? '').trim().toLowerCase();
  return findings.filter((x) => {
    if (f.severity && x.severity !== f.severity) return false;
    if (f.klass && x.vuln_class !== f.klass) return false;
    if (f.verdict === 'none' ? x.verdict !== null : f.verdict && x.verdict !== f.verdict) return false;
    if (!q) return true;
    return (
      x.title.toLowerCase().includes(q) ||
      x.file.toLowerCase().includes(q) ||
      (x.cwe ?? '').toLowerCase().includes(q)
    );
  });
}

/** Deterministic one-line executive headline: highest severity present + top file. */
export function deriveHeadline(report: CodeReviewReport): string {
  const total = report.counts.total;
  if (total === 0) return 'No findings were reported for this scan.';
  const top = SEVERITY_ORDER.find((s) => (report.counts.by_severity[s] ?? 0) > 0) ?? 'info';
  const n = report.counts.by_severity[top] ?? 0;
  const files = Object.entries(report.counts.by_file ?? {}).sort((a, b) => b[1] - a[1]);
  const topFile = files[0];
  const chains = report.chains.length;
  const parts = [`Confirm the ${n} ${SEVERITY_META[top].label.toLowerCase()} finding${n === 1 ? '' : 's'} first`];
  if (topFile) parts.push(`${topFile[1]} of ${total} findings sit in ${topFile[0]}`);
  if (chains > 0) parts.push(`${chains} exploit chain${chains === 1 ? '' : 's'} link findings together`);
  return parts.join(' · ') + '.';
}

export const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low', 'info'];

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

export function shortSha(sha: string | null | undefined): string {
  if (!sha) return '';
  return sha.slice(0, 7);
}

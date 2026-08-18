'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useParams, useRouter } from 'next/navigation';
import { FileDown, FileJson, FileSpreadsheet, History, Loader2, Play, Presentation, Search as SearchIcon, Target } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import {
  Assessment,
  AssessmentListItem,
  CompareResult,
  STATUS_META,
  TechniqueExplain,
  TechniqueResult,
  ThreatGroup,
  UseCaseItem,
  fmtDate,
} from '../lib';
import { DrillDownPanel } from '../components/DrillDownPanel';
import { RuleListPanel } from '../components/RuleListPanel';
import { UploadSummaryCard } from '../components/UploadSummaryCard';
import { AssumptionsNA } from '../components/AssumptionsNA';
import { CompareView } from '../components/CompareView';
import { CoverageHeatmap } from '../components/CoverageHeatmap';
import { ExecutiveBand } from '../components/ExecutiveBand';
import { GapsRoadmap } from '../components/GapsRoadmap';
import { TechniqueDrawer } from '../components/TechniqueDrawer';

const POLL_MS = 5_000;
const USE_CASE_FETCH_LIMIT = 500;

type Tab = 'coverage' | 'gaps' | 'assumptions' | 'compare';

export default function MitreResultsPage() {
  const router = useRouter();
  const params = useParams<{ assessmentId: string }>();
  const assessmentId = params.assessmentId;

  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [threatGroups, setThreatGroups] = useState<ThreatGroup[]>([]);
  const [useCases, setUseCases] = useState<UseCaseItem[]>([]);
  const [useCasesTotal, setUseCasesTotal] = useState(0);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<Tab>('coverage');
  const [selectedTechnique, setSelectedTechnique] = useState<string | null>(null);
  const [explain, setExplain] = useState<TechniqueExplain | null>(null);
  // Phase 14b: drill-down panels — every number opens one of these.
  const [drill, setDrill] = useState<{
    title: string;
    subtitle?: string | null;
    items: TechniqueResult[];
    grouped?: boolean;
  } | null>(null);
  const [ruleDrill, setRuleDrill] = useState<{
    title: string;
    rules: UseCaseItem[];
  } | null>(null);
  // Phase 14f: past-run switcher
  const [pastRuns, setPastRuns] = useState<AssessmentListItem[] | null>(null);
  const [runsOpen, setRunsOpen] = useState(false);
  const [runError, setRunError] = useState('');
  const [bulkAttesting, setBulkAttesting] = useState<string | null>(null);
  const [bulkAttestError, setBulkAttestError] = useState('');
  const [downloadError, setDownloadError] = useState('');
  const [compareOptions, setCompareOptions] = useState<AssessmentListItem[] | null>(null);
  const [compareWith, setCompareWith] = useState('');
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState('');
  const [userRole, setUserRole] = useState('');
  const statusRef = useRef<string>('');

  const authHeaders = () => ({
    Authorization: `Bearer ${localStorage.getItem('access_token')}`,
  });

  const load = useCallback(async () => {
    try {
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}`,
        { headers: authHeaders() }
      );
      statusRef.current = res.data.status;
      setAssessment(res.data);
      setError('');
    } catch (err: any) {
      if (err.response?.status === 401) router.push('/login');
      else setError(err.response?.data?.detail || 'Failed to load the assessment');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId]);

  // Static per-ATT&CK-version group catalog for the threat-group overlay;
  // fetched once, failure just hides the picker.
  useEffect(() => {
    axios
      .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/attack/groups`, {
        headers: authHeaders(),
      })
      .then((res) => setThreatGroups(res.data.groups ?? []))
      .catch(() => setThreatGroups([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Initial load + poll every 5s while running (visibility-aware — the
  // admin page's pattern with a shorter interval).
  useEffect(() => {
    if (!localStorage.getItem('access_token')) {
      router.push('/login');
      return;
    }
    load();
    const interval = setInterval(() => {
      if (!document.hidden && statusRef.current === 'running') load();
    }, POLL_MS);
    const onVisible = () => {
      if (!document.hidden && statusRef.current === 'running') load();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', onVisible);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId]);

  const loadUseCases = useCallback(async () => {
    try {
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}/use-cases`,
        { headers: authHeaders(), params: { limit: USE_CASE_FETCH_LIMIT } }
      );
      setUseCases(res.data.items);
      setUseCasesTotal(res.data.total);
    } catch {
      // non-fatal: the drawer just shows no mapped rules
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId]);

  // Once completed, fetch the parsed rules once (feeds the technique drawer).
  useEffect(() => {
    if (assessment?.status !== 'completed') return;
    loadUseCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessment?.status, assessmentId]);

  // Phase 14a: fetch the plain-language four-block explanation when a
  // technique is opened. Non-fatal — the drawer falls back to its existing
  // content if the fetch fails.
  useEffect(() => {
    setExplain(null);
    if (!selectedTechnique || statusRef.current !== 'completed') return;
    let cancelled = false;
    axios
      .get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}/techniques/${selectedTechnique}/explain`,
        { headers: authHeaders() }
      )
      .then((res) => {
        if (!cancelled) setExplain(res.data);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTechnique, assessmentId]);

  // Role gates the mapping-edit controls (server enforces regardless).
  useEffect(() => {
    axios
      .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`, { headers: authHeaders() })
      .then((res) => setUserRole(res.data.role ?? ''))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Phase 10: reviewer mapping correction — PATCH the full new technique-ID
  // list for one rule, then refresh results (coverage is recomputed
  // server-side) and the drawer's rule list.
  const handleEditMappings = useCallback(
    async (useCaseId: string, techniqueIds: string[]) => {
      try {
        await axios.patch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}/use-cases/${useCaseId}/mappings`,
          { technique_ids: techniqueIds },
          { headers: authHeaders() }
        );
      } catch (err: any) {
        throw new Error(err.response?.data?.detail || 'Could not save the mapping change');
      }
      await Promise.all([load(), loadUseCases()]);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [assessmentId, load, loadUseCases]
  );

  // 2026-08-19: tool-coverage attestation — creates a tool-attested rule
  // row server-side and recomputes coverage, then refetches everything.
  const attestIds = useCallback(
    async (tool: string, techniqueIds: string[]) => {
      // endpoint caps 50 ids per call — chunk larger confirmations
      for (let i = 0; i < techniqueIds.length; i += 50) {
        try {
          await axios.post(
            `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}/tool-attest`,
            { tool, technique_ids: techniqueIds.slice(i, i + 50) },
            { headers: authHeaders() }
          );
        } catch (err: any) {
          throw new Error(err.response?.data?.detail || 'Could not save the attestation');
        }
      }
      await Promise.all([load(), loadUseCases()]);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [assessmentId, load, loadUseCases]
  );

  const handleAttest = useCallback(
    (techniqueId: string, tool: string) => attestIds(tool, [techniqueId]),
    [attestIds]
  );

  // Phase 14f: past-run switcher — completed runs (archived included, so
  // history stays reachable) loaded once the assessment completes.
  useEffect(() => {
    if (assessment?.status !== 'completed' || pastRuns !== null) return;
    axios
      .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments`, {
        headers: authHeaders(),
        params: { include_archived: true },
      })
      .then((res) =>
        setPastRuns(
          (res.data as AssessmentListItem[]).filter((a) => a.status === 'completed')
        )
      )
      .catch(() => setPastRuns([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessment?.status]);

  // Lazily load the compare options the first time the Compare tab opens.
  // Archived runs stay selectable here (Phase 14f acceptance).
  useEffect(() => {
    if (tab !== 'compare' || compareOptions !== null) return;
    axios
      .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments`, {
        headers: authHeaders(),
        params: { include_archived: true },
      })
      .then((res) =>
        setCompareOptions(
          (res.data as AssessmentListItem[]).filter(
            (a) => a.status === 'completed' && a.assessment_id !== assessmentId
          )
        )
      )
      .catch(() => setCompareOptions([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, assessmentId]);

  const handleCompareSelect = async (otherId: string) => {
    setCompareWith(otherId);
    setCompareResult(null);
    setCompareError('');
    if (!otherId) return;
    setCompareLoading(true);
    try {
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}/compare/${otherId}`,
        { headers: authHeaders() }
      );
      setCompareResult(res.data);
    } catch (err: any) {
      setCompareError(err.response?.data?.detail || 'Comparison failed');
    } finally {
      setCompareLoading(false);
    }
  };

  const handleDownloadPdf = async (scope: 'full' | 'executive' | 'coverage' | 'gaps' | 'assumptions') => {
    setDownloadError('');
    try {
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}/report?format=pdf&scope=${scope}`,
        { headers: authHeaders() }
      );
      const binary = atob(res.data.data);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${assessment?.name || 'assessment'}-${
        scope === 'executive' ? 'executive-summary' : scope === 'full' ? 'attack-coverage' : scope
      }.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setDownloadError(err.response?.data?.detail || 'Failed to download the PDF report');
    }
  };

  const handleDownloadPptx = async () => {
    setDownloadError('');
    try {
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}/export.pptx`,
        { headers: authHeaders(), responseType: 'blob' }
      );
      const url = URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${assessment?.name || 'assessment'}-briefing-deck.pptx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setDownloadError(err.response?.data?.detail || 'Failed to download the PowerPoint deck');
    }
  };

  const handleDownloadXlsx = async (scope: 'full' | 'coverage' | 'gaps' | 'assumptions' = 'full') => {
    setDownloadError('');
    try {
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}/export.xlsx?scope=${scope}`,
        { headers: authHeaders(), responseType: 'blob' }
      );
      const url = URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${assessment?.name || 'assessment'}-${
        scope === 'full' ? 'attack-coverage' : scope
      }.xlsx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setDownloadError(err.response?.data?.detail || 'Failed to download the XLSX export');
    }
  };

  // On-page answer to "is this area / asset / TTP covered?" — matches
  // technique IDs and names, tactic names (area), ATT&CK platforms (asset),
  // and your own rule names/log sources; results open in the drill-down
  // panel grouped by state, each row one click from the full drawer story.
  const [siteSearch, setSiteSearch] = useState('');
  const runSiteSearch = () => {
    const query = siteSearch.trim().toLowerCase();
    if (!query || !summary) return;
    const tacticKeys = new Set<string>();
    for (const [domainKey, domain] of Object.entries(summary.domains)) {
      for (const t of domain.tactics) {
        if (t.name.toLowerCase().includes(query)) tacticKeys.add(`${domainKey}:${t.id}`);
      }
    }
    const ruleTechniqueIds = new Set(
      useCases
        .filter(
          (uc) =>
            uc.name.toLowerCase().includes(query) ||
            (uc.log_source ?? '').toLowerCase().includes(query)
        )
        .flatMap((uc) => uc.mappings.map((m) => m.technique_id))
    );
    // Threat groups too ("apt29", "lazarus", "cozy bear") — ≥3 chars so a
    // 1-2 letter query can't union half the group catalog into the result.
    const groupTechniqueIds = new Set(
      query.length >= 3
        ? threatGroups
            .filter(
              (g) =>
                g.name.toLowerCase().includes(query) ||
                g.id.toLowerCase() === query ||
                g.aliases.some((a) => a.toLowerCase().includes(query))
            )
            .flatMap((g) => g.technique_ids)
        : []
    );
    const matches = techniques.filter(
      (t) =>
        t.technique_id.toLowerCase().includes(query) ||
        (t.name ?? '').toLowerCase().includes(query) ||
        (t.platforms ?? []).some((p) => p.toLowerCase().includes(query)) ||
        t.tactics.some((id) => tacticKeys.has(`${t.domain}:${id}`)) ||
        ruleTechniqueIds.has(t.technique_id) ||
        groupTechniqueIds.has(t.technique_id)
    );
    openDrill(
      `“${siteSearch.trim()}” — ${matches.length} technique${matches.length === 1 ? '' : 's'}`,
      matches,
      {
        grouped: true,
        subtitle:
          'Matches on technique ID/name, attack stage, platform, threat group, and your rule names — grouped by coverage state. Click any row for the full story.',
      }
    );
  };

  const handleDownloadNavigator = async () => {
    setDownloadError('');
    try {
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}/navigator`,
        { headers: authHeaders(), responseType: 'blob' }
      );
      const isZip = String(res.headers['content-type'] ?? '').includes('zip');
      const url = URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${assessment?.name || 'assessment'}-navigator${isZip ? '-layers.zip' : '-layer.json'}`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setDownloadError(err.response?.data?.detail || 'Failed to download the Navigator layer');
    }
  };

  const handleRun = async () => {
    setRunError('');
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}/run`,
        null,
        { headers: authHeaders() }
      );
      statusRef.current = 'running';
      await load();
    } catch (err: any) {
      setRunError(err.response?.data?.detail || 'Could not start the run');
    }
  };

  const status = assessment ? STATUS_META[assessment.status] ?? STATUS_META.pending : null;
  const summary = assessment?.summary ?? null;
  const techniques = assessment?.technique_results ?? [];

  const TABS: { key: Tab; label: string }[] = [
    { key: 'coverage', label: 'Coverage' },
    { key: 'gaps', label: 'Gaps & Roadmap' },
    { key: 'assumptions', label: 'Assumptions & N/A' },
    { key: 'compare', label: 'Compare' },
  ];
  const completed = assessment?.status === 'completed';

  // Phase 14b handlers shared by all number-bearing components.
  const openDrill = (
    title: string,
    items: TechniqueResult[],
    opts?: { grouped?: boolean; subtitle?: string }
  ) => setDrill({ title, items, grouped: opts?.grouped, subtitle: opts?.subtitle });
  const openRuleDrillRules = (title: string, rules: UseCaseItem[]) =>
    setRuleDrill({ title, rules });
  const openRuleDrill = (mappingStatus: string | null, title: string) =>
    openRuleDrillRules(
      title,
      mappingStatus
        ? useCases.filter((uc) => uc.mapping_status === mappingStatus)
        : useCases
    );
  // Phase 14d: optional project metadata from the intake (all fields optional).
  const intakeMeta = ((assessment?.params as any)?.intake ?? {}) as {
    project_name?: string | null;
    scope_label?: string | null;
    prepared_by?: string | null;
    purpose_note?: string | null;
  };
  const metaLine = [intakeMeta.project_name, intakeMeta.scope_label,
    intakeMeta.prepared_by ? `Prepared by ${intakeMeta.prepared_by}` : null]
    .filter(Boolean)
    .join(' · ');

  return (
    <AppShell fullWidth>
      <TooltipProvider>
        {error && (
          <div role="alert" className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {assessment && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="flex min-w-0 items-center gap-2 text-lg font-semibold">
                <Target size={18} strokeWidth={2} className="shrink-0 text-primary" aria-hidden="true" />
                <span className="truncate">{assessment.name}</span>
              </h1>
              {status && (
                <span className={cn('inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium', status.chip)}>
                  {status.label}
                </span>
              )}
              <div className="ml-auto flex flex-wrap items-center gap-1.5">
                {/* Phase 14f: jump to any past run without going back to the list */}
                {completed && pastRuns !== null && pastRuns.length > 1 && (
                  <div className="relative">
                    <Button
                      size="sm"
                      variant="outline"
                      aria-expanded={runsOpen}
                      aria-haspopup="listbox"
                      onClick={() => setRunsOpen((v) => !v)}
                    >
                      <History size={14} className="mr-1" aria-hidden="true" />
                      Past runs ({pastRuns.length})
                    </Button>
                    {runsOpen && (
                      <div
                        role="listbox"
                        aria-label="Past assessment runs"
                        className="absolute right-0 z-50 mt-1 max-h-80 w-80 max-w-[calc(100vw-1.5rem)] overflow-y-auto rounded-md border bg-background p-1 shadow-md"
                      >
                        {pastRuns.map((run) => {
                          const isCurrent = run.assessment_id === assessmentId;
                          const delta =
                            run.strict_pct !== null && summary
                              ? Math.round((run.strict_pct - summary.overall.strict_pct) * 10) / 10
                              : null;
                          return (
                            <div
                              key={run.assessment_id}
                              className={cn(
                                'flex items-center gap-2 rounded px-2 py-1.5 text-xs',
                                isCurrent ? 'bg-muted/60' : 'hover:bg-primary/5'
                              )}
                            >
                              <button
                                type="button"
                                disabled={isCurrent}
                                onClick={() => {
                                  setRunsOpen(false);
                                  router.push(`/mitre/${run.assessment_id}`);
                                }}
                                className="min-w-0 flex-1 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                              >
                                <span className="block truncate font-medium">
                                  {run.name}
                                  {run.archived ? ' (archived)' : ''}
                                  {isCurrent ? ' — this run' : ''}
                                </span>
                                <span className="text-muted-foreground">
                                  {fmtDate(run.completed_at)} · {run.strict_pct}%
                                  {!isCurrent && delta !== null && delta !== 0 && (
                                    <span className={delta > 0 ? 'text-emerald-600' : 'text-rose-600'}>
                                      {' '}({delta > 0 ? '+' : ''}{delta} vs this)
                                    </span>
                                  )}
                                </span>
                              </button>
                              {!isCurrent && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setRunsOpen(false);
                                    setTab('compare');
                                    handleCompareSelect(run.assessment_id);
                                  }}
                                  className="shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-medium hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                >
                                  Compare
                                </button>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span>
                      <Button size="sm" variant="outline" onClick={() => handleDownloadPdf('executive')} disabled={!completed}>
                        <FileDown size={14} className="mr-1" aria-hidden="true" /> Exec PDF
                      </Button>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">
                    {completed
                      ? 'A 1–3 page executive summary — scorecard, top-5 fixes, roadmap and trend. Made for forwarding to leadership.'
                      : 'Available once the assessment completes.'}
                  </TooltipContent>
                </Tooltip>
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span>
                      <Button size="sm" variant="outline" onClick={() => handleDownloadPdf('full')} disabled={!completed}>
                        <FileDown size={14} className="mr-1" aria-hidden="true" /> Full PDF
                      </Button>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">
                    {completed
                      ? 'The complete report: executive summary plus the detailed gap register, coverage tables and appendices.'
                      : 'Available once the assessment completes.'}
                  </TooltipContent>
                </Tooltip>
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span>
                      <Button size="sm" variant="outline" onClick={() => handleDownloadXlsx('full')} disabled={!completed}>
                        <FileSpreadsheet size={14} className="mr-1" aria-hidden="true" /> XLSX
                      </Button>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">
                    {completed
                      ? 'Full gap register as a spreadsheet — every technique, rule, gap and assumption.'
                      : 'Available once the assessment completes.'}
                  </TooltipContent>
                </Tooltip>
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span>
                      <Button size="sm" variant="outline" onClick={handleDownloadPptx} disabled={!completed}>
                        <Presentation size={14} className="mr-1" aria-hidden="true" /> PPT
                      </Button>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">
                    {completed
                      ? 'A presentation-ready briefing deck: headline result, coverage chart, detection quality, top fixes and roadmap — for sharing with stakeholders.'
                      : 'Available once the assessment completes.'}
                  </TooltipContent>
                </Tooltip>
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span>
                      <Button size="sm" variant="outline" onClick={handleDownloadNavigator} disabled={!completed}>
                        <FileJson size={14} className="mr-1" aria-hidden="true" /> Navigator
                      </Button>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">
                    {completed
                      ? 'For your technical team: a machine-readable layer file (JSON) to open at attack.mitre.org/navigator — it paints your coverage onto MITRE’s official interactive matrix. Not a readable document; use the PDFs for that.'
                      : 'Available once the assessment completes.'}
                  </TooltipContent>
                </Tooltip>
                <span className="hidden text-xs text-muted-foreground sm:inline">
                  created {fmtDate(assessment.created_at)}
                </span>
              </div>
            </div>
            {(metaLine || intakeMeta.purpose_note) && (
              <div className="text-xs text-muted-foreground">
                {metaLine && <p>{metaLine}</p>}
                {intakeMeta.purpose_note && <p>{intakeMeta.purpose_note}</p>}
              </div>
            )}
            {downloadError && (
              <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {downloadError}
              </div>
            )}

            {(() => {
              // Phase 13d provenance line: only for SIEM-pulled assessments
              const siem = (assessment.params as any)?.siem;
              if (!siem) return null;
              return (
                <p className="text-xs text-muted-foreground">
                  Rules pulled read-only from Microsoft Sentinel
                  {siem.trigger === 'scheduled' ? ' by the automatic schedule' : ''}
                  {siem.connection_name ? ` · connection “${siem.connection_name}”` : ''}
                  {siem.workspace_ref?.workspace ? ` · workspace ${siem.workspace_ref.workspace}` : ''}
                  {siem.pulled_at ? ` · ${fmtDate(siem.pulled_at)}` : ''}
                  {typeof siem.rule_count === 'number' ? ` · ${siem.rule_count} rules` : ''}
                </p>
              );
            })()}

            {assessment.status === 'running' && (
              <div className="flex items-center gap-3 rounded-md bg-sky-50 p-5 text-sm text-sky-900">
                <Loader2 size={18} className="animate-spin" aria-hidden="true" />
                <div>
                  <p className="font-medium">Assessing your coverage…</p>
                  <p className="text-xs">
                    We&apos;re mapping rules to techniques, filtering to your environment,
                    and computing the results. Untagged rules go through AI tagging, so
                    this can take a few minutes. The page refreshes itself.
                  </p>
                </div>
              </div>
            )}

            {assessment.status === 'failed' && (
              <div className="space-y-3 rounded-md border border-rose-200 bg-rose-50 p-5 text-sm text-rose-900">
                <p className="font-medium">This run didn&apos;t finish.</p>
                <p>{assessment.error_message}</p>
                <Button size="sm" onClick={handleRun}>
                  <Play size={14} className="mr-1.5" aria-hidden="true" /> Re-run assessment
                </Button>
                {runError && <p className="text-xs text-rose-700">{runError}</p>}
              </div>
            )}

            {assessment.status === 'pending' && (
              <div className="space-y-3 rounded-md bg-muted/40 p-5 text-sm">
                <p>
                  This assessment is uploaded and parsed, but hasn&apos;t been run yet.
                </p>
                <Button size="sm" onClick={handleRun}>
                  <Play size={14} className="mr-1.5" aria-hidden="true" /> Run assessment
                </Button>
                {runError && <p className="text-xs text-destructive">{runError}</p>}
              </div>
            )}

            {assessment.status === 'completed' && summary && (
              <>
                <ExecutiveBand
                  assessment={assessment}
                  summary={summary}
                  techniques={techniques}
                  onSelectTechnique={setSelectedTechnique}
                  onDrill={openDrill}
                />

                {assessment.tool_coverage &&
                  assessment.tool_coverage.adjusted_pct !== null && (
                    <div className="rounded-md border border-blue-300 bg-blue-50 px-3 py-2 text-sm dark:border-blue-900 dark:bg-blue-950/40">
                      <span className="font-semibold text-blue-700 dark:text-blue-300">
                        Including{' '}
                        {assessment.tool_coverage.matched_tools
                          .map((t) => t.label)
                          .join(', ')}
                        &apos;s MITRE-evaluated detections:{' '}
                        {assessment.tool_coverage.adjusted_pct}%
                      </span>{' '}
                      <span className="text-muted-foreground">
                        ({assessment.tool_coverage.extra_open_covered} open
                        techniques those tools were evaluated against ·{' '}
                        {assessment.tool_coverage.caveat} Source:
                        evals.mitre.org)
                      </span>
                      {(userRole === 'admin' || userRole === 'reviewer') && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {assessment.tool_coverage.matched_tools.map((t) => {
                            const credited = Object.entries(
                              assessment.tool_coverage!.by_technique
                            )
                              .filter(([, labels]) => labels.includes(t.label))
                              .map(([tid]) => tid);
                            if (credited.length === 0) return null;
                            return (
                              <button
                                key={t.label}
                                type="button"
                                disabled={bulkAttesting !== null}
                                onClick={async () => {
                                  const ok = window.confirm(
                                    `Attest all ${credited.length} credited techniques for ${t.label}?\n\n` +
                                      `This records that your SOC receives and monitors ${t.label}'s alerts ` +
                                      `for these techniques, creates one auditable tool-attested rule per ` +
                                      `technique in your name, and recomputes the coverage score.`
                                  );
                                  if (!ok) return;
                                  setBulkAttesting(t.label);
                                  setBulkAttestError('');
                                  try {
                                    await attestIds(t.label, credited);
                                  } catch (err) {
                                    setBulkAttestError(
                                      err instanceof Error ? err.message : 'Attestation failed'
                                    );
                                  } finally {
                                    setBulkAttesting(null);
                                  }
                                }}
                                className="rounded-md border border-blue-400 bg-white px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50 dark:bg-transparent dark:text-blue-300 dark:hover:bg-blue-900/40"
                              >
                                {bulkAttesting === t.label
                                  ? 'Attesting…'
                                  : `Client confirmed — attest all ${credited.length} for ${t.label}`}
                              </button>
                            );
                          })}
                          {bulkAttestError && (
                            <p className="text-xs text-destructive">{bulkAttestError}</p>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                <UploadSummaryCard
                  assessment={assessment}
                  summary={summary}
                  useCases={useCases}
                  onDrillRules={openRuleDrillRules}
                />

                <div className="flex flex-wrap items-center gap-1 border-b" role="tablist" aria-label="Assessment result views">
                  {TABS.map((t) => (
                    <button
                      key={t.key}
                      type="button"
                      role="tab"
                      aria-selected={tab === t.key}
                      onClick={() => setTab(t.key)}
                      className={cn(
                        '-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors',
                        tab === t.key
                          ? 'border-primary text-foreground'
                          : 'border-transparent text-muted-foreground hover:text-foreground'
                      )}
                    >
                      {t.label}
                    </button>
                  ))}
                  {/* Right side of the same row: site search + this-tab-only
                      downloads (no extra toolbar row). */}
                  <span className="ml-auto flex items-center gap-1 pb-1">
                    <input
                      type="search"
                      value={siteSearch}
                      onChange={(e) => setSiteSearch(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && runSiteSearch()}
                      placeholder="Is it covered? Try 'T1486', 'ransomware', 'linux', 'APT29'…"
                      aria-label="Search techniques, attack stages, platforms, threat groups and rules"
                      className="h-7 w-64 max-w-[50vw] rounded-md border border-input bg-background px-2 text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    />
                    <Tooltip delayDuration={150}>
                      <TooltipTrigger asChild>
                        <button
                          type="button"
                          aria-label="Search this assessment"
                          onClick={runSiteSearch}
                          className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <SearchIcon size={14} aria-hidden="true" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs text-xs">
                        Search anything — a technique ID or name, an attack stage,
                        a platform/asset type, a threat group, or one of your rules —
                        and see its coverage state instantly.
                      </TooltipContent>
                    </Tooltip>
                    {tab !== 'compare' && (
                      <>
                        <Tooltip delayDuration={150}>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              aria-label="Download only this tab as PDF"
                              onClick={() => handleDownloadPdf(tab as 'coverage' | 'gaps' | 'assumptions')}
                              className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                              <FileDown size={14} aria-hidden="true" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent className="text-xs">Download only this tab as PDF</TooltipContent>
                        </Tooltip>
                        <Tooltip delayDuration={150}>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              aria-label="Download only this tab as Excel"
                              onClick={() => handleDownloadXlsx(tab as 'coverage' | 'gaps' | 'assumptions')}
                              className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                              <FileSpreadsheet size={14} aria-hidden="true" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent className="text-xs">Download only this tab as Excel</TooltipContent>
                        </Tooltip>
                      </>
                    )}
                  </span>
                </div>

                {tab === 'coverage' && (
                  <CoverageHeatmap
                    summary={summary}
                    techniques={techniques}
                    logSources={assessment?.log_source_coverage ?? undefined}
                    threatGroups={threatGroups}
                    onSelectTechnique={setSelectedTechnique}
                    onDrill={openDrill}
                  />
                )}
                {tab === 'gaps' && (
                  <GapsRoadmap
                    summary={summary}
                    techniques={techniques}
                    onSelectTechnique={setSelectedTechnique}
                  />
                )}
                {tab === 'assumptions' && (
                  <AssumptionsNA
                    summary={summary}
                    techniques={techniques}
                    onDrill={openDrill}
                    onDrillRules={openRuleDrill}
                    onSelectTechnique={setSelectedTechnique}
                  />
                )}
                {tab === 'compare' && (
                  <CompareView
                    options={compareOptions ?? []}
                    selectedId={compareWith}
                    onSelect={handleCompareSelect}
                    result={compareResult}
                    loading={compareLoading}
                    error={compareError}
                    onSelectTechnique={setSelectedTechnique}
                  />
                )}

                <DrillDownPanel
                  title={drill?.title ?? null}
                  subtitle={drill?.subtitle}
                  items={drill?.items ?? []}
                  grouped={drill?.grouped}
                  useCases={useCases}
                  onSelectTechnique={setSelectedTechnique}
                  onClose={() => setDrill(null)}
                />
                <RuleListPanel
                  title={ruleDrill?.title ?? null}
                  rules={ruleDrill?.rules ?? []}
                  truncated={useCasesTotal > useCases.length}
                  onSelectTechnique={setSelectedTechnique}
                  onClose={() => setRuleDrill(null)}
                />
                <TechniqueDrawer
                  techniqueId={selectedTechnique}
                  explain={explain}
                  onClose={() => setSelectedTechnique(null)}
                  techniques={techniques}
                  summary={summary}
                  useCases={useCases}
                  useCasesTruncated={useCasesTotal > useCases.length}
                  canEdit={userRole === 'admin' || userRole === 'reviewer'}
                  onEditMappings={handleEditMappings}
                  toolCoverage={assessment.tool_coverage?.by_technique ?? null}
                  onAttest={handleAttest}
                />
              </>
            )}
          </div>
        )}
      </TooltipProvider>
    </AppShell>
  );
}

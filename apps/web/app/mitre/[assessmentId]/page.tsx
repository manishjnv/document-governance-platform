'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useParams, useRouter } from 'next/navigation';
import { FileDown, FileJson, FileSpreadsheet, Loader2, Play, Target } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import {
  Assessment,
  AssessmentListItem,
  CompareResult,
  STATUS_META,
  UseCaseItem,
  fmtDate,
} from '../lib';
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
  const [useCases, setUseCases] = useState<UseCaseItem[]>([]);
  const [useCasesTotal, setUseCasesTotal] = useState(0);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<Tab>('coverage');
  const [selectedTechnique, setSelectedTechnique] = useState<string | null>(null);
  const [runError, setRunError] = useState('');
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

  // Lazily load the compare options the first time the Compare tab opens.
  useEffect(() => {
    if (tab !== 'compare' || compareOptions !== null) return;
    axios
      .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments`, {
        headers: authHeaders(),
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

  const handleDownloadPdf = async () => {
    setDownloadError('');
    try {
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}/report?format=pdf`,
        { headers: authHeaders() }
      );
      const binary = atob(res.data.data);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${assessment?.name || 'assessment'}-attack-coverage.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setDownloadError(err.response?.data?.detail || 'Failed to download the PDF report');
    }
  };

  const handleDownloadXlsx = async () => {
    setDownloadError('');
    try {
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}/export.xlsx`,
        { headers: authHeaders(), responseType: 'blob' }
      );
      const url = URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${assessment?.name || 'assessment'}-attack-coverage.xlsx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setDownloadError(err.response?.data?.detail || 'Failed to download the XLSX export');
    }
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
              <div className="ml-auto flex items-center gap-1.5">
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span>
                      <Button size="sm" variant="outline" onClick={handleDownloadPdf} disabled={!completed}>
                        <FileDown size={14} className="mr-1" aria-hidden="true" /> PDF
                      </Button>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">
                    {completed
                      ? 'Executive + detailed report as a PDF.'
                      : 'Available once the assessment completes.'}
                  </TooltipContent>
                </Tooltip>
                <Tooltip delayDuration={150}>
                  <TooltipTrigger asChild>
                    <span>
                      <Button size="sm" variant="outline" onClick={handleDownloadXlsx} disabled={!completed}>
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
                      <Button size="sm" variant="outline" onClick={handleDownloadNavigator} disabled={!completed}>
                        <FileJson size={14} className="mr-1" aria-hidden="true" /> Navigator
                      </Button>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs">
                    {completed
                      ? 'Coverage as a MITRE ATT&CK Navigator layer — open it in the official Navigator (one file per matrix).'
                      : 'Available once the assessment completes.'}
                  </TooltipContent>
                </Tooltip>
                <span className="hidden text-xs text-muted-foreground sm:inline">
                  created {fmtDate(assessment.created_at)}
                </span>
              </div>
            </div>
            {downloadError && (
              <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {downloadError}
              </div>
            )}

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
                  onSelectTechnique={setSelectedTechnique}
                />

                <div className="flex gap-1 border-b" role="tablist" aria-label="Assessment result views">
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
                </div>

                {tab === 'coverage' && (
                  <CoverageHeatmap
                    summary={summary}
                    techniques={techniques}
                    onSelectTechnique={setSelectedTechnique}
                  />
                )}
                {tab === 'gaps' && (
                  <GapsRoadmap summary={summary} onSelectTechnique={setSelectedTechnique} />
                )}
                {tab === 'assumptions' && <AssumptionsNA summary={summary} />}
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

                <TechniqueDrawer
                  techniqueId={selectedTechnique}
                  onClose={() => setSelectedTechnique(null)}
                  techniques={techniques}
                  summary={summary}
                  useCases={useCases}
                  useCasesTruncated={useCasesTotal > useCases.length}
                  canEdit={userRole === 'admin' || userRole === 'reviewer'}
                  onEditMappings={handleEditMappings}
                />
              </>
            )}
          </div>
        )}
      </TooltipProvider>
    </AppShell>
  );
}

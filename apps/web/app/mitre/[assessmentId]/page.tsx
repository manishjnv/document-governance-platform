'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useParams, useRouter } from 'next/navigation';
import { Loader2, Play, Target } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { TooltipProvider } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { Assessment, STATUS_META, UseCaseItem, fmtDate } from '../lib';
import { AssumptionsNA } from '../components/AssumptionsNA';
import { CoverageHeatmap } from '../components/CoverageHeatmap';
import { ExecutiveBand } from '../components/ExecutiveBand';
import { GapsRoadmap } from '../components/GapsRoadmap';
import { TechniqueDrawer } from '../components/TechniqueDrawer';

const POLL_MS = 5_000;
const USE_CASE_FETCH_LIMIT = 500;

type Tab = 'coverage' | 'gaps' | 'assumptions';

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

  // Once completed, fetch the parsed rules once (feeds the technique drawer).
  useEffect(() => {
    if (assessment?.status !== 'completed') return;
    axios
      .get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${assessmentId}/use-cases`,
        { headers: authHeaders(), params: { limit: USE_CASE_FETCH_LIMIT } }
      )
      .then((res) => {
        setUseCases(res.data.items);
        setUseCasesTotal(res.data.total);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessment?.status, assessmentId]);

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
  ];

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
              <span className="ml-auto text-xs text-muted-foreground">
                created {fmtDate(assessment.created_at)}
              </span>
            </div>

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

                <TechniqueDrawer
                  techniqueId={selectedTechnique}
                  onClose={() => setSelectedTechnique(null)}
                  techniques={techniques}
                  summary={summary}
                  useCases={useCases}
                  useCasesTruncated={useCasesTotal > useCases.length}
                />
              </>
            )}
          </div>
        )}
      </TooltipProvider>
    </AppShell>
  );
}

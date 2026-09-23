'use client';

import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useParams, useRouter } from 'next/navigation';
import {
  Bug,
  Check,
  Copy,
  Download,
  MoreHorizontal,
  Pencil,
  X,
} from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { AlertBanner, Chip, PageHeader, Skeleton, SkeletonRows } from '@/components/app';
import { cn } from '@/lib/utils';
import {
  CodeReviewDetail,
  CodeReviewFinding,
  SEVERITY_META,
  SOURCE_FORMAT_LABEL,
  Severity,
  Verdict,
  filterFindings,
  fmtDate,
  shortSha,
} from '../lib';
import { ReviewBand } from './components/ReviewBand';
import { SeverityStrip } from './components/SeverityStrip';
import { FindingsTable, SortKey, SortDir } from './components/FindingsTable';
import { ChainsTab } from './components/ChainsTab';
import { ScanDetailsTab } from './components/ScanDetailsTab';
import { FindingDrawer } from './components/FindingDrawer';

type Tab = 'findings' | 'chains' | 'details';

function sortFindings(findings: CodeReviewFinding[], key: SortKey, dir: SortDir): CodeReviewFinding[] {
  const arr = [...findings];
  const mult = dir === 'asc' ? 1 : -1;
  arr.sort((a, b) => {
    let cmp = 0;
    switch (key) {
      case 'idx':
        cmp = a.idx - b.idx;
        break;
      case 'severity':
        cmp = SEVERITY_META[a.severity].order - SEVERITY_META[b.severity].order;
        if (cmp === 0) cmp = (b.cvss_score ?? -1) - (a.cvss_score ?? -1);
        break;
      case 'title':
        cmp = a.title.localeCompare(b.title);
        break;
      case 'vuln_class':
        cmp = a.vuln_class_label.localeCompare(b.vuln_class_label);
        break;
      case 'cwe':
        cmp = (a.cwe ?? '').localeCompare(b.cwe ?? '');
        break;
      case 'cvss_score':
        cmp = (a.cvss_score ?? -1) - (b.cvss_score ?? -1);
        break;
      case 'confidence':
        cmp = a.confidence - b.confidence;
        break;
      case 'file':
        cmp = a.file.localeCompare(b.file);
        break;
    }
    return cmp * mult;
  });
  return arr;
}

export default function CodeReviewResultsPage() {
  const router = useRouter();
  const params = useParams<{ reviewId: string }>();
  const reviewId = params.reviewId;

  const [review, setReview] = useState<CodeReviewDetail | null>(null);
  const [error, setError] = useState('');
  const [downloadError, setDownloadError] = useState('');
  const [renaming, setRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState('');
  const [renameError, setRenameError] = useState('');
  const [linkCopied, setLinkCopied] = useState(false);
  const [degradedDismissed, setDegradedDismissed] = useState(false);

  const [tab, setTab] = useState<Tab>('findings');
  const [severityFilter, setSeverityFilter] = useState<Severity | null>(null);
  const [search, setSearch] = useState('');
  const [klass, setKlass] = useState<string | null>(null);
  const [verdict, setVerdict] = useState<Verdict | 'none' | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('severity');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const authHeaders = () => ({
    Authorization: `Bearer ${localStorage.getItem('access_token')}`,
  });

  const load = () =>
    axios
      .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/codereview/reviews/${reviewId}`, {
        headers: authHeaders(),
      })
      .then((res) => setReview(res.data))
      .catch((err) => {
        if (err.response?.status === 401) router.push('/login');
        else setError(err.response?.data?.detail || 'Failed to load the review');
      });

  useEffect(() => {
    if (!localStorage.getItem('access_token')) {
      router.push('/login');
      return;
    }
    load();
    try {
      setDegradedDismissed(sessionStorage.getItem(`cr-degraded-dismissed-${reviewId}`) === '1');
    } catch {
      // ponytail: sessionStorage unavailable (private mode) — banner just stays visible
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reviewId]);

  const download = async (kind: 'xlsx' | 'pptx') => {
    setDownloadError('');
    try {
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/codereview/reviews/${reviewId}/export.${kind}`,
        { headers: authHeaders(), responseType: 'blob' }
      );
      const url = URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${review?.name || 'code-review'}-${kind === 'xlsx' ? 'code-review.xlsx' : 'briefing-deck.pptx'}`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setDownloadError(err.response?.data?.detail || `Failed to download the ${kind.toUpperCase()} export`);
    }
  };

  const saveRename = async () => {
    if (!renameValue.trim() || !review) return;
    setRenameError('');
    try {
      await axios.patch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/codereview/reviews/${reviewId}`,
        { name: renameValue.trim() },
        { headers: authHeaders() }
      );
      setRenaming(false);
      await load();
    } catch (err: any) {
      setRenameError(err.response?.data?.detail || 'Could not rename the review');
    }
  };

  const copyPageLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 1500);
    } catch {
      // ponytail: clipboard permission denial is non-fatal
    }
  };

  const dismissDegraded = () => {
    setDegradedDismissed(true);
    try {
      sessionStorage.setItem(`cr-degraded-dismissed-${reviewId}`, '1');
    } catch {
      // ponytail: sessionStorage unavailable — dismissal just doesn't persist
    }
  };

  const findings = review?.report.findings ?? [];

  const filtered = useMemo(
    () => filterFindings(findings, { severity: severityFilter, klass, verdict, query: search }),
    [findings, severityFilter, klass, verdict, search]
  );
  const sorted = useMemo(() => sortFindings(filtered, sortKey, sortDir), [filtered, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  if (error) {
    return (
      <AppShell>
        <AlertBanner kind="error">{error}</AlertBanner>
      </AppShell>
    );
  }

  if (!review) {
    return (
      <AppShell>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
          <SkeletonRows rows={6} />
        </div>
      </AppShell>
    );
  }

  const report = review.report;

  return (
    <AppShell>
      <TooltipProvider>
        <PageHeader
          back={{ href: '/codereview', label: 'Reviews' }}
          title={
            renaming ? (
              <div className="flex items-center gap-1">
                <input
                  autoFocus
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') saveRename();
                    if (e.key === 'Escape') setRenaming(false);
                  }}
                  aria-label="New review name"
                  className="h-9 w-72 rounded-lg border border-input bg-card px-2.5 text-base outline-none focus:border-primary focus:ring-[3px] focus:ring-accent"
                />
                <button
                  type="button"
                  aria-label="Save name"
                  disabled={!renameValue.trim()}
                  onClick={saveRename}
                  className="rounded-md p-1 text-ok hover:bg-ok-soft disabled:opacity-50"
                >
                  <Check size={14} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  aria-label="Cancel rename"
                  onClick={() => setRenaming(false)}
                  className="rounded-md p-1 text-muted-foreground hover:bg-muted"
                >
                  <X size={14} aria-hidden="true" />
                </button>
              </div>
            ) : (
              <>
                <span className="flex flex-wrap items-center gap-2">
                  <Bug size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
                  {review.name}
                  {review.demo && (
                    <Chip tone="demo" xs tip="Shared sample review — read-only for everyone">
                      Demo
                    </Chip>
                  )}
                  {review.editable !== false && (
                    <button
                      type="button"
                      aria-label={`Rename ${review.name}`}
                      onClick={() => {
                        setRenaming(true);
                        setRenameValue(review.name);
                      }}
                      className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <Pencil size={13} aria-hidden="true" />
                    </button>
                  )}
                </span>
                {renameError && <p className="mt-1 text-xs text-destructive">{renameError}</p>}
              </>
            )
          }
          meta={
            <span className="flex flex-wrap items-center gap-1.5">
              <Chip tone="neutral" xs tip="Original scan output format">
                {SOURCE_FORMAT_LABEL[report.source_format]}
              </Chip>
              {review.git_sha && (
                <Chip tone="neutral" xs className="font-mono" tip={review.git_sha}>
                  {shortSha(review.git_sha)}
                </Chip>
              )}
              <Tooltip delayDuration={150}>
                <TooltipTrigger asChild>
                  <span>{fmtDate(review.created_at)}</span>
                </TooltipTrigger>
                <TooltipContent className="text-xs">When this review was imported</TooltipContent>
              </Tooltip>
            </span>
          }
          actions={
            <>
              <Button size="sm" variant="outline" onClick={() => download('xlsx')} aria-label="Download XLSX register">
                <Download size={14} className="mr-1.5" aria-hidden="true" />
                XLSX
              </Button>
              <Button size="sm" variant="outline" onClick={() => download('pptx')} aria-label="Download PPTX briefing deck">
                <Download size={14} className="mr-1.5" aria-hidden="true" />
                PPTX
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button size="sm" variant="outline" aria-label="More actions">
                    <MoreHorizontal size={14} aria-hidden="true" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={copyPageLink}>
                    <Copy size={14} className="mr-2" aria-hidden="true" />
                    {linkCopied ? 'Copied' : 'Copy link'}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          }
        />

        {downloadError && (
          <p role="alert" className="mb-3 text-xs text-destructive">
            {downloadError}
          </p>
        )}

        {report.degraded && !degradedDismissed && (
          <AlertBanner kind="warn" onDismiss={dismissDegraded} className="mb-3">
            <span className="font-medium">Scan degraded.</span> {report.degraded_reason}
          </AlertBanner>
        )}

        <div className="space-y-4">
          <ReviewBand report={report} onSelectSeverity={(s) => setSeverityFilter(s)} />

          <SeverityStrip
            findings={findings}
            filter={{ klass, verdict, query: search }}
            severity={severityFilter}
            onChange={setSeverityFilter}
          />

          <div role="tablist" className="flex gap-5 border-b border-border">
            {([
              ['findings', 'Findings'],
              ['chains', `Exploit chains (${report.chains.length})`],
              ['details', 'Scan details'],
            ] as [Tab, string][]).map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={tab === id}
                onClick={() => setTab(id)}
                className={cn(
                  '-mb-px border-b-2 border-transparent px-0.5 pb-2.5 text-[13px] font-medium text-muted-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  tab === id ? 'border-primary font-semibold text-foreground' : 'hover:text-foreground'
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {tab === 'findings' && (
            <FindingsTable
              rows={sorted}
              allFindings={findings}
              totalCount={findings.length}
              search={search}
              onSearchChange={setSearch}
              klass={klass}
              onKlassChange={setKlass}
              verdict={verdict}
              onVerdictChange={setVerdict}
              sortKey={sortKey}
              sortDir={sortDir}
              onSort={toggleSort}
              onOpenFinding={setSelectedIdx}
              showFixColumn={report.run_extras?.mode === 'fix'}
            />
          )}
          {tab === 'chains' && <ChainsTab chains={report.chains} onOpenFinding={setSelectedIdx} />}
          {tab === 'details' && <ScanDetailsTab report={report} />}

          <p className="border-t pt-3 text-[11px] text-muted-foreground">
            Findings produced by Visa Vulnerability Agentic Harness (Apache-2.0). AI-generated
            triage candidates — confirm before acting.
          </p>
        </div>

        <FindingDrawer reviewId={reviewId} list={sorted} selectedIdx={selectedIdx} onSelect={setSelectedIdx} />
      </TooltipProvider>
    </AppShell>
  );
}

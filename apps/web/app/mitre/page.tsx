'use client';

import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Archive, ArchiveRestore, Check, Loader2, Pencil, Plus, Target, X } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { AssessmentListItem, DOMAIN_LABELS, STATUS_META, fmtDate, orderedDomains } from './lib';
import { CoverageSparkline } from './components/CoverageSparkline';

/** Plain-words helper line per non-completed status. */
const STATUS_HELP: Record<string, string> = {
  pending: 'Uploaded and parsed — open it to run the assessment.',
  running: 'Running now — mapping your rules to ATT&CK techniques. This takes a few minutes.',
  failed: 'The run didn’t finish — open it to see why and re-run.',
};

export default function MitreListPage() {
  const router = useRouter();
  const [items, setItems] = useState<AssessmentListItem[] | null>(null);
  const [error, setError] = useState('');
  // Phase 14f: client-side search/filter + archive housekeeping
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showArchived, setShowArchived] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [actionError, setActionError] = useState('');

  const authHeaders = () => ({
    Authorization: `Bearer ${localStorage.getItem('access_token')}`,
  });

  const load = () =>
    axios
      .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments`, {
        headers: authHeaders(),
        params: { include_archived: true }, // hidden client-side by default
      })
      .then((res) => setItems(res.data))
      .catch((err) => {
        if (err.response?.status === 401) router.push('/login');
        else setError(err.response?.data?.detail || 'Failed to load assessments');
      });

  useEffect(() => {
    if (!localStorage.getItem('access_token')) {
      router.push('/login');
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const patchAssessment = async (id: string, body: { name?: string; archived?: boolean }) => {
    setActionError('');
    try {
      await axios.patch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/mitre/assessments/${id}`,
        body,
        { headers: authHeaders() }
      );
      await load();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Could not update the assessment');
    }
  };

  const visible = useMemo(() => {
    if (items === null) return null;
    const query = search.trim().toLowerCase();
    return items.filter(
      (i) =>
        (showArchived || !i.archived) &&
        (!statusFilter || i.status === statusFilter) &&
        (!query ||
          i.name.toLowerCase().includes(query) ||
          (i.project_name ?? '').toLowerCase().includes(query) ||
          (i.customer ?? '').toLowerCase().includes(query))
    );
  }, [items, search, statusFilter, showArchived]);

  /** Delta vs the previous completed run (chronological, from ALL items). */
  const deltaFor = (item: AssessmentListItem): number | null => {
    if (item.status !== 'completed' || item.strict_pct === null || items === null) return null;
    const index = items.findIndex((x) => x.assessment_id === item.assessment_id);
    const previous = items
      .slice(index + 1)
      .find((x) => x.status === 'completed' && x.strict_pct !== null);
    if (!previous) return null;
    return Math.round((item.strict_pct - (previous.strict_pct as number)) * 10) / 10;
  };

  return (
    <AppShell>
      <TooltipProvider>
        <div className="mb-4 flex items-center justify-between gap-2">
          <h1 className="flex items-center gap-2 text-lg font-semibold">
            <Target size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
            MITRE Assessments
          </h1>
          <div className="flex items-center gap-1.5">
            <Button asChild size="sm" variant="outline">
              <Link href="/mitre/connections">SIEM connections</Link>
            </Button>
            <Button asChild size="sm">
              <Link href="/mitre/new">
                <Plus size={15} className="mr-1" aria-hidden="true" />
                New assessment
              </Link>
            </Button>
          </div>
        </div>

        {error && (
          <div role="alert" className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {items !== null && items.length > 0 && (
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, customer, or project…"
              aria-label="Search assessments by name, customer, or project"
              className="h-8 w-56 rounded-md border border-input bg-background px-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filter by status"
              className="h-8 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="">All statuses</option>
              {Object.entries(STATUS_META).map(([key, meta]) => (
                <option key={key} value={key}>{meta.label}</option>
              ))}
            </select>
            {items.some((i) => i.archived) && (
              <label className="flex cursor-pointer items-center gap-1.5 text-xs text-muted-foreground">
                <input
                  type="checkbox"
                  checked={showArchived}
                  onChange={(e) => setShowArchived(e.target.checked)}
                  className="h-3.5 w-3.5"
                />
                Show archived ({items.filter((i) => i.archived).length})
              </label>
            )}
            <span className="ml-auto">
              <CoverageSparkline items={items} />
            </span>
          </div>
        )}
        {actionError && (
          <p role="alert" className="mb-2 text-xs text-destructive">{actionError}</p>
        )}

        {items !== null && items.length === 0 && !error && (
          <div className="rounded-md bg-muted/40 p-8 text-center">
            <Target size={28} className="mx-auto mb-3 text-muted-foreground" aria-hidden="true" />
            <p className="mx-auto max-w-md text-sm text-muted-foreground">
              Upload your SIEM detection rules and we&apos;ll show you exactly which MITRE
              ATT&CK techniques you can and can&apos;t detect. You get a coverage score, a
              ranked gap list, and a build roadmap — tailored to the log sources you
              already have.
            </p>
            <Button asChild size="sm" className="mt-4">
              <Link href="/mitre/new">Start your first assessment</Link>
            </Button>
          </div>
        )}

        {visible !== null && visible.length === 0 && items !== null && items.length > 0 && (
          <p className="rounded-md bg-muted/40 p-6 text-center text-sm text-muted-foreground">
            No assessments match your search or filters.
          </p>
        )}

        {/* Compact card grid — one card per run, everything readable at a
            glance, whole card clickable, scales 1 → 3 columns by screen. */}
        {visible !== null && visible.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {visible.map((item) => {
              const status = STATUS_META[item.status] ?? STATUS_META.pending;
              const brief = orderedDomains(item.domains_brief ?? {}).filter(
                ([, d]) => (d.applicable ?? 0) > 0
              );
              const covered = brief.reduce((s, [, d]) => s + (d.covered ?? 0), 0);
              const applicable = brief.reduce((s, [, d]) => s + (d.applicable ?? 0), 0);
              const delta = deltaFor(item);
              const renaming = renamingId === item.assessment_id;
              return (
                <div
                  key={item.assessment_id}
                  role="link"
                  tabIndex={0}
                  aria-label={`Open assessment ${item.name}`}
                  onClick={() => !renaming && router.push(`/mitre/${item.assessment_id}`)}
                  onKeyDown={(e) => {
                    if (!renaming && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault();
                      router.push(`/mitre/${item.assessment_id}`);
                    }
                  }}
                  className="group cursor-pointer rounded-md border p-3.5 transition-colors hover:border-primary/50 hover:bg-primary/[0.03] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {/* Header: name + chips, actions right */}
                  <div className="flex items-start justify-between gap-2">
                    {renaming ? (
                      <span
                        className="flex min-w-0 flex-1 items-center gap-1"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          autoFocus
                          value={renameValue}
                          onChange={(e) => setRenameValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && renameValue.trim()) {
                              patchAssessment(item.assessment_id, { name: renameValue.trim() });
                              setRenamingId(null);
                            }
                            if (e.key === 'Escape') setRenamingId(null);
                          }}
                          aria-label="New assessment name"
                          className="h-7 w-full min-w-0 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        />
                        <button
                          type="button"
                          aria-label="Save name"
                          disabled={!renameValue.trim()}
                          onClick={() => {
                            patchAssessment(item.assessment_id, { name: renameValue.trim() });
                            setRenamingId(null);
                          }}
                          className="rounded p-1 text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
                        >
                          <Check size={14} aria-hidden="true" />
                        </button>
                        <button
                          type="button"
                          aria-label="Cancel rename"
                          onClick={() => setRenamingId(null)}
                          className="rounded p-1 text-muted-foreground hover:bg-muted"
                        >
                          <X size={14} aria-hidden="true" />
                        </button>
                      </span>
                    ) : (
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold leading-snug">{item.name}</p>
                        {(item.customer || item.project_name || item.archived || item.siem) && (
                          <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                            {item.customer && <span className="truncate font-medium">{item.customer}</span>}
                            {item.project_name && <span className="truncate">{item.project_name}</span>}
                            {item.siem && (
                              <span className="rounded-full border border-sky-200 bg-sky-100 px-1.5 py-0.5 font-medium text-sky-800">
                                {item.siem.platform === 'splunk' ? 'Splunk' : 'Sentinel'}
                                {item.siem.trigger === 'scheduled' ? ' · auto' : ''}
                              </span>
                            )}
                            {item.archived && (
                              <span className="rounded-full border px-1.5 py-0.5 font-medium">Archived</span>
                            )}
                          </p>
                        )}
                      </div>
                    )}
                    {!renaming && (
                      <span
                        className="flex shrink-0 items-center gap-0.5"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Tooltip delayDuration={150}>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              aria-label={`Rename ${item.name}`}
                              onClick={() => {
                                setRenamingId(item.assessment_id);
                                setRenameValue(item.name);
                              }}
                              className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                              <Pencil size={13} aria-hidden="true" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent className="text-xs">Rename</TooltipContent>
                        </Tooltip>
                        <Tooltip delayDuration={150}>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              aria-label={item.archived ? `Unarchive ${item.name}` : `Archive ${item.name}`}
                              onClick={() =>
                                patchAssessment(item.assessment_id, { archived: !item.archived })
                              }
                              className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                              {item.archived ? (
                                <ArchiveRestore size={13} aria-hidden="true" />
                              ) : (
                                <Archive size={13} aria-hidden="true" />
                              )}
                            </button>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs text-xs">
                            {item.archived
                              ? 'Bring back to the default list.'
                              : 'Hide from the default list — stays available in Compare. Nothing is deleted.'}
                          </TooltipContent>
                        </Tooltip>
                      </span>
                    )}
                  </div>

                  {/* Body */}
                  {item.status === 'completed' && item.strict_pct !== null ? (
                    <>
                      <div className="mt-2.5 flex items-baseline gap-2">
                        <span className="text-2xl font-bold leading-none text-primary">
                          {item.strict_pct}%
                        </span>
                        <span className="min-w-0 text-[11px] leading-tight text-muted-foreground">
                          coverage — your rules detect {covered} of {applicable} applicable
                          techniques
                        </span>
                        {delta !== null && delta !== 0 && (
                          <span
                            className={cn(
                              'ml-auto shrink-0 text-[11px] font-semibold',
                              delta > 0 ? 'text-emerald-600' : 'text-rose-600'
                            )}
                            title={`${delta > 0 ? '+' : ''}${delta} points vs your previous completed run`}
                          >
                            {delta > 0 ? '▲' : '▼'} {Math.abs(delta)}
                          </span>
                        )}
                      </div>
                      <div className="mt-2 space-y-1">
                        {brief.map(([key, d]) => (
                          <div key={key} className="flex items-center gap-2 text-[11px]">
                            <span className="w-16 shrink-0 text-muted-foreground">
                              {DOMAIN_LABELS[key] ?? key}
                            </span>
                            <div className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-muted">
                              <div
                                className="h-full rounded-full bg-primary"
                                style={{ width: `${Math.min(100, d.strict_pct ?? 0)}%` }}
                              />
                            </div>
                            <span className="w-10 shrink-0 text-right text-muted-foreground">
                              {d.strict_pct}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <p className="mt-2.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                      {item.status === 'running' && (
                        <Loader2 size={13} className="animate-spin" aria-hidden="true" />
                      )}
                      {STATUS_HELP[item.status] ?? ''}
                    </p>
                  )}

                  {/* Footer */}
                  <div className="mt-2.5 flex items-center gap-2 border-t pt-2 text-[11px] text-muted-foreground">
                    <span
                      className={cn(
                        'inline-flex items-center rounded-full border px-1.5 py-0.5 font-medium',
                        status.chip
                      )}
                    >
                      {status.label}
                    </span>
                    <span>ATT&CK v{item.attack_version}</span>
                    <span className="ml-auto">{fmtDate(item.created_at)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </TooltipProvider>
    </AppShell>
  );
}

'use client';

import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Archive, ArchiveRestore, Check, Pencil, Plus, Target, X } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { AssessmentListItem, DOMAIN_LABELS, STATUS_META, fmtDate } from './lib';

function TrendArrow({ item, items }: { item: AssessmentListItem; items: AssessmentListItem[] }) {
  if (item.status !== 'completed' || item.strict_pct === null) return null;
  const index = items.findIndex((x) => x.assessment_id === item.assessment_id);
  const previous = items
    .slice(index + 1)
    .find((x) => x.status === 'completed' && x.strict_pct !== null);
  if (!previous) return null;
  const delta = Math.round((item.strict_pct - (previous.strict_pct as number)) * 10) / 10;
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <span
          className={cn(
            'cursor-default text-xs font-semibold',
            delta > 0 && 'text-emerald-600',
            delta < 0 && 'text-rose-600',
            delta === 0 && 'text-muted-foreground'
          )}
        >
          {delta > 0 ? '▲' : delta < 0 ? '▼' : '–'}
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">
        {delta === 0
          ? 'No change vs the previous completed run.'
          : `${delta > 0 ? '+' : ''}${delta} points vs the previous completed run (${previous.strict_pct}%). Open the assessment's Compare tab for the full diff.`}
      </TooltipContent>
    </Tooltip>
  );
}

function DomainMiniBars({ item }: { item: AssessmentListItem }) {
  const brief = Object.entries(item.domains_brief ?? {}).filter(
    ([, d]) => (d.applicable ?? 0) > 0
  );
  if (brief.length === 0) return <span className="text-xs text-muted-foreground">—</span>;
  return (
    <div className="flex flex-col gap-1">
      {brief.map(([key, d]) => (
        <Tooltip key={key} delayDuration={150}>
          <TooltipTrigger asChild>
            <div className="flex cursor-default items-center gap-1.5">
              <span className="w-4 text-[10px] font-semibold text-muted-foreground">
                {(DOMAIN_LABELS[key] ?? key)[0]}
              </span>
              <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{ width: `${Math.min(100, d.strict_pct ?? 0)}%` }}
                />
              </div>
              <span className="text-[10px] text-muted-foreground">{d.strict_pct}%</span>
            </div>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs text-xs">
            {DOMAIN_LABELS[key] ?? key}: {d.covered} of {d.applicable} applicable techniques
            covered ({d.strict_pct}% strict).
          </TooltipContent>
        </Tooltip>
      ))}
    </div>
  );
}

/** Phase 14f: tiny inline SVG sparkline over completed runs' coverage %. */
function CoverageSparkline({ items }: { items: AssessmentListItem[] }) {
  const points = items
    .filter((i) => i.status === 'completed' && i.strict_pct !== null && !i.archived)
    .slice()
    .reverse(); // list is newest-first; the trend reads left → right in time
  if (points.length < 2) return null;
  const max = Math.max(...points.map((p) => p.strict_pct as number), 1);
  const w = 120;
  const h = 28;
  const step = w / (points.length - 1);
  const path = points
    .map(
      (p, i) =>
        `${i === 0 ? 'M' : 'L'}${(i * step).toFixed(1)},${(
          h - 3 - ((p.strict_pct as number) / max) * (h - 6)
        ).toFixed(1)}`
    )
    .join(' ');
  const first = points[0].strict_pct;
  const last = points[points.length - 1].strict_pct;
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <span className="flex cursor-default items-center gap-2 text-xs text-muted-foreground">
          Your trend so far
          <svg width={w} height={h} aria-hidden="true" className="overflow-visible">
            <path d={path} fill="none" stroke="currentColor" strokeWidth="1.5" className="text-primary" />
          </svg>
          {first}% → {last}%
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">
        Coverage % across your {points.length} completed runs, oldest to newest.
      </TooltipContent>
    </Tooltip>
  );
}

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
          (i.project_name ?? '').toLowerCase().includes(query))
    );
  }, [items, search, statusFilter, showArchived]);

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
              placeholder="Search by name or project…"
              aria-label="Search assessments by name or project"
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
            <label className="flex cursor-pointer items-center gap-1.5 text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={showArchived}
                onChange={(e) => setShowArchived(e.target.checked)}
                className="h-3.5 w-3.5"
              />
              Show archived ({items.filter((i) => i.archived).length})
            </label>
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

        {visible !== null && items !== null && items.length > 0 && (
          <div className="overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Coverage</TableHead>
                  <TableHead className="hidden lg:table-cell">By matrix</TableHead>
                  <TableHead className="hidden sm:table-cell">ATT&CK</TableHead>
                  <TableHead className="hidden md:table-cell">Created</TableHead>
                  <TableHead className="w-16"><span className="sr-only">Actions</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map((item) => {
                  const status = STATUS_META[item.status] ?? STATUS_META.pending;
                  return (
                    <TableRow
                      key={item.assessment_id}
                      className="cursor-pointer"
                      onClick={() => router.push(`/mitre/${item.assessment_id}`)}
                    >
                      <TableCell className="text-sm font-medium">
                        {renamingId === item.assessment_id ? (
                          <span
                            className="flex items-center gap-1"
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
                              className="h-7 w-48 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
                        <span className="inline-flex flex-wrap items-center gap-1.5">
                          {item.name}
                          {item.project_name && (
                            <span className="text-xs font-normal text-muted-foreground">
                              · {item.project_name}
                            </span>
                          )}
                          {item.archived && (
                            <span className="inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                              Archived
                            </span>
                          )}
                          {item.siem && (
                            <Tooltip delayDuration={150}>
                              <TooltipTrigger asChild>
                                <span className="inline-flex cursor-default items-center rounded-full border border-sky-200 bg-sky-100 px-1.5 py-0.5 text-[10px] font-medium text-sky-800">
                                  Sentinel{item.siem.trigger === 'scheduled' ? ' · auto' : ''}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent className="max-w-xs text-xs">
                                Rules pulled read-only from Microsoft Sentinel
                                {item.siem.trigger === 'scheduled'
                                  ? ' by the automatic schedule.'
                                  : ' (manual pull).'}
                              </TooltipContent>
                            </Tooltip>
                          )}
                        </span>
                        )}
                      </TableCell>
                      <TableCell>
                        <span
                          className={cn(
                            'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium',
                            status.chip
                          )}
                        >
                          {status.label}
                        </span>
                      </TableCell>
                      <TableCell>
                        {item.strict_pct !== null ? (
                          <div className="flex items-center gap-2">
                            <Tooltip delayDuration={150}>
                              <TooltipTrigger asChild>
                                <div className="flex cursor-default items-center gap-2">
                                  <span className="w-12 text-sm font-semibold">{item.strict_pct}%</span>
                                  <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
                                    <div
                                      className="h-full rounded-full bg-primary"
                                      style={{ width: `${Math.min(100, item.strict_pct)}%` }}
                                    />
                                  </div>
                                </div>
                              </TooltipTrigger>
                              <TooltipContent className="max-w-xs text-xs">
                                Strict coverage: techniques with a qualifying detection, out of
                                those applicable to your environment. Weighted (partial counts
                                as half): {item.weighted_pct}%.
                              </TooltipContent>
                            </Tooltip>
                            <TrendArrow item={item} items={items} />
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="hidden lg:table-cell">
                        <DomainMiniBars item={item} />
                      </TableCell>
                      <TableCell className="hidden text-xs text-muted-foreground sm:table-cell">
                        v{item.attack_version}
                      </TableCell>
                      <TableCell className="hidden text-xs text-muted-foreground md:table-cell">
                        {fmtDate(item.created_at)}
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <span className="flex items-center gap-0.5">
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
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </TooltipProvider>
    </AppShell>
  );
}

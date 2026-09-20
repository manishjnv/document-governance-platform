'use client';

import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Bug, MoreHorizontal, Plus, Search } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { PageHeader, Chip, EmptyState, SkeletonRows, AlertBanner, SeverityBar, type ChipTone } from '@/components/app';
import {
  CodeReviewListItem,
  Severity,
  SEVERITY_META,
  SEVERITY_ORDER,
  SOURCE_FORMAT_LABEL,
  fmtDate,
  shortSha,
} from './lib';

type SortKey = 'newest' | 'oldest' | 'most_findings' | 'name';

const SORTERS: Record<SortKey, (a: CodeReviewListItem, b: CodeReviewListItem) => number> = {
  newest: (a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''),
  oldest: (a, b) => (a.created_at ?? '').localeCompare(b.created_at ?? ''),
  most_findings: (a, b) => b.counts.total - a.counts.total,
  name: (a, b) => a.name.localeCompare(b.name),
};

/** Chip tone + bar-fill token per severity, matching the sev-* design tokens. */
const SEV_TONE: Record<Severity, ChipTone> = {
  critical: 'crit',
  high: 'high',
  medium: 'med',
  low: 'low',
  info: 'info',
};

export default function CodeReviewListPage() {
  const router = useRouter();
  const [items, setItems] = useState<CodeReviewListItem[] | null>(null);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<SortKey>('newest');
  const [actionError, setActionError] = useState('');
  const [renaming, setRenaming] = useState<CodeReviewListItem | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [deleting, setDeleting] = useState<CodeReviewListItem | null>(null);
  const [busy, setBusy] = useState(false);

  const authHeaders = () => ({
    Authorization: `Bearer ${localStorage.getItem('access_token')}`,
  });

  const load = () =>
    axios
      .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/codereview/reviews`, {
        headers: authHeaders(),
      })
      .then((res) => setItems(res.data))
      .catch((err) => {
        if (err.response?.status === 401) router.push('/login');
        else setError(err.response?.data?.detail || 'Failed to load reviews');
      });

  useEffect(() => {
    if (!localStorage.getItem('access_token')) {
      router.push('/login');
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRename = async () => {
    if (!renaming || !renameValue.trim()) return;
    setActionError('');
    setBusy(true);
    try {
      await axios.patch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/codereview/reviews/${renaming.review_id}`,
        { name: renameValue.trim() },
        { headers: authHeaders() }
      );
      setRenaming(null);
      await load();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Could not rename the review');
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!deleting) return;
    setActionError('');
    setBusy(true);
    try {
      await axios.delete(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/codereview/reviews/${deleting.review_id}`,
        { headers: authHeaders() }
      );
      setDeleting(null);
      await load();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Could not delete the review');
    } finally {
      setBusy(false);
    }
  };

  const visible = useMemo(() => {
    if (items === null) return null;
    const query = search.trim().toLowerCase();
    const filtered = query
      ? items.filter(
          (i) => i.name.toLowerCase().includes(query) || i.repo_label.toLowerCase().includes(query)
        )
      : items;
    return [...filtered].sort(SORTERS[sort]);
  }, [items, search, sort]);

  return (
    <AppShell>
      <TooltipProvider>
        <PageHeader
          title={
            <span className="flex items-center gap-2">
              <Bug size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
              Code Security Reviews
            </span>
          }
          actions={
            <>
              <Button asChild size="sm" variant="outline">
                <Link href="/codereview/new">Get scanner</Link>
              </Button>
              <Button asChild size="sm">
                <Link href="/codereview/new">
                  <Plus size={15} className="mr-1" aria-hidden="true" />
                  New review
                </Link>
              </Button>
            </>
          }
        />

        {error && (
          <AlertBanner kind="error" className="mb-4">
            {error}
          </AlertBanner>
        )}

        {items !== null && items.length > 0 && (
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search
                size={14}
                strokeWidth={2}
                className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name or repo…"
                aria-label="Search reviews by name or repo"
                className="h-9 w-56 rounded-lg border border-input bg-card pl-8 pr-2.5 text-[13px] text-foreground outline-none placeholder:text-muted-foreground focus:border-primary focus:ring-[3px] focus:ring-accent"
              />
            </div>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortKey)}
              aria-label="Sort reviews"
              className="h-9 rounded-lg border border-input bg-card px-2 text-[13px] text-foreground outline-none focus:border-primary focus:ring-[3px] focus:ring-accent"
            >
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
              <option value="most_findings">Most findings</option>
              <option value="name">Name</option>
            </select>
          </div>
        )}
        {actionError && (
          <p role="alert" className="mb-2 text-xs text-sev-crit">{actionError}</p>
        )}

        {items === null && !error && <SkeletonRows rows={3} />}

        {items !== null && items.length === 0 && !error && (
          <EmptyState
            icon={<Bug size={28} aria-hidden="true" />}
            title={
              <>
                Run the Visa Vulnerability Agentic Harness scan on your repo and upload its
                findings.json to get a reviewable findings register plus client-ready XLSX and
                PPTX deliverables.
              </>
            }
            description={
              <>
                Built on Visa&apos;s open-source Vulnerability Agentic Harness (Apache-2.0).
                ScopeSense is not affiliated with or endorsed by Visa, Inc.
              </>
            }
            action={
              <div className="flex gap-2">
                <Button asChild size="sm" variant="outline">
                  <Link href="/codereview/new">Get scanner</Link>
                </Button>
                <Button asChild size="sm">
                  <Link href="/codereview/new">New review</Link>
                </Button>
              </div>
            }
          />
        )}

        {visible !== null && visible.length === 0 && items !== null && items.length > 0 && (
          <EmptyState title="No reviews match your search." />
        )}

        {visible !== null && visible.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {visible.map((item) => {
              const total = item.counts.total;
              return (
                <div
                  key={item.review_id}
                  role="link"
                  tabIndex={0}
                  aria-label={`Open review ${item.name}`}
                  onClick={() => router.push(`/codereview/${item.review_id}`)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      router.push(`/codereview/${item.review_id}`);
                    }
                  }}
                  className="group cursor-pointer rounded-[10px] border border-border bg-card p-4 transition-colors ease-app hover:border-primary/50 hover:bg-accent-soft/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold leading-snug text-foreground">{item.name}</p>
                      <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                        <span className="truncate font-mono text-xs">{item.repo_label}</span>
                        {item.git_sha && (
                          <Chip tone="neutral" xs className="font-mono" tip={item.git_sha}>
                            {shortSha(item.git_sha)}
                          </Chip>
                        )}
                      </p>
                    </div>
                    <span className="flex shrink-0 items-center gap-0.5" onClick={(e) => e.stopPropagation()}>
                      {item.demo && (
                        <Chip
                          tone="demo"
                          xs
                          tip="Shared sample review — visible to every signed-in user, read-only"
                        >
                          Demo
                        </Chip>
                      )}
                      {item.editable !== false && (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <button
                              type="button"
                              aria-label={`Actions for ${item.name}`}
                              className="shrink-0 rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                              <MoreHorizontal size={15} aria-hidden="true" />
                            </button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="rounded-lg">
                            <DropdownMenuItem
                              className="rounded-lg"
                              onClick={() => {
                                setRenaming(item);
                                setRenameValue(item.name);
                              }}
                            >
                              Rename
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="rounded-lg text-destructive focus:text-destructive"
                              onClick={() => setDeleting(item)}
                            >
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </span>
                  </div>

                  <Tooltip delayDuration={150}>
                    <TooltipTrigger asChild>
                      <SeverityBar counts={item.counts.by_severity} className="mt-3" />
                    </TooltipTrigger>
                    <TooltipContent className="text-xs">
                      {total === 0
                        ? 'No findings'
                        : SEVERITY_ORDER.filter((s) => (item.counts.by_severity[s] ?? 0) > 0)
                            .map((s) => `${item.counts.by_severity[s]} ${SEVERITY_META[s].label.toLowerCase()}`)
                            .join(' · ')}
                    </TooltipContent>
                  </Tooltip>
                  <div className="mt-2 flex flex-wrap items-center gap-1">
                    {total === 0 ? (
                      <span className="text-[11px] text-muted-foreground">No findings</span>
                    ) : (
                      SEVERITY_ORDER.filter((s) => (item.counts.by_severity[s] ?? 0) > 0).map((s) => (
                        <Chip key={s} tone={SEV_TONE[s]} dot xs>
                          {item.counts.by_severity[s]} {SEVERITY_META[s].label.toLowerCase()}
                        </Chip>
                      ))
                    )}
                  </div>

                  <div className="mt-2.5 flex items-center gap-2 border-t border-border pt-2 text-[11px] text-muted-foreground">
                    <span className="font-semibold tabular-nums text-foreground">
                      {total} finding{total === 1 ? '' : 's'}
                    </span>
                    <Chip tone="neutral" xs tip="Import source format">
                      {SOURCE_FORMAT_LABEL[item.source_format]}
                    </Chip>
                    <span className="ml-auto tabular-nums">{fmtDate(item.created_at)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </TooltipProvider>

      <Dialog open={!!renaming} onOpenChange={(open) => !open && setRenaming(null)}>
        <DialogContent className="max-w-sm rounded-xl p-0">
          <DialogHeader className="px-5 pb-1.5 pt-[18px]">
            <DialogTitle className="text-base font-semibold">Rename review</DialogTitle>
          </DialogHeader>
          <div className="px-5 pb-4">
            <input
              autoFocus
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleRename();
              }}
              aria-label="New review name"
              className="h-9 w-full rounded-lg border border-input bg-card px-2.5 text-[13px] text-foreground outline-none focus:border-primary focus:ring-[3px] focus:ring-accent"
            />
          </div>
          <DialogFooter className="flex justify-end gap-2 px-5 pb-[18px] pt-3">
            <Button variant="outline" size="sm" onClick={() => setRenaming(null)} disabled={busy}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleRename} disabled={busy || !renameValue.trim()}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!deleting} onOpenChange={(open) => !open && setDeleting(null)}>
        <DialogContent className="max-w-sm rounded-xl p-0">
          <DialogHeader className="px-5 pb-1.5 pt-[18px]">
            <DialogTitle className="text-base font-semibold">Delete review</DialogTitle>
          </DialogHeader>
          <p className="px-5 pb-4 text-[13.5px] text-muted-foreground">
            Delete &quot;{deleting?.name}&quot;? This can&apos;t be undone.
          </p>
          <DialogFooter className="flex justify-end gap-2 px-5 pb-[18px] pt-3">
            <Button variant="outline" size="sm" onClick={() => setDeleting(null)} disabled={busy}>
              Cancel
            </Button>
            <Button variant="destructive" size="sm" onClick={handleDelete} disabled={busy}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}

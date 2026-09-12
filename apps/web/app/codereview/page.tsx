'use client';

import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Bug, MoreHorizontal, Plus } from 'lucide-react';
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
import {
  CodeReviewListItem,
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
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h1 className="flex items-center gap-2 text-lg font-semibold">
            <Bug size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
            Code Security Reviews
          </h1>
          <div className="flex items-center gap-1.5">
            <Button asChild size="sm" variant="outline">
              <Link href="/codereview/new">Get scanner</Link>
            </Button>
            <Button asChild size="sm">
              <Link href="/codereview/new">
                <Plus size={15} className="mr-1" aria-hidden="true" />
                New review
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
              placeholder="Search by name or repo…"
              aria-label="Search reviews by name or repo"
              className="h-8 w-56 rounded-md border border-input bg-background px-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortKey)}
              aria-label="Sort reviews"
              className="h-8 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
              <option value="most_findings">Most findings</option>
              <option value="name">Name</option>
            </select>
          </div>
        )}
        {actionError && (
          <p role="alert" className="mb-2 text-xs text-destructive">{actionError}</p>
        )}

        {items === null && !error && (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="animate-pulse rounded-md border p-3.5">
                <div className="h-4 w-2/3 rounded bg-muted" />
                <div className="mt-2 h-3 w-1/3 rounded bg-muted" />
                <div className="mt-3 h-1.5 w-full rounded-full bg-muted" />
                <div className="mt-2 h-3 w-1/2 rounded bg-muted" />
                <div className="mt-3 h-3 w-1/3 rounded bg-muted" />
              </div>
            ))}
          </div>
        )}

        {items !== null && items.length === 0 && !error && (
          <div className="rounded-md bg-muted/40 p-8 text-center">
            <Bug size={28} className="mx-auto mb-3 text-muted-foreground" aria-hidden="true" />
            <p className="mx-auto max-w-md text-sm text-muted-foreground">
              Run the Visa Vulnerability Agentic Harness scan on your repo and upload its
              findings.json to get a reviewable findings register plus client-ready XLSX and
              PPTX deliverables.
            </p>
            <div className="mt-4 flex justify-center gap-2">
              <Button asChild size="sm" variant="outline">
                <Link href="/codereview/new">Get scanner</Link>
              </Button>
              <Button asChild size="sm">
                <Link href="/codereview/new">New review</Link>
              </Button>
            </div>
          </div>
        )}

        {visible !== null && visible.length === 0 && items !== null && items.length > 0 && (
          <p className="rounded-md bg-muted/40 p-6 text-center text-sm text-muted-foreground">
            No reviews match your search.
          </p>
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
                  className="group cursor-pointer rounded-md border p-3.5 transition-colors hover:border-primary/50 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold leading-snug">{item.name}</p>
                      <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                        <span className="truncate">{item.repo_label}</span>
                        {item.git_sha && (
                          <Tooltip delayDuration={150}>
                            <TooltipTrigger asChild>
                              <span className="rounded-full border bg-muted/40 px-1.5 py-0.5 font-mono text-xs">
                                {shortSha(item.git_sha)}
                              </span>
                            </TooltipTrigger>
                            <TooltipContent className="text-xs font-mono">{item.git_sha}</TooltipContent>
                          </Tooltip>
                        )}
                      </p>
                    </div>
                    {item.demo && (
                      <Tooltip delayDuration={150}>
                        <TooltipTrigger asChild>
                          <span className="shrink-0 rounded-full border border-sky-200 bg-sky-100 px-1.5 py-0.5 text-[10px] font-medium text-sky-800">
                            Demo
                          </span>
                        </TooltipTrigger>
                        <TooltipContent className="text-xs">Shared sample review — visible to every signed-in user, read-only</TooltipContent>
                      </Tooltip>
                    )}
                    {item.editable !== false && (
                    <span onClick={(e) => e.stopPropagation()}>
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
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => {
                              setRenaming(item);
                              setRenameValue(item.name);
                            }}
                          >
                            Rename
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => setDeleting(item)}
                          >
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </span>
                    )}
                  </div>

                  <Tooltip delayDuration={150}>
                    <TooltipTrigger asChild>
                      <div className="mt-3 flex h-1.5 w-full overflow-hidden rounded-full bg-muted">
                        {total > 0 &&
                          SEVERITY_ORDER.map((s) => {
                            const count = item.counts.by_severity[s] ?? 0;
                            if (count === 0) return null;
                            return (
                              <span
                                key={s}
                                className={SEVERITY_META[s].dot}
                                style={{ width: `${(count / total) * 100}%` }}
                              />
                            );
                          })}
                      </div>
                    </TooltipTrigger>
                    <TooltipContent className="text-xs">
                      {total === 0
                        ? 'No findings'
                        : SEVERITY_ORDER.filter((s) => (item.counts.by_severity[s] ?? 0) > 0)
                            .map((s) => `${item.counts.by_severity[s]} ${SEVERITY_META[s].label.toLowerCase()}`)
                            .join(' · ')}
                    </TooltipContent>
                  </Tooltip>
                  <p className="mt-1.5 text-[11px] text-slate-700">
                    {total === 0 ? (
                      'No findings'
                    ) : (
                      SEVERITY_ORDER.filter((s) => (item.counts.by_severity[s] ?? 0) > 0).map((s, idx) => (
                        <span key={s}>
                          {idx > 0 && ' · '}
                          <span className={SEVERITY_META[s].text}>{item.counts.by_severity[s]}</span>{' '}
                          {SEVERITY_META[s].label.toLowerCase()}
                        </span>
                      ))
                    )}
                  </p>

                  <div className="mt-2.5 flex items-center gap-2 border-t pt-2 text-[11px] text-muted-foreground">
                    <span>{total} finding{total === 1 ? '' : 's'}</span>
                    <Tooltip delayDuration={150}>
                      <TooltipTrigger asChild>
                        <span className="rounded-full border bg-muted/40 px-1.5 py-0.5 font-medium">
                          {SOURCE_FORMAT_LABEL[item.source_format]}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent className="text-xs">Import source format</TooltipContent>
                    </Tooltip>
                    <span className="ml-auto">{fmtDate(item.created_at)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </TooltipProvider>

      <Dialog open={!!renaming} onOpenChange={(open) => !open && setRenaming(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Rename review</DialogTitle>
          </DialogHeader>
          <input
            autoFocus
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleRename();
            }}
            aria-label="New review name"
            className="h-9 w-full rounded-md border border-input bg-background px-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <DialogFooter>
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
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete review</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Delete &quot;{deleting?.name}&quot;? This can&apos;t be undone.
          </p>
          <DialogFooter>
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

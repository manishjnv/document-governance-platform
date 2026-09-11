'use client';

import { useMemo } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, Search as SearchIcon } from 'lucide-react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { CodeReviewFinding, SEVERITY_META, VERDICT_META, Verdict } from '../../lib';

export type SortKey = 'idx' | 'severity' | 'title' | 'vuln_class' | 'cwe' | 'cvss_score' | 'confidence' | 'file';
export type SortDir = 'asc' | 'desc';

const CWE_RE = /^CWE-(\d+)$/i;

/** Focus the next/previous data row relative to the row that was
 * keyboard-navigated from, wrapping at the table body boundary is not
 * needed — clamped at the ends. */
function moveRowFocus(row: HTMLElement, dir: 1 | -1) {
  const rows = Array.from(row.closest('tbody, [data-row-list]')?.querySelectorAll<HTMLElement>('[data-row]') ?? []);
  const i = rows.indexOf(row);
  const next = rows[i + dir];
  next?.focus();
}

function SeverityCell({ severity }: { severity: CodeReviewFinding['severity'] }) {
  const meta = SEVERITY_META[severity] ?? SEVERITY_META.info;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', meta.dot)} aria-hidden="true" />
      {meta.label}
    </span>
  );
}

function CweCell({ cwe }: { cwe: string | null }) {
  if (!cwe) return <span className="text-muted-foreground">—</span>;
  const match = cwe.match(CWE_RE);
  if (!match) return <span className="text-muted-foreground">{cwe}</span>;
  return (
    <a
      href={`https://cwe.mitre.org/data/definitions/${match[1]}.html`}
      target="_blank"
      rel="noreferrer"
      className="text-primary hover:underline"
    >
      {cwe}
    </a>
  );
}

function ConfidenceCell({ confidence, votes }: { confidence: number; votes: number }) {
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <div className="h-1.5 w-14 rounded-full bg-muted" aria-label={`${Math.round(confidence * 100)}% confidence`}>
          <div className="h-1.5 rounded-full bg-primary" style={{ width: `${Math.round(confidence * 100)}%` }} />
        </div>
      </TooltipTrigger>
      <TooltipContent className="text-xs">
        {Math.round(confidence * 100)}% · {votes} vote{votes === 1 ? '' : 's'}
      </TooltipContent>
    </Tooltip>
  );
}

function VerdictCell({ verdict }: { verdict: CodeReviewFinding['verdict'] }) {
  if (!verdict) return <span className="text-muted-foreground">—</span>;
  const meta = VERDICT_META[verdict as Verdict];
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <span className={cn('inline-flex cursor-default items-center whitespace-nowrap rounded-full border px-1.5 py-0.5 text-[11px] font-medium', meta.chip)}>
          {meta.label}
        </span>
      </TooltipTrigger>
      <TooltipContent className="text-xs">{meta.tooltip}</TooltipContent>
    </Tooltip>
  );
}

export function FindingsTable({
  rows,
  allFindings,
  totalCount,
  search,
  onSearchChange,
  klass,
  onKlassChange,
  verdict,
  onVerdictChange,
  sortKey,
  sortDir,
  onSort,
  onOpenFinding,
}: {
  /** Current filtered + sorted findings to render. */
  rows: CodeReviewFinding[];
  /** Unfiltered findings, used only to build the class dropdown options. */
  allFindings: CodeReviewFinding[];
  /** Total findings before any filter (for "showing X of Y"). */
  totalCount: number;
  search: string;
  onSearchChange: (v: string) => void;
  klass: string | null;
  onKlassChange: (v: string | null) => void;
  verdict: Verdict | 'none' | null;
  onVerdictChange: (v: Verdict | 'none' | null) => void;
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (key: SortKey) => void;
  onOpenFinding: (idx: number) => void;
}) {
  const classOptions = useMemo(() => {
    const map = new Map<string, string>();
    allFindings.forEach((f) => map.set(f.vuln_class, f.vuln_class_label));
    return Array.from(map.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  }, [allFindings]);

  const SortHeader = ({ label, sk }: { label: string; sk: SortKey }) => (
    <TableHead className="sticky top-0 z-10 h-auto whitespace-nowrap bg-background px-2.5 py-2">
      <button
        type="button"
        onClick={() => onSort(sk)}
        className="flex items-center gap-1 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {label}
        {sortKey === sk ? (
          sortDir === 'asc' ? <ArrowUp size={11} aria-hidden="true" /> : <ArrowDown size={11} aria-hidden="true" />
        ) : (
          <ArrowUpDown size={11} className="text-muted-foreground/50" aria-hidden="true" />
        )}
      </button>
    </TableHead>
  );

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full sm:w-64">
          <SearchIcon size={13} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <input
            type="search"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search title, file, or CWE…"
            aria-label="Search findings by title, file, or CWE"
            className="h-8 w-full rounded-md border border-input bg-background pl-7 pr-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <select
          value={klass ?? ''}
          onChange={(e) => onKlassChange(e.target.value || null)}
          aria-label="Filter by vulnerability class"
          className="h-8 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="">All classes</option>
          {classOptions.map(([id, label]) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={verdict ?? ''}
          onChange={(e) => onVerdictChange((e.target.value || null) as Verdict | 'none' | null)}
          aria-label="Filter by verdict"
          className="h-8 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="">All verdicts</option>
          <option value="TRUE_POSITIVE">Confirmed</option>
          <option value="FALSE_POSITIVE">False positive</option>
          <option value="none">Unverified</option>
        </select>
      </div>

      <div className="hidden overflow-x-auto rounded-md border sm:block">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <SortHeader label="#" sk="idx" />
              <SortHeader label="Severity" sk="severity" />
              <SortHeader label="Title" sk="title" />
              <SortHeader label="Class" sk="vuln_class" />
              <SortHeader label="CWE" sk="cwe" />
              <SortHeader label="CVSS" sk="cvss_score" />
              <SortHeader label="Confidence" sk="confidence" />
              <SortHeader label="File:lines" sk="file" />
              <TableHead className="sticky top-0 z-10 h-auto whitespace-nowrap bg-background px-2.5 py-2">Verdict</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((f, i) => (
              <TableRow
                key={f.idx}
                data-row
                tabIndex={0}
                role="button"
                aria-label={`Open finding ${f.idx}: ${f.title}`}
                onClick={() => onOpenFinding(f.idx)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onOpenFinding(f.idx);
                  } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    moveRowFocus(e.currentTarget, 1);
                  } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    moveRowFocus(e.currentTarget, -1);
                  }
                }}
                className={cn(
                  'cursor-pointer transition-colors hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  i % 2 === 1 && 'bg-muted/30'
                )}
              >
                <TableCell className="px-2.5 py-1.5 text-muted-foreground">{f.idx}</TableCell>
                <TableCell className="px-2.5 py-1.5">
                  <SeverityCell severity={f.severity} />
                </TableCell>
                <TableCell className="max-w-xs px-2.5 py-1.5 font-medium">
                  <span className="line-clamp-2">{f.title}</span>
                </TableCell>
                <TableCell className="px-2.5 py-1.5 text-muted-foreground">{f.vuln_class_label}</TableCell>
                <TableCell className="px-2.5 py-1.5">
                  <CweCell cwe={f.cwe} />
                </TableCell>
                <TableCell className="px-2.5 py-1.5 text-right font-mono text-xs">{f.cvss_score ?? '—'}</TableCell>
                <TableCell className="px-2.5 py-1.5">
                  <ConfidenceCell confidence={f.confidence} votes={f.votes} />
                </TableCell>
                <TableCell className="max-w-xs px-2.5 py-1.5">
                  <Tooltip delayDuration={150}>
                    <TooltipTrigger asChild>
                      <span className="block truncate font-mono text-xs text-muted-foreground">
                        {f.file}:{f.line_start}-{f.line_end}
                      </span>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-sm break-all text-xs">
                      {f.file}:{f.line_start}-{f.line_end}
                    </TooltipContent>
                  </Tooltip>
                </TableCell>
                <TableCell className="px-2.5 py-1.5">
                  <VerdictCell verdict={f.verdict} />
                </TableCell>
              </TableRow>
            ))}
            {rows.length === 0 && (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={9} className="px-2.5 py-6 text-center text-sm text-muted-foreground">
                  No findings match your search or filter.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Mobile card rows */}
      <div data-row-list className="space-y-1.5 sm:hidden">
        {rows.map((f) => (
          <div
            key={f.idx}
            data-row
            tabIndex={0}
            role="button"
            aria-label={`Open finding ${f.idx}: ${f.title}`}
            onClick={() => onOpenFinding(f.idx)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onOpenFinding(f.idx);
              }
            }}
            className="cursor-pointer rounded-md border p-3 transition-colors hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="line-clamp-2 text-sm font-medium">{f.title}</span>
              <SeverityCell severity={f.severity} />
            </div>
            <div className="mt-1 truncate font-mono text-xs text-muted-foreground">
              {f.file}:{f.line_start}-{f.line_end}
            </div>
          </div>
        ))}
        {rows.length === 0 && <p className="py-6 text-center text-sm text-muted-foreground">No findings match your search or filter.</p>}
      </div>

      <p className="text-xs text-muted-foreground">
        Showing {rows.length} of {totalCount} finding{totalCount === 1 ? '' : 's'}
      </p>
    </div>
  );
}

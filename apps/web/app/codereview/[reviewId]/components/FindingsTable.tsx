'use client';

import { useMemo } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, Search as SearchIcon } from 'lucide-react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Chip, type ChipTone } from '@/components/app';
import { cn } from '@/lib/utils';
import { CodeReviewFinding, FIX_STATUS_META, FixStatus, SEVERITY_META, Severity, VERDICT_META, Verdict } from '../../lib';

export type SortKey = 'idx' | 'severity' | 'title' | 'vuln_class' | 'cwe' | 'cvss_score' | 'confidence' | 'file';
export type SortDir = 'asc' | 'desc';

const CWE_RE = /^CWE-(\d+)$/i;

const SEV_TONE: Record<Severity, ChipTone> = {
  critical: 'crit',
  high: 'high',
  medium: 'med',
  low: 'low',
  info: 'info',
};

const VERDICT_TONE: Record<Verdict, ChipTone> = {
  TRUE_POSITIVE: 'ok',
  FALSE_POSITIVE: 'neutral',
};

const FIX_STATUS_TONE: Record<FixStatus, ChipTone> = {
  fixed: 'ok',
  patch_rejected: 'crit',
  needs_review: 'med',
  not_fixed: 'neutral',
  not_attempted: 'neutral',
};

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
    <Chip tone={SEV_TONE[severity] ?? 'info'} dot xs>
      {meta.label}
    </Chip>
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
      className="font-mono text-xs text-primary hover:underline"
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

function FixCell({ fix }: { fix: CodeReviewFinding['fix'] }) {
  if (!fix) return <span className="text-muted-foreground">—</span>;
  const brokeTests = fix.tests === 'broke_tests';
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <span>
          <Chip tone={brokeTests ? 'crit' : FIX_STATUS_TONE[fix.status]} xs>
            {FIX_STATUS_META[fix.status].label}
          </Chip>
        </span>
      </TooltipTrigger>
      <TooltipContent className="text-xs">
        {brokeTests ? 'Fix broke a test: do not treat as fixed' : FIX_STATUS_META[fix.status].label}
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
        <span>
          <Chip tone={VERDICT_TONE[verdict as Verdict]} xs>
            {meta.label}
          </Chip>
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
  showFixColumn,
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
  /** Show the compact Fix-status column — only meaningful for a fix-mode run-folder upload. */
  showFixColumn?: boolean;
}) {
  const classOptions = useMemo(() => {
    const map = new Map<string, string>();
    allFindings.forEach((f) => map.set(f.vuln_class, f.vuln_class_label));
    return Array.from(map.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  }, [allFindings]);

  const SortHeader = ({ label, sk, right }: { label: string; sk: SortKey; right?: boolean }) => (
    <TableHead className={cn('h-auto whitespace-nowrap px-2.5 py-2', right && 'r')}>
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
            className="h-8 w-full rounded-md border border-input bg-card pl-7 pr-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <select
          value={klass ?? ''}
          onChange={(e) => onKlassChange(e.target.value || null)}
          aria-label="Filter by vulnerability class"
          className="h-8 rounded-md border border-input bg-card px-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
          className="h-8 rounded-md border border-input bg-card px-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="">All verdicts</option>
          <option value="TRUE_POSITIVE">Confirmed</option>
          <option value="FALSE_POSITIVE">False positive</option>
          <option value="none">Unverified</option>
        </select>
      </div>

      <div className="overflow-hidden rounded-[10px] border border-border bg-card">
        <Table className="tbl cards">
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <SortHeader label="#" sk="idx" />
              <SortHeader label="Severity" sk="severity" />
              <SortHeader label="Title" sk="title" />
              <SortHeader label="Class" sk="vuln_class" />
              <SortHeader label="CWE" sk="cwe" />
              <SortHeader label="CVSS" sk="cvss_score" right />
              <SortHeader label="Confidence" sk="confidence" />
              <SortHeader label="File:lines" sk="file" />
              <TableHead className="h-auto whitespace-nowrap px-2.5 py-2">Verdict</TableHead>
              {showFixColumn && <TableHead className="h-auto whitespace-nowrap px-2.5 py-2">Fix</TableHead>}
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
                  'clickable transition-colors hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  i % 2 === 1 && 'bg-muted/30'
                )}
              >
                <TableCell className="px-2.5 py-1.5 font-mono text-xs text-muted-foreground" data-th="#">
                  {f.idx}
                </TableCell>
                <TableCell className="px-2.5 py-1.5" data-th="Severity">
                  <SeverityCell severity={f.severity} />
                </TableCell>
                <TableCell className="max-w-xs px-2.5 py-1.5 font-medium" data-th="Title">
                  <span className="line-clamp-2">{f.title}</span>
                </TableCell>
                <TableCell className="px-2.5 py-1.5 text-muted-foreground" data-th="Class">
                  {f.vuln_class_label}
                </TableCell>
                <TableCell className="px-2.5 py-1.5" data-th="CWE">
                  <CweCell cwe={f.cwe} />
                </TableCell>
                <TableCell className="r px-2.5 py-1.5 font-mono text-xs tabular-nums" data-th="CVSS">
                  {f.cvss_score ?? '—'}
                </TableCell>
                <TableCell className="px-2.5 py-1.5" data-th="Confidence">
                  <ConfidenceCell confidence={f.confidence} votes={f.votes} />
                </TableCell>
                <TableCell className="max-w-xs px-2.5 py-1.5" data-th="File:lines">
                  <Tooltip delayDuration={150}>
                    <TooltipTrigger asChild>
                      <span className="line-clamp-2 break-all font-mono text-xs text-muted-foreground">
                        {f.file}:{f.line_start}-{f.line_end}
                      </span>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-sm break-all text-xs">
                      {f.file}:{f.line_start}-{f.line_end}
                    </TooltipContent>
                  </Tooltip>
                </TableCell>
                <TableCell className="px-2.5 py-1.5" data-th="Verdict">
                  <VerdictCell verdict={f.verdict} />
                </TableCell>
                {showFixColumn && (
                  <TableCell className="px-2.5 py-1.5" data-th="Fix">
                    <FixCell fix={f.fix} />
                  </TableCell>
                )}
              </TableRow>
            ))}
            {rows.length === 0 && (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={showFixColumn ? 10 : 9} className="px-2.5 py-6 text-center text-sm text-muted-foreground">
                  No findings match your search or filter.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <p className="text-xs text-muted-foreground">
        Showing {rows.length} of {totalCount} finding{totalCount === 1 ? '' : 's'}
      </p>
    </div>
  );
}

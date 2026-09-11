'use client';

import { useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { CodeReviewFinding, SEVERITY_META, VERDICT_META, Verdict } from '../../lib';
import { useSheetResize } from '../../../mitre/components/useSheetResize';

const CWE_RE = /^CWE-(\d+)$/i;

function SeverityChip({ severity }: { severity: CodeReviewFinding['severity'] }) {
  const meta = SEVERITY_META[severity] ?? SEVERITY_META.info;
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <span className={cn('inline-flex cursor-default items-center rounded-full border px-1.5 py-0.5 text-[11px] font-medium', meta.chip)}>
          {meta.label}
        </span>
      </TooltipTrigger>
      <TooltipContent className="text-xs">{meta.label} severity (scanner-assigned)</TooltipContent>
    </Tooltip>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="whitespace-pre-wrap text-sm leading-snug">{children}</div>
    </div>
  );
}

/** Right-side resizable drawer for one finding, with prev/next through the
 * caller's current filtered+sorted `list` and a `?finding=N` deep link. */
export function FindingDrawer({
  reviewId,
  list,
  selectedIdx,
  onSelect,
}: {
  reviewId: string;
  /** Current filtered + sorted findings — prev/next walk this array. */
  list: CodeReviewFinding[];
  selectedIdx: number | null;
  onSelect: (idx: number | null) => void;
}) {
  const resize = useSheetResize();
  const [copied, setCopied] = useState(false);

  // Deep link: open ?finding=N once on mount.
  useEffect(() => {
    // ponytail: window.location instead of useSearchParams — avoids the Suspense boundary Next requires
    const raw = new URLSearchParams(window.location.search).get('finding');
    if (raw !== null) {
      const n = Number(raw);
      if (Number.isFinite(n)) onSelect(n);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const position = useMemo(() => list.findIndex((f) => f.idx === selectedIdx), [list, selectedIdx]);
  const selected = position >= 0 ? list[position] : null;
  const cweMatch = selected?.cwe?.match(CWE_RE);

  const goTo = (delta: 1 | -1) => {
    const next = list[position + delta];
    if (next) onSelect(next.idx);
  };

  const copyLink = async () => {
    if (!selected) return;
    const url = `${window.location.origin}/codereview/${reviewId}?finding=${selected.idx}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ponytail: clipboard permission denial is non-fatal, silently ignore
    }
  };

  return (
    <Sheet open={selected !== null} onOpenChange={(open) => !open && onSelect(null)}>
      <SheetContent side="right" style={resize.style} className="flex w-full flex-col overflow-y-auto p-5 sm:max-w-lg">
        {resize.handle}
        {selected && (
          <>
            <SheetTitle className="flex flex-wrap items-center gap-2 text-base">
              <span className="font-mono text-muted-foreground">#{selected.idx}</span>
              <SeverityChip severity={selected.severity} />
              {selected.title}
            </SheetTitle>

            <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground sm:grid-cols-3">
              {selected.cwe && (
                <div>
                  <div className="font-semibold text-foreground">CWE</div>
                  <CweRef cwe={selected.cwe} match={cweMatch} />
                </div>
              )}
              {selected.cvss_score != null && (
                <div>
                  <div className="font-semibold text-foreground">CVSS</div>
                  {selected.cvss_score} {selected.cvss_rating ? `(${selected.cvss_rating})` : ''}
                  {selected.cvss_vector && <div className="break-all font-mono text-[11px]">{selected.cvss_vector}</div>}
                </div>
              )}
              <div>
                <div className="font-semibold text-foreground">Confidence</div>
                {Math.round(selected.confidence * 100)}% · {selected.votes} vote{selected.votes === 1 ? '' : 's'}
              </div>
              {selected.verdict && (
                <div>
                  <div className="font-semibold text-foreground">Verdict</div>
                  <span className={cn('inline-flex items-center rounded-full border px-1.5 py-0.5 text-[11px] font-medium', VERDICT_META[selected.verdict as Verdict].chip)}>
                    {VERDICT_META[selected.verdict as Verdict].label}
                  </span>
                  {selected.verdict_confidence != null && ` ${selected.verdict_confidence}%`}
                  {selected.verdict_reason && <div className="mt-0.5">{selected.verdict_reason}</div>}
                </div>
              )}
              <div>
                <div className="font-semibold text-foreground">File</div>
                <span className="break-all font-mono">
                  {selected.file}:{selected.line_start}-{selected.line_end}
                </span>
              </div>
              {(selected.source_ref || selected.sink_ref) && (
                <div>
                  <div className="font-semibold text-foreground">Source → Sink</div>
                  <span className="break-all font-mono text-[11px]">{selected.source_ref ?? '?'} {'->'} {selected.sink_ref ?? '?'}</span>
                </div>
              )}
            </div>

            <div className="mt-4 flex-1 space-y-4">
              {selected.description && <Section label="Description">{selected.description}</Section>}
              {selected.impact && <Section label="Impact">{selected.impact}</Section>}
              {selected.exploit_scenario && <Section label="Exploit scenario">{selected.exploit_scenario}</Section>}
              {selected.preconditions.length > 0 && (
                <div>
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Preconditions</div>
                  <ul className="list-disc space-y-0.5 pl-4 text-sm">
                    {selected.preconditions.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>
              )}
              {selected.code_snippet && (
                <div>
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Code</div>
                  <pre className="overflow-x-auto rounded-md bg-muted/60 p-2.5 font-mono text-xs">
                    {selected.code_snippet.split('\n').map((line, i) => (
                      <div key={i}>
                        <span className="mr-3 select-none text-muted-foreground/60">{selected.line_start + i}</span>
                        {line}
                      </div>
                    ))}
                  </pre>
                </div>
              )}
              {selected.recommendation && <Section label="How to fix">{selected.recommendation}</Section>}
              {selected.exploitability_notes && <Section label="Exploitability">{selected.exploitability_notes}</Section>}
              {selected.verifier_reasoning && <Section label="Verifier reasoning">{selected.verifier_reasoning}</Section>}
              {selected.duplicates.length > 0 && (
                <div>
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Also at</div>
                  <ul className="list-disc space-y-0.5 pl-4 font-mono text-xs">
                    {selected.duplicates.map((d, i) => (
                      <li key={i}>
                        {d.file}:{d.line_start}-{d.line_end}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="sticky bottom-0 -mx-5 mt-4 flex items-center justify-between gap-2 border-t bg-background px-5 py-3">
              <Button size="sm" variant="outline" disabled={position <= 0} onClick={() => goTo(-1)}>
                <ChevronLeft size={14} className="mr-1" aria-hidden="true" />
                Prev
              </Button>
              <span className="text-xs text-muted-foreground">
                {position + 1} of {list.length}
              </span>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" onClick={copyLink}>
                  <Copy size={14} className="mr-1" aria-hidden="true" />
                  {copied ? 'Copied' : 'Copy link'}
                </Button>
                <Button size="sm" variant="outline" disabled={position < 0 || position >= list.length - 1} onClick={() => goTo(1)}>
                  Next
                  <ChevronRight size={14} className="ml-1" aria-hidden="true" />
                </Button>
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

function CweRef({ cwe, match }: { cwe: string; match: RegExpMatchArray | null | undefined }) {
  if (!match) return <span>{cwe}</span>;
  return (
    <a href={`https://cwe.mitre.org/data/definitions/${match[1]}.html`} target="_blank" rel="noreferrer" className="text-primary hover:underline">
      {cwe}
    </a>
  );
}

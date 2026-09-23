'use client';

import { useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Copy, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { AlertBanner, Chip, useResize, type ChipTone } from '@/components/app';
import { cn } from '@/lib/utils';
import {
  CodeReviewFinding,
  DEEP_VERIFIED_LABEL,
  FIX_STATUS_META,
  FIX_TESTS_META,
  FixStatus,
  SEVERITY_META,
  Severity,
  VERDICT_META,
  Verdict,
} from '../../lib';
import { FIX_RE, RISK_RE } from './highlightWords';

const CWE_RE = /^CWE-(\d+)$/i;
const WIDTH_KEY = 'codereview-sheet-width';

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

/* ---------- rich text: highlight keywords, code tokens, links; bullet long prose ---------- */
const ABBREV_RE = /^(e\.g|i\.e|etc|vs|cf)$/i;
const CODE_RE =
  /`[^`]+`|https?:\/\/[^\s)]+|\b(?:GET|POST|PUT|PATCH|DELETE)\s+\/[\w\-./:?=&{}]*|\b(?:[A-Za-z_$][\w$]*\.)+[A-Za-z_$][\w$]*(?:\(\))?|\b[a-z][\w$]*[A-Z][\w$]*(?:\(\))?|\b[\w.-]+\.(?:js|ts|py|json|yml|yaml|html|env)\b|\b\w+\(\)|\/(?:[\w\-]+\/)+[\w\-.]*|\/[a-z][\w\-]+\b/g;

function Code({ children }: { children: string }) {
  return (
    <code className="rounded bg-muted px-1 py-0.5 font-mono text-[12px] text-foreground ring-1 ring-inset ring-border">
      {children}
    </code>
  );
}

/** Colour a sentence: code chips, links, risk words (rose) and fix words (emerald). */
function Highlight({ text, fixTone }: { text: string; fixTone?: boolean }) {
  const parts: React.ReactNode[] = [];
  let last = 0;
  let key = 0;
  const words = (chunk: string) => {
    const re = fixTone ? FIX_RE : RISK_RE;
    const cls = fixTone ? 'font-semibold text-ok' : 'font-semibold text-sev-crit';
    let l = 0;
    re.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(chunk)) !== null) {
      if (m.index > l) parts.push(chunk.slice(l, m.index));
      parts.push(<span key={`w${key++}`} className={cls}>{m[0]}</span>);
      l = m.index + m[0].length;
    }
    if (l < chunk.length) parts.push(chunk.slice(l));
  };
  CODE_RE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = CODE_RE.exec(text)) !== null) {
    if (m.index > last) words(text.slice(last, m.index));
    const tok = m[0];
    if (ABBREV_RE.test(tok)) {
      words(tok);
    } else if (/^https?:\/\//.test(tok)) {
      parts.push(
        <a key={`l${key++}`} href={tok} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-primary hover:underline">
          {tok}
          <ExternalLink size={11} aria-hidden="true" />
        </a>
      );
    } else {
      parts.push(<Code key={`c${key++}`}>{tok.replace(/^`|`$/g, '')}</Code>);
    }
    last = m.index + tok.length;
  }
  if (last < text.length) words(text.slice(last));
  return <>{parts}</>;
}

/** Split prose into short sentences and render as bullets when there are several. */
function RichText({ text, fixTone }: { text: string; fixTone?: boolean }) {
  const sentences = useMemo(
    () =>
      text
        .replace(/\s+/g, ' ')
        .replace(/(e\.g|i\.e|etc|vs|cf)\.\s/gi, '$1․ ') // protect abbreviations from the sentence split
        .split(/(?<=[.!?])(?<!\.\.)\s+(?=[A-Z`(])/) // (?<!\.\.) = ellipsis is not a sentence end
        .map((s) => s.replace(/․/g, '.').trim())
        .filter(Boolean),
    [text]
  );
  if (sentences.length <= 1) {
    return (
      <p className="text-[13.5px] leading-relaxed text-foreground">
        <Highlight text={text} fixTone={fixTone} />
      </p>
    );
  }
  return (
    <ul className="space-y-1 text-[13.5px] leading-relaxed text-foreground">
      {sentences.map((s, i) => (
        <li key={i} className="flex gap-2">
          <span className={cn('mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full', fixTone ? 'bg-ok' : 'bg-ink3')} aria-hidden="true" />
          <span className="min-w-0">
            <Highlight text={s} fixTone={fixTone} />
          </span>
        </li>
      ))}
    </ul>
  );
}

function Section({ label, tone, hint, children }: { label: string; tone: string; hint: string; children: React.ReactNode }) {
  return (
    <section>
      <Tooltip delayDuration={200}>
        <TooltipTrigger asChild>
          <h3 className="mb-1.5 flex w-fit cursor-default items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">
            <span className={cn('h-2 w-2 rounded-sm', tone)} aria-hidden="true" />
            {label}
          </h3>
        </TooltipTrigger>
        <TooltipContent side="right" className="max-w-xs text-xs">{hint}</TooltipContent>
      </Tooltip>
      {children}
    </section>
  );
}

function Fact({ label, tip, children, className }: { label: string; tip: string; children: React.ReactNode; className?: string }) {
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <div className={cn('min-w-0 cursor-default rounded-md border border-border bg-muted/30 px-2.5 py-1.5 transition-colors hover:bg-muted/60', className)}>
          <div className="text-[10px] font-semibold uppercase tracking-wide text-ink3">{label}</div>
          <div className="mt-0.5 text-xs text-foreground">{children}</div>
        </div>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">{tip}</TooltipContent>
    </Tooltip>
  );
}

function cvssTone(score: number) {
  if (score >= 9) return 'text-sev-crit';
  if (score >= 7) return 'text-sev-high';
  if (score >= 4) return 'text-sev-med';
  return 'text-sev-low';
}

function SeverityChip({ severity }: { severity: CodeReviewFinding['severity'] }) {
  const meta = SEVERITY_META[severity] ?? SEVERITY_META.info;
  return (
    <Chip tone={SEV_TONE[severity] ?? 'info'} dot tip={`${meta.label} severity (scanner-assigned)`}>
      {meta.label}
    </Chip>
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
  const resize = useResize({ storageKey: WIDTH_KEY, min: 360, edge: 'left', fallback: 576 });
  const resizeStyle = resize.width
    ? { width: `min(${resize.width}px, 100vw)`, maxWidth: `min(${resize.width}px, 100vw)` }
    : undefined;
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
      <SheetContent
        side="right"
        style={resizeStyle}
        className="flex w-full flex-col gap-0 p-0 sm:max-w-xl"
        grip={
          <div
            {...resize.gripProps}
            aria-label="Resize panel (drag, or use arrow keys)"
            title="Drag to resize"
            className="absolute left-0 top-0 z-10 flex h-full w-3 cursor-ew-resize touch-none items-center justify-center focus-visible:outline-none group"
          >
            <i className="block h-10 w-1 rounded-full bg-line2 transition-colors duration-150 ease-app group-hover:bg-primary group-focus-visible:bg-primary" />
          </div>
        }
      >
        {selected && (
          <>
            <div className="border-b border-border px-6 pb-3 pt-4">
              <SheetTitle className="flex flex-wrap items-center gap-2 text-base font-semibold leading-snug text-foreground">
                <SeverityChip severity={selected.severity} />
                {selected.title}
                {selected.deep && (
                  <Chip tone="violet" xs tip="One of the scanner's top findings by CVSS, re-analyzed in a dedicated deep pass">
                    {DEEP_VERIFIED_LABEL}
                  </Chip>
                )}
              </SheetTitle>
              <p className="mt-1 font-mono text-xs text-muted-foreground">
                #{selected.idx} · {selected.vuln_class_label}
              </p>
            </div>

            <div className="flex-1 space-y-4 overflow-y-auto px-6 py-4">
            {/* Quick facts */}
            <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
              <Fact label="CWE" tip="Common Weakness Enumeration entry — opens the MITRE definition.">
                {selected.cwe ? (
                  cweMatch ? (
                    <a
                      href={`https://cwe.mitre.org/data/definitions/${cweMatch[1]}.html`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
                    >
                      {selected.cwe}
                      <ExternalLink size={11} aria-hidden="true" />
                    </a>
                  ) : (
                    selected.cwe
                  )
                ) : (
                  '—'
                )}
              </Fact>
              <Fact label="CVSS" tip={selected.cvss_vector ? `Vector: ${selected.cvss_vector}` : 'CVSS 3.1 base score'}>
                {selected.cvss_score != null ? (
                  <span className={cn('font-semibold', cvssTone(selected.cvss_score))}>
                    {selected.cvss_score} {selected.cvss_rating ? `· ${selected.cvss_rating}` : ''}
                  </span>
                ) : (
                  '—'
                )}
              </Fact>
              <Fact label="Confidence" tip={`${Math.round(selected.confidence * 100)}% from ${selected.votes} model vote${selected.votes === 1 ? '' : 's'}`}>
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-1.5 w-12 rounded-full bg-muted">
                    <span className="block h-1.5 rounded-full bg-primary" style={{ width: `${Math.round(selected.confidence * 100)}%` }} />
                  </span>
                  {Math.round(selected.confidence * 100)}%
                </span>
              </Fact>
              <Fact label="Verdict" tip={selected.verdict ? `${VERDICT_META[selected.verdict as Verdict].tooltip}${selected.verdict_confidence != null ? ` (${selected.verdict_confidence}/10)` : ''}` : 'Not reviewed by the verifier'}>
                {selected.verdict ? (
                  <Chip tone={VERDICT_TONE[selected.verdict as Verdict]}>
                    {VERDICT_META[selected.verdict as Verdict].label}
                  </Chip>
                ) : (
                  '—'
                )}
              </Fact>
              <Fact label="File" tip={`${selected.file} lines ${selected.line_start}–${selected.line_end}`} className="col-span-2">
                <span className="block truncate font-mono text-[12px]">
                  {selected.file}
                  <span className="text-muted-foreground">:{selected.line_start}-{selected.line_end}</span>
                </span>
              </Fact>
              {(selected.source_ref || selected.sink_ref) && (
                <Fact label="Source → Sink" tip="Where attacker-controlled data enters (source) and where it does damage (sink)." className="col-span-2 sm:col-span-3">
                  <span className="flex flex-wrap items-center gap-1 font-mono text-[12px]">
                    <span className="text-sev-info">{selected.source_ref ?? '?'}</span>
                    <span className="text-muted-foreground">→</span>
                    <span className="text-sev-crit">{selected.sink_ref ?? '?'}</span>
                  </span>
                </Fact>
              )}
            </div>

            {selected.verdict_reason && (
              <div className="rounded-md border-l-2 border-ok bg-ok-soft/60 px-3 py-2">
                <RichText text={selected.verdict_reason} />
              </div>
            )}

            <div className="space-y-4">
              {selected.description && (
                <Section label="What is wrong" tone="bg-sev-crit" hint="The weakness the scanner found, in plain words.">
                  <RichText text={selected.description} />
                </Section>
              )}
              {selected.impact && (
                <Section label="Why it matters" tone="bg-sev-high" hint="What an attacker gains if this is real.">
                  <RichText text={selected.impact} />
                </Section>
              )}
              {selected.recommendation && (
                <Section label="How to fix" tone="bg-ok" hint="Suggested remediation — verify before applying.">
                  <RichText text={selected.recommendation} fixTone />
                </Section>
              )}
              {selected.exploit_scenario && (
                <Section label="How it is exploited" tone="bg-sev-med" hint="A concrete attack path the scanner reasoned about.">
                  <RichText text={selected.exploit_scenario} />
                </Section>
              )}
              {selected.preconditions.length > 0 && (
                <Section label="Preconditions" tone="bg-ink3" hint="What must already be true for the attack to work.">
                  <ul className="space-y-1 text-[13.5px] leading-relaxed text-foreground">
                    {selected.preconditions.map((p, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-ink3" aria-hidden="true" />
                        <span className="min-w-0"><Highlight text={p} /></span>
                      </li>
                    ))}
                  </ul>
                </Section>
              )}
              {selected.code_snippet && (
                <Section label="Code" tone="bg-foreground" hint={`${selected.file}, starting at line ${selected.line_start}`}>
                  <pre className="overflow-auto rounded-lg border border-border bg-muted/50 p-3 font-mono text-xs leading-[1.55]">
                    {selected.code_snippet.split('\n').map((line, i) => (
                      <div key={i} className="whitespace-pre">
                        <span className="mr-3 inline-block w-8 select-none text-right text-muted-foreground">{selected.line_start + i}</span>
                        {line}
                      </div>
                    ))}
                  </pre>
                </Section>
              )}
              {selected.exploitability_notes && (
                <Section label="Exploitability" tone="bg-sev-med" hint="How easy the scanner thinks this is to exploit in practice.">
                  <RichText text={selected.exploitability_notes} />
                </Section>
              )}
              {selected.verifier_reasoning && (
                <Section label="Verifier reasoning" tone="bg-ok" hint="The second-pass model's reasoning for its verdict.">
                  <RichText text={selected.verifier_reasoning} />
                </Section>
              )}
              {selected.duplicates.length > 0 && (
                <Section label="Also at" tone="bg-line2" hint="Other locations with the same pattern.">
                  <ul className="space-y-0.5 font-mono text-xs text-muted-foreground">
                    {selected.duplicates.map((d, i) => (
                      <li key={i}>
                        {d.file}:{d.line_start}-{d.line_end}
                      </li>
                    ))}
                  </ul>
                </Section>
              )}
              {selected.fix && (
                <Section label="Fix" tone="bg-primary" hint="What the scanner's own automated fix attempt did to this finding.">
                  <div className="min-w-0 space-y-2.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <Chip tone={selected.fix.tests === 'broke_tests' ? 'crit' : FIX_STATUS_TONE[selected.fix.status]} tip={selected.fix.scanner_verdict}>
                        {FIX_STATUS_META[selected.fix.status].label}
                      </Chip>
                      {selected.fix.tests && (
                        <span className="text-xs text-muted-foreground">
                          {FIX_TESTS_META[selected.fix.tests].label}
                          {selected.fix.tests_detail ? ` — ${selected.fix.tests_detail}` : ''}
                        </span>
                      )}
                    </div>
                    {selected.fix.tests === 'broke_tests' && (
                      <AlertBanner kind="error">Fix broke a test: do not treat as fixed</AlertBanner>
                    )}
                    {selected.fix.files.length > 0 && (
                      <div className="min-w-0">
                        <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-ink3">Files changed</div>
                        <ul className="space-y-0.5 font-mono text-xs text-muted-foreground">
                          {selected.fix.files.map((f, i) => (
                            <li key={i} className="truncate">{f}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {selected.fix.patch && (
                      <details className="min-w-0 rounded-md border border-border">
                        <summary className="cursor-pointer select-none px-2.5 py-1.5 text-xs font-medium text-foreground">
                          Patch
                        </summary>
                        <pre className="min-w-0 overflow-auto border-t border-border bg-muted/50 p-3 font-mono text-xs leading-[1.55]">
                          {selected.fix.patch}
                        </pre>
                      </details>
                    )}
                  </div>
                </Section>
              )}
              {selected.deep && (
                <Section label="Scanner evidence" tone="bg-violet" hint="The scanner's own deep-analysis pass on this finding.">
                  <div className="min-w-0 space-y-2.5">
                    {selected.deep.root_cause && <RichText text={selected.deep.root_cause} />}
                    {(selected.deep.gates.source || selected.deep.gates.sink || selected.deep.gates.missing_control) && (
                      <div className="flex flex-wrap gap-1.5">
                        {selected.deep.gates.source && <Chip tone="neutral" xs tip="Gate: source">Source: {selected.deep.gates.source}</Chip>}
                        {selected.deep.gates.sink && <Chip tone="neutral" xs tip="Gate: sink">Sink: {selected.deep.gates.sink}</Chip>}
                        {selected.deep.gates.missing_control && (
                          <Chip tone="neutral" xs tip="Gate: missing control">Missing control: {selected.deep.gates.missing_control}</Chip>
                        )}
                      </div>
                    )}
                    {selected.deep.remaining_risks.length > 0 && (
                      <div className="min-w-0">
                        <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-ink3">Remaining risks</div>
                        <ul className="space-y-1 text-[13.5px] leading-relaxed text-foreground">
                          {selected.deep.remaining_risks.map((r, i) => (
                            <li key={i} className="flex gap-2">
                              <span className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-sev-crit" aria-hidden="true" />
                              <span className="min-w-0"><Highlight text={r} /></span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </Section>
              )}
            </div>
            </div>

            <div className="flex items-center justify-between gap-2 border-t border-border bg-card px-5 py-2.5">
              <Tooltip delayDuration={200}>
                <TooltipTrigger asChild>
                  <Button size="sm" variant="outline" disabled={position <= 0} onClick={() => goTo(-1)}>
                    <ChevronLeft size={14} className="mr-1" aria-hidden="true" />
                    Prev
                  </Button>
                </TooltipTrigger>
                <TooltipContent className="text-xs">Previous finding in the current list</TooltipContent>
              </Tooltip>
              <span className="text-xs text-muted-foreground">
                {position + 1} of {list.length}
              </span>
              <div className="flex items-center gap-2">
                <Tooltip delayDuration={200}>
                  <TooltipTrigger asChild>
                    <Button size="sm" variant="outline" onClick={copyLink}>
                      <Copy size={14} className="mr-1" aria-hidden="true" />
                      {copied ? 'Copied' : 'Copy link'}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="text-xs">Copy a link that opens this finding directly</TooltipContent>
                </Tooltip>
                <Tooltip delayDuration={200}>
                  <TooltipTrigger asChild>
                    <Button size="sm" variant="outline" disabled={position < 0 || position >= list.length - 1} onClick={() => goTo(1)}>
                      Next
                      <ChevronRight size={14} className="ml-1" aria-hidden="true" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="text-xs">Next finding in the current list</TooltipContent>
                </Tooltip>
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

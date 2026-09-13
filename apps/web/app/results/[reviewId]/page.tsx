/**
 * T-704: Review results page with scorecard
 * Display review findings, scores, and risk assessment
 */

'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import axios from 'axios';
import Link from 'next/link';
import { ChevronDown, FileText, Check, RotateCcw, MapPin, HelpCircle } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  PageHeader,
  KpiTile,
  Chip,
  EmptyState,
  SkeletonRows,
  AlertBanner,
  useResize,
  type ChipTone,
  type KpiTone,
} from '@/components/app';
import { cn } from '@/lib/utils';

function scoreTextClass(score: number) {
  return score >= 80 ? 'text-ok' : score >= 60 ? 'text-sev-med' : 'text-sev-crit';
}
function scoreFillClass(score: number) {
  return score >= 80 ? 'bg-ok' : score >= 60 ? 'bg-sev-med' : 'bg-sev-crit';
}

// Left pane width (px) before the user has ever dragged the resize grip.
const SPLIT_FALLBACK_WIDTH = 640;

// Short, plain-English explanation shown on hover/focus of the "?" icon
// next to a metric -- see docs/planning/SCORING_METHODOLOGY.md for the
// full methodology and the frameworks it's grounded in (ISO 31000/NIST
// risk framing, PMBOK scope-completeness structure, IACCM's most-
// negotiated-terms research).
function InfoTip({ text }: { text: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button type="button" className="ml-1 align-middle text-muted-foreground hover:text-foreground">
          <HelpCircle size={13} strokeWidth={2} aria-label="What does this mean?" />
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-[240px] text-xs">{text}</TooltipContent>
    </Tooltip>
  );
}

interface Finding {
  finding_id: string;
  finding_source: string;
  title: string;
  category: string;
  severity: string;
  confidence: number;
  recommendation: string;
  description: string;
  section_ref: string | null;
  evidence_type: string | null;
  matched_text: string | null;
  status: string;
  risk_area: string;
}

interface AuditMeta {
  parsed_text_sha256?: string;
  models_used?: Record<string, string>;
  rules_version?: string;
  app_git_sha?: string;
  generated_at_utc?: string;
}

interface ReviewData {
  review_id: string;
  doc_id: string;
  status: string;
  audit_meta: AuditMeta | null;
  overall_score: number;
  risk_score: number;
  findings_count: {
    critical: number;
    major: number;
    medium: number;
    low: number;
    info: number;
  };
  findings: Finding[];
  risk_breakdown: Record<string, number> | null;
}

interface DocSection {
  heading: string;
  level: number;
  content: string;
  page_number: number | null;
}

interface DocInfo {
  original_filename: string;
  project_name: string | null;
  document_type: string | null;
  page_count: number | null;
  created_at: string;
  parsed_sections: DocSection[] | null;
}

const SEVERITIES = ['critical', 'major', 'medium', 'low', 'info'] as const;

const SEV_LABEL: Record<(typeof SEVERITIES)[number], string> = {
  critical: 'Critical',
  major: 'Major',
  medium: 'Medium',
  low: 'Low',
  info: 'Info',
};

// KpiTile has no low/info-specific tone -- accent/grey are the closest read.
const SEV_KPI_TONE: Record<(typeof SEVERITIES)[number], KpiTone> = {
  critical: 'crit',
  major: 'high',
  medium: 'med',
  low: 'accent',
  info: 'grey',
};

const SEVERITY_CHIP_TONE: Record<string, ChipTone> = {
  critical: 'crit',
  major: 'high',
  medium: 'med',
  low: 'low',
};
function sevChipTone(severity: string): ChipTone {
  return SEVERITY_CHIP_TONE[severity.toLowerCase()] ?? 'neutral';
}

// Section headings can repeat/contain characters that aren't safe as a raw
// DOM id -- slugify so scrollIntoView has a stable, unique target.
function sectionSlug(heading: string, index: number) {
  return `doc-section-${index}-${heading.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}`;
}

export default function ResultsPage() {
  const params = useParams();
  const reviewId = params.reviewId;
  const [review, setReview] = useState<ReviewData | null>(null);
  const [docInfo, setDocInfo] = useState<DocInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);
  const [areaFilter, setAreaFilter] = useState<string | null>(null);
  const [showDocument, setShowDocument] = useState(true);
  const [highlightedSection, setHighlightedSection] = useState<string | null>(null);
  const router = useRouter();
  const docPaneRef = useRef<HTMLDivElement>(null);
  const splitContainerRef = useRef<HTMLDivElement>(null);

  const {
    width: splitWidth,
    resizing: resizingSplit,
    gripProps: splitGripProps,
  } = useResize({
    storageKey: 'results_split_width',
    min: 320,
    max: () => (splitContainerRef.current?.clientWidth ?? 1200) * 0.8,
    edge: 'right',
    origin: () => splitContainerRef.current?.getBoundingClientRect().left ?? 0,
    fallback: SPLIT_FALLBACK_WIDTH,
  });

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchReview();
  }, [router, reviewId]);

  const fetchReview = async () => {
    try {
      const token = localStorage.getItem('access_token');

      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/reviews/${reviewId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      setReview({
        ...response.data,
        overall_score: response.data.overall_score ?? 0,
        risk_score: response.data.risk_score ?? 0,
      });
      setError('');

      axios
        .get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${response.data.doc_id}`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        .then((res) => setDocInfo(res.data))
        .catch(() => {});
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch review');
    } finally {
      setLoading(false);
    }
  };

  const handleViewReport = async () => {
    try {
      const token = localStorage.getItem('access_token');
      // Plain <a href target="_blank"> can't attach an Authorization header,
      // so a direct link to this endpoint always 401'd ("Missing
      // authorization credentials"). Fetch it authenticated instead and
      // open the HTML as a blob URL.
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/reviews/${reviewId}/report?format=html`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const blob = new Blob([res.data.data], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load report');
    }
  };

  const handleDownloadPdf = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/reviews/${reviewId}/report?format=pdf`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const binary = atob(res.data.data);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const base = docInfo?.original_filename?.replace(/\.[^.]+$/, '') || 'review';
      link.download = `${base}-report.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to download PDF report');
    }
  };

  const handleSetStatus = async (finding: Finding, newStatus: string) => {
    try {
      const token = localStorage.getItem('access_token');
      await axios.patch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/reviews/${reviewId}/findings/${finding.finding_id}`,
        { status: newStatus },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setReview((r) =>
        r
          ? {
              ...r,
              findings: r.findings.map((f) =>
                f.finding_id === finding.finding_id ? { ...f, status: newStatus } : f
              ),
            }
          : r
      );
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update finding');
    }
  };

  const sectionIndexByHeading = useMemo(() => {
    const map = new Map<string, number>();
    docInfo?.parsed_sections?.forEach((s, i) => {
      if (!map.has(s.heading)) map.set(s.heading, i);
    });
    return map;
  }, [docInfo]);

  const handleLocateInDoc = (sectionRef: string | null) => {
    if (!sectionRef || !docInfo?.parsed_sections) return;
    // section_ref is formatted as "Heading (p.N)" or just "Heading" -- strip the page suffix to match.
    const heading = sectionRef.replace(/\s*\(p\.\d+\)\s*$/, '');
    const index = sectionIndexByHeading.get(heading);
    if (index === undefined) return;

    if (!showDocument) setShowDocument(true);
    const slug = sectionSlug(heading, index);
    // Wait a tick for the panel to mount if it was just opened.
    setTimeout(() => {
      const el = window.document.getElementById(slug);
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setHighlightedSection(slug);
      setTimeout(() => setHighlightedSection((cur) => (cur === slug ? null : cur)), 2000);
    }, showDocument ? 0 : 100);
  };

  // "Section 5" / "Appendix A" mentions inside finding text resolve to the
  // parsed section whose heading carries that number/letter, so they can be
  // rendered as jump links into the document panel.
  const sectionByToken = useMemo(() => {
    const map = new Map<string, string>();
    docInfo?.parsed_sections?.forEach((s) => {
      const num = s.heading.match(/^\s*(\d+(?:\.\d+)*)[.)]?\s/);
      if (num && !map.has(num[1])) map.set(num[1], s.heading);
      const app = s.heading.match(/appendix\s+([a-z0-9]+)/i);
      if (app) {
        const key = `appendix ${app[1].toLowerCase()}`;
        if (!map.has(key)) map.set(key, s.heading);
      }
    });
    return map;
  }, [docInfo]);

  const SECTION_REF_RE = /\b(?:Section|§)\s*(\d+(?:\.\d+)*)|\bAppendix\s+([A-Z0-9]+)\b/gi;

  const renderWithSectionLinks = (text: string | null) => {
    if (!text) return text;
    const nodes: React.ReactNode[] = [];
    let last = 0;
    for (const m of text.matchAll(SECTION_REF_RE)) {
      const token = m[1] ? m[1] : `appendix ${(m[2] || '').toLowerCase()}`;
      const heading = sectionByToken.get(token);
      if (!heading || m.index === undefined) continue; // no such section -- leave plain
      nodes.push(text.slice(last, m.index));
      nodes.push(
        <button
          key={`${m.index}-${token}`}
          type="button"
          onClick={() => handleLocateInDoc(heading)}
          title={`Jump to "${heading}" in the document`}
          className="inline-flex items-baseline gap-0.5 rounded-sm px-0.5 font-medium text-primary underline decoration-primary/50 underline-offset-2 hover:bg-primary/10 hover:decoration-primary"
        >
          <MapPin size={10} strokeWidth={2.5} className="self-center" aria-hidden="true" />
          {m[0]}
        </button>
      );
      last = m.index + m[0].length;
    }
    if (nodes.length === 0) return text;
    nodes.push(text.slice(last));
    return nodes;
  };

  const visibleFindings = useMemo(() => {
    if (!review) return [];
    return review.findings
      .filter((f) => !severityFilter || f.severity.toLowerCase() === severityFilter)
      .filter((f) => !areaFilter || f.risk_area === areaFilter);
  }, [review, severityFilter, areaFilter]);

  // Rule-engine findings only fire when a required section/keyword/format
  // check FAILS -- so every rule-sourced finding already represents a gap,
  // no separate "expected sections" list needed to compute this.
  const ruleGaps = useMemo(
    () => review?.findings.filter((f) => f.finding_source === 'rule') ?? [],
    [review]
  );

  if (loading) {
    return (
      <AppShell fullWidth>
        <p className="py-4 text-center text-muted-foreground">Loading review...</p>
        <SkeletonRows rows={5} />
      </AppShell>
    );
  }

  if (error || !review) {
    return (
      <AppShell>
        <div className="mx-auto max-w-4xl">
          <AlertBanner kind="error">
            <p className="mb-2">{error || 'Review not found'}</p>
            <Link href="/dashboard" className="font-medium text-sev-crit hover:underline">
              Back to Dashboard
            </Link>
          </AlertBanner>
        </div>
      </AppShell>
    );
  }

  const riskTone: ChipTone = review.risk_score > 70 ? 'crit' : review.risk_score > 40 ? 'med' : 'ok';
  const riskBand = review.risk_score > 70 ? 'High' : review.risk_score > 40 ? 'Medium' : 'Low';
  const riskTextClass = review.risk_score > 70 ? 'text-sev-crit' : review.risk_score > 40 ? 'text-sev-med' : 'text-ok';

  const findingsPanel = (
    <>
      {/* Overall Score / Risk Level */}
      <div className="mb-2 grid grid-cols-2 gap-1.5">
        <div className="rounded-[10px] border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">Overall Score</span>
            <InfoTip text="How complete and well-written this document is (0-100), across scope, clarity, commercial terms, delivery, and more. Higher is better." />
          </div>
          <div className={cn('mt-0.5 text-[28px] font-semibold tabular-nums', scoreTextClass(review.overall_score))}>
            {review.overall_score.toFixed(1)}
          </div>
          <div
            role="progressbar"
            aria-valuenow={review.overall_score}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Overall score"
            className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-na"
          >
            <div
              className={cn('h-full rounded-full transition-[width] duration-500 ease-app', scoreFillClass(review.overall_score))}
              style={{ width: `${review.overall_score}%` }}
            />
          </div>
        </div>

        <div className="rounded-[10px] border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">Risk Level</span>
            <InfoTip text="How much this document could hurt you if signed as-is -- combines how severe the issues are and how many there are. Higher is worse." />
          </div>
          <div className="mt-0.5 flex items-baseline gap-2.5">
            <span className={cn('text-[28px] font-semibold tabular-nums', riskTextClass)}>
              {review.risk_score.toFixed(0)}%
            </span>
            <Chip tone={riskTone}>{riskBand}</Chip>
          </div>
        </div>
      </div>

      {/* Risk breakdown by axis -- which KIND of risk is driving the score */}
      {review.risk_breakdown && Object.keys(review.risk_breakdown).length > 0 && (
        <div className="mb-2 rounded-[10px] border border-border bg-card">
          <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-2.5">
            <h3 className="text-sm font-semibold">
              Risk by Area
              <InfoTip text="The same risk score, split by area (Legal, Commercial, Delivery, etc.) so you can see what's actually driving it. Click an area to filter the findings below to just that area." />
            </h3>
            {areaFilter && (
              <button
                onClick={() => setAreaFilter(null)}
                className="text-xs font-normal text-primary hover:underline"
              >
                clear filter
              </button>
            )}
          </div>
          <div className="space-y-1.5 p-4">
            {Object.entries(review.risk_breakdown)
              .sort((a, b) => b[1] - a[1])
              .map(([axis, score]) => {
                const active = areaFilter === axis;
                return (
                  <button
                    key={axis}
                    onClick={() => setAreaFilter(active ? null : axis)}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-lg p-1 text-xs transition-colors duration-150 ease-app',
                      active ? 'ring-2 ring-offset-1 ring-primary' : 'hover:bg-muted/60'
                    )}
                  >
                    <span className="w-20 shrink-0 truncate text-left text-[12.5px] font-medium text-foreground">{axis}</span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-na">
                      <div
                        className={cn('h-full rounded-full transition-[width] duration-500 ease-app', scoreFillClass(score))}
                        style={{ width: `${score}%` }}
                      />
                    </div>
                    <span className="w-9 shrink-0 text-right text-[12.5px] font-semibold tabular-nums text-foreground">
                      {score.toFixed(0)}%
                    </span>
                  </button>
                );
              })}
          </div>
        </div>
      )}

      {/* Document X-Ray: sections found + rule-engine gaps at a glance */}
      {docInfo?.parsed_sections && docInfo.parsed_sections.length > 0 && (
        <div className="mb-2 rounded-[10px] border border-border bg-card">
          <div className="border-b border-border px-4 py-2.5">
            <h3 className="text-sm font-semibold">
              Document X-Ray
              <InfoTip text="A quick scan of the document itself: which sections it has, and which required sections/checks are missing." />
            </h3>
          </div>
          <div className="grid grid-cols-2 gap-3 p-4 text-xs">
            <div>
              <h4 className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">
                Sections Found ({docInfo.parsed_sections.length})
              </h4>
              <ul className="space-y-0.5">
                {docInfo.parsed_sections.map((s, i) => (
                  <li key={i} className="truncate text-foreground">
                    {s.heading}
                    {s.page_number != null && <span className="text-muted-foreground"> (p.{s.page_number})</span>}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">
                Gaps Detected ({ruleGaps.length})
              </h4>
              {ruleGaps.length === 0 ? (
                <p className="text-muted-foreground">None -- passes all rule checks.</p>
              ) : (
                <ul className="space-y-0.5">
                  {ruleGaps.map((f) => (
                    <li key={f.finding_id} className="truncate text-sev-crit">
                      {f.title}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Findings Summary (clickable filters) */}
      <div className="mb-2 rounded-[10px] border border-border bg-card">
        <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-2.5">
          <h3 className="text-sm font-semibold">
            Findings Summary
            <InfoTip text="Every issue found, grouped by how serious it is. Click a number to filter the list below to just that severity." />
          </h3>
          {severityFilter && (
            <button
              onClick={() => setSeverityFilter(null)}
              className="text-xs font-normal text-primary hover:underline"
            >
              clear filter
            </button>
          )}
        </div>
        <div className="grid grid-cols-5 gap-1.5 p-4">
          {SEVERITIES.map((sev) => {
            const active = severityFilter === sev;
            return (
              <KpiTile
                key={sev}
                label={SEV_LABEL[sev]}
                value={review.findings_count[sev]}
                tone={SEV_KPI_TONE[sev]}
                active={active}
                onClick={() => setSeverityFilter(active ? null : sev)}
              />
            );
          })}
        </div>
      </div>

      {/* Findings Details */}
      <div className="rounded-[10px] border border-border bg-card">
        <div className="border-b border-border px-4 py-2.5">
          <h3 className="text-sm font-semibold">
            Findings {(severityFilter || areaFilter) && <span className="font-normal text-muted-foreground">({visibleFindings.length} of {review.findings.length})</span>}
          </h3>
        </div>
        <div className="p-4">
          {visibleFindings.length === 0 ? (
            <EmptyState title="No findings in this filter." />
          ) : (
            <div className="space-y-2">
              {visibleFindings.map((finding) => {
                const title = finding.title || finding.category?.replace(/_/g, ' ') || 'Finding';
                const fixed = finding.status === 'resolved';
                const isOpen = expandedFinding === finding.finding_id;
                return (
                  <div
                    key={finding.finding_id}
                    className={cn(
                      'overflow-hidden rounded-[10px] border transition-colors duration-150 ease-app',
                      isOpen ? 'border-primary bg-accent-soft' : 'border-border bg-card',
                      fixed && 'opacity-60'
                    )}
                  >
                    <button
                      onClick={() => setExpandedFinding(isOpen ? null : finding.finding_id)}
                      aria-expanded={isOpen}
                      aria-controls={`finding-detail-${finding.finding_id}`}
                      className="flex w-full items-center justify-between gap-2 px-3.5 py-2.5 text-left hover:bg-muted/40"
                    >
                      <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                        <Chip tone={sevChipTone(finding.severity)} xs className="uppercase tracking-wide">
                          {finding.severity}
                        </Chip>
                        {finding.risk_area && (
                          <Chip tone="neutral" xs>
                            {finding.risk_area}
                          </Chip>
                        )}
                        {fixed && (
                          <Chip tone="ok" xs className="gap-1">
                            <Check size={9} strokeWidth={3} aria-hidden="true" /> Fixed
                          </Chip>
                        )}
                        {finding.evidence_type && (
                          <Chip tone="neutral" xs>
                            {finding.evidence_type.replace(/_/g, ' ')}
                          </Chip>
                        )}
                        <h3 className={cn('truncate text-[13px] font-semibold text-foreground', fixed && 'line-through')}>
                          {title}
                        </h3>
                        {finding.section_ref && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleLocateInDoc(finding.section_ref);
                            }}
                            className="flex shrink-0 items-center gap-0.5 text-[11px] font-semibold text-primary hover:underline"
                          >
                            <MapPin size={10} strokeWidth={2.5} aria-hidden="true" />
                            {finding.section_ref}
                          </button>
                        )}
                      </div>
                      <ChevronDown
                        size={14}
                        strokeWidth={2}
                        aria-hidden="true"
                        className={cn('ml-2 shrink-0 transition-transform duration-150 ease-app', isOpen && 'rotate-180')}
                      />
                    </button>

                    {isOpen && (
                      <div id={`finding-detail-${finding.finding_id}`} className="space-y-2.5 border-t border-border px-3.5 py-3 text-[13px]">
                        <div>
                          <h4 className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">Description</h4>
                          <p className="leading-relaxed">{renderWithSectionLinks(finding.description)}</p>
                        </div>
                        {finding.matched_text && (
                          <div>
                            <h4 className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">Document Text</h4>
                            <blockquote className="border-l-2 border-line2 pl-2.5 italic text-muted-foreground">
                              {renderWithSectionLinks(finding.matched_text)}
                            </blockquote>
                          </div>
                        )}
                        <div>
                          <h4 className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">Recommendation</h4>
                          <p className="leading-relaxed">{renderWithSectionLinks(finding.recommendation)}</p>
                        </div>
                        <div>
                          <h4 className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">Confidence</h4>
                          <p className="font-semibold tabular-nums text-foreground">{finding.confidence}%</p>
                        </div>
                        <div className="pt-1">
                          {fixed ? (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleSetStatus(finding, 'open')}
                            >
                              <RotateCcw size={14} strokeWidth={2} className="mr-1.5" aria-hidden="true" />
                              Reopen
                            </Button>
                          ) : (
                            <Button size="sm" onClick={() => handleSetStatus(finding, 'resolved')}>
                              <Check size={14} strokeWidth={2} className="mr-1.5" aria-hidden="true" />
                              Mark Fixed
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {review.audit_meta && (
        <p className="px-1 text-[11px] text-ink3">
          {[
            review.audit_meta.models_used &&
              Object.values(review.audit_meta.models_used).length > 0 &&
              `Models: ${[...new Set(Object.values(review.audit_meta.models_used))].join(', ')}`,
            review.audit_meta.rules_version && `Rules ${review.audit_meta.rules_version}`,
            review.audit_meta.parsed_text_sha256 &&
              `Doc SHA-256 ${review.audit_meta.parsed_text_sha256.slice(0, 12)}…`,
            review.audit_meta.app_git_sha &&
              review.audit_meta.app_git_sha !== 'unknown' &&
              `Build ${review.audit_meta.app_git_sha.slice(0, 8)}`,
          ]
            .filter(Boolean)
            .join(' · ')}
        </p>
      )}
    </>
  );

  return (
    <AppShell fullWidth>
      <TooltipProvider delayDuration={200}>
        <PageHeader
          title="Review Results"
          back={{ href: '/dashboard', label: 'Back to Dashboard' }}
          meta={
            docInfo && (
              <>
                <span className="font-medium text-foreground">{docInfo.original_filename}</span>
                {docInfo.project_name && <> &middot; Project: {docInfo.project_name}</>}
                {docInfo.document_type && <> &middot; {docInfo.document_type}</>}
                {docInfo.page_count != null && <> &middot; {docInfo.page_count} page{docInfo.page_count === 1 ? '' : 's'}</>}
                {' '}&middot; Uploaded {new Date(docInfo.created_at).toLocaleDateString()}
              </>
            )
          }
          actions={
            <>
              {docInfo?.parsed_sections && docInfo.parsed_sections.length > 0 && (
                <Button size="sm" variant="outline" onClick={() => setShowDocument((s) => !s)}>
                  <FileText size={14} strokeWidth={2} className="mr-1.5" aria-hidden="true" />
                  {showDocument ? 'Hide Document' : 'Show Document'}
                </Button>
              )}
              <Button size="sm" variant="outline" onClick={handleDownloadPdf}>
                Download PDF
              </Button>
              <Button size="sm" onClick={handleViewReport}>
                View Full Report
              </Button>
            </>
          }
        />

        {showDocument && docInfo?.parsed_sections ? (
          <div
            ref={splitContainerRef}
            className={cn('flex flex-col items-start gap-3 md:flex-row md:gap-0', resizingSplit && 'select-none')}
          >
            <div
              style={{ '--split-w': `${splitWidth ?? SPLIT_FALLBACK_WIDTH}px` } as React.CSSProperties}
              className="w-full min-w-0 md:w-[var(--split-w)] md:flex-none"
            >
              {findingsPanel}
            </div>

            {/* Drag-to-resize grip (panes stack on mobile, no grip) */}
            <div
              {...splitGripProps}
              aria-label="Resize document pane (drag, or use arrow keys)"
              title="Drag to resize"
              className="hidden md:flex w-3.5 flex-none self-stretch cursor-col-resize touch-none items-center justify-center group focus-visible:outline-none"
            >
              <i className="block h-10 w-1 rounded-full bg-line2 transition-colors duration-150 ease-app group-hover:bg-primary group-focus-visible:bg-primary" />
            </div>

            <div className="w-full min-w-0 flex-1">
              <div className="flex max-h-[calc(100vh-2rem)] flex-col overflow-hidden rounded-[10px] border border-border bg-card md:sticky md:top-4">
                <div className="border-b border-border px-4 py-2.5">
                  <h3 className="text-sm font-semibold">Document</h3>
                </div>
                <div ref={docPaneRef} className="space-y-1 overflow-y-auto p-4">
                  {docInfo.parsed_sections.map((section, i) => {
                    const slug = sectionSlug(section.heading, i);
                    return (
                      <div
                        key={slug}
                        id={slug}
                        className={cn(
                          'rounded-lg p-2 transition-colors duration-[450ms] ease-app',
                          highlightedSection === slug && 'bg-accent-soft'
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[13px] font-semibold text-foreground">{section.heading}</span>
                          {section.page_number != null && (
                            <span className="shrink-0 text-[11px] font-medium tabular-nums text-ink3">
                              p.{section.page_number}
                            </span>
                          )}
                        </div>
                        <p className="mt-1 whitespace-pre-wrap text-[12.5px] text-muted-foreground">{section.content}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        ) : (
          findingsPanel
        )}
      </TooltipProvider>
    </AppShell>
  );
}

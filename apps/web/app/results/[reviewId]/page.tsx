/**
 * T-704: Review results page with scorecard
 * Display review findings, scores, and risk assessment
 */

'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import axios from 'axios';
import Link from 'next/link';
import { ArrowLeft, ChevronDown, FileText, Check, RotateCcw, MapPin, HelpCircle } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

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
  const [splitPercent, setSplitPercent] = useState(33);
  const [resizingSplit, setResizingSplit] = useState(false);
  const router = useRouter();
  const docPaneRef = useRef<HTMLDivElement>(null);
  const splitContainerRef = useRef<HTMLDivElement>(null);

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

  const startSplitResize = (e: React.MouseEvent) => {
    e.preventDefault();
    setResizingSplit(true);
  };

  useEffect(() => {
    if (!resizingSplit) return;

    const onMouseMove = (e: MouseEvent) => {
      const container = splitContainerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setSplitPercent(Math.min(80, Math.max(20, pct)));
    };
    const onMouseUp = () => setResizingSplit(false);

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, [resizingSplit]);

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
      <AppShell>
        <div className="flex items-center justify-center py-16">
          <p className="text-muted-foreground">Loading review...</p>
        </div>
      </AppShell>
    );
  }

  if (error || !review) {
    return (
      <AppShell>
        <div className="max-w-4xl mx-auto">
          <div role="alert" className="bg-red-50 border border-red-200 rounded-md p-6">
            <p className="text-red-900 mb-4">{error || 'Review not found'}</p>
            <Link href="/dashboard" className="text-red-700 hover:text-red-900 font-medium">
              Back to Dashboard
            </Link>
          </div>
        </div>
      </AppShell>
    );
  }

  const scoreStatus = (score: number) => {
    if (score >= 80) return 'green';
    if (score >= 60) return 'yellow';
    return 'red';
  };

  const severityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'bg-red-100 text-red-950 border-red-400';
      case 'major':
        return 'bg-orange-100 text-orange-950 border-orange-400';
      case 'medium':
        return 'bg-yellow-100 text-yellow-950 border-yellow-400';
      case 'low':
        return 'bg-blue-100 text-blue-950 border-blue-400';
      default:
        return 'bg-gray-100 text-gray-950 border-gray-400';
    }
  };

  const severityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'bg-red-700 text-white';
      case 'major':
        return 'bg-orange-700 text-white';
      case 'medium':
        return 'bg-yellow-700 text-white';
      case 'low':
        return 'bg-blue-700 text-white';
      default:
        return 'bg-gray-700 text-white';
    }
  };

  const STAT_STYLES: Record<(typeof SEVERITIES)[number], { bg: string; text: string; label: string }> = {
    critical: { bg: 'bg-red-100', text: 'text-red-800', label: 'Critical' },
    major: { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Major' },
    medium: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Medium' },
    low: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Low' },
    info: { bg: 'bg-gray-200', text: 'text-gray-800', label: 'Info' },
  };

  const findingsPanel = (
    <>
      {/* Overall Score / Risk Level */}
      <div className="grid grid-cols-2 gap-1.5 mb-2">
        <Card>
          <CardHeader className="text-center pb-0.5 pt-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              Overall Score
              <InfoTip text="How complete and well-written this document is (0-100), across scope, clarity, commercial terms, delivery, and more. Higher is better." />
            </CardTitle>
          </CardHeader>
          <CardContent className="text-center pb-2">
            <div
              className={`text-3xl font-bold mb-1 ${
                scoreStatus(review.overall_score) === 'green'
                  ? 'text-green-700'
                  : scoreStatus(review.overall_score) === 'yellow'
                  ? 'text-yellow-700'
                  : 'text-red-700'
              }`}
            >
              {review.overall_score.toFixed(1)}
            </div>
            <div
              role="progressbar"
              aria-valuenow={review.overall_score}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Overall score"
              className="w-full bg-gray-200 rounded-full h-1.5"
            >
              <div
                className={`h-1.5 rounded-full ${
                  scoreStatus(review.overall_score) === 'green'
                    ? 'bg-green-600'
                    : scoreStatus(review.overall_score) === 'yellow'
                    ? 'bg-yellow-600'
                    : 'bg-red-600'
                }`}
                style={{ width: `${review.overall_score}%` }}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="text-center pb-0.5 pt-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              Risk Level
              <InfoTip text="How much this document could hurt you if signed as-is -- combines how severe the issues are and how many there are. Higher is worse." />
            </CardTitle>
          </CardHeader>
          <CardContent className="text-center pb-2">
            <div
              className={`text-3xl font-bold mb-1 ${
                review.risk_score > 70
                  ? 'text-red-700'
                  : review.risk_score > 40
                  ? 'text-yellow-700'
                  : 'text-green-700'
              }`}
            >
              {review.risk_score.toFixed(0)}%
            </div>
            <p
              className={`text-xs font-semibold ${
                review.risk_score > 70
                  ? 'text-red-700'
                  : review.risk_score > 40
                  ? 'text-yellow-700'
                  : 'text-green-700'
              }`}
            >
              {review.risk_score > 70 ? 'High' : review.risk_score > 40 ? 'Medium' : 'Low'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Risk breakdown by axis -- which KIND of risk is driving the score */}
      {review.risk_breakdown && Object.keys(review.risk_breakdown).length > 0 && (
        <Card className="mb-2">
          <CardHeader className="pb-0.5 pt-2">
            <CardTitle className="text-sm">
              Risk by Area
              <InfoTip text="The same risk score, split by area (Legal, Commercial, Delivery, etc.) so you can see what's actually driving it. Click an area to filter the findings below to just that area." />
              {areaFilter && (
                <button
                  onClick={() => setAreaFilter(null)}
                  className="ml-2 text-xs font-normal text-primary hover:underline"
                >
                  clear filter
                </button>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="pb-2">
            <div className="space-y-1.5">
              {Object.entries(review.risk_breakdown)
                .sort((a, b) => b[1] - a[1])
                .map(([axis, score]) => {
                  const active = areaFilter === axis;
                  return (
                    <button
                      key={axis}
                      onClick={() => setAreaFilter(active ? null : axis)}
                      className={cn(
                        'flex items-center gap-2 text-xs w-full rounded-md p-0.5 transition-all',
                        active ? 'ring-2 ring-offset-1 ring-primary' : 'hover:bg-muted/60'
                      )}
                    >
                      <span className="w-20 shrink-0 text-foreground font-medium truncate text-left">{axis}</span>
                      <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                        <div
                          className={cn(
                            'h-1.5 rounded-full transition-[width] duration-500 ease-out',
                            score > 70 ? 'bg-red-600' : score > 40 ? 'bg-yellow-600' : 'bg-green-600'
                          )}
                          style={{ width: `${score}%` }}
                        />
                      </div>
                      <span className="w-9 shrink-0 text-right text-muted-foreground">{score.toFixed(0)}%</span>
                    </button>
                  );
                })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Document X-Ray: sections found + rule-engine gaps at a glance */}
      {docInfo?.parsed_sections && docInfo.parsed_sections.length > 0 && (
        <Card className="mb-2">
          <CardHeader className="pb-0.5 pt-2">
            <CardTitle className="text-sm">
              Document X-Ray
              <InfoTip text="A quick scan of the document itself: which sections it has, and which required sections/checks are missing." />
            </CardTitle>
          </CardHeader>
          <CardContent className="pb-2">
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <h4 className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wide mb-1">
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
                <h4 className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wide mb-1">
                  Gaps Detected ({ruleGaps.length})
                </h4>
                {ruleGaps.length === 0 ? (
                  <p className="text-muted-foreground">None -- passes all rule checks.</p>
                ) : (
                  <ul className="space-y-0.5">
                    {ruleGaps.map((f) => (
                      <li key={f.finding_id} className="truncate text-red-700">
                        {f.title}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Findings Summary (clickable filters) */}
      <Card className="mb-2">
        <CardHeader className="pb-0.5 pt-2">
          <CardTitle className="text-sm">
            Findings Summary
            <InfoTip text="Every issue found, grouped by how serious it is. Click a number to filter the list below to just that severity." />
            {severityFilter && (
              <button
                onClick={() => setSeverityFilter(null)}
                className="ml-2 text-xs font-normal text-primary hover:underline"
              >
                clear filter
              </button>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-2">
          <div className="grid grid-cols-5 gap-1.5">
            {SEVERITIES.map((sev) => {
              const style = STAT_STYLES[sev];
              const active = severityFilter === sev;
              return (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(active ? null : sev)}
                  className={cn(
                    'text-center p-2 rounded-md transition-all',
                    style.bg,
                    active ? 'ring-2 ring-offset-1 ring-primary' : 'hover:ring-1 hover:ring-primary/40'
                  )}
                >
                  <div className={cn('text-2xl font-bold', style.text)}>
                    {review.findings_count[sev]}
                  </div>
                  <div className="text-foreground text-xs font-medium">{style.label}</div>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Findings Details */}
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0 pb-0.5 pt-2">
          <CardTitle className="text-sm">
            Findings {(severityFilter || areaFilter) && <span className="text-muted-foreground font-normal">({visibleFindings.length} of {review.findings.length})</span>}
          </CardTitle>
          <div className="flex items-center gap-1.5">
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
          </div>
        </CardHeader>
        <CardContent className="pb-2">
          {visibleFindings.length === 0 ? (
            <p className="text-muted-foreground text-sm">No findings in this filter.</p>
          ) : (
            <div className="space-y-1">
              {visibleFindings.map((finding) => {
                const title = finding.title || finding.category?.replace(/_/g, ' ') || 'Finding';
                const fixed = finding.status === 'resolved';
                return (
                  <div
                    key={finding.finding_id}
                    className={cn(
                      'border rounded-md overflow-hidden',
                      severityColor(finding.severity),
                      fixed && 'opacity-60'
                    )}
                  >
                    <button
                      onClick={() =>
                        setExpandedFinding(
                          expandedFinding === finding.finding_id ? null : finding.finding_id
                        )
                      }
                      aria-expanded={expandedFinding === finding.finding_id}
                      aria-controls={`finding-detail-${finding.finding_id}`}
                      className="w-full py-1.5 px-2.5 text-left flex justify-between items-center gap-2 hover:brightness-95"
                    >
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className={cn('shrink-0 text-[9px] font-bold uppercase tracking-wide px-1 py-0.5 rounded leading-none', severityBadge(finding.severity))}>
                          {finding.severity}
                        </span>
                        {finding.risk_area && (
                          <span className="shrink-0 text-[9px] font-semibold uppercase tracking-wide px-1 py-0.5 rounded leading-none bg-muted text-muted-foreground">
                            {finding.risk_area}
                          </span>
                        )}
                        {fixed && (
                          <span className="shrink-0 flex items-center gap-0.5 text-[9px] font-bold uppercase tracking-wide px-1 py-0.5 rounded leading-none bg-green-700 text-white">
                            <Check size={9} strokeWidth={3} /> Fixed
                          </span>
                        )}
                        {finding.evidence_type && (
                          <span className="shrink-0 text-[9px] font-semibold uppercase tracking-wide px-1 py-0.5 rounded leading-none border border-muted-foreground/30 text-muted-foreground">
                            {finding.evidence_type.replace(/_/g, ' ')}
                          </span>
                        )}
                        <h3 className={cn('font-semibold text-xs truncate', fixed && 'line-through')}>
                          {title}
                        </h3>
                        {finding.section_ref && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleLocateInDoc(finding.section_ref);
                            }}
                            className="shrink-0 flex items-center gap-0.5 text-[11px] font-semibold text-primary hover:underline"
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
                        className={`ml-2 shrink-0 transition-transform duration-150 ${
                          expandedFinding === finding.finding_id ? 'rotate-180' : ''
                        }`}
                      />
                    </button>

                    {expandedFinding === finding.finding_id && (
                      <div id={`finding-detail-${finding.finding_id}`} className="border-t px-2.5 py-2 space-y-2 text-xs">
                        <div>
                          <h4 className="font-semibold mb-1 text-xs uppercase tracking-wide text-muted-foreground">Description</h4>
                          <p>{finding.description}</p>
                        </div>
                        {finding.matched_text && (
                          <div>
                            <h4 className="font-semibold mb-1 text-xs uppercase tracking-wide text-muted-foreground">Document Text</h4>
                            <blockquote className="border-l-2 border-muted-foreground/30 pl-2 italic text-muted-foreground">
                              {finding.matched_text}
                            </blockquote>
                          </div>
                        )}
                        <div>
                          <h4 className="font-semibold mb-1 text-xs uppercase tracking-wide text-muted-foreground">Recommendation</h4>
                          <p>{finding.recommendation}</p>
                        </div>
                        <div>
                          <h4 className="font-semibold mb-1 text-xs uppercase tracking-wide text-muted-foreground">Confidence</h4>
                          <p>{finding.confidence}%</p>
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
        </CardContent>
      </Card>

      {review.audit_meta && (
        <p className="text-[11px] text-muted-foreground px-1">
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
      <div className="w-full">
        <div className="flex items-center justify-between mb-1">
          <h1 className="text-xl font-bold text-foreground">Review Results</h1>
          <Link
            href="/dashboard"
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground font-medium"
          >
            <ArrowLeft size={16} strokeWidth={2} aria-hidden="true" />
            Back to Dashboard
          </Link>
        </div>

        {docInfo && (
          <p className="text-sm text-muted-foreground mb-2">
            <span className="font-medium text-foreground">{docInfo.original_filename}</span>
            {docInfo.project_name && <> &middot; Project: {docInfo.project_name}</>}
            {docInfo.document_type && <> &middot; {docInfo.document_type}</>}
            {docInfo.page_count != null && <> &middot; {docInfo.page_count} page{docInfo.page_count === 1 ? '' : 's'}</>}
            {' '}&middot; Uploaded {new Date(docInfo.created_at).toLocaleDateString()}
          </p>
        )}

        {showDocument && docInfo?.parsed_sections ? (
          <div ref={splitContainerRef} className={cn('flex items-start gap-0', resizingSplit && 'select-none')}>
            <div style={{ width: `${splitPercent}%` }} className="min-w-0 pr-1">
              {findingsPanel}
            </div>

            {/* Drag-to-resize divider */}
            <div
              onMouseDown={startSplitResize}
              className="w-1.5 shrink-0 self-stretch cursor-col-resize rounded-full bg-border hover:bg-primary/50 active:bg-primary transition-colors"
            />

            <div style={{ width: `${100 - splitPercent}%` }} className="min-w-0 pl-1">
              <Card className="sticky top-4 max-h-[calc(100vh-2rem)] flex flex-col">
                <CardHeader className="pb-0.5 pt-2">
                  <CardTitle className="text-sm">Document</CardTitle>
                </CardHeader>
                <CardContent className="overflow-y-auto pb-2" ref={docPaneRef}>
                  <div className="space-y-4 text-sm">
                    {docInfo.parsed_sections.map((section, i) => {
                      const slug = sectionSlug(section.heading, i);
                      return (
                        <div
                          key={slug}
                          id={slug}
                          className={cn(
                            'rounded-md p-2 -m-2 transition-colors duration-500',
                            highlightedSection === slug && 'bg-yellow-100'
                          )}
                        >
                          <h4 className="font-semibold text-foreground mb-1">
                            {section.heading}
                            {section.page_number != null && (
                              <span className="ml-2 text-xs font-normal text-muted-foreground">
                                p.{section.page_number}
                              </span>
                            )}
                          </h4>
                          <p className="whitespace-pre-wrap text-muted-foreground">{section.content}</p>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        ) : (
          findingsPanel
        )}
      </div>
      </TooltipProvider>
    </AppShell>
  );
}

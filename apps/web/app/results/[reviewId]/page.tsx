/**
 * T-704: Review results page with scorecard
 * Display review findings, scores, and risk assessment
 */

'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import axios from 'axios';
import Link from 'next/link';
import { ArrowLeft, ChevronDown, FileText, Check, RotateCcw } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface Finding {
  finding_id: string;
  title: string;
  category: string;
  severity: string;
  confidence: number;
  recommendation: string;
  description: string;
  section_ref: string | null;
  status: string;
}

interface ReviewData {
  review_id: string;
  doc_id: string;
  status: string;
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
  const [showDocument, setShowDocument] = useState(false);
  const [highlightedSection, setHighlightedSection] = useState<string | null>(null);
  const router = useRouter();
  const docPaneRef = useRef<HTMLDivElement>(null);

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

  const visibleFindings = useMemo(() => {
    if (!review) return [];
    if (!severityFilter) return review.findings;
    return review.findings.filter((f) => f.severity.toLowerCase() === severityFilter);
  }, [review, severityFilter]);

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
        return 'bg-red-50 text-red-900 border-red-300';
      case 'major':
        return 'bg-orange-50 text-orange-900 border-orange-300';
      case 'medium':
        return 'bg-yellow-50 text-yellow-900 border-yellow-300';
      case 'low':
        return 'bg-blue-50 text-blue-900 border-blue-300';
      default:
        return 'bg-gray-50 text-gray-900 border-gray-300';
    }
  };

  const STAT_STYLES: Record<(typeof SEVERITIES)[number], { bg: string; text: string; label: string }> = {
    critical: { bg: 'bg-red-50', text: 'text-red-700', label: 'Critical' },
    major: { bg: 'bg-orange-50', text: 'text-orange-700', label: 'Major' },
    medium: { bg: 'bg-yellow-50', text: 'text-yellow-700', label: 'Medium' },
    low: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'Low' },
    info: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Info' },
  };

  const findingsPanel = (
    <>
      {/* Findings Summary (clickable filters) */}
      <Card className="mb-4">
        <CardHeader className="pb-1 pt-3">
          <CardTitle className="text-base">
            Findings Summary
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
        <CardContent className="pb-3">
          <div className="grid grid-cols-5 gap-2">
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
        <CardHeader className="flex-row items-center justify-between space-y-0 pb-1 pt-3">
          <CardTitle className="text-base">
            Findings {severityFilter && <span className="text-muted-foreground font-normal">({visibleFindings.length} of {review.findings.length})</span>}
          </CardTitle>
          <div className="flex items-center gap-2">
            {docInfo?.parsed_sections && docInfo.parsed_sections.length > 0 && (
              <Button size="sm" variant="outline" onClick={() => setShowDocument((s) => !s)}>
                <FileText size={14} strokeWidth={2} className="mr-1.5" aria-hidden="true" />
                {showDocument ? 'Hide Document' : 'Show Document'}
              </Button>
            )}
            <Button size="sm" onClick={handleViewReport}>
              View Full Report
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pb-3">
          {visibleFindings.length === 0 ? (
            <p className="text-muted-foreground text-sm">No findings in this filter.</p>
          ) : (
            <div className="space-y-2">
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
                      className="w-full py-2.5 px-3 text-left flex justify-between items-center gap-3 hover:brightness-95"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="shrink-0 text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded bg-black/10">
                          {finding.severity}
                        </span>
                        {fixed && (
                          <span className="shrink-0 flex items-center gap-0.5 text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded bg-green-600 text-white">
                            <Check size={10} strokeWidth={3} /> Fixed
                          </span>
                        )}
                        <h3 className={cn('font-semibold text-sm truncate', fixed && 'line-through')}>
                          {title}
                        </h3>
                        {finding.section_ref && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleLocateInDoc(finding.section_ref);
                            }}
                            className="shrink-0 text-xs font-normal text-primary hover:underline"
                          >
                            &middot; {finding.section_ref}
                          </button>
                        )}
                      </div>
                      <ChevronDown
                        size={16}
                        strokeWidth={2}
                        aria-hidden="true"
                        className={`ml-4 shrink-0 transition-transform duration-150 ${
                          expandedFinding === finding.finding_id ? 'rotate-180' : ''
                        }`}
                      />
                    </button>

                    {expandedFinding === finding.finding_id && (
                      <div id={`finding-detail-${finding.finding_id}`} className="border-t px-3 py-3 space-y-3 text-sm">
                        <div>
                          <h4 className="font-semibold mb-1 text-xs uppercase tracking-wide text-muted-foreground">Description</h4>
                          <p>{finding.description}</p>
                        </div>
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
    </>
  );

  return (
    <AppShell fullWidth>
      <div className="max-w-[1600px] mx-auto">
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
          <p className="text-sm text-muted-foreground mb-4">
            <span className="font-medium text-foreground">{docInfo.original_filename}</span>
            {docInfo.project_name && <> &middot; Project: {docInfo.project_name}</>}
            {docInfo.document_type && <> &middot; {docInfo.document_type}</>}
            {docInfo.page_count != null && <> &middot; {docInfo.page_count} page{docInfo.page_count === 1 ? '' : 's'}</>}
            {' '}&middot; Uploaded {new Date(docInfo.created_at).toLocaleDateString()}
          </p>
        )}

        {/* Overall Score Card */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
          {/* Score */}
          <Card>
            <CardHeader className="text-center pb-1 pt-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Overall Score</CardTitle>
            </CardHeader>
            <CardContent className="text-center pb-3">
              <div
                className={`text-4xl font-bold mb-1 ${
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

          {/* Risk Score */}
          <Card>
            <CardHeader className="text-center pb-1 pt-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Risk Level</CardTitle>
            </CardHeader>
            <CardContent className="text-center pb-3">
              <div
                className={`text-4xl font-bold mb-1 ${
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
                className={`text-sm font-semibold ${
                  review.risk_score > 70
                    ? 'text-red-700'
                    : review.risk_score > 40
                    ? 'text-yellow-700'
                    : 'text-green-700'
                }`}
              >
                {review.risk_score > 70
                  ? 'High'
                  : review.risk_score > 40
                  ? 'Medium'
                  : 'Low'}
              </p>
            </CardContent>
          </Card>
        </div>

        {showDocument && docInfo?.parsed_sections ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
            <div>{findingsPanel}</div>
            <Card className="lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] flex flex-col">
              <CardHeader className="pb-1 pt-3">
                <CardTitle className="text-base">Document</CardTitle>
              </CardHeader>
              <CardContent className="overflow-y-auto pb-3" ref={docPaneRef}>
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
        ) : (
          findingsPanel
        )}
      </div>
    </AppShell>
  );
}

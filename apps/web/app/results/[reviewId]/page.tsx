/**
 * T-704: Review results page with scorecard
 * Display review findings, scores, and risk assessment
 */

'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import axios from 'axios';
import Link from 'next/link';
import { ArrowLeft, ChevronDown } from 'lucide-react';
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

const SEVERITIES = ['critical', 'major', 'medium', 'low', 'info'] as const;

export default function ResultsPage() {
  const params = useParams();
  const reviewId = params.reviewId;
  const [review, setReview] = useState<ReviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);
  const router = useRouter();

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
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch review');
    } finally {
      setLoading(false);
    }
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

  return (
    <AppShell fullWidth>
      <div className="max-w-[1400px] mx-auto">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-bold text-foreground">Review Results</h1>
          <Link
            href="/dashboard"
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground font-medium"
          >
            <ArrowLeft size={16} strokeWidth={2} aria-hidden="true" />
            Back to Dashboard
          </Link>
        </div>

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
            <Button asChild size="sm">
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL}/api/v1/reviews/${reviewId}/report?format=html`}
                target="_blank"
                rel="noopener noreferrer"
              >
                View Full Report
              </a>
            </Button>
          </CardHeader>
          <CardContent className="pb-3">
            {visibleFindings.length === 0 ? (
              <p className="text-muted-foreground text-sm">No findings in this filter.</p>
            ) : (
              <div className="space-y-2">
                {visibleFindings.map((finding) => {
                  const title = finding.title || finding.category?.replace(/_/g, ' ') || 'Finding';
                  return (
                    <div
                      key={finding.finding_id}
                      className={`border rounded-md overflow-hidden ${severityColor(finding.severity)}`}
                    >
                      <button
                        onClick={() =>
                          setExpandedFinding(
                            expandedFinding === finding.finding_id ? null : finding.finding_id
                          )
                        }
                        aria-expanded={expandedFinding === finding.finding_id}
                        aria-controls={`finding-detail-${finding.finding_id}`}
                        className="w-full py-2.5 px-3 text-left flex justify-between items-center hover:brightness-95"
                      >
                        <h3 className="font-semibold text-sm">{title}</h3>
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
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

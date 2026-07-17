/**
 * T-704: Review results page with scorecard
 * Display review findings, scores, and risk assessment
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import axios from 'axios';
import Link from 'next/link';
import { ArrowLeft, ChevronDown } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface Finding {
  finding_id: string;
  title: string;
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

export default function ResultsPage() {
  const params = useParams();
  const reviewId = params.reviewId;
  const [review, setReview] = useState<ReviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null);
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

      setReview(response.data);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch review');
    } finally {
      setLoading(false);
    }
  };

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
          <div role="alert" className="bg-red-50 border border-red-200 rounded-lg p-6">
            <p className="text-red-800 mb-4">{error || 'Review not found'}</p>
            <Link href="/dashboard" className="text-red-600 hover:text-red-700 font-medium">
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
        return 'bg-red-100 text-red-800 border-red-300';
      case 'major':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  return (
    <AppShell>
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-foreground">Review Results</h1>
          <Link
            href="/dashboard"
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground font-medium"
          >
            <ArrowLeft size={16} strokeWidth={2} aria-hidden="true" />
            Back to Dashboard
          </Link>
        </div>

        {/* Overall Score Card */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Score */}
          <Card>
            <CardHeader className="text-center pb-2">
              <CardTitle className="text-base font-medium text-muted-foreground">Overall Score</CardTitle>
            </CardHeader>
            <CardContent className="text-center">
              <div
                className={`text-6xl font-bold mb-2 ${
                  scoreStatus(review.overall_score) === 'green'
                    ? 'text-green-600'
                    : scoreStatus(review.overall_score) === 'yellow'
                    ? 'text-yellow-600'
                    : 'text-red-600'
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
                className="w-full bg-gray-200 rounded-full h-2"
              >
                <div
                  className={`h-2 rounded-full ${
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
            <CardHeader className="text-center pb-2">
              <CardTitle className="text-base font-medium text-muted-foreground">Risk Level</CardTitle>
            </CardHeader>
            <CardContent className="text-center">
              <div
                className={`text-6xl font-bold mb-2 ${
                  review.risk_score > 70
                    ? 'text-red-600'
                    : review.risk_score > 40
                    ? 'text-yellow-600'
                    : 'text-green-600'
                }`}
              >
                {review.risk_score.toFixed(0)}%
              </div>
              <p
                className={`text-lg font-medium ${
                  review.risk_score > 70
                    ? 'text-red-600'
                    : review.risk_score > 40
                    ? 'text-yellow-600'
                    : 'text-green-600'
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

        {/* Findings Summary */}
        <Card className="mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Findings Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-5 gap-3">
              <div className="text-center p-3 bg-red-50 rounded-md">
                <div className="text-3xl font-bold text-red-600">{review.findings_count.critical}</div>
                <div className="text-gray-600 text-sm">Critical</div>
              </div>
              <div className="text-center p-3 bg-orange-50 rounded-md">
                <div className="text-3xl font-bold text-orange-600">{review.findings_count.major}</div>
                <div className="text-gray-600 text-sm">Major</div>
              </div>
              <div className="text-center p-3 bg-yellow-50 rounded-md">
                <div className="text-3xl font-bold text-yellow-600">{review.findings_count.medium}</div>
                <div className="text-gray-600 text-sm">Medium</div>
              </div>
              <div className="text-center p-3 bg-blue-50 rounded-md">
                <div className="text-3xl font-bold text-blue-600">{review.findings_count.low}</div>
                <div className="text-gray-600 text-sm">Low</div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-md">
                <div className="text-3xl font-bold text-gray-600">{review.findings_count.info}</div>
                <div className="text-gray-600 text-sm">Info</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Findings Details */}
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-lg">Findings</CardTitle>
            <Button asChild>
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL}/api/v1/reviews/${reviewId}/report?format=html`}
                target="_blank"
                rel="noopener noreferrer"
              >
                View Full Report
              </a>
            </Button>
          </CardHeader>
          <CardContent>
            {review.findings.length === 0 ? (
              <p className="text-gray-500">No findings reported.</p>
            ) : (
              <div className="space-y-3">
                {review.findings.map((finding) => (
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
                      className="w-full p-4 text-left flex justify-between items-start hover:opacity-90"
                    >
                      <div className="flex-1">
                        <h3 className="font-bold mb-1">{finding.title}</h3>
                        <p className="text-sm opacity-75">{finding.description.substring(0, 100)}...</p>
                      </div>
                      <ChevronDown
                        size={18}
                        strokeWidth={2}
                        aria-hidden="true"
                        className={`ml-4 shrink-0 transition-transform duration-150 ${
                          expandedFinding === finding.finding_id ? 'rotate-180' : ''
                        }`}
                      />
                    </button>

                    {expandedFinding === finding.finding_id && (
                      <div id={`finding-detail-${finding.finding_id}`} className="border-t p-4 bg-opacity-50">
                        <div className="mb-4">
                          <h4 className="font-bold mb-2">Description</h4>
                          <p>{finding.description}</p>
                        </div>
                        <div className="mb-4">
                          <h4 className="font-bold mb-2">Recommendation</h4>
                          <p>{finding.recommendation}</p>
                        </div>
                        <div>
                          <h4 className="font-bold mb-2">Confidence</h4>
                          <p>{finding.confidence}%</p>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}

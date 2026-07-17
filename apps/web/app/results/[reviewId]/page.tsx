/**
 * T-704: Review results page with scorecard
 * Display review findings, scores, and risk assessment
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import axios from 'axios';
import Link from 'next/link';

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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Loading review...</p>
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <div role="alert" className="bg-red-50 border border-red-200 rounded-lg p-6">
            <p className="text-red-800 mb-4">{error || 'Review not found'}</p>
            <Link href="/dashboard" className="text-red-600 hover:text-red-700 font-medium">
              Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-900">Review Results</h1>
            <Link
              href="/dashboard"
              className="text-gray-600 hover:text-gray-900 font-medium"
            >
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Overall Score Card */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Score */}
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <h2 className="text-gray-600 text-lg font-medium mb-4">Overall Score</h2>
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
          </div>

          {/* Risk Score */}
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <h2 className="text-gray-600 text-lg font-medium mb-4">Risk Level</h2>
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
          </div>
        </div>

        {/* Findings Summary */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Findings Summary</h2>
          <div className="grid grid-cols-5 gap-4">
            <div className="text-center p-4 bg-red-50 rounded-lg">
              <div className="text-3xl font-bold text-red-600">{review.findings_count.critical}</div>
              <div className="text-gray-600 text-sm">Critical</div>
            </div>
            <div className="text-center p-4 bg-orange-50 rounded-lg">
              <div className="text-3xl font-bold text-orange-600">{review.findings_count.major}</div>
              <div className="text-gray-600 text-sm">Major</div>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg">
              <div className="text-3xl font-bold text-yellow-600">{review.findings_count.medium}</div>
              <div className="text-gray-600 text-sm">Medium</div>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-3xl font-bold text-blue-600">{review.findings_count.low}</div>
              <div className="text-gray-600 text-sm">Low</div>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-3xl font-bold text-gray-600">{review.findings_count.info}</div>
              <div className="text-gray-600 text-sm">Info</div>
            </div>
          </div>
        </div>

        {/* Findings Details */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">Findings</h2>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL}/api/v1/reviews/${reviewId}/report?format=html`}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded-lg"
            >
              View Full Report
            </a>
          </div>

          {review.findings.length === 0 ? (
            <p className="text-gray-500">No findings reported.</p>
          ) : (
            <div className="space-y-4">
              {review.findings.map((finding) => (
                <div
                  key={finding.finding_id}
                  className={`border rounded-lg overflow-hidden ${severityColor(finding.severity)}`}
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
                    <span className="text-2xl ml-4" aria-hidden="true">
                      {expandedFinding === finding.finding_id ? '−' : '+'}
                    </span>
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
        </div>
      </div>
    </div>
  );
}

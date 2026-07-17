/**
 * T-2004/T-2005/T-2009/T-2010: Main search page
 * Wires SearchFilter + SearchResults + AnalyticsChart + CSV export
 * Calls GET /api/v1/search endpoint and POST /api/v1/search/history
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { Download } from 'lucide-react';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import SearchFilter from '@/components/SearchFilter';
import SearchResults from '@/components/SearchResults';
import AnalyticsChart from '@/components/AnalyticsChart';
import { exportToCsv, formatSearchResultsForCsv } from '@/lib/exportCsv';

interface SearchResult {
  doc_id: string;
  filename: string;
  document_type: string | null;
  rank: number;
  snippet: string;
  created_at: string;
}

interface SearchResponse {
  query: string;
  total: number;
  skip: number;
  limit: number;
  results: SearchResult[];
}

export default function SearchPage() {
  const router = useRouter();
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [total, setTotal] = useState(0);
  const [lastQuery, setLastQuery] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
    }
  }, [router]);

  const handleSearch = async (filters: {
    query: string;
    document_type: string | null;
    date_from: string | null;
    date_to: string | null;
  }) => {
    try {
      setLoading(true);
      setError('');
      const token = localStorage.getItem('access_token');

      // Build query params
      const params = new URLSearchParams();
      params.append('q', filters.query);
      if (filters.document_type) {
        params.append('document_type', filters.document_type);
      }
      if (filters.date_from) {
        params.append('date_from', filters.date_from);
      }
      if (filters.date_to) {
        params.append('date_to', filters.date_to);
      }
      params.append('skip', '0');
      params.append('limit', '20');

      // Execute search
      const response = await axios.get<SearchResponse>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/search?${params.toString()}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      setResults(response.data.results);
      setTotal(response.data.total);
      setLastQuery(filters.query);

      // Log search to history (fire and forget)
      axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/search/history`,
        {
          query: filters.query,
          filters: {
            document_type: filters.document_type,
            date_from: filters.date_from,
            date_to: filters.date_to,
          },
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      ).catch((err) => {
        console.error('Failed to log search history:', err);
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Search failed. Please try again.');
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  const handleDocumentClick = (docId: string) => {
    router.push(`/document/${docId}`);
  };

  const handleExportCsv = () => {
    if (results.length === 0) {
      alert('No results to export');
      return;
    }
    const formattedRows = formatSearchResultsForCsv(results);
    const timestamp = new Date().toISOString().split('T')[0];
    exportToCsv(`search-results-${timestamp}.csv`, formattedRows);
  };

  // Sample analytics data: document type distribution (would be driven by analytics API later)
  const docTypeDistribution = {
    labels: results.length > 0 ? ['SOW', 'Proposal', 'Other'] : [],
    datasets:
      results.length > 0
        ? [
            {
              label: 'Document Count',
              data: [
                results.filter((r) => r.document_type === 'SOW').length,
                results.filter((r) => r.document_type === 'Proposal').length,
                results.filter((r) => r.document_type === 'Other').length,
              ],
            },
          ]
        : [],
  };

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Search Documents</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Full-text search with filtering and analytics
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div role="alert" className="bg-destructive/10 text-destructive border border-destructive/30 rounded-md p-4 mb-6">
          <p>{error}</p>
        </div>
      )}

      {/* Search Filter */}
      <SearchFilter onSearch={handleSearch} loading={loading} />

      {/* Results Section (only show if search has been performed) */}
      {total > 0 || lastQuery ? (
        <>
          {/* Results Header with Export Button */}
          <div className="flex items-center justify-between mb-4 mt-6">
            <h2 className="text-lg font-semibold">
              Results {lastQuery && `for "${lastQuery}"`}
            </h2>
            {results.length > 0 && (
              <Button variant="outline" size="sm" onClick={handleExportCsv} className="gap-2">
                <Download size={16} strokeWidth={2} aria-hidden="true" />
                Export to CSV
              </Button>
            )}
          </div>

          {/* Search Results */}
          <div className="mb-8">
            <SearchResults
              results={results}
              total={total}
              loading={loading}
              onDocumentClick={handleDocumentClick}
            />
          </div>

          {/* Analytics Chart (only if results exist) */}
          {results.length > 0 && docTypeDistribution.labels.length > 0 && (
            <div className="mb-8">
              <h2 className="text-lg font-semibold mb-4">Analytics</h2>
              <AnalyticsChart
                title="Document Type Distribution"
                labels={docTypeDistribution.labels}
                datasets={docTypeDistribution.datasets}
                type="bar"
                height={300}
              />
            </div>
          )}
        </>
      ) : null}
    </AppShell>
  );
}

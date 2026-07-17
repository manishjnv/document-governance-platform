/**
 * T-2004: Search filter UI component
 * Controlled form for full-text search + filters (document_type, date range)
 * Persists last-used filters to localStorage
 */

'use client';

import { useEffect, useState } from 'react';

interface SearchFilterProps {
  onSearch: (filters: {
    query: string;
    document_type: string | null;
    date_from: string | null;
    date_to: string | null;
  }) => void;
  loading?: boolean;
}

const STORAGE_KEY = 'search_filters';
const DOCUMENT_TYPES = ['SOW', 'Proposal', 'Other'];

export default function SearchFilter({ onSearch, loading = false }: SearchFilterProps) {
  const [query, setQuery] = useState('');
  const [documentType, setDocumentType] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState<string | null>(null);
  const [dateTo, setDateTo] = useState<string | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        setQuery(parsed.query || '');
        setDocumentType(parsed.document_type || null);
        setDateFrom(parsed.date_from || null);
        setDateTo(parsed.date_to || null);
      }
    } catch (err) {
      console.error('Failed to load saved filters from localStorage:', err);
    }
  }, []);

  // Save to localStorage whenever filters change
  const saveFilters = () => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          query,
          document_type: documentType,
          date_from: dateFrom,
          date_to: dateTo,
        })
      );
    } catch (err) {
      console.error('Failed to save filters to localStorage:', err);
    }
  };

  const handleSearch = () => {
    saveFilters();
    onSearch({
      query,
      document_type: documentType,
      date_from: dateFrom,
      date_to: dateTo,
    });
  };

  const handleReset = () => {
    setQuery('');
    setDocumentType(null);
    setDateFrom(null);
    setDateTo(null);
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Search Filters</h2>

      <div className="space-y-4">
        {/* Query Input */}
        <div>
          <label htmlFor="query" className="block text-sm font-medium text-foreground mb-1">
            Search Query
          </label>
          <input
            id="query"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., contract, amendment, termination..."
            className="w-full px-4 py-2 border border-input rounded-lg focus:ring-2 focus:ring-ring focus:border-transparent"
            disabled={loading}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
        </div>

        {/* Document Type Select */}
        <div>
          <label htmlFor="documentType" className="block text-sm font-medium text-foreground mb-1">
            Document Type
          </label>
          <select
            id="documentType"
            value={documentType || ''}
            onChange={(e) => setDocumentType(e.target.value || null)}
            className="w-full px-4 py-2 border border-input rounded-lg focus:ring-2 focus:ring-ring focus:border-transparent"
            disabled={loading}
          >
            <option value="">All Types</option>
            {DOCUMENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>

        {/* Date Range */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="dateFrom" className="block text-sm font-medium text-foreground mb-1">
              From Date
            </label>
            <input
              id="dateFrom"
              type="date"
              value={dateFrom || ''}
              onChange={(e) => setDateFrom(e.target.value || null)}
              className="w-full px-4 py-2 border border-input rounded-lg focus:ring-2 focus:ring-ring focus:border-transparent"
              disabled={loading}
            />
          </div>
          <div>
            <label htmlFor="dateTo" className="block text-sm font-medium text-foreground mb-1">
              To Date
            </label>
            <input
              id="dateTo"
              type="date"
              value={dateTo || ''}
              onChange={(e) => setDateTo(e.target.value || null)}
              className="w-full px-4 py-2 border border-input rounded-lg focus:ring-2 focus:ring-ring focus:border-transparent"
              disabled={loading}
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4">
          <button
            onClick={handleSearch}
            disabled={loading}
            className="flex-1 bg-primary hover:bg-primary/90 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-lg transition"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
          <button
            onClick={handleReset}
            disabled={loading}
            className="flex-1 bg-gray-200 hover:bg-gray-300 disabled:bg-gray-100 text-gray-900 font-medium py-2 px-4 rounded-lg transition"
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  );
}

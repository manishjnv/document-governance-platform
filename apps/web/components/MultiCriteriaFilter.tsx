/**
 * T-2011: Multi-criteria filter UI component
 * Extends SearchFilter with document_type multi-select and score-range slider
 * Client-side validation matches server-side validate_filters() logic
 */

'use client';

import { useEffect, useState } from 'react';

interface MultiCriteriaFilterProps {
  onFilterChange: (filters: {
    document_type: string | null;
    date_from: string | null;
    date_to: string | null;
    score_min: number | null;
    score_max: number | null;
  }) => void;
  loading?: boolean;
}

const STORAGE_KEY = 'multi_criteria_filters';
const DOCUMENT_TYPES = ['SOW', 'Proposal', 'Other'];

export default function MultiCriteriaFilter({
  onFilterChange,
  loading = false,
}: MultiCriteriaFilterProps) {
  const [documentType, setDocumentType] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState<string | null>(null);
  const [dateTo, setDateTo] = useState<string | null>(null);
  const [scoreMin, setScoreMin] = useState<number | null>(null);
  const [scoreMax, setScoreMax] = useState<number | null>(null);
  const [errors, setErrors] = useState<string[]>([]);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        setDocumentType(parsed.document_type || null);
        setDateFrom(parsed.date_from || null);
        setDateTo(parsed.date_to || null);
        setScoreMin(parsed.score_min !== undefined ? parsed.score_min : null);
        setScoreMax(parsed.score_max !== undefined ? parsed.score_max : null);
      }
    } catch (err) {
      console.error('Failed to load saved filters from localStorage:', err);
    }
  }, []);

  // Validate filters client-side
  const validateFilters = () => {
    const validationErrors: string[] = [];

    // Validate date range
    if (dateFrom && dateTo && dateFrom > dateTo) {
      validationErrors.push('From date must be on or before to date');
    }

    // Validate score range
    if (scoreMin !== null && scoreMax !== null && scoreMin > scoreMax) {
      validationErrors.push('Score minimum must be less than or equal to maximum');
    }

    // Validate score bounds
    if (scoreMin !== null && (scoreMin < 0 || scoreMin > 100)) {
      validationErrors.push('Score minimum must be between 0 and 100');
    }

    if (scoreMax !== null && (scoreMax < 0 || scoreMax > 100)) {
      validationErrors.push('Score maximum must be between 0 and 100');
    }

    setErrors(validationErrors);
    return validationErrors.length === 0;
  };

  const handleApplyFilters = () => {
    if (!validateFilters()) {
      return;
    }

    // Save to localStorage
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          document_type: documentType,
          date_from: dateFrom,
          date_to: dateTo,
          score_min: scoreMin,
          score_max: scoreMax,
        })
      );
    } catch (err) {
      console.error('Failed to save filters to localStorage:', err);
    }

    onFilterChange({
      document_type: documentType,
      date_from: dateFrom,
      date_to: dateTo,
      score_min: scoreMin,
      score_max: scoreMax,
    });
  };

  const handleReset = () => {
    setDocumentType(null);
    setDateFrom(null);
    setDateTo(null);
    setScoreMin(null);
    setScoreMax(null);
    setErrors([]);
    localStorage.removeItem(STORAGE_KEY);
    onFilterChange({
      document_type: null,
      date_from: null,
      date_to: null,
      score_min: null,
      score_max: null,
    });
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Advanced Filters</h2>

      <div className="space-y-4">
        {/* Document Type Multi-Select */}
        <div>
          <label htmlFor="documentType" className="block text-sm font-medium text-gray-700 mb-2">
            Document Type
          </label>
          <select
            id="documentType"
            value={documentType || ''}
            onChange={(e) => setDocumentType(e.target.value || null)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
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
            <label htmlFor="dateFrom" className="block text-sm font-medium text-gray-700 mb-1">
              From Date
            </label>
            <input
              id="dateFrom"
              type="date"
              value={dateFrom || ''}
              onChange={(e) => setDateFrom(e.target.value || null)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              disabled={loading}
            />
          </div>
          <div>
            <label htmlFor="dateTo" className="block text-sm font-medium text-gray-700 mb-1">
              To Date
            </label>
            <input
              id="dateTo"
              type="date"
              value={dateTo || ''}
              onChange={(e) => setDateTo(e.target.value || null)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              disabled={loading}
            />
          </div>
        </div>

        {/* Score Range */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="scoreMin" className="block text-sm font-medium text-gray-700 mb-1">
              Min Score (0-100)
            </label>
            <input
              id="scoreMin"
              type="number"
              min="0"
              max="100"
              value={scoreMin ?? ''}
              onChange={(e) => setScoreMin(e.target.value ? parseInt(e.target.value, 10) : null)}
              placeholder="0"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              disabled={loading}
            />
          </div>
          <div>
            <label htmlFor="scoreMax" className="block text-sm font-medium text-gray-700 mb-1">
              Max Score (0-100)
            </label>
            <input
              id="scoreMax"
              type="number"
              min="0"
              max="100"
              value={scoreMax ?? ''}
              onChange={(e) => setScoreMax(e.target.value ? parseInt(e.target.value, 10) : null)}
              placeholder="100"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              disabled={loading}
            />
          </div>
        </div>

        {/* Validation Errors */}
        {errors.length > 0 && (
          <div role="alert" className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-sm font-medium text-red-800 mb-1">Validation Errors:</p>
            <ul className="list-disc list-inside space-y-1">
              {errors.map((error, idx) => (
                <li key={idx} className="text-sm text-red-700">
                  {error}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4">
          <button
            onClick={handleApplyFilters}
            disabled={loading}
            className="flex-1 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-lg transition"
          >
            {loading ? 'Applying...' : 'Apply Filters'}
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

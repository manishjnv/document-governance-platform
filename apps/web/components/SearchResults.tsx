/**
 * T-2004: Search results display component
 * Renders list of search results with rank badges, document type badges, snippets
 */

'use client';

interface SearchResult {
  doc_id: string;
  filename: string;
  document_type: string | null;
  rank: number;
  snippet: string;
  created_at: string;
}

interface SearchResultsProps {
  results: SearchResult[];
  total: number;
  loading?: boolean;
  onDocumentClick?: (docId: string) => void;
  onReviewClick?: (docId: string) => void;
  reviewingDocId?: string | null;
}

export default function SearchResults({
  results,
  total,
  loading = false,
  onDocumentClick,
  onReviewClick,
  reviewingDocId = null,
}: SearchResultsProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <p className="text-gray-500">Searching...</p>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <p className="text-gray-500">No results found. Try adjusting your search filters.</p>
      </div>
    );
  }

  const getDocTypeColor = (type: string | null) => {
    if (!type) return 'bg-gray-100 text-gray-700';
    switch (type) {
      case 'SOW':
        return 'bg-blue-100 text-blue-700';
      case 'Proposal':
        return 'bg-green-100 text-green-700';
      case 'Other':
        return 'bg-gray-100 text-gray-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const getRankColor = (rank: number) => {
    // rank is 0-1; higher is better
    if (rank >= 0.8) return 'bg-green-100 text-green-700';
    if (rank >= 0.6) return 'bg-yellow-100 text-yellow-700';
    return 'bg-red-100 text-red-700';
  };

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow p-4">
        <p className="text-sm text-gray-600">
          Found <span className="font-semibold">{total}</span> result{total !== 1 ? 's' : ''}
        </p>
      </div>

      {results.map((result) => (
        <div key={result.doc_id} className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition">
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-purple-600 hover:underline cursor-pointer">
                <button
                  onClick={() => onDocumentClick?.(result.doc_id)}
                  className="text-left w-full hover:text-purple-700"
                >
                  {result.filename}
                </button>
              </h3>
            </div>
          </div>

          {/* Badges Row */}
          <div className="flex items-center gap-2 mb-3">
            {result.document_type && (
              <span className={`text-xs font-medium px-2 py-1 rounded ${getDocTypeColor(result.document_type)}`}>
                {result.document_type}
              </span>
            )}
            <span className={`text-xs font-medium px-2 py-1 rounded ${getRankColor(result.rank)}`}>
              Relevance: {(result.rank * 100).toFixed(0)}%
            </span>
            <span className="text-xs text-gray-500">
              {new Date(result.created_at).toLocaleDateString()}
            </span>
            {onReviewClick && (
              <button
                onClick={() => onReviewClick(result.doc_id)}
                disabled={reviewingDocId === result.doc_id}
                className="text-xs font-medium text-purple-600 hover:underline ml-auto disabled:opacity-50 disabled:no-underline"
              >
                {reviewingDocId === result.doc_id ? 'Reviewing... (~20s)' : 'Review'}
              </button>
            )}
          </div>

          {/* Snippet */}
          <p className="text-gray-700 text-sm leading-relaxed line-clamp-3">
            {result.snippet}
          </p>
        </div>
      ))}
    </div>
  );
}

/**
 * T-2040: Knowledge Base Search UI component
 * Renders search box + full-text search results over FAQs, best practices, guides
 */

'use client';

import { useCallback, useState } from 'react';
import axios from 'axios';

interface KBArticle {
  article_id: string;
  article_type: 'faq' | 'best_practice' | 'guide';
  title: string;
  snippet: string;
  rank: number;
}

interface KnowledgeBaseSearchProps {
  placeholder?: string;
  onArticleSelect?: (article: KBArticle) => void;
}

export default function KnowledgeBaseSearch({
  placeholder = 'Search FAQs, best practices, guides...',
  onArticleSelect,
}: KnowledgeBaseSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<KBArticle[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      setResults([]);
      setHasSearched(false);
      return;
    }

    setLoading(true);
    setHasSearched(true);

    try {
      const response = await axios.get('/api/v1/knowledge-base/articles/search', {
        params: { q: query, limit: 20 },
      });
      setResults(response.data.results || []);
    } catch (error) {
      console.error('Search error:', error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query]);

  const getArticleTypeLabel = (type: string) => {
    switch (type) {
      case 'faq':
        return 'FAQ';
      case 'best_practice':
        return 'Best Practice';
      case 'guide':
        return 'Guide';
      default:
        return type;
    }
  };

  const getArticleTypeColor = (type: string) => {
    switch (type) {
      case 'faq':
        return 'bg-blue-100 text-blue-700';
      case 'best_practice':
        return 'bg-green-100 text-green-700';
      case 'guide':
        return 'bg-purple-100 text-purple-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const getRankColor = (rank: number) => {
    if (rank >= 0.8) return 'bg-green-100 text-green-700';
    if (rank >= 0.6) return 'bg-yellow-100 text-yellow-700';
    return 'bg-orange-100 text-orange-700';
  };

  return (
    <div className="w-full space-y-4">
      {/* Search Form */}
      <form onSubmit={handleSearch} className="bg-white rounded-lg shadow p-6">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            aria-label={placeholder}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 transition"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      {/* Results */}
      {hasSearched && (
        <div className="space-y-3">
          {loading && (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <p className="text-gray-500">Searching knowledge base...</p>
            </div>
          )}

          {!loading && results.length === 0 && (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <p className="text-gray-500">
                No results found. Try different keywords or browse our help resources.
              </p>
            </div>
          )}

          {!loading &&
            results.length > 0 && (
              <>
                <div className="bg-white rounded-lg shadow p-4">
                  <p className="text-sm text-gray-600">
                    Found <span className="font-semibold">{results.length}</span> result
                    {results.length !== 1 ? 's' : ''}
                  </p>
                </div>

                {results.map((article) => (
                  <div
                    key={article.article_id}
                    onClick={() => onArticleSelect?.(article)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onArticleSelect?.(article);
                      }
                    }}
                    className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition cursor-pointer"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-purple-600 hover:underline">
                          {article.title}
                        </h3>
                      </div>
                    </div>

                    {/* Badges Row */}
                    <div className="flex items-center gap-2 mb-3">
                      <span
                        className={`text-xs font-medium px-2 py-1 rounded ${getArticleTypeColor(
                          article.article_type
                        )}`}
                      >
                        {getArticleTypeLabel(article.article_type)}
                      </span>
                      <span className={`text-xs font-medium px-2 py-1 rounded ${getRankColor(article.rank)}`}>
                        Relevance: {(article.rank * 100).toFixed(0)}%
                      </span>
                    </div>

                    {/* Snippet */}
                    <p className="text-gray-700 text-sm leading-relaxed line-clamp-3">
                      {article.snippet || 'No preview available'}
                    </p>
                  </div>
                ))}
              </>
            )}
        </div>
      )}
    </div>
  );
}

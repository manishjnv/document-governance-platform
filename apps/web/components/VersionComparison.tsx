/**
 * T-2030: Version comparison component
 * Renders diff between two document versions: added/removed lines
 * Contract: {doc_a_version: int, doc_b_version: int, added: [str,...], removed: [str,...]}
 */

'use client';

import { useMemo } from 'react';

interface VersionComparisonProps {
  docAVersion: number;
  docBVersion: number;
  added: string[];
  removed: string[];
}

interface DiffLine {
  type: 'added' | 'removed' | 'context';
  content: string;
}

export default function VersionComparison({
  docAVersion,
  docBVersion,
  added,
  removed,
}: VersionComparisonProps) {
  // Build a unified diff view: all removed lines, then all added lines
  const diffLines: DiffLine[] = useMemo(() => {
    const lines: DiffLine[] = [];

    // Add removed lines
    removed.forEach((line) => {
      lines.push({ type: 'removed', content: line });
    });

    // Add added lines
    added.forEach((line) => {
      lines.push({ type: 'added', content: line });
    });

    return lines;
  }, [added, removed]);

  // ponytail: unified diff format, no context merge; if diff is very large
  // (>500 lines), consider pagination or a collapsible tree view.
  const isEmpty = diffLines.length === 0;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {/* Header with version numbers */}
      <div className="mb-4 pb-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Version Comparison
        </h3>
        <p className="text-sm text-gray-600">
          Comparing version <span className="font-mono font-medium">{docAVersion}</span> to{' '}
          <span className="font-mono font-medium">{docBVersion}</span>
        </p>
      </div>

      {/* Summary stats */}
      <div className="mb-4 grid grid-cols-2 gap-4">
        <div className="bg-red-50 rounded p-3 border border-red-200">
          <p className="text-xs text-red-700 font-semibold">REMOVED</p>
          <p className="text-2xl font-bold text-red-600">{removed.length}</p>
        </div>
        <div className="bg-green-50 rounded p-3 border border-green-200">
          <p className="text-xs text-green-700 font-semibold">ADDED</p>
          <p className="text-2xl font-bold text-green-600">{added.length}</p>
        </div>
      </div>

      {/* Diff view */}
      <div className="bg-gray-50 rounded border border-gray-200 overflow-x-auto">
        {isEmpty ? (
          <div className="p-6 text-center">
            <p className="text-gray-500">No differences found between versions</p>
          </div>
        ) : (
          <div className="font-mono text-xs divide-y divide-gray-300">
            {diffLines.map((line, idx) => {
              const isRemoved = line.type === 'removed';
              const isAdded = line.type === 'added';

              return (
                <div
                  key={`${line.type}-${idx}`}
                  className={`
                    flex items-start px-4 py-2
                    ${isRemoved ? 'bg-red-50 hover:bg-red-100' : ''}
                    ${isAdded ? 'bg-green-50 hover:bg-green-100' : ''}
                  `}
                >
                  {/* Type indicator */}
                  <span
                    className={`
                      flex-shrink-0 w-6 text-center font-bold mr-3
                      ${isRemoved ? 'text-red-600' : ''}
                      ${isAdded ? 'text-green-600' : ''}
                    `}
                  >
                    {isRemoved ? '−' : isAdded ? '+' : ' '}
                  </span>

                  {/* Content (break long lines) */}
                  <span
                    className={`
                      flex-1 break-words
                      ${isRemoved ? 'text-red-800' : ''}
                      ${isAdded ? 'text-green-800' : ''}
                    `}
                  >
                    {line.content}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer: total changes */}
      {!isEmpty && (
        <div className="mt-4 text-sm text-gray-600">
          <p>
            Total changes: <span className="font-semibold">{added.length + removed.length}</span> lines
          </p>
        </div>
      )}
    </div>
  );
}

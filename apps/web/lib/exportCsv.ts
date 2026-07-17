/**
 * T-2010: CSV export utility
 * Client-side CSV generation and download via Blob + anchor click
 *
 * ponytail: PDF export skipped (no jspdf installed; add when actually requested,
 * don't build speculative infra).
 */

/**
 * Convert an array of objects to a CSV string.
 * @param rows Array of objects (each becomes one CSV row)
 * @returns CSV string with headers on first line
 */
function toCsvString(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) {
    return '';
  }

  // Get all unique keys from all rows (preserving order)
  const keys = Array.from(new Set(rows.flatMap(Object.keys)));

  // Helper to escape CSV values (wrap in quotes if contains comma, newline, or quote)
  const escapeCsv = (value: unknown): string => {
    const str = String(value ?? '');
    if (str.includes(',') || str.includes('\n') || str.includes('"')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  // Header row
  const header = keys.map(escapeCsv).join(',');

  // Data rows
  const dataRows = rows.map((row) => keys.map((key) => escapeCsv(row[key])).join(',')).join('\n');

  return `${header}\n${dataRows}`;
}

/**
 * Export rows to a CSV file and trigger browser download.
 * @param filename Name of the file to download (e.g., "results.csv")
 * @param rows Array of objects to export as CSV rows
 */
export function exportToCsv(filename: string, rows: Record<string, unknown>[]): void {
  if (rows.length === 0) {
    console.warn('exportToCsv: empty rows array');
    return;
  }

  const csv = toCsvString(rows);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');

  // Create object URL and trigger download
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Clean up the object URL
  URL.revokeObjectURL(url);
}

/**
 * Helper to format search results for CSV export.
 * @param results Array of search result objects
 * @returns Formatted rows suitable for exportToCsv
 */
export function formatSearchResultsForCsv(
  results: Array<{
    doc_id: string;
    filename: string;
    document_type: string | null;
    rank: number;
    snippet: string;
    created_at: string;
  }>
): Record<string, unknown>[] {
  return results.map((result) => ({
    'Document ID': result.doc_id,
    Filename: result.filename,
    'Document Type': result.document_type || '',
    'Relevance Score': (result.rank * 100).toFixed(0) + '%',
    Snippet: result.snippet,
    'Created Date': new Date(result.created_at).toLocaleDateString(),
  }));
}

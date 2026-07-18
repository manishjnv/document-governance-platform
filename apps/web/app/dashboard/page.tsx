/**
 * T-703: Document list page with filtering
 * Dashboard showing uploaded documents and their review status
 */

'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import Link from 'next/link';
import { ArrowUpDown } from 'lucide-react';
import {
  type ColumnDef,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { AppShell } from '@/components/AppShell';

const DOCUMENT_TYPES = ['SOW', 'Proposal', 'RFP', 'Other'];

interface Document {
  doc_id: string;
  filename: string;
  original_filename: string;
  project_name: string | null;
  document_type: string;
  page_count: number;
  created_at: string;
  latest_overall_score: number | null;
  latest_completeness_score: number | null;
}

function SortableHeader({ label, column }: { label: string; column: any }) {
  return (
    <button
      className="flex items-center gap-1 font-medium hover:text-foreground"
      onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
    >
      {label}
      <ArrowUpDown size={14} strokeWidth={2} aria-hidden="true" />
    </button>
  );
}

function ScoreCell({ value }: { value: number | null }) {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground">-</span>;
  }
  const color =
    value >= 80 ? 'text-green-600' : value >= 50 ? 'text-yellow-600' : 'text-red-600';
  return <span className={`font-medium ${color}`}>{value.toFixed(0)}</span>;
}

export default function DashboardPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [orgId, setOrgId] = useState('');
  const [filterType, setFilterType] = useState('');
  const [sorting, setSorting] = useState<SortingState>([]);
  const [reviewingDocId, setReviewingDocId] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  // Fetches on mount and re-fetches whenever the type filter changes.
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    fetchDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterType]);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');

      // Get current user to get org_id
      const userResponse = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const org = userResponse.data.org_id;
      setOrgId(org);

      // Fetch documents
      let url = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents?org_id=${org}`;
      if (filterType) {
        url += `&document_type=${filterType}`;
      }

      const response = await axios.get(url, {
        headers: { Authorization: `Bearer ${token}` },
      });

      setDocuments(response.data);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch documents');
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (docId: string) => {
    try {
      setError('');
      setReviewingDocId(docId);
      const token = localStorage.getItem('access_token');

      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/reviews/${docId}/trigger`,
        {},
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      router.push(`/results/${response.data.review_id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to trigger review');
    } finally {
      setReviewingDocId(null);
    }
  };

  const handleView = async (docId: string) => {
    try {
      const token = localStorage.getItem('access_token');

      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/reviews`,
        {
          params: { doc_id: docId, org_id: orgId },
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const latest = response.data[0];
      if (!latest) {
        setError('No review yet for this document -- click Review first');
        return;
      }
      router.push(`/results/${latest.review_id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load review');
    }
  };

  // Stats: computed client-side from the currently-loaded (filtered) page of documents.
  const stats = useMemo(() => {
    const byType: Record<string, number> = {};
    for (const doc of documents) {
      const type = doc.document_type || 'Unknown';
      byType[type] = (byType[type] || 0) + 1;
    }
    return { total: documents.length, byType };
  }, [documents]);

  const columns = useMemo<ColumnDef<Document>[]>(
    () => [
      {
        id: 'filename',
        header: ({ column }) => <SortableHeader label="Filename" column={column} />,
        accessorFn: (doc) => doc.original_filename || doc.filename,
        cell: (info) => (
          <span className="font-medium">{info.getValue<string>()}</span>
        ),
      },
      {
        id: 'project_name',
        header: ({ column }) => <SortableHeader label="Project" column={column} />,
        accessorFn: (doc) => doc.project_name || '-',
      },
      {
        id: 'document_type',
        header: ({ column }) => <SortableHeader label="Type" column={column} />,
        accessorFn: (doc) => doc.document_type || 'Unknown',
      },
      {
        id: 'latest_completeness_score',
        header: ({ column }) => <SortableHeader label="Completeness" column={column} />,
        accessorFn: (doc) => doc.latest_completeness_score,
        cell: (info) => <ScoreCell value={info.getValue<number | null>()} />,
      },
      {
        id: 'latest_overall_score',
        header: ({ column }) => <SortableHeader label="Accuracy" column={column} />,
        accessorFn: (doc) => doc.latest_overall_score,
        cell: (info) => <ScoreCell value={info.getValue<number | null>()} />,
      },
      {
        id: 'page_count',
        header: ({ column }) => <SortableHeader label="Pages" column={column} />,
        accessorFn: (doc) => doc.page_count || '-',
      },
      {
        id: 'created_at',
        header: ({ column }) => <SortableHeader label="Uploaded" column={column} />,
        accessorFn: (doc) => doc.created_at,
        cell: (info) => new Date(info.getValue<string>()).toLocaleDateString(),
      },
      {
        id: 'actions',
        header: 'Actions',
        cell: ({ row }) => {
          const isReviewing = reviewingDocId === row.original.doc_id;
          return (
            <div className="flex items-center gap-2">
              <Button
                variant="link"
                size="sm"
                className="h-auto p-0"
                disabled={isReviewing}
                onClick={() => handleReview(row.original.doc_id)}
              >
                {isReviewing ? 'Reviewing... (~20s)' : 'Review'}
              </Button>
              <span className="text-muted-foreground">•</span>
              <Button
                variant="link"
                size="sm"
                className="h-auto p-0"
                disabled={isReviewing}
                onClick={() => handleView(row.original.doc_id)}
              >
                View
              </Button>
            </div>
          );
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [orgId, reviewingDocId]
  );

  const table = useReactTable({
    data: documents,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Documents</h1>
        <Button asChild>
          <Link href="/upload">Upload Document</Link>
        </Button>
      </div>

      {/* Stats + Filter row */}
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div className="flex flex-wrap gap-3">
          <div className="rounded-lg border px-4 py-2">
            <p className="text-xs text-muted-foreground">Total</p>
            <p className="text-lg font-semibold">{stats.total}</p>
          </div>
          {DOCUMENT_TYPES.map((type) => (
            <div key={type} className="rounded-lg border px-4 py-2">
              <p className="text-xs text-muted-foreground">{type}</p>
              <p className="text-lg font-semibold">{stats.byType[type] || 0}</p>
            </div>
          ))}
        </div>

        <div>
          <label htmlFor="filterType" className="block text-sm font-medium mb-2">
            Filter by Type
          </label>
          <select
            id="filterType"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-1.5 text-sm border border-input rounded-md focus:ring-2 focus:ring-ring bg-background"
          >
            <option value="">All Types</option>
            {DOCUMENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div role="alert" className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Documents Table */}
      {loading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">Loading documents...</p>
        </div>
      ) : documents.length === 0 ? (
        <div className="rounded-lg border p-8 text-center">
          <p className="text-muted-foreground mb-4">No documents uploaded yet</p>
          <Button asChild>
            <Link href="/upload">Upload Your First Document</Link>
          </Button>
        </div>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </AppShell>
  );
}

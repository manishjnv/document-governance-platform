/**
 * T-703: Document list page with filtering
 * Dashboard showing uploaded documents and their review status
 */

'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import Link from 'next/link';
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
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

interface Document {
  doc_id: string;
  filename: string;
  original_filename: string;
  document_type: string;
  page_count: number;
  created_at: string;
}

export default function DashboardPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [orgId, setOrgId] = useState('');
  const [filterType, setFilterType] = useState('');
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchDocuments();
  }, [router]);

  const fetchDocuments = async () => {
    try {
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
    }
  };

  const columns = useMemo<ColumnDef<Document>[]>(
    () => [
      {
        id: 'filename',
        header: 'Filename',
        accessorFn: (doc) => doc.original_filename || doc.filename,
        cell: (info) => (
          <span className="font-medium">{info.getValue<string>()}</span>
        ),
      },
      {
        id: 'document_type',
        header: 'Type',
        accessorFn: (doc) => doc.document_type || 'Unknown',
      },
      {
        id: 'page_count',
        header: 'Pages',
        accessorFn: (doc) => doc.page_count || '-',
      },
      {
        id: 'created_at',
        header: 'Uploaded',
        accessorFn: (doc) => new Date(doc.created_at).toLocaleDateString(),
      },
      {
        id: 'actions',
        header: 'Actions',
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <Button
              variant="link"
              size="sm"
              className="h-auto p-0"
              onClick={() => handleReview(row.original.doc_id)}
            >
              Review
            </Button>
            <span className="text-muted-foreground">•</span>
            <Button variant="link" size="sm" className="h-auto p-0" asChild>
              <Link href={`/document/${row.original.doc_id}`}>View</Link>
            </Button>
          </div>
        ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const table = useReactTable({
    data: documents,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Documents</h1>
        <Button asChild>
          <Link href="/upload">Upload Document</Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="mb-6">
        <label htmlFor="filterType" className="block text-sm font-medium mb-2">
          Filter by Type
        </label>
        <select
          id="filterType"
          value={filterType}
          onChange={(e) => {
            setFilterType(e.target.value);
            setLoading(true);
          }}
          className="px-3 py-1.5 text-sm border border-input rounded-md focus:ring-2 focus:ring-ring bg-background"
        >
          <option value="">All Types</option>
          <option value="SOW">Statement of Work</option>
          <option value="Proposal">Proposal</option>
          <option value="ProjectPlan">Project Plan</option>
        </select>
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

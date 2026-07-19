/**
 * Per-project detail page (Phase A of Document Lifecycle plan): rollup
 * metrics + the project's documents.
 */

'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import axios from 'axios';
import Link from 'next/link';
import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface ProjectSummary {
  project_id: string;
  name: string;
  document_count: number;
  average_latest_score: number | null;
  open_critical_count: number;
}

interface Document {
  doc_id: string;
  filename: string;
  original_filename: string;
  project_id: string | null;
  document_type: string;
  created_at: string;
  latest_overall_score: number | null;
}

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    (async () => {
      try {
        const userResponse = await axios.get(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        const orgId = userResponse.data.org_id;

        const [projectsResponse, documentsResponse] = await Promise.all([
          axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects`, {
            headers: { Authorization: `Bearer ${token}` },
            params: { org_id: orgId },
          }),
          axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents`, {
            headers: { Authorization: `Bearer ${token}` },
            params: { org_id: orgId, limit: 1000 },
          }),
        ]);

        const found = projectsResponse.data.find(
          (p: ProjectSummary) => p.project_id === params.id
        );
        if (!found) {
          setError('Project not found');
          return;
        }
        setProject(found);
        setDocuments(
          documentsResponse.data.filter((d: Document) => d.project_id === params.id)
        );
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load project');
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  if (loading) {
    return (
      <AppShell>
        <p className="text-muted-foreground">Loading project...</p>
      </AppShell>
    );
  }

  if (error || !project) {
    return (
      <AppShell>
        <div role="alert" className="bg-destructive/10 border border-destructive/30 rounded-md p-4">
          <p className="text-destructive">{error || 'Project not found'}</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link href="/dashboard" className="text-sm text-primary hover:underline">
            &larr; Dashboard
          </Link>
          <h1 className="text-2xl font-bold mt-1">{project.name}</h1>
        </div>
        <Button asChild>
          <Link href={`/upload?project_id=${project.project_id}`}>Upload to this project</Link>
        </Button>
      </div>

      <div className="flex flex-wrap gap-3 mb-6">
        <div className="rounded-lg border px-4 py-2">
          <p className="text-xs text-muted-foreground">Documents</p>
          <p className="text-lg font-semibold">{project.document_count}</p>
        </div>
        <div className="rounded-lg border px-4 py-2">
          <p className="text-xs text-muted-foreground">Average score</p>
          <p className="text-lg font-semibold">
            {project.average_latest_score !== null
              ? project.average_latest_score.toFixed(0)
              : '-'}
          </p>
        </div>
        <div className="rounded-lg border px-4 py-2">
          <p className="text-xs text-muted-foreground">Open critical findings</p>
          <p className="text-lg font-semibold">{project.open_critical_count}</p>
        </div>
      </div>

      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Filename</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Score</TableHead>
              <TableHead>Uploaded</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {documents.map((doc) => (
              <TableRow key={doc.doc_id}>
                <TableCell className="font-medium">
                  {doc.original_filename || doc.filename}
                </TableCell>
                <TableCell>{doc.document_type || 'Unknown'}</TableCell>
                <TableCell>
                  {doc.latest_overall_score !== null
                    ? doc.latest_overall_score.toFixed(0)
                    : '-'}
                </TableCell>
                <TableCell>{new Date(doc.created_at).toLocaleDateString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </AppShell>
  );
}

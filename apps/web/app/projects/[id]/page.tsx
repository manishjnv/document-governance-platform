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
import { PageHeader, Chip, EmptyState, AlertBanner, KpiTile } from '@/components/app';
import { cn } from '@/lib/utils';

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
        <p className="py-12 text-center text-sm text-muted-foreground">Loading project...</p>
      </AppShell>
    );
  }

  if (error || !project) {
    return (
      <AppShell>
        <AlertBanner kind="error">{error || 'Project not found'}</AlertBanner>
      </AppShell>
    );
  }

  const uploadHref = `/upload?project_id=${project.project_id}`;
  const uploadButton = (
    <Button asChild>
      <Link href={uploadHref}>Upload to this project</Link>
    </Button>
  );

  return (
    <AppShell>
      <PageHeader
        title={project.name}
        back={{ href: '/dashboard', label: 'Dashboard' }}
        actions={uploadButton}
      />

      <div className="mb-[18px] grid grid-cols-1 gap-3 sm:grid-cols-3">
        <KpiTile label="Documents" value={project.document_count} />
        <KpiTile
          label="Average score"
          value={project.average_latest_score !== null ? project.average_latest_score.toFixed(0) : '-'}
        />
        <KpiTile label="Open critical findings" value={project.open_critical_count} tone="crit" />
      </div>

      {documents.length === 0 ? (
        <EmptyState title="No documents in this project yet." action={uploadButton} />
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="tbl cards">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Type</th>
                <th className="r">Score</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                const score = doc.latest_overall_score;
                const scoreClass =
                  score == null
                    ? 'text-ink3'
                    : score >= 80
                      ? 'text-ok'
                      : score >= 50
                        ? 'text-sev-med'
                        : 'text-sev-crit';
                return (
                  <tr key={doc.doc_id}>
                    <td data-th="Filename" className="font-medium text-foreground">
                      {doc.original_filename || doc.filename}
                    </td>
                    <td data-th="Type">
                      <Chip tone="neutral" xs>
                        {doc.document_type || 'Unknown'}
                      </Chip>
                    </td>
                    <td data-th="Score" className={cn('r font-medium tabular-nums', scoreClass)}>
                      {score !== null ? score.toFixed(0) : '-'}
                    </td>
                    <td data-th="Uploaded" className="tabular-nums text-muted-foreground">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}

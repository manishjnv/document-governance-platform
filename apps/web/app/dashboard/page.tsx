/**
 * T-703: Document list page with filtering
 * Dashboard showing uploaded documents and their review status
 */

'use client';

import { Fragment, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import Link from 'next/link';
import { ArrowDown, ArrowUp } from 'lucide-react';
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
  project_id: string | null;
  document_group_id: string;
  version: number;
  document_type: string;
  page_count: number;
  created_at: string;
  latest_overall_score: number | null;
  latest_completeness_score: number | null;
}

interface ProjectSummary {
  project_id: string;
  name: string;
  document_count: number;
  average_latest_score: number | null;
  open_critical_count: number;
}

interface LinkSuggestion {
  suggestion_id: string;
  doc_id: string;
  filename: string;
  suggested_doc_id: string;
  suggested_filename: string;
  suggested_version: number;
  similarity_score: number;
}

function ScoreCell({ value }: { value: number | null }) {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground">-</span>;
  }
  const color =
    value >= 80 ? 'text-green-600' : value >= 50 ? 'text-yellow-600' : 'text-red-600';
  return <span className={`font-medium ${color}`}>{value.toFixed(0)}</span>;
}

function TrendIndicator({ current, previous }: { current: number | null; previous: number | null }) {
  if (current === null || previous === null) return null;
  const delta = current - previous;
  if (Math.abs(delta) < 0.5) return null;
  const Icon = delta > 0 ? ArrowUp : ArrowDown;
  const color = delta > 0 ? 'text-green-600' : 'text-red-600';
  return (
    <span className={`inline-flex items-center ${color}`} title={`${delta > 0 ? '+' : ''}${delta.toFixed(0)} vs previous version`}>
      <Icon size={14} strokeWidth={2} aria-hidden="true" />
    </span>
  );
}

function AssignProjectControl({
  doc,
  projectOptions,
  onAssign,
}: {
  doc: Document;
  projectOptions: ProjectSummary[];
  onAssign: (docId: string, projectId: string | null, projectName: string | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState('');

  if (!open) {
    return (
      <button className="text-primary hover:underline" onClick={() => setOpen(true)}>
        Assign project
      </button>
    );
  }

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    const existing = projectOptions.find((p) => p.name === trimmed);
    onAssign(doc.doc_id, existing ? existing.project_id : null, existing ? null : trimmed);
    setOpen(false);
    setValue('');
  };

  return (
    <span className="inline-flex items-center gap-1">
      <input
        autoFocus
        type="text"
        list={`assign-project-options-${doc.doc_id}`}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            submit();
          }
          if (e.key === 'Escape') setOpen(false);
        }}
        placeholder="Project name"
        className="px-2 py-1 text-sm border border-input rounded-md bg-background w-40"
      />
      <datalist id={`assign-project-options-${doc.doc_id}`}>
        {projectOptions.map((p) => (
          <option key={p.project_id} value={p.name} />
        ))}
      </datalist>
      <button className="text-primary hover:underline text-sm" onClick={submit}>
        Save
      </button>
      <button className="text-muted-foreground hover:underline text-sm" onClick={() => setOpen(false)}>
        Cancel
      </button>
    </span>
  );
}

function DocumentsTable({
  documents,
  reviewingDocId,
  onReview,
  onView,
  onDelete,
  projectOptions,
  onAssignProject,
}: {
  documents: Document[];
  reviewingDocId: string | null;
  onReview: (docId: string) => void;
  onView: (docId: string) => void;
  onDelete: (docId: string) => void;
  projectOptions: ProjectSummary[];
  onAssignProject: (docId: string, projectId: string | null, projectName: string | null) => void;
}) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  // Group by document_group_id -- each group is one logical document's
  // version history, newest first.
  const versionGroups = useMemo(() => {
    const byGroup = new Map<string, Document[]>();
    for (const doc of documents) {
      const bucket = byGroup.get(doc.document_group_id) ?? [];
      bucket.push(doc);
      byGroup.set(doc.document_group_id, bucket);
    }
    return Array.from(byGroup.values())
      .map((versions) => versions.sort((a, b) => b.version - a.version))
      .sort((a, b) => new Date(b[0].created_at).getTime() - new Date(a[0].created_at).getTime());
  }, [documents]);

  const toggleGroup = (groupId: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
      return next;
    });
  };

  const renderActions = (doc: Document, compareToVersion?: number) => {
    const isReviewing = reviewingDocId === doc.doc_id;
    return (
      <div className="flex items-center gap-2">
        <button
          className="text-primary hover:underline disabled:opacity-50"
          disabled={isReviewing}
          onClick={() => onReview(doc.doc_id)}
        >
          {isReviewing ? 'Reviewing... (~20s)' : 'Review'}
        </button>
        <span className="text-muted-foreground">•</span>
        <button
          className="text-primary hover:underline disabled:opacity-50"
          disabled={isReviewing}
          onClick={() => onView(doc.doc_id)}
        >
          View
        </button>
        <span className="text-muted-foreground">•</span>
        <Link href={`/upload?version_of=${doc.doc_id}`} className="text-primary hover:underline">
          New version
        </Link>
        {!doc.project_id && (
          <>
            <span className="text-muted-foreground">•</span>
            <AssignProjectControl doc={doc} projectOptions={projectOptions} onAssign={onAssignProject} />
          </>
        )}
        {compareToVersion !== undefined && (
          <>
            <span className="text-muted-foreground">•</span>
            <Link
              href={`/versions/diff?doc_id=${doc.doc_id}&other_version=${compareToVersion}`}
              className="text-primary hover:underline"
            >
              Compare vs v{compareToVersion}
            </Link>
          </>
        )}
        <span className="text-muted-foreground">•</span>
        <button
          className="text-destructive hover:underline disabled:opacity-50"
          disabled={isReviewing}
          onClick={() => onDelete(doc.doc_id)}
        >
          Delete
        </button>
      </div>
    );
  };

  return (
    <div className="rounded-lg border overflow-hidden">
      <Table className="text-xs [&_th]:h-8 [&_th]:py-1.5 [&_th]:px-3 [&_td]:py-1.5 [&_td]:px-3">
        <TableHeader>
          <TableRow>
            <TableHead>Filename</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Completeness</TableHead>
            <TableHead>Accuracy</TableHead>
            <TableHead>Uploaded</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {versionGroups.map((versions) => {
            const latest = versions[0];
            const previous = versions[1];
            const isExpanded = expandedGroups.has(latest.document_group_id);
            const hasHistory = versions.length > 1;
            return (
              <Fragment key={latest.document_group_id}>
                <TableRow>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      {hasHistory && (
                        <button
                          onClick={() => toggleGroup(latest.document_group_id)}
                          className="text-muted-foreground hover:text-foreground w-4"
                          aria-label={isExpanded ? 'Collapse versions' : 'Expand versions'}
                        >
                          {isExpanded ? '▾' : '▸'}
                        </button>
                      )}
                      <span>{latest.original_filename || latest.filename}</span>
                      {hasHistory && (
                        <span className="text-xs text-muted-foreground">
                          v{latest.version} ({versions.length} versions)
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>{latest.document_type || 'Unknown'}</TableCell>
                  <TableCell>
                    <ScoreCell value={latest.latest_completeness_score} />
                  </TableCell>
                  <TableCell>
                    <span className="flex items-center gap-1">
                      <ScoreCell value={latest.latest_overall_score} />
                      {previous && (
                        <TrendIndicator
                          current={latest.latest_overall_score}
                          previous={previous.latest_overall_score}
                        />
                      )}
                    </span>
                  </TableCell>
                  <TableCell>{new Date(latest.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>{renderActions(latest, previous?.version)}</TableCell>
                </TableRow>
                {isExpanded &&
                  versions.slice(1).map((doc) => (
                    <TableRow key={doc.doc_id} className="bg-muted/30">
                      <TableCell className="pl-8 text-muted-foreground">
                        v{doc.version} -- {doc.original_filename || doc.filename}
                      </TableCell>
                      <TableCell>{doc.document_type || 'Unknown'}</TableCell>
                      <TableCell>
                        <ScoreCell value={doc.latest_completeness_score} />
                      </TableCell>
                      <TableCell>
                        <ScoreCell value={doc.latest_overall_score} />
                      </TableCell>
                      <TableCell>{new Date(doc.created_at).toLocaleDateString()}</TableCell>
                      <TableCell>{renderActions(doc, latest.version)}</TableCell>
                    </TableRow>
                  ))}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

export default function DashboardPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [orgId, setOrgId] = useState('');
  const [filterType, setFilterType] = useState('');
  const [reviewingDocId, setReviewingDocId] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<LinkSuggestion[]>([]);
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

      const [documentsResponse, projectsResponse, suggestionsResponse] = await Promise.all([
        axios.get(url, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects`, {
          headers: { Authorization: `Bearer ${token}` },
          params: { org_id: org },
        }),
        axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/suggestions`, {
          headers: { Authorization: `Bearer ${token}` },
          params: { org_id: org },
        }),
      ]);

      setDocuments(documentsResponse.data);
      setProjects(projectsResponse.data);
      setSuggestions(suggestionsResponse.data);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch documents');
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestion = async (suggestionId: string, action: 'accept' | 'dismiss') => {
    try {
      const token = localStorage.getItem('access_token');
      await axios.patch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/suggestions/${suggestionId}`,
        { action },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSuggestions((prev) => prev.filter((s) => s.suggestion_id !== suggestionId));
      if (action === 'accept') fetchDocuments();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update suggestion');
    }
  };

  const handleAssignProject = async (
    docId: string,
    projectId: string | null,
    projectName: string | null
  ) => {
    try {
      const token = localStorage.getItem('access_token');
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);
      if (projectName) params.append('project_name', projectName);
      await axios.patch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${docId}/project?${params.toString()}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchDocuments();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to assign project');
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

  const handleDelete = async (docId: string) => {
    if (!confirm('Permanently delete this document, its reviews, and all findings? This cannot be undone.')) return;
    try {
      const token = localStorage.getItem('access_token');
      await axios.delete(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${docId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchDocuments();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete document');
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

  // Group documents by project for the collapsible dashboard sections.
  // Documents with no project_id land in a single "Ungrouped" bucket.
  const groups = useMemo(() => {
    const byProjectId = new Map<string, Document[]>();
    const ungrouped: Document[] = [];
    for (const doc of documents) {
      if (!doc.project_id) {
        ungrouped.push(doc);
        continue;
      }
      const bucket = byProjectId.get(doc.project_id) ?? [];
      bucket.push(doc);
      byProjectId.set(doc.project_id, bucket);
    }

    const projectGroups = projects
      .filter((p) => byProjectId.has(p.project_id))
      .map((p) => ({ project: p, documents: byProjectId.get(p.project_id)! }));

    return { projectGroups, ungrouped };
  }, [documents, projects]);

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-medium">Documents</h1>
        <Button asChild>
          <Link href="/upload">Upload Document</Link>
        </Button>
      </div>

      {/* Version-link suggestions: dismissible, persist until acted on */}
      {suggestions.length > 0 && (
        <div className="space-y-2 mb-6">
          {suggestions.map((s) => (
            <div
              key={s.suggestion_id}
              className="flex items-center justify-between gap-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3"
            >
              <p className="text-sm text-blue-900">
                <strong>{s.filename}</strong> looks like it could be a new version of{' '}
                <strong>{s.suggested_filename}</strong> (v{s.suggested_version}) --
                link as v{s.suggested_version + 1}?{' '}
                <span className="text-blue-700">
                  ({Math.round(s.similarity_score * 100)}% similar)
                </span>
              </p>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  className="text-sm font-medium text-blue-700 hover:underline"
                  onClick={() => handleSuggestion(s.suggestion_id, 'accept')}
                >
                  Link as v{s.suggested_version + 1}
                </button>
                <button
                  className="text-sm text-muted-foreground hover:underline"
                  onClick={() => handleSuggestion(s.suggestion_id, 'dismiss')}
                >
                  Dismiss
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Stats + Filter row */}
      <div className="flex flex-nowrap items-center justify-between gap-4 mb-6">
        <div className="flex flex-wrap items-center gap-x-3 rounded-lg border text-sm min-w-0">
          <span className="text-slate-700">
            Total <span className="font-normal text-slate-900">{stats.total}</span>
          </span>
          {DOCUMENT_TYPES.map((type) => (
            <span key={type} className="text-slate-700">
              {type} <span className="font-normal text-slate-900">{stats.byType[type] || 0}</span>
            </span>
          ))}
        </div>

        <div className="flex items-center gap-2 shrink-0 whitespace-nowrap">
          <label htmlFor="filterType" className="text-sm font-medium">
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
        <div className="space-y-2">
          {groups.projectGroups.map(({ project, documents: projectDocs }) => (
            <details key={project.project_id} className="rounded-lg border" open>
              <summary className="cursor-pointer select-none px-3 py-2 text-sm flex items-center justify-between gap-4">
                <span className="font-medium">
                  {project.name}{' '}
                  <span className="text-muted-foreground font-normal">
                    ({projectDocs.length} document{projectDocs.length === 1 ? '' : 's'})
                  </span>
                </span>
                <span className="flex items-center gap-4 text-xs text-muted-foreground">
                  {project.average_latest_score !== null && (
                    <span>Avg score: {project.average_latest_score.toFixed(0)}</span>
                  )}
                  {project.open_critical_count > 0 && (
                    <span className="text-red-600 font-medium">
                      {project.open_critical_count} critical
                    </span>
                  )}
                  <Link
                    href={`/projects/${project.project_id}`}
                    className="text-primary hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    View project
                  </Link>
                </span>
              </summary>
              <div className="px-2 pb-2">
                <DocumentsTable
                  documents={projectDocs}
                  reviewingDocId={reviewingDocId}
                  onReview={handleReview}
                  onView={handleView}
                  onDelete={handleDelete}
                  projectOptions={projects}
                  onAssignProject={handleAssignProject}
                />
              </div>
            </details>
          ))}

          {groups.ungrouped.length > 0 && (
            <details className="rounded-lg border" open>
              <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium">
                No Project{' '}
                <span className="text-muted-foreground font-normal">
                  ({groups.ungrouped.length} document{groups.ungrouped.length === 1 ? '' : 's'})
                </span>
              </summary>
              <div className="px-2 pb-2">
                <DocumentsTable
                  documents={groups.ungrouped}
                  reviewingDocId={reviewingDocId}
                  onReview={handleReview}
                  onView={handleView}
                  onDelete={handleDelete}
                  projectOptions={projects}
                  onAssignProject={handleAssignProject}
                />
              </div>
            </details>
          )}
        </div>
      )}
    </AppShell>
  );
}

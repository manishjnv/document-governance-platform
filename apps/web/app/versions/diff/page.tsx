/**
 * Version-diff view (Phase C of Document Lifecycle plan): given two
 * versions of a document, shows Resolved / New / Persisted findings.
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import Link from 'next/link';
import { AppShell } from '@/components/AppShell';

interface FindingSummary {
  finding_id: string;
  category: string;
  title: string;
  severity: string;
  section_ref: string | null;
  status: string;
}

interface FindingDiff {
  older_version: number;
  newer_version: number;
  resolved: FindingSummary[];
  new: FindingSummary[];
  persisted: FindingSummary[];
}

function severityColor(severity: string) {
  switch (severity) {
    case 'critical':
      return 'border-red-300 bg-red-50 text-red-800';
    case 'major':
      return 'border-orange-300 bg-orange-50 text-orange-800';
    case 'medium':
      return 'border-yellow-300 bg-yellow-50 text-yellow-800';
    default:
      return 'border-border bg-muted/40 text-foreground';
  }
}

function FindingCard({ finding }: { finding: FindingSummary }) {
  return (
    <div className={`rounded-md border px-3 py-2 text-sm ${severityColor(finding.severity)}`}>
      <p className="font-medium">{finding.title}</p>
      <p className="text-xs opacity-80">
        {finding.category}
        {finding.section_ref ? ` -- ${finding.section_ref}` : ''}
      </p>
    </div>
  );
}

export default function VersionDiffPage() {
  const router = useRouter();
  const [diff, setDiff] = useState<FindingDiff | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const docId = params.get('doc_id');
    const otherVersion = params.get('other_version');
    if (!docId || !otherVersion) {
      setError('Missing doc_id or other_version in the URL');
      setLoading(false);
      return;
    }

    axios
      .get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/${docId}/versions/${otherVersion}/finding-diff`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      .then((res) => setDiff(res.data))
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load version diff'))
      .finally(() => setLoading(false));
  }, [router]);

  return (
    <AppShell>
      <div className="mb-6">
        <Link href="/dashboard" className="text-sm text-primary hover:underline">
          &larr; Dashboard
        </Link>
        <h1 className="text-2xl font-bold mt-1">Version Comparison</h1>
        {diff && (
          <p className="text-muted-foreground text-sm">
            v{diff.older_version} &rarr; v{diff.newer_version}
          </p>
        )}
      </div>

      {loading && <p className="text-muted-foreground">Loading...</p>}

      {error && (
        <div role="alert" className="bg-destructive/10 border border-destructive/30 rounded-md p-4 mb-6">
          <p className="text-destructive">{error}</p>
        </div>
      )}

      {diff && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <h2 className="font-semibold mb-3 text-green-700">
              Resolved ({diff.resolved.length})
            </h2>
            <div className="space-y-2">
              {diff.resolved.length === 0 && (
                <p className="text-sm text-muted-foreground">Nothing resolved.</p>
              )}
              {diff.resolved.map((f) => (
                <FindingCard key={f.finding_id} finding={f} />
              ))}
            </div>
          </div>

          <div>
            <h2 className="font-semibold mb-3 text-blue-700">New ({diff.new.length})</h2>
            <div className="space-y-2">
              {diff.new.length === 0 && (
                <p className="text-sm text-muted-foreground">No new findings.</p>
              )}
              {diff.new.map((f) => (
                <FindingCard key={f.finding_id} finding={f} />
              ))}
            </div>
          </div>

          <div>
            <h2 className="font-semibold mb-3 text-red-700">
              Persisted ({diff.persisted.length})
            </h2>
            <div className="space-y-2">
              {diff.persisted.length === 0 && (
                <p className="text-sm text-muted-foreground">Nothing persisted.</p>
              )}
              {diff.persisted.map((f) => (
                <FindingCard key={f.finding_id} finding={f} />
              ))}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

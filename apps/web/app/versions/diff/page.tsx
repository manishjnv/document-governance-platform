/**
 * Version-diff view (Phase C of Document Lifecycle plan): given two
 * versions of a document, shows Resolved / New / Persisted findings.
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { AppShell } from '@/components/AppShell';
import { PageHeader, KpiTile, type KpiTone, EmptyState, AlertBanner, SkeletonRows } from '@/components/app';
import { cn } from '@/lib/utils';

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

const SEVERITY_CLASSES: Record<string, string> = {
  critical: 'border-l-sev-crit bg-sev-crit-soft',
  major: 'border-l-sev-high bg-sev-high-soft',
  medium: 'border-l-sev-med bg-sev-med-soft',
};
const DEFAULT_SEVERITY_CLASS = 'border-l-line2 bg-muted/40';

function FindingCard({ finding }: { finding: FindingSummary }) {
  return (
    <div
      className={cn(
        'rounded-lg border border-border border-l-[3px] px-3 py-2 text-sm',
        SEVERITY_CLASSES[finding.severity] || DEFAULT_SEVERITY_CLASS
      )}
    >
      <p className="font-medium text-foreground">{finding.title}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">
        {finding.category}
        {finding.section_ref ? ` -- ${finding.section_ref}` : ''}
      </p>
    </div>
  );
}

function DiffColumn({
  tone,
  label,
  items,
  emptyText,
}: {
  tone: KpiTone;
  label: string;
  items: FindingSummary[];
  emptyText: string;
}) {
  return (
    <div className="space-y-2.5">
      <KpiTile label={label} value={items.length} tone={tone} />
      <div className="space-y-2">
        {items.length === 0 ? (
          <EmptyState title={emptyText} />
        ) : (
          items.map((f) => <FindingCard key={f.finding_id} finding={f} />)
        )}
      </div>
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
      <PageHeader
        title="Version Comparison"
        meta={diff ? `v${diff.older_version} → v${diff.newer_version}` : undefined}
        back={{ href: '/dashboard', label: 'Dashboard' }}
      />

      {loading && (
        <>
          <p className="sr-only">Loading...</p>
          <SkeletonRows rows={3} />
        </>
      )}

      {error && <AlertBanner kind="error">{error}</AlertBanner>}

      {diff && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <DiffColumn tone="ok" label="Resolved" items={diff.resolved} emptyText="Nothing resolved." />
          <DiffColumn tone="accent" label="New" items={diff.new} emptyText="No new findings." />
          <DiffColumn tone="crit" label="Persisted" items={diff.persisted} emptyText="Nothing persisted." />
        </div>
      )}
    </AppShell>
  );
}

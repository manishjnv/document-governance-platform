'use client';

import { CodeReviewReport } from '../../lib';

function Dl({ rows }: { rows: [string, React.ReactNode][] }) {
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-[13px]">
      {rows.map(([k, v], i) => (
        <div className="contents" key={i}>
          <dt className="text-ink3">{k}</dt>
          <dd className="text-right font-medium text-foreground">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-[10px] border border-border bg-card p-4">
      <h3 className="mb-2.5 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">{title}</h3>
      {children}
    </div>
  );
}

/** Scan details tab: metrics + run manifest definition lists, ingest notes,
 * and the raw scanner summary text. */
export function ScanDetailsTab({ report }: { report: CodeReviewReport }) {
  const m = report.metrics;
  const manifest = report.manifest;

  const metricRows: [string, React.ReactNode][] = [
    ['Files in scope', m.total_files_in_scope ?? '—'],
    ['Files analyzed', m.analyzed_files_unique ?? '—'],
    ['Duration', m.duration_sec != null ? `${Math.round(m.duration_sec)}s` : '—'],
    ['Tokens', m.total_tokens != null ? m.total_tokens.toLocaleString() : '—'],
    ['Verifier true positives', m.true_positive_count ?? '—'],
    ['Verifier false positives', m.false_positive_count ?? '—'],
    ['Degraded reason', report.degraded ? report.degraded_reason || '—' : 'Not degraded'],
    ['Dropped findings', report.dropped_count],
    ['Raw findings before dedup', report.raw_findings_count],
  ];

  const manifestRows: [string, React.ReactNode][] = manifest
    ? [
        ['Target git sha', manifest.target_git_sha ?? '—'],
        ['VVAH version', report.tool_version ?? '—'],
        ...Object.entries(manifest.models).map(
          ([role, mo]) => [`${role} model`, `${mo.id} (${mo.provider})`] as [string, React.ReactNode]
        ),
        ['Total cost', manifest.total_cost_usd != null ? `$${manifest.total_cost_usd.toFixed(2)}` : '—'],
        ['Total tokens', manifest.total_tokens != null ? manifest.total_tokens.toLocaleString() : '—'],
      ]
    : [];

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <SectionCard title="Scan metrics">
        <Dl rows={metricRows} />
      </SectionCard>
      <SectionCard title="Run manifest">
        {manifest ? <Dl rows={manifestRows} /> : <p className="text-sm text-muted-foreground">not uploaded</p>}
      </SectionCard>

      <SectionCard title="Ingest notes">
        {report.assumptions.length > 0 ? (
          <ul className="list-disc space-y-1 pl-4 text-[13px] text-foreground">
            {report.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">none</p>
        )}
      </SectionCard>

      {report.summary_text && (
        <div className="rounded-[10px] border border-border bg-card p-4 sm:col-span-2">
          <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">Scanner summary</h3>
          <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-muted-foreground">{report.summary_text}</p>
        </div>
      )}
    </div>
  );
}

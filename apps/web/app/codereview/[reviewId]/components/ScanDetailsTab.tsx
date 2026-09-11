'use client';

import { CodeReviewReport } from '../../lib';

function Dl({ rows }: { rows: [string, React.ReactNode][] }) {
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
      {rows.map(([k, v], i) => (
        <div className="contents" key={i}>
          <dt className="text-muted-foreground">{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
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
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Scan metrics</h3>
          <Dl rows={metricRows} />
        </div>
        <div>
          <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Run manifest</h3>
          {manifest ? <Dl rows={manifestRows} /> : <p className="text-sm text-muted-foreground">not uploaded</p>}
        </div>
      </div>

      <div>
        <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Ingest notes</h3>
        {report.assumptions.length > 0 ? (
          <ul className="list-disc space-y-0.5 pl-4 text-sm">
            {report.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">none</p>
        )}
      </div>

      {report.summary_text && (
        <div>
          <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Scanner summary</h3>
          <p className="whitespace-pre-wrap text-sm text-muted-foreground">{report.summary_text}</p>
        </div>
      )}
    </div>
  );
}

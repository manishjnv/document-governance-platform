'use client';

import { CodeReviewReport, deepVerifiedNote } from '../../lib';

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

function SectionCard({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-[10px] border border-border bg-card p-4${className ? ` ${className}` : ''}`}>
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
  const extras = report.run_extras;

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

      {extras && (
        <SectionCard title="Run coverage" className="sm:col-span-2">
          <div className="space-y-3">
            <p className="text-[13px] text-foreground">{deepVerifiedNote(extras.deep_verified, extras.total)}</p>

            {extras.coverage && (
              <Dl
                rows={[
                  ['Coverage', extras.coverage.coverage_pct != null ? `${extras.coverage.coverage_pct}%` : '—'],
                  ['Files in scope', extras.coverage.files_in_scope ?? '—'],
                  ['Files analyzed', extras.coverage.files_analyzed ?? '—'],
                  ['Chunks', extras.coverage.chunks ?? '—'],
                ]}
              />
            )}

            {extras.coverage && extras.coverage.health.length > 0 && (
              <div>
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">Scan health</div>
                <ul className="list-disc space-y-1 pl-4 text-[13px] text-foreground">
                  {extras.coverage.health.map((h, i) => (
                    <li key={i}>{h}</li>
                  ))}
                </ul>
              </div>
            )}

            {extras.tests && (
              <div>
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">Test summary</div>
                <Dl
                  rows={[
                    ['Build', extras.tests.build ?? '—'],
                    ['Cases', extras.tests.cases],
                    ['Failures', extras.tests.failures],
                  ]}
                />
                {extras.tests.failing.length > 0 && (
                  <ul className="mt-1.5 space-y-0.5 font-mono text-xs text-muted-foreground">
                    {extras.tests.failing.map((t, i) => (
                      <li key={i}>
                        {t.test}
                        {t.message ? `: ${t.message}` : ''}
                      </li>
                    ))}
                  </ul>
                )}
                {extras.tests.not_run_modules.length > 0 && (
                  <p className="mt-1.5 text-xs text-muted-foreground">
                    Not tested: {extras.tests.not_run_modules.join(', ')}
                  </p>
                )}
              </div>
            )}

            {extras.coverage?.threat_model && (
              <details className="rounded-md border border-border">
                <summary className="cursor-pointer select-none px-2.5 py-1.5 text-xs font-medium text-foreground">
                  Threat model
                </summary>
                <p className="whitespace-pre-wrap border-t border-border px-2.5 py-2 text-[13px] leading-relaxed text-muted-foreground">
                  {extras.coverage.threat_model}
                </p>
              </details>
            )}
          </div>
        </SectionCard>
      )}

      {report.summary_text && (
        <div className="rounded-[10px] border border-border bg-card p-4 sm:col-span-2">
          <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">Scanner summary</h3>
          <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-muted-foreground">{report.summary_text}</p>
        </div>
      )}
    </div>
  );
}

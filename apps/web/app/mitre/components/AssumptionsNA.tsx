'use client';

import { useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { DOMAIN_LABELS, NaEntry, Summary } from '../lib';

/** Assumptions list + the N/A appendix grouped by why each technique left
 * the denominator. Grouping keys off the backend's own reason phrasing
 * (derived reasons have fixed shapes; anything else is customer-declared
 * verbatim text). */
const GROUPS = [
  {
    key: 'domain',
    title: 'Whole matrix not applicable',
    blurb: 'These ATT&CK areas don’t apply to your environment at all.',
    match: (r: string) => r.includes('matrix:'),
  },
  {
    key: 'platform',
    title: 'Platform not in your environment',
    blurb: 'These techniques only work on platforms your inventory doesn’t include.',
    match: (r: string) => r.startsWith('targets '),
  },
  {
    key: 'deprecated',
    title: 'Deprecated by MITRE',
    blurb: 'MITRE no longer maintains these techniques, so they aren’t assessed.',
    match: (r: string) => r.startsWith('deprecated in ATT&CK'),
  },
  {
    key: 'customer',
    title: 'Excluded by you',
    blurb: 'You asked us not to assess these — each reason is shown exactly as you gave it.',
    match: () => true, // catch-all: customer-declared verbatim reasons
  },
];

export function AssumptionsNA({ summary }: { summary: Summary }) {
  const grouped = useMemo(() => {
    const buckets = new Map<string, NaEntry[]>();
    for (const entry of summary.not_applicable) {
      const group = GROUPS.find((g) => g.match(entry.reason ?? ''))!;
      const list = buckets.get(group.key) ?? [];
      list.push(entry);
      buckets.set(group.key, list);
    }
    return buckets;
  }, [summary.not_applicable]);

  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-2 text-sm font-semibold">Assumptions made in this assessment</h3>
        <p className="mb-2 text-xs text-muted-foreground">
          Read these before trusting the numbers — they describe what we had to assume or
          could not verify.
        </p>
        <ul className="space-y-1.5">
          {summary.assumptions.map((assumption, i) => (
            <li key={i} className="rounded-md bg-muted/40 px-3 py-2 text-sm leading-snug">
              {assumption}
            </li>
          ))}
          {summary.assumptions.length === 0 && (
            <li className="text-sm text-muted-foreground">No assumptions were needed.</li>
          )}
        </ul>
      </section>

      <section>
        <h3 className="mb-1 text-sm font-semibold">
          Not-applicable techniques ({summary.not_applicable.length})
        </h3>
        <p className="mb-3 text-xs text-muted-foreground">
          These leave the coverage denominator — the headline percentage makes no claim
          about them.
        </p>
        <div className="space-y-4">
          {GROUPS.map((group) => {
            const entries = grouped.get(group.key) ?? [];
            if (entries.length === 0) return null;
            return (
              <div key={group.key}>
                <h4 className="text-xs font-semibold">
                  {group.title} <span className="font-normal text-muted-foreground">({entries.length})</span>
                </h4>
                <p className="mb-1.5 text-xs text-muted-foreground">{group.blurb}</p>
                <div className="max-h-72 overflow-y-auto rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-28">Technique</TableHead>
                        <TableHead className="w-24 hidden sm:table-cell">Matrix</TableHead>
                        <TableHead>Reason</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {entries.map((entry) => (
                        <TableRow key={entry.technique_id}>
                          <TableCell className="text-xs font-medium">{entry.technique_id}</TableCell>
                          <TableCell className="hidden text-xs text-muted-foreground sm:table-cell">
                            {DOMAIN_LABELS[entry.domain] ?? entry.domain}
                          </TableCell>
                          <TableCell className="text-xs">{entry.reason}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

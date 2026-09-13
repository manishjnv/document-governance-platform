'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

type BarSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

const ORDER: BarSeverity[] = ['critical', 'high', 'medium', 'low', 'info'];

const BAR_CLASS: Record<BarSeverity, string> = {
  critical: 'bg-sev-crit',
  high: 'bg-sev-high',
  medium: 'bg-sev-med',
  low: 'bg-sev-low',
  info: 'bg-sev-info',
};

export interface SeverityBarProps {
  counts: Partial<Record<BarSeverity, number>>;
  className?: string;
}

/** Stacked horizontal severity bar: one bg-sev-* segment per non-zero
 * severity, sized by its share of the total. Empty track when total is 0. */
export function SeverityBar({ counts, className }: SeverityBarProps) {
  const total = ORDER.reduce((sum, s) => sum + (counts[s] ?? 0), 0);
  const label = ORDER.filter((s) => (counts[s] ?? 0) > 0)
    .map((s) => `${counts[s]} ${s}`)
    .join(', ');

  return (
    <div
      role="img"
      aria-label={label || 'No findings'}
      className={cn('flex h-1.5 w-full overflow-hidden rounded-full bg-na', className)}
    >
      {total > 0 &&
        ORDER.map((s) => {
          const count = counts[s] ?? 0;
          if (count === 0) return null;
          return <span key={s} className={BAR_CLASS[s]} style={{ width: `${(count / total) * 100}%` }} />;
        })}
    </div>
  );
}

'use client';

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { AssessmentListItem } from '../lib';

/** Phase 14f: tiny inline SVG sparkline over completed runs' coverage %.
 * Items are newest-first (the list endpoint's order); needs a TooltipProvider
 * ancestor. Shared by the assessment list and the connections page. */
export function CoverageSparkline({ items }: { items: AssessmentListItem[] }) {
  const points = items
    .filter((i) => i.status === 'completed' && i.strict_pct !== null && !i.archived)
    .slice()
    .reverse(); // list is newest-first; the trend reads left → right in time
  if (points.length < 2) return null;
  const max = Math.max(...points.map((p) => p.strict_pct as number), 1);
  const w = 120;
  const h = 28;
  const step = w / (points.length - 1);
  const path = points
    .map(
      (p, i) =>
        `${i === 0 ? 'M' : 'L'}${(i * step).toFixed(1)},${(
          h - 3 - ((p.strict_pct as number) / max) * (h - 6)
        ).toFixed(1)}`
    )
    .join(' ');
  const first = points[0].strict_pct;
  const last = points[points.length - 1].strict_pct;
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <span className="flex cursor-default items-center gap-2 text-xs text-muted-foreground">
          Your trend so far
          <svg width={w} height={h} aria-hidden="true" className="overflow-visible">
            <path d={path} fill="none" stroke="currentColor" strokeWidth="1.5" className="text-primary" />
          </svg>
          {first}% → {last}%
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">
        Coverage % across your {points.length} completed runs, oldest to newest.
      </TooltipContent>
    </Tooltip>
  );
}

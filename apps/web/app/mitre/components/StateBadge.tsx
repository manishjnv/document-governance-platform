'use client';

import { Chip, type ChipTone } from '@/components/app';
import { STATE_META, STATUS_META } from '../lib';

/** Tone per state string this badge might receive — technique coverage
 * states (covered/partial/not_covered/not_applicable) and assessment run
 * states (pending/running/completed/failed) share this one component. */
const STATE_TONE: Record<string, ChipTone> = {
  covered: 'ok',
  partial: 'med',
  not_covered: 'crit',
  not_applicable: 'neutral',
  pending: 'neutral',
  running: 'info',
  completed: 'ok',
  failed: 'crit',
};

/** State chip with the plain-English hover explanation (locked UI rule:
 * every state badge gets a tooltip). Self-contained tooltip (Chip carries
 * its own TooltipProvider), so no ancestor is required. */
export function StateBadge({ state, className }: { state: string; className?: string }) {
  const meta = STATE_META[state] ?? STATUS_META[state];
  const tip = meta && 'tip' in meta ? meta.tip : undefined;
  return (
    <Chip tone={STATE_TONE[state] ?? 'neutral'} dot tip={tip} className={className}>
      {meta?.label ?? state}
    </Chip>
  );
}

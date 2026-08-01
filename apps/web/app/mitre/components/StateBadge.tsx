'use client';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { STATE_META } from '../lib';

/** State chip with the plain-English hover explanation (locked UI rule:
 * every state badge gets a tooltip). Assumes a TooltipProvider ancestor. */
export function StateBadge({ state, className }: { state: string; className?: string }) {
  const meta = STATE_META[state] ?? {
    label: state,
    chip: 'bg-muted text-muted-foreground border-transparent',
    tip: '',
  };
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <span
          className={cn(
            'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium cursor-default',
            meta.chip,
            className
          )}
        >
          {meta.label}
        </span>
      </TooltipTrigger>
      {meta.tip && <TooltipContent className="max-w-xs text-xs">{meta.tip}</TooltipContent>}
    </Tooltip>
  );
}

'use client';

import * as React from 'react';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

export type KpiTone = 'default' | 'accent' | 'ok' | 'crit' | 'high' | 'med' | 'grey';

const toneClass: Record<KpiTone, string> = {
  default: 'text-foreground',
  accent: 'text-primary',
  ok: 'text-ok',
  crit: 'text-sev-crit',
  high: 'text-sev-high',
  med: 'text-sev-med',
  grey: 'text-ink3',
};

export interface KpiTileProps {
  label: React.ReactNode;
  value: React.ReactNode;
  sub?: React.ReactNode;
  tone?: KpiTone;
  tip?: string;
  onClick?: () => void;
  active?: boolean;
  className?: string;
}

export function KpiTile({ label, value, sub, tone = 'default', tip, onClick, active, className }: KpiTileProps) {
  const Tag = onClick ? 'button' : 'div';

  const content = (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      aria-pressed={onClick && active !== undefined ? active : undefined}
      className={cn(
        'flex min-w-0 flex-col gap-1 rounded-[10px] border border-border bg-card px-3.5 py-3 text-left',
        onClick &&
          'cursor-pointer transition-[border-color,background-color] duration-150 ease-app hover:border-primary hover:bg-accent-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        active && 'border-primary bg-accent-soft',
        className
      )}
    >
      <span className="text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">{label}</span>
      <span className={cn('text-2xl font-semibold leading-[1.1] tracking-[-.02em] tabular-nums max-[760px]:text-xl', toneClass[tone])}>
        {value}
      </span>
      {sub != null && <span className="text-xs text-ink3">{sub}</span>}
    </Tag>
  );

  if (!tip) return content;

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent>{tip}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

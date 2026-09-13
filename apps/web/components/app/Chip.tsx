'use client';

import * as React from 'react';
import { Badge, type BadgeProps } from '@/components/ui/badge';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

export type ChipTone = NonNullable<BadgeProps['tone']>;

export interface ChipProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'children'> {
  tone?: ChipTone;
  dot?: boolean;
  tip?: string;
  xs?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function Chip({ tone = 'neutral', dot, tip, xs, className, children, ...rest }: ChipProps) {
  const badge = (
    <Badge
      tone={tone}
      className={cn(xs && 'h-[18px] px-1.5 text-[10.5px]', className)}
      {...rest}
    >
      {dot && <i aria-hidden className="h-2 w-2 flex-none rounded-full bg-current" />}
      {children}
    </Badge>
  );

  if (!tip) return badge;

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>{badge}</TooltipTrigger>
        <TooltipContent>{tip}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

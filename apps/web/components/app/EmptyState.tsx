'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface EmptyStateProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

export function EmptyState({ title, description, action, icon, className }: EmptyStateProps) {
  return (
    <div className={cn('rounded-[10px] border border-dashed border-line2 bg-card/60 px-5 py-9 text-center text-muted-foreground', className)}>
      {icon != null && <div className="mb-2 flex justify-center text-ink3">{icon}</div>}
      <h3 className="mb-1.5 text-sm font-semibold text-foreground">{title}</h3>
      {description != null && <div className="text-[13px]">{description}</div>}
      {action != null && <div className="mt-3 flex justify-center">{action}</div>}
    </div>
  );
}

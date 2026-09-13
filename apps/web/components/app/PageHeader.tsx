'use client';

import * as React from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface PageHeaderProps {
  title: React.ReactNode;
  meta?: React.ReactNode;
  actions?: React.ReactNode;
  back?: { href: string; label: string };
  className?: string;
}

export function PageHeader({ title, meta, actions, back, className }: PageHeaderProps) {
  return (
    <div className={cn('mb-[18px] flex flex-wrap items-start justify-between gap-4', className)}>
      <div className="min-w-0">
        {back && (
          <Link href={back.href} className="mb-1 inline-flex items-center gap-1 text-[13px] text-primary hover:underline">
            <ArrowLeft size={14} />
            {back.label}
          </Link>
        )}
        <h1 className="text-2xl font-semibold leading-tight tracking-[-.01em]">{title}</h1>
        {meta != null && <div className="mt-1 text-[13px] text-muted-foreground">{meta}</div>}
      </div>
      {actions != null && (
        <div className="flex flex-wrap items-center gap-2 max-[760px]:w-full">{actions}</div>
      )}
    </div>
  );
}

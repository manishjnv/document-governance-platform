'use client';

import * as React from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

export type AlertKind = 'error' | 'warn' | 'ok' | 'info' | 'blue';

const kindClass: Record<AlertKind, string> = {
  error: 'bg-sev-crit-soft border-sev-crit text-sev-crit',
  warn: 'bg-amber-bg border-sev-med text-sev-med',
  ok: 'bg-ok-soft border-ok text-ok',
  info: 'bg-sev-info-soft border-sev-info text-sev-info',
  blue: 'bg-accent-soft border-primary text-primary',
};

const kindRole: Record<AlertKind, 'alert' | 'status'> = {
  error: 'alert',
  warn: 'status',
  ok: 'status',
  info: 'status',
  blue: 'status',
};

export interface AlertBannerProps {
  kind?: AlertKind;
  children: React.ReactNode;
  onDismiss?: () => void;
  className?: string;
}

export function AlertBanner({ kind = 'info', children, onDismiss, className }: AlertBannerProps) {
  return (
    <div
      role={kindRole[kind]}
      className={cn('flex items-start gap-2.5 rounded-lg border px-3.5 py-3 text-[13px]', kindClass[kind], className)}
    >
      <div className="min-w-0 flex-1">{children}</div>
      {onDismiss && (
        <button
          type="button"
          aria-label="Dismiss"
          onClick={onDismiss}
          className="ml-auto rounded-md p-1 hover:bg-black/5"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}

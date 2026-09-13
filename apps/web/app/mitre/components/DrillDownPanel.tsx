'use client';

import { useMemo } from 'react';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { EmptyState } from '@/components/app';
import { cn } from '@/lib/utils';
import {
  STATE_META,
  STATE_PLAIN,
  TechniqueResult,
  UseCaseItem,
  partialWhyBrief,
} from '../lib';
import { useSheetResize } from './useSheetResize';

const STATE_ORDER = ['covered', 'partial', 'not_covered', 'not_applicable'];

// Dot colors retargeted to design tokens — STATE_META.cell (lib.ts) still
// carries the pre-redesign Tailwind colors shared with other consumers.
const STATE_DOT: Record<string, string> = {
  covered: 'bg-ok',
  partial: 'bg-sev-med',
  not_covered: 'bg-sev-crit',
  not_applicable: 'bg-ink3',
};

/** Phase 14b: the reusable drill-down behind every technique count/percentage.
 * Lists techniques (state color, name, plain state phrase, partial rows get
 * their brief why inline); each row click-throughs to the 14a drawer, which
 * opens on top of this sheet. */
export function DrillDownPanel({
  title,
  subtitle,
  items,
  grouped,
  useCases,
  onSelectTechnique,
  onClose,
}: {
  /** null title = closed. */
  title: string | null;
  subtitle?: string | null;
  items: TechniqueResult[];
  /** Group rows by state (used by the %-tiles); off for single-state lists. */
  grouped?: boolean;
  useCases: UseCaseItem[];
  onSelectTechnique: (techniqueId: string) => void;
  onClose: () => void;
}) {
  const resize = useSheetResize();
  const groups = useMemo(() => {
    if (!grouped) return [[null, items] as [string | null, TechniqueResult[]]];
    return STATE_ORDER.map(
      (state) =>
        [state, items.filter((t) => t.state === state)] as [
          string | null,
          TechniqueResult[],
        ]
    ).filter(([, list]) => list.length > 0);
  }, [items, grouped]);

  return (
    <Sheet open={title !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent
        side="right"
        style={resize.style}
        grip={resize.handle}
        className="flex w-full flex-col gap-0 p-0 sm:max-w-md"
      >
        <div className="border-b border-border px-6 pb-3 pt-4">
          <SheetTitle className="text-base font-semibold">{title}</SheetTitle>
          {subtitle && <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        <div className="flex-1 space-y-4 overflow-y-auto px-6 py-4">
          {groups.map(([state, list]) => (
            <div key={state ?? 'all'}>
              {state && (
                <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-[.05em] text-ink3">
                  {STATE_META[state].label} ({list.length})
                </div>
              )}
              <div className="space-y-1">
                {list.map((t) => {
                  const why =
                    t.state === 'partial'
                      ? partialWhyBrief(useCases, t.technique_id)
                      : null;
                  return (
                    <button
                      key={`${t.domain}:${t.technique_id}`}
                      type="button"
                      onClick={() => onSelectTechnique(t.technique_id)}
                      className="flex w-full items-start gap-2 rounded-lg border border-border px-3 py-2 text-left text-[13px] transition-colors hover:bg-accent-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <span
                        aria-hidden="true"
                        className={cn(
                          'mt-1 h-2.5 w-2.5 shrink-0 rounded-full',
                          STATE_DOT[t.state] ?? 'bg-ink3'
                        )}
                      />
                      <span className="min-w-0">
                        <span className="font-medium font-mono">{t.technique_id}</span>{' '}
                        {t.name && <span>{t.name}</span>}
                        <span className="block text-xs text-muted-foreground">
                          {t.state === 'not_applicable' && t.na_reason
                            ? t.na_reason
                            : STATE_PLAIN[t.state] ?? t.state}
                          {why ? ` — ${why}` : ''}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
          {items.length === 0 && <EmptyState title="Nothing to show here." />}
        </div>
      </SheetContent>
    </Sheet>
  );
}

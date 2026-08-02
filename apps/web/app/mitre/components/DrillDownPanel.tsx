'use client';

import { useMemo } from 'react';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
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
        className="w-full overflow-y-auto p-5 sm:max-w-md"
      >
        {resize.handle}
        <SheetTitle className="text-base">{title}</SheetTitle>
        {subtitle && <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>}
        <div className="mt-4 space-y-4">
          {groups.map(([state, list]) => (
            <div key={state ?? 'all'}>
              {state && (
                <div className="mb-1.5 text-xs font-semibold text-muted-foreground">
                  {STATE_META[state].label} ({list.length})
                </div>
              )}
              <div className="space-y-1">
                {list.map((t) => {
                  const meta = STATE_META[t.state] ?? STATE_META.not_applicable;
                  const why =
                    t.state === 'partial'
                      ? partialWhyBrief(useCases, t.technique_id)
                      : null;
                  return (
                    <button
                      key={`${t.domain}:${t.technique_id}`}
                      type="button"
                      onClick={() => onSelectTechnique(t.technique_id)}
                      className="flex w-full items-start gap-2 rounded-md border px-2.5 py-1.5 text-left text-sm transition-colors hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <span
                        aria-hidden="true"
                        className={cn(
                          'mt-1 h-2.5 w-2.5 shrink-0 rounded-sm',
                          meta.cell.split(' ')[0]
                        )}
                      />
                      <span className="min-w-0">
                        <span className="font-medium">{t.technique_id}</span>{' '}
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
          {items.length === 0 && (
            <p className="text-sm text-muted-foreground">Nothing to show here.</p>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

'use client';

import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { EmptyState } from '@/components/app';
import { MAPPING_STATUS_PLAIN, SOURCE_META, UseCaseItem } from '../lib';
import { useSheetResize } from './useSheetResize';

/** Phase 14b: rule-centric drill-down — behind the parse-preview tiles and
 * the rules-by-mapping-status counts. Technique chips click through to the
 * drawer when the host page has one (results page); plain text otherwise
 * (wizard preview, where no results exist yet). */
export function RuleListPanel({
  title,
  subtitle,
  rules,
  truncated,
  onSelectTechnique,
  onClose,
}: {
  /** null title = closed. */
  title: string | null;
  subtitle?: string | null;
  rules: UseCaseItem[];
  truncated?: boolean;
  onSelectTechnique?: (techniqueId: string) => void;
  onClose: () => void;
}) {
  const resize = useSheetResize();
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
        <div className="flex-1 space-y-2 overflow-y-auto px-6 py-4">
          {rules.map((uc) => (
            <div key={uc.use_case_id} className="rounded-lg border border-border px-3 py-2 text-[13px]">
              <div className="font-medium leading-snug">{uc.name}</div>
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-muted-foreground">
                <span>{MAPPING_STATUS_PLAIN[uc.mapping_status] ?? uc.mapping_status}</span>
                <span>
                  {uc.enabled === false
                    ? 'Disabled'
                    : uc.enabled === true
                      ? 'Enabled'
                      : 'Status unknown'}
                </span>
                {uc.log_source && <span>{uc.log_source}</span>}
                <span className="text-muted-foreground/70">{uc.row_ref}</span>
              </div>
              {uc.mappings.length > 0 && (
                <div className="mt-1.5 space-y-1">
                  {/* Phase 14g: the mapping journey per technique — source in
                      plain words, confidence, and the stored rationale
                      verbatim (the evidence for the mapping). */}
                  {uc.mappings.map((m) => (
                    <div key={m.technique_id} className="flex flex-wrap items-baseline gap-x-1.5 text-[11px]">
                      {onSelectTechnique ? (
                        <button
                          type="button"
                          onClick={() => onSelectTechnique(m.technique_id)}
                          className="rounded-full border border-border bg-muted/40 px-2 py-0.5 font-mono font-medium transition-colors hover:bg-accent-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          {m.technique_id}
                        </button>
                      ) : (
                        <span className="rounded-full border border-border bg-muted/40 px-2 py-0.5 font-mono font-medium">
                          {m.technique_id}
                        </span>
                      )}
                      <span className="text-muted-foreground">
                        {(SOURCE_META[m.source] ?? SOURCE_META.ai).label}
                        {typeof m.confidence === 'number' && m.confidence < 1
                          ? ` at ${Math.round(m.confidence * 100)}% confidence`
                          : ''}
                        {m.rationale ? ` — ${m.rationale}` : ''}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          {rules.length === 0 && <EmptyState title="No rules in this group." />}
          {truncated && (
            <p className="text-[11px] text-muted-foreground">
              Showing the first 500 rules only — the XLSX export holds everything.
            </p>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

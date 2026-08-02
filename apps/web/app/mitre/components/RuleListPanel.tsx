'use client';

import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { MAPPING_STATUS_PLAIN, UseCaseItem } from '../lib';

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
  return (
    <Sheet open={title !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full overflow-y-auto p-5 sm:max-w-md">
        <SheetTitle className="text-base">{title}</SheetTitle>
        {subtitle && <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>}
        <div className="mt-4 space-y-2">
          {rules.map((uc) => (
            <div key={uc.use_case_id} className="rounded-md border p-2.5 text-sm">
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
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {uc.mappings.map((m) =>
                    onSelectTechnique ? (
                      <button
                        key={m.technique_id}
                        type="button"
                        onClick={() => onSelectTechnique(m.technique_id)}
                        className="rounded-full border bg-muted/40 px-2 py-0.5 text-[11px] font-medium transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        {m.technique_id}
                      </button>
                    ) : (
                      <span
                        key={m.technique_id}
                        className="rounded-full border bg-muted/40 px-2 py-0.5 text-[11px] font-medium"
                      >
                        {m.technique_id}
                      </span>
                    )
                  )}
                </div>
              )}
            </div>
          ))}
          {rules.length === 0 && (
            <p className="text-sm text-muted-foreground">No rules in this group.</p>
          )}
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

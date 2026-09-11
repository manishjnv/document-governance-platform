'use client';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Chain, SEVERITY_META, Severity } from '../../lib';

function SeverityChip({ severity }: { severity: Severity }) {
  const meta = SEVERITY_META[severity] ?? SEVERITY_META.info;
  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <span className={`inline-flex cursor-default items-center rounded-full border px-1.5 py-0.5 text-[11px] font-medium ${meta.chip}`}>
          {meta.label}
        </span>
      </TooltipTrigger>
      <TooltipContent className="text-xs">Chain severity (highest step)</TooltipContent>
    </Tooltip>
  );
}

/** Exploit chains tab: one card per chain with clickable step pills that
 * open the finding drawer for that step's idx. */
export function ChainsTab({ chains, onOpenFinding }: { chains: Chain[]; onOpenFinding: (idx: number) => void }) {
  if (chains.length === 0) {
    return <p className="text-sm text-muted-foreground">The scanner did not link any findings into an exploit chain.</p>;
  }
  return (
    <div className="space-y-2">
      {chains.map((chain, i) => (
        <div key={i} className="rounded-md border p-3.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium">{chain.title}</span>
            <SeverityChip severity={(chain.severity as Severity) ?? 'info'} />
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs">
            {chain.steps.map((step, si) => (
              <span key={step} className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => onOpenFinding(step)}
                  className="rounded-full border bg-muted/40 px-2 py-0.5 font-medium text-primary transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  #{step}
                </button>
                {si < chain.steps.length - 1 && <span className="text-muted-foreground">→</span>}
              </span>
            ))}
          </div>
          {chain.narrative && <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">{chain.narrative}</p>}
        </div>
      ))}
    </div>
  );
}

'use client';

import { Chip, type ChipTone } from '@/components/app';
import { Chain, SEVERITY_META, Severity } from '../../lib';

const SEV_TONE: Record<Severity, ChipTone> = {
  critical: 'crit',
  high: 'high',
  medium: 'med',
  low: 'low',
  info: 'info',
};

function SeverityChip({ severity }: { severity: Severity }) {
  const meta = SEVERITY_META[severity] ?? SEVERITY_META.info;
  return (
    <Chip tone={SEV_TONE[severity] ?? 'info'} dot tip="Chain severity (highest step)">
      {meta.label}
    </Chip>
  );
}

/** Exploit chains tab: one card per chain with clickable step pills that
 * open the finding drawer for that step's idx. No attack-graph visual ships
 * here yet — see change log. */
export function ChainsTab({ chains, onOpenFinding }: { chains: Chain[]; onOpenFinding: (idx: number) => void }) {
  if (chains.length === 0) {
    return <p className="text-sm text-muted-foreground">The scanner did not link any findings into an exploit chain.</p>;
  }
  return (
    <div className="space-y-2.5">
      {chains.map((chain, i) => (
        <div key={i} className="rounded-[10px] border border-border bg-card p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-foreground">{chain.title}</span>
            <SeverityChip severity={(chain.severity as Severity) ?? 'info'} />
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs">
            {chain.steps.map((step, si) => (
              <span key={step} className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => onOpenFinding(step)}
                  className="rounded-full border border-border bg-muted px-2 py-0.5 font-mono font-medium text-primary transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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

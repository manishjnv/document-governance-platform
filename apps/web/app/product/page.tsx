import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'Product',
  description:
    'How ScopeWise reviews a SOW or RFP: six specialist AI agents plus a deterministic rule engine, scored and explained.',
  alternates: { canonical: '/product' },
};

const AGENTS = [
  {
    name: 'Scope',
    desc: 'Checks that deliverables are concretely defined, boundaries are clear, and acceptance criteria exist for every deliverable -- the most common source of scope creep.',
  },
  {
    name: 'Delivery',
    desc: 'Looks at timelines, milestones, and dependencies for realism -- flags gaps that tend to blow up a schedule after signature.',
  },
  {
    name: 'Commercial',
    desc: 'Reviews payment terms, liability caps, and penalty clauses for anything that shifts risk onto you without you noticing.',
  },
  {
    name: 'Security',
    desc: 'Checks data-handling, access-control, and compliance language against what a project of this kind should specify.',
  },
  {
    name: 'PMO',
    desc: 'Looks at governance structure, reporting cadence, and change-control process -- the things that determine whether a project stays on track.',
  },
  {
    name: 'Legal',
    desc: 'Flags ambiguous language, indemnification terms, and termination clauses that a non-lawyer would otherwise miss.',
  },
];

export default function ProductPage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />

      <main className="max-w-4xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">How ScopeWise works</h1>
        <p className="text-lg text-muted-foreground mb-12">
          Upload a Statement of Work or RFP. ScopeWise parses it, runs six
          specialist AI agents and a deterministic rule engine against it in
          parallel, and returns a risk-scored review with every finding tied
          back to the exact clause it came from.
        </p>

        <h2 className="text-2xl font-bold mb-6">Six specialist AI reviewers</h2>
        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          {AGENTS.map((agent) => (
            <div key={agent.name} className="rounded-lg border p-5">
              <h3 className="font-semibold mb-2">{agent.name}</h3>
              <p className="text-sm text-muted-foreground">{agent.desc}</p>
            </div>
          ))}
        </div>

        <h2 className="text-2xl font-bold mb-4">Plus a rule engine</h2>
        <p className="text-muted-foreground mb-12">
          Alongside the AI agents, a set of deterministic rules checks for
          specific, well-known SOW and RFP risk patterns -- things like a
          missing liability cap, an undefined SLA, or a document type
          (SOW vs. RFP) mismatch in the language used. Rules don&apos;t hallucinate;
          they either match or they don&apos;t, which keeps the AI agents honest.
        </p>

        <h2 className="text-2xl font-bold mb-4">Versioning and fix-verification</h2>
        <p className="text-muted-foreground mb-12">
          When you upload a revised version of a document, ScopeWise links it
          to the original and re-reviews it. Findings from the previous
          version are automatically checked against the new one: resolved
          issues are marked verified, and issues that are still present stay
          open -- regardless of whether someone manually marked them &quot;fixed&quot;
          in between. The re-review is what actually verifies a fix, not a
          checkbox.
        </p>

        <div className="text-center">
          <Link
            href="/login"
            className="inline-block rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90 mb-4"
          >
            Get started
          </Link>
          <p className="text-sm text-muted-foreground">
            See it applied to{' '}
            <Link href="/use-cases/sow-review" className="underline hover:no-underline">
              SOW review
            </Link>
            .
          </p>
        </div>
      </main>

      <MarketingFooter />
    </div>
  );
}

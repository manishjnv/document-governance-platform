import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'For Procurement Teams',
  description:
    'ScopeWise for procurement: review vendor SOWs and RFP responses for commercial and scope risk before award, without a lawyer on every deal.',
  alternates: { canonical: '/solutions/for-procurement' },
};

export default function ForProcurementPage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />

      <main className="max-w-4xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">ScopeWise for procurement</h1>
        <p className="text-lg text-muted-foreground mb-12">
          Every vendor SOW or RFP response that lands on a procurement desk
          has to be checked before award -- for pricing clarity, for scope
          that actually matches what was requested, for commercial terms
          that don&apos;t quietly shift risk onto your organization. Legal
          isn&apos;t available for every deal, and a manual read-through under
          deadline pressure misses things.
        </p>

        <h2 className="text-2xl font-bold mb-4">The problem procurement runs into</h2>
        <p className="text-muted-foreground mb-6">
          A vendor&apos;s SOW looks complete on a skim: sections for scope,
          pricing, timeline, terms. What&apos;s harder to catch reading fast is
          what&apos;s <em>missing</em> or vague -- an out-of-scope hourly rate
          that isn&apos;t defined, a payment schedule with no clear milestone
          triggers, a deliverable described as &quot;software enhancements&quot;
          with no acceptance criteria attached. Those gaps don&apos;t show up as
          red flags on a first read. They show up three months into the
          engagement as a change order or a dispute.
        </p>
        <p className="text-muted-foreground mb-12">
          At the same time, procurement teams are usually running review
          cycles against a deadline -- a vendor is waiting on a signature,
          a budget window is closing -- so a review process that takes days
          because it has to route through legal for every document isn&apos;t
          sustainable at volume.
        </p>

        <h2 className="text-2xl font-bold mb-4">What ScopeWise checks</h2>
        <p className="text-muted-foreground mb-6">
          Upload the vendor&apos;s SOW or RFP response and ScopeWise runs it
          through six specialist AI agents plus a deterministic rule engine
          in parallel. For procurement, the highest-value agents are:
        </p>
        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Commercial</h3>
            <p className="text-sm text-muted-foreground">
              Reviews pricing model, payment schedule, out-of-scope rates,
              and escalation clauses -- flags anything ambiguous or
              undefined before it becomes a billing dispute.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Scope</h3>
            <p className="text-sm text-muted-foreground">
              Checks that deliverables are concretely defined with
              acceptance criteria, and flags language that signals scope
              creep -- &quot;best effort,&quot; &quot;and other related work&quot; -- so what
              you&apos;re buying is actually what&apos;s written down.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Delivery</h3>
            <p className="text-sm text-muted-foreground">
              Looks at timelines, milestones, and vendor dependencies for
              gaps -- an undefined warranty period or missing customer
              responsibilities are the kind of thing that stalls a project
              after signature.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Ambiguous language scan</h3>
            <p className="text-sm text-muted-foreground">
              A deterministic scan flags every instance of vague phrasing
              -- &quot;TBD,&quot; &quot;industry standard,&quot; &quot;as needed&quot; -- across the whole
              document, so you&apos;re not hunting for it manually.
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mb-4">Where legal still fits in</h2>
        <p className="text-muted-foreground mb-12">
          ScopeWise isn&apos;t a replacement for legal review -- it&apos;s a triage
          layer in front of it. Every finding is tied back to the exact
          clause it came from, scored by severity, so you can clear the
          low-risk vendor SOWs yourself and route only the ones with real
          commercial or legal exposure to counsel, instead of sending
          everything through the same queue.
        </p>

        <div className="text-center mb-6">
          <Link
            href="/login"
            className="inline-block rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90"
          >
            Get started
          </Link>
        </div>
        <p className="text-center text-sm text-muted-foreground">
          See how ScopeWise handles{' '}
          <Link href="/use-cases/sow-review" className="underline">
            SOW review
          </Link>{' '}
          and{' '}
          <Link href="/use-cases/rfp-review" className="underline">
            RFP review
          </Link>
          .
        </p>
      </main>

      <MarketingFooter />
    </div>
  );
}

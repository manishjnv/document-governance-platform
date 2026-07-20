import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'For Agencies & Consultancies',
  description:
    'ScopeWise for agencies and consultancies: self-check outbound SOWs before sending to a client and catch the scope gaps that turn into unpaid work later.',
  alternates: { canonical: '/solutions/for-agencies' },
};

export default function ForAgenciesPage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />

      <main className="max-w-4xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">ScopeWise for agencies and consultancies</h1>
        <p className="text-lg text-muted-foreground mb-12">
          Most SOW review tools are built for the buyer&apos;s side. But the
          document usually gets written by the agency, under deadline
          pressure to get a proposal out the door -- and it&apos;s the agency
          that eats the cost when a deliverable was described loosely
          enough that the client expects three rounds of revisions for
          free, or a dependency the client owns was never written down.
        </p>

        <h2 className="text-2xl font-bold mb-4">Scope creep starts at drafting, not delivery</h2>
        <p className="text-muted-foreground mb-6">
          By the time a project is underway and a client is asking for
          &quot;just one more small thing,&quot; the SOW has already been signed.
          Whether that request is in scope or a billable change order
          depends entirely on how precisely the original document defined
          deliverables and boundaries -- and that&apos;s decided at drafting
          time, not during delivery. A deliverable written as &quot;website
          redesign&quot; with no page count, no revision limit, and no
          acceptance criteria isn&apos;t a scope boundary at all; it&apos;s an
          open invitation.
        </p>
        <p className="text-muted-foreground mb-12">
          Agencies rarely have in-house legal reviewing every outbound SOW
          before it goes to a client, and even when they do, the review
          tends to focus on liability and payment terms -- not on whether
          the scope language itself is tight enough to prevent a dispute
          six weeks in.
        </p>

        <h2 className="text-2xl font-bold mb-4">What ScopeWise catches before you send it</h2>
        <p className="text-muted-foreground mb-6">
          Run your own draft SOW through ScopeWise before it goes to the
          client. The same six agents that review inbound documents work
          just as well on outbound ones:
        </p>
        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Scope</h3>
            <p className="text-sm text-muted-foreground">
              Flags deliverables without acceptance criteria, undefined
              scope boundaries, and scope-creep language like &quot;and other
              related work&quot; -- the exact phrasing that turns into unpaid
              extra rounds later.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Delivery</h3>
            <p className="text-sm text-muted-foreground">
              Checks that client-side dependencies and responsibilities
              are documented -- if the client owes you content, approvals,
              or access by a certain date and it isn&apos;t written down, a
              slip on their end becomes your delay.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Commercial</h3>
            <p className="text-sm text-muted-foreground">
              Confirms out-of-scope work has a defined rate and that
              payment milestones are tied to concrete triggers, so
              &quot;we&apos;ll invoice when it&apos;s done&quot; isn&apos;t left open to
              interpretation.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Ambiguous language scan</h3>
            <p className="text-sm text-muted-foreground">
              Surfaces every vague phrase in the draft -- &quot;best effort,&quot;
              &quot;as needed,&quot; &quot;TBD&quot; -- so you can tighten it before a client
              can read it as a blank check.
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mb-4">Tighter scope, fewer disputes</h2>
        <p className="text-muted-foreground mb-12">
          Every finding points to the exact clause and explains why it&apos;s a
          risk and how to fix it, so tightening a draft SOW is a fast pass,
          not a rewrite. And because ScopeWise re-checks revised versions
          against the original, you can confirm a fix actually landed
          before the document goes out the door.
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
          <Link href="/use-cases/scope-creep-prevention" className="underline">
            scope creep prevention
          </Link>
          .
        </p>
      </main>

      <MarketingFooter />
    </div>
  );
}

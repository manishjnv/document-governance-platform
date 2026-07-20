import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'SOW Review',
  description:
    'AI-powered Statement of Work review that catches vague deliverables, missing acceptance criteria, undefined liability caps, and unclear payment terms before signature.',
  alternates: { canonical: '/use-cases/sow-review' },
};

const FAQS = [
  {
    q: 'What kind of SOW problems does ScopeWise catch?',
    a: 'Vague deliverables ("software enhancements" with no specifics), missing or undefined acceptance criteria, undefined liability caps, unclear payment terms, and open-ended scope language like "including but not limited to" or "as needed" that leaves the door open to disputes later.',
  },
  {
    q: 'Does ScopeWise review RFPs too, or only SOWs?',
    a: 'Both. SOW review and RFP review use different agent logic under the hood -- an SOW defines delivered work, an RFP evaluates vendors -- but the same platform handles either document type.',
  },
  {
    q: 'Is this a substitute for legal review?',
    a: 'No. ScopeWise flags risk patterns and ambiguous language so a human reviewer knows exactly where to look, and the Legal agent output is not independently validated by a legal SME yet. It is a first-pass triage tool, not a replacement for counsel on a material contract.',
  },
  {
    q: 'How fast is a review?',
    a: 'Six specialist AI agents plus the rule engine run in parallel against the document, with each agent capped at 30 seconds, so a full review typically finishes in well under a minute.',
  },
];

export default function SowReviewPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: FAQS.map((f) => ({
      '@type': 'Question',
      name: f.q,
      acceptedAnswer: { '@type': 'Answer', text: f.a },
    })),
  };

  return (
    <div className="min-h-screen bg-background">
      {/* eslint-disable-next-line react/no-danger */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <MarketingHeader />

      <main className="max-w-4xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">SOW review, before you sign</h1>
        <p className="text-lg text-muted-foreground mb-12">
          A Statement of Work is usually read once, quickly, by someone who
          is not a lawyer and is under pressure to get a deal moving. The
          problems that actually cost money later are rarely dramatic --
          they&apos;re a missing sentence, an undefined term, or a clause that
          reads fine until the project is three months in.
        </p>

        <h2 className="text-2xl font-bold mb-4">Where SOWs commonly go wrong</h2>
        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Vague deliverables</h3>
            <p className="text-sm text-muted-foreground">
              &quot;Software enhancements&quot; or &quot;ongoing support&quot;
              with no specifics is not a deliverable, it&apos;s a placeholder.
              Without a concrete definition, either side can argue the work
              is or isn&apos;t done.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Missing acceptance criteria</h3>
            <p className="text-sm text-muted-foreground">
              If there&apos;s no defined condition for &quot;this is
              done and accepted,&quot; sign-off becomes a negotiation
              instead of a checklist -- the single most common source of
              scope disputes.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Undefined liability caps</h3>
            <p className="text-sm text-muted-foreground">
              No limitation-of-liability clause, or one with no stated cap,
              means exposure is effectively unbounded if something goes
              wrong -- often the highest-stakes gap in the whole document.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Unclear payment terms</h3>
            <p className="text-sm text-muted-foreground">
              Ambiguous payment schedules, undefined out-of-scope rates, or
              no escalation clause turn a fixed-price engagement into an
              open-ended cost conversation once work is underway.
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mb-4">How ScopeWise catches it</h2>
        <p className="text-muted-foreground mb-4">
          Three of ScopeWise&apos;s six specialist agents are built directly
          around these failure modes:
        </p>
        <ul className="list-disc pl-6 text-muted-foreground mb-6 space-y-2">
          <li>
            <strong>Scope agent</strong> -- extracts every deliverable and
            checks it against acceptance-criteria language, flags
            open-ended phrases like &quot;and other related work,&quot; and
            checks whether a change-control process is defined at all.
          </li>
          <li>
            <strong>Commercial agent</strong> -- reads pricing model,
            payment schedule, and out-of-scope rates, and flags missing or
            ambiguous escalation clauses as high-confidence findings, since
            an absent clause is unambiguous by definition.
          </li>
          <li>
            <strong>Legal agent</strong> -- checks for a limitation-of-liability
            clause and its cap, indemnification terms, IP ownership of work
            product, and termination-for-cause language with a cure period.
          </li>
        </ul>
        <p className="text-muted-foreground mb-12">
          Alongside the agents, a deterministic rule engine scans for
          well-known SOW risk patterns and a separate ambiguous-language
          scan flags weasel phrases like &quot;reasonable efforts,&quot;
          &quot;TBD,&quot; and &quot;as needed&quot; wherever they appear,
          regardless of which section they&apos;re in. Every finding is tied
          back to the exact clause it came from, with a confidence score --
          nothing is asserted without a quote.
        </p>

        <div className="rounded-lg border p-6 mb-12">
          <h2 className="text-xl font-bold mb-4">FAQ</h2>
          <div className="space-y-5">
            {FAQS.map((f) => (
              <div key={f.q}>
                <h3 className="font-semibold mb-1">{f.q}</h3>
                <p className="text-sm text-muted-foreground">{f.a}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="text-center">
          <Link
            href="/pricing"
            className="inline-block rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90 mb-4"
          >
            See pricing
          </Link>
          <p className="text-sm text-muted-foreground">
            Reviewing SOWs for procurement?{' '}
            <Link href="/solutions/for-procurement" className="underline hover:no-underline">
              See ScopeWise for procurement teams
            </Link>
            . Reviewing for legal risk?{' '}
            <Link href="/solutions/for-legal" className="underline hover:no-underline">
              See ScopeWise for legal teams
            </Link>
            .
          </p>
        </div>
      </main>

      <MarketingFooter />
    </div>
  );
}

import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'RFP Review',
  description:
    'AI-powered RFP review for procurement teams: evaluate vendor responses, check evaluation criteria and submission requirements, and catch red flags before award.',
  alternates: { canonical: '/use-cases/rfp-review' },
};

const FAQS = [
  {
    q: 'How is RFP review different from SOW review?',
    a: 'An RFP evaluates vendors rather than defining delivered work, so ScopeWise checks for different things: whether evaluation criteria are defined, whether vendor qualification requirements are clear, and whether submission format, deadline, and Q&A process are specified -- instead of deliverables and acceptance criteria.',
  },
  {
    q: 'Can ScopeWise review a vendor’s RFP response, or only the RFP itself?',
    a: 'ScopeWise reviews the document you upload -- either the RFP you’re issuing (to check it’s clear enough to get comparable responses) or a vendor’s response (to check the commercial and legal terms it proposes) -- against the same set of risk agents.',
  },
  {
    q: 'What red flags does it catch in a vendor response?',
    a: 'Undefined or ambiguous pricing, missing out-of-scope rates, uncapped liability, unclear IP ownership of deliverables, and vague qualification claims -- the same categories of risk the Commercial and Legal agents check for on any document.',
  },
  {
    q: 'Does it replace a procurement scoring process?',
    a: 'No. ScopeWise flags risk in the document text itself -- ambiguity, missing terms, red-flag clauses -- it does not score vendors against your weighted evaluation criteria. It’s a pre-award risk check that runs alongside your existing scoring process, not a replacement for it.',
  },
];

export default function RfpReviewPage() {
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
        <h1 className="text-3xl md:text-4xl font-bold mb-4">RFP review for procurement teams</h1>
        <p className="text-lg text-muted-foreground mb-12">
          An RFP is a different document than a SOW -- it&apos;s built to
          evaluate vendors, not define delivered work. That means the risk
          questions are different too: are the evaluation criteria clear
          enough to compare vendors fairly? Are qualification requirements
          specific? Is the submission process well-defined enough to avoid
          a disputed award? ScopeWise checks the document for exactly
          these gaps, on both the RFP you issue and the responses you get
          back.
        </p>

        <h2 className="text-2xl font-bold mb-4">What goes wrong in RFPs</h2>
        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Undefined evaluation criteria</h3>
            <p className="text-sm text-muted-foreground">
              If it&apos;s not clear how responses will be scored, vendors
              submit proposals optimized for the wrong thing -- and a
              losing bidder has real grounds to challenge the award.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Vague vendor qualification</h3>
            <p className="text-sm text-muted-foreground">
              Loosely defined qualification requirements let unqualified
              vendors respond, which wastes evaluation time and weakens
              your ability to disqualify a bad fit later.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Missing submission logistics</h3>
            <p className="text-sm text-muted-foreground">
              No defined submission format, deadline, or Q&amp;A window
              creates inconsistent responses that are hard to compare
              apples-to-apples.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Red flags in vendor responses</h3>
            <p className="text-sm text-muted-foreground">
              Once responses come in, the same commercial and legal risks
              from SOW review apply -- ambiguous pricing, uncapped
              liability, undefined IP ownership -- now buried inside a
              response document you didn&apos;t write.
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mb-4">How ScopeWise handles RFPs</h2>
        <p className="text-muted-foreground mb-4">
          ScopeWise treats RFP as a distinct document type, not a SOW with
          different labels. The Scope agent checks for defined evaluation
          criteria and scope of the requested proposal instead of
          deliverables; the Delivery agent checks for submission deadline,
          Q&amp;A window, and award date instead of a project timeline; the
          Commercial agent checks for budget-range disclosure and required
          pricing format instead of fixed payment terms. The rule engine
          runs an RFP-specific rule set covering evaluation criteria,
          vendor qualification, submission format and deadline, the Q&amp;A
          process, and award criteria.
        </p>
        <p className="text-muted-foreground mb-12">
          When you upload a vendor&apos;s response instead, the same
          Commercial and Legal agents that catch pricing ambiguity and
          uncapped liability in a SOW apply just as directly -- so red
          flags in a proposal surface before you sign, not after.
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
            href="/login"
            className="inline-block rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90 mb-4"
          >
            Get started
          </Link>
          <p className="text-sm text-muted-foreground">
            Running vendor evaluations?{' '}
            <Link href="/solutions/for-procurement" className="underline hover:no-underline">
              See ScopeWise for procurement teams
            </Link>
            .
          </p>
        </div>
      </main>

      <MarketingFooter />
    </div>
  );
}

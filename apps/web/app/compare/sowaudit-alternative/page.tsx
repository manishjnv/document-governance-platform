import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'ScopeSense vs SOWaudit.com',
  description:
    'How ScopeSense SOW & RFP Review compares with SOWaudit.com: scope, review approach, evidence, re-review and exports, sourced from their own site.',
  alternates: { canonical: '/compare/sowaudit-alternative' },
};

// Source for every "SOWaudit" cell: sowaudit.com (homepage), fetched 2026-09-12.
const ROWS = [
  {
    criterion: 'What it reviews',
    them: 'A single Statement of Work, uploaded as a PDF or DOCX up to 10MB, or pasted as text.',
    us: 'Both SOWs and RFPs, so a procurement team can run the same review before and after the contract is signed.',
  },
  {
    criterion: 'Review approach',
    them: 'A "3-pass forensic architecture": one pass for scope gaps, one for liability and change-control traps, one reconciling payment terms against scope language, covering 9 risk categories and 62 named checks.',
    us: 'Six specialist reviewer agents (Scope, Delivery, Commercial, Security, PMO, Legal) plus a deterministic rule engine of about 40 SOW/RFP rules, run in parallel.',
  },
  {
    criterion: 'Evidence',
    them: 'Every finding cites the exact SOW language it came from, and includes corrected contract language meant to be pasted directly into a redline.',
    us: 'Every finding is anchored to the clause and page it came from and carries a confidence score; nothing is asserted without a quote.',
  },
  {
    criterion: 'Re-review after redlines',
    them: '"One project, one credit" — a document can be reaudited after client redlines without spending another credit, with full version history kept per project.',
    us: 'A revised upload is linked to the original; every prior finding is checked again against the new text and marked verified or still open by the re-review itself.',
  },
  {
    criterion: 'Across multiple documents',
    them: 'Not stated publicly whether findings roll up across more than one project.',
    us: 'Projects and rollups group related documents (an SOW and its RFP, or a set of related SOWs) so risk is visible across the set, not just one file.',
  },
  {
    criterion: 'Report output',
    them: 'Not stated publicly whether a formatted PDF report is produced; the dashboard and redline text are the described deliverables.',
    us: 'A PDF report with an audit footer, for handing to a counterparty or filing alongside the signed contract.',
  },
];

const FAQS = [
  {
    q: 'Is this page affiliated with SOWaudit.com?',
    a: 'No. ScopeSense is not affiliated with, endorsed by, or partnered with SOWaudit. Every SOWaudit claim on this page is sourced from sowaudit.com and dated.',
  },
  {
    q: 'Does ScopeSense review RFPs as well as SOWs?',
    a: 'Yes. RFP support runs through the same six reviewer agents and rule engine as SOW review, so a procurement team can use one tool pre- and post-signature.',
  },
  {
    q: 'What happens when a document is revised after redlines?',
    a: 'Upload the new version and ScopeSense links it to the original. Every earlier finding is re-checked against the new text and marked verified or still open, not by a manual checkbox.',
  },
  {
    q: 'Does ScopeSense replace legal judgment on a contract?',
    a: 'No. It flags risk patterns and ambiguous language with evidence for a person to decide on. Severity ratings are assigned by the model and have not been validated by an external legal reviewer.',
  },
];

export default function SowauditAlternativePage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'FAQPage',
        mainEntity: FAQS.map((f) => ({
          '@type': 'Question',
          name: f.q,
          acceptedAnswer: { '@type': 'Answer', text: f.a },
        })),
      },
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://scopesense.in/' },
          { '@type': 'ListItem', position: 2, name: 'Compare', item: 'https://scopesense.in/compare' },
          {
            '@type': 'ListItem',
            position: 3,
            name: 'ScopeSense vs SOWaudit.com',
            item: 'https://scopesense.in/compare/sowaudit-alternative',
          },
        ],
      },
    ],
  };

  return (
    <div className="min-h-screen bg-background">
      {/* eslint-disable-next-line react/no-danger */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <MarketingHeader />

      <main className="max-w-4xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">
          ScopeSense vs SOWaudit.com, side by side
        </h1>
        <p className="text-lg text-muted-foreground mb-12">
          SOWaudit.com is a single-document SOW review tool. This page
          compares it with ScopeSense&apos;s SOW & RFP Review on scope,
          review approach, evidence and re-review, using only claims each
          product states about itself in public. It is not a ranking of
          which is better for every buyer.
        </p>
        <p className="text-sm text-muted-foreground mb-12">
          Every SOWaudit claim below is quoted or paraphrased from
          sowaudit.com as it read on 2026-09-12. Where its site does not
          state something publicly, the cell says so rather than guessing
          at a feature it may or may not have.
        </p>

        <h2 className="text-2xl font-bold mb-6">The comparison</h2>
        <div className="overflow-x-auto mb-12">
          <table className="w-full text-sm border-collapse">
            <caption className="sr-only">
              Comparison of SOWaudit.com and ScopeSense across scope, review
              approach, evidence, re-review, cross-document rollups and
              report output.
            </caption>
            <thead>
              <tr className="border-b">
                <th scope="col" className="text-left font-semibold py-3 pr-4">Criterion</th>
                <th scope="col" className="text-left font-semibold py-3 pr-4">SOWaudit.com</th>
                <th scope="col" className="text-left font-semibold py-3">ScopeSense</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.criterion} className="border-b align-top">
                  <td className="py-3 pr-4 font-medium">{row.criterion}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{row.them}</td>
                  <td className="py-3 text-muted-foreground">{row.us}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-bold mb-4">Where SOWaudit still wins</h2>
        <p className="text-muted-foreground mb-6">
          SOWaudit.com describes a second tool, Margin Sentinel, that runs
          after signature: it classifies ongoing project communications as
          in-scope, out-of-scope or ambiguous against the signed baseline
          and auto-drafts change-order language. ScopeSense reviews the
          documents themselves — the SOW, the RFP, the redline — and does
          not currently monitor day-to-day project communications for
          scope creep during delivery.
        </p>
        <p className="text-muted-foreground mb-6">
          Its per-project pricing ties one credit to unlimited reaudits of
          that project, which is a simple model for a team reviewing SOWs
          one at a time. Whether that fits better than a review that also
          covers RFPs and rolls findings up across projects depends on how
          a team actually works.
        </p>
        <p className="text-muted-foreground mb-12">
          ScopeSense&apos;s severity ratings are model-assigned and have not
          been validated by an external legal reviewer; that limitation
          applies to a rule-based or forensic-pass tool too, whenever
          software rather than counsel is doing the first read.
        </p>

        <h2 className="text-2xl font-bold mb-4">Where the review is measured</h2>
        <p className="text-muted-foreground mb-12">
          On our labeled SOW test set the pipeline reached 29 of 29
          ground-truth findings with zero rule-engine false positives
          (ScopeSense accuracy baseline, July 2026). That is a measure of
          recall on a labeled set, not a promise about every document; the{' '}
          <Link href="/product/sow-review" className="underline hover:no-underline">
            product page
          </Link>{' '}
          explains what the rule engine and the reviewer agents each check.
        </p>

        <h2 className="text-2xl font-bold mb-4">How to decide</h2>
        <p className="text-muted-foreground mb-12">
          If the job is reviewing one SOW at a time, before or after
          signature, and the redline-ready language SOWaudit describes is
          what a team needs, its per-project pricing may be the simpler
          fit. If the job spans an RFP stage as well as the SOW, involves
          more than one document per engagement, or needs the review
          rolled up across a set of related contracts for a procurement
          or legal team managing several vendors at once, that is the
          shape ScopeSense is built for. Neither tool decides a contract
          for you; both hand a person the evidence to decide faster.
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

        <div className="text-center mb-12">
          <Link
            href="/login"
            className="inline-block rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90 mb-4"
          >
            Start a review
          </Link>
          <p className="text-sm text-muted-foreground">
            See the{' '}
            <Link href="/product/sow-review" className="underline hover:no-underline">
              SOW & RFP Review product page
            </Link>{' '}
            or{' '}
            <Link href="/contact" className="underline hover:no-underline">
              contact us
            </Link>
            .
          </p>
        </div>

        <p className="text-xs text-muted-foreground">
          SOWaudit is a trademark of its owner. ScopeSense is not affiliated
          with SOWaudit.
        </p>
      </main>

      <MarketingFooter />
    </div>
  );
}

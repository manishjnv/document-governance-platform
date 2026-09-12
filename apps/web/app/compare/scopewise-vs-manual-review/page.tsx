import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'ScopeWise vs Manual SOW Review',
  description:
    'Side by side: what an AI-assisted SOW review changes versus a manual read, where it is faster and more consistent, and where a human reviewer still wins.',
  alternates: { canonical: '/compare/scopewise-vs-manual-review' },
};

const ROWS = [
  {
    criterion: 'Time to first read',
    manual:
      'Depends on who is free; a long SOW can sit in a queue for days before anyone opens it.',
    scopewise:
      'Six reviewer agents and the rule engine run in parallel, each agent capped at 30 seconds, so a first pass is typically back in under a minute.',
  },
  {
    criterion: 'Consistency across reviewers',
    manual:
      "Two reviewers reading the same document flag different things; the checklist lives in someone's head.",
    scopewise:
      'The same 20 SOW rules and the same six reviewer prompts run on every document, so two uploads of the same file produce the same rule findings.',
  },
  {
    criterion: 'Evidence traceability',
    manual:
      'Comments in the margin or an email summary; the reasoning is rarely tied to the exact clause.',
    scopewise:
      'Every finding quotes the clause it came from and carries a confidence score. Nothing is asserted without a quote.',
  },
  {
    criterion: 'Re-review after redlines',
    manual: 'The revised version is skimmed for the changes someone remembers asking for.',
    scopewise:
      'The new version is linked to the original and re-reviewed; each prior finding is checked again and marked verified or still open by the re-review, not by a checkbox.',
  },
  {
    criterion: 'Cost',
    manual: 'Reviewer time on every document, including the low-risk ones.',
    scopewise:
      'Quote-based pricing sized to review volume; reviewer time goes to the documents the review flags.',
  },
  {
    criterion: 'What it cannot do',
    manual: 'A good reviewer applies business context, negotiation strategy and legal judgment.',
    scopewise:
      'It flags risk patterns and ambiguous language for a human to decide on. Severity ratings are assigned by the model and are not validated by a legal specialist. It is not legal advice.',
  },
];

const FAQS = [
  {
    q: 'Does ScopeWise replace legal review?',
    a: 'No. It reads every document first, flags the clauses that need attention and why, and lets the low-risk ones move faster. Counsel still decides on the material contracts.',
  },
  {
    q: 'Will two reviewers get the same result?',
    a: 'The rule-engine findings are deterministic, so yes for those. The reviewer agents are language models and their prose can vary between runs, which is why every finding quotes its evidence so a reader can check it.',
  },
  {
    q: 'How does a re-review work?',
    a: 'Upload the revised version and ScopeWise links it to the original. Each earlier finding is re-checked against the new text and marked verified or still open.',
  },
  {
    q: 'What document types are supported?',
    a: "PDF, DOCX, DOC, XLSX, XLS and CSV, including scanned PDFs, which are OCR'd before review.",
  },
];

export default function ScopeWiseVsManualReviewPage() {
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
          {
            '@type': 'ListItem',
            position: 1,
            name: 'Home',
            item: 'https://scopewise.assessiq.in/',
          },
          {
            '@type': 'ListItem',
            position: 2,
            name: 'ScopeWise vs manual SOW review',
            item: 'https://scopewise.assessiq.in/compare/scopewise-vs-manual-review',
          },
        ],
      },
    ],
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
        <h1 className="text-3xl md:text-4xl font-bold mb-4">
          ScopeWise vs manual SOW review, side by side
        </h1>
        <p className="text-lg text-muted-foreground mb-12">
          Most Statements of Work are reviewed once, quickly, by whoever needs
          the project to start. This page compares that manual read with an
          AI-assisted review in ScopeWise on the things that decide whether a
          risk gets caught, and is honest about where a human reviewer still
          does the better job.
        </p>

        <h2 className="text-2xl font-bold mb-6">The comparison</h2>
        <div className="overflow-x-auto mb-12">
          <table className="w-full text-sm border-collapse">
            <caption className="sr-only">
              Comparison of manual SOW review and ScopeWise across time,
              consistency, evidence, re-review, cost and limitations.
            </caption>
            <thead>
              <tr className="border-b">
                <th scope="col" className="text-left font-semibold py-3 pr-4">
                  Criterion
                </th>
                <th scope="col" className="text-left font-semibold py-3 pr-4">
                  Manual review
                </th>
                <th scope="col" className="text-left font-semibold py-3">
                  ScopeWise
                </th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.criterion} className="border-b align-top">
                  <td className="py-3 pr-4 font-medium">{row.criterion}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{row.manual}</td>
                  <td className="py-3 text-muted-foreground">{row.scopewise}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h2 className="text-2xl font-bold mb-4">Where a human still wins</h2>
        <p className="text-muted-foreground mb-6">
          The model rates severity from the text of the document. Whether an
          uncapped liability clause is acceptable for this deal is a business
          judgment, and those severity ratings have not been validated by an
          external legal reviewer.
        </p>
        <p className="text-muted-foreground mb-6">
          ScopeWise is a first-pass triage tool, not legal advice. On a
          material contract, counsel reads the clauses the review flags and
          decides.
        </p>
        <p className="text-muted-foreground mb-12">
          What to push back on first, what to concede and how hard to push
          depend on bargaining position and relationship, none of which is
          contained in the document itself.
        </p>

        <h2 className="text-2xl font-bold mb-4">Where the review is measured</h2>
        <p className="text-muted-foreground mb-12">
          On our labeled SOW test set the pipeline reached 29 of 29
          ground-truth findings with zero rule-engine false positives
          (ScopeWise accuracy baseline, July 2026). That is a measure of
          recall on a labeled set, not a promise about every document; the{' '}
          <Link href="/product/sow-review" className="underline hover:no-underline">
            product page
          </Link>{' '}
          explains what the rule engine and the reviewer agents each check.
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
            Start a review
          </Link>
          <p className="text-sm text-muted-foreground">
            See the{' '}
            <Link href="/use-cases/sow-review" className="underline hover:no-underline">
              SOW review use case
            </Link>{' '}
            or{' '}
            <Link href="/contact" className="underline hover:no-underline">
              contact us
            </Link>
            .
          </p>
        </div>
      </main>

      <MarketingFooter />
    </div>
  );
}

import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'SOW & RFP Review',
  description:
    'Six specialist AI reviewers plus a deterministic rule engine score your SOW or RFP, quote the evidence for every finding and verify fixes on re-review.',
  alternates: { canonical: '/product/sow-review' },
  openGraph: { images: [{ url: '/og-sow-review.png', width: 1200, height: 630, alt: 'ScopeWise SOW & RFP Review: evidence for every finding' }] },
  twitter: { images: ['/og-sow-review.png'] },
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

const EXTRAS = [
  {
    name: 'Projects and rollups',
    desc: 'Group documents under a project and see risk roll up across versions and vendors.',
  },
  {
    name: 'OCR for scanned documents',
    desc: "Scanned PDFs are OCR'd before review, so a photographed contract works as well as a native file.",
  },
  {
    name: 'PDF report with audit footer',
    desc: 'Every exported report carries the review date, model configuration and build identifier in its footer.',
  },
  {
    name: 'Supported formats',
    desc: 'PDF, DOCX, DOC, XLSX, XLS, CSV.',
  },
];

export default function SowReviewProductPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'SoftwareApplication',
        name: 'ScopeWise SOW & RFP Review',
        applicationCategory: 'BusinessApplication',
        operatingSystem: 'Web',
        url: 'https://scopewise.assessiq.in/product/sow-review',
        description:
          'Six specialist AI reviewers plus a deterministic rule engine score your SOW or RFP, quote the evidence for every finding and verify fixes on re-review.',
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
            name: 'SOW & RFP Review',
            item: 'https://scopewise.assessiq.in/product/sow-review',
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
          SOW and RFP review with evidence for every finding
        </h1>
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

        <h2 className="text-2xl font-bold mb-4">Risk by area, evidence anchored</h2>
        <p className="text-muted-foreground mb-6">
          Each review returns an overall risk score and a Risk by Area
          breakdown across scope, delivery, commercial, security, PMO and
          legal. Every finding quotes the clause it came from and carries a
          confidence score; nothing is asserted without a quote.
        </p>
        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          {EXTRAS.map((item) => (
            <div key={item.name} className="rounded-lg border p-5">
              <h3 className="font-semibold mb-2">{item.name}</h3>
              <p className="text-sm text-muted-foreground">{item.desc}</p>
            </div>
          ))}
        </div>

        <h2 className="text-2xl font-bold mb-4">Measured on a labeled test set</h2>
        <p className="text-muted-foreground mb-12">
          On our labeled SOW test set the pipeline reached 29 of 29
          ground-truth findings with zero rule-engine false positives
          (ScopeWise accuracy baseline, July 2026). Severity ratings are
          assigned by the model and have not yet been validated by an
          external legal reviewer; ScopeWise is a first-pass triage tool,
          not legal advice.
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
            </Link>{' '}
            or{' '}
            <Link href="/use-cases/rfp-review" className="underline hover:no-underline">
              RFP review
            </Link>
            . Or{' '}
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

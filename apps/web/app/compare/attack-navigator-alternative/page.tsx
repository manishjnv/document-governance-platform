import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'ScopeWise vs ATT&CK Navigator',
  description:
    'How ScopeWise MITRE ATT&CK Coverage compares with the free ATT&CK Navigator on layer building, applicability and gaps — and why it exports a layer too.',
  alternates: { canonical: '/compare/attack-navigator-alternative' },
};

// Source for every "Navigator" cell: github.com/mitre-attack/attack-navigator
// (README) and mitre-attack.github.io/attack-navigator, fetched 2026-09-12.
const ROWS = [
  {
    criterion: 'What it is',
    them: 'A free, browser-based visualization and annotation tool for the ATT&CK matrix. Its own documentation describes it as providing "basic navigation and annotation of ATT&CK matrices."',
    us: 'A coverage-assessment pipeline: you upload a detection rule export and an environment inventory, and it produces a scored, evidenced assessment.',
  },
  {
    criterion: 'How the data gets in',
    them: 'A "layer" — the file Navigator visualizes — is either "created interactively within the Navigator or generated programmatically," including via example scripts in its repository. Either way, someone has to build it.',
    us: 'The rule export and environment inventory are ingested directly. Applicability is decided per technique, and every "not applicable" call carries a printed reason rather than a blank cell.',
  },
  {
    criterion: 'Applicability and gaps',
    them: 'Not stated publicly as a Navigator feature; it visualizes whatever scores or colors a layer file already contains.',
    us: 'A tagging ladder and detection-strength score per technique, ranked gaps, and a roadmap ordered by what closes the most exposure first.',
  },
  {
    criterion: 'Deliverables',
    them: 'The layer itself, viewed or exported inside the tool. Report generation such as PDF, XLSX or PPTX is not part of its documented feature set.',
    us: 'PDF (executive and detailed), an XLSX tracker with reference detection queries, an 18-slide PPTX, and — because Navigator is the standard viewer for this data — a Navigator layer file generated from the same assessment.',
  },
  {
    criterion: 'Cost and license',
    them: 'Free and open source, Apache License 2.0.',
    us: 'Quote-based; the assessment is the paid product, not the layer visualization.',
  },
];

const FAQS = [
  {
    q: 'Is ScopeWise trying to replace the ATT&CK Navigator?',
    a: 'No. Navigator is the standard way to view and share an ATT&CK layer, and ScopeWise exports one from every assessment so the result opens there too. They solve different problems: Navigator visualizes a layer you already have; ScopeWise builds the scored layer from your raw rule export.',
  },
  {
    q: 'Can I still open a ScopeWise assessment in the Navigator?',
    a: 'Yes. Every assessment includes a Navigator layer export alongside the PDF, XLSX and PPTX outputs.',
  },
  {
    q: 'Does ScopeWise need my raw logs or SIEM data?',
    a: 'No. It ingests your detection rule export and an environment inventory you provide; it does not require log or telemetry access.',
  },
  {
    q: 'How is a technique marked not applicable?',
    a: 'Applicability is decided per technique against your stated environment, and every N/A call is printed with the reason, so a reviewer can check the assumption rather than take a blank cell on faith.',
  },
];

export default function AttackNavigatorAlternativePage() {
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
          { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://scopewise.assessiq.in/' },
          { '@type': 'ListItem', position: 2, name: 'Compare', item: 'https://scopewise.assessiq.in/compare' },
          {
            '@type': 'ListItem',
            position: 3,
            name: 'ScopeWise vs ATT&CK Navigator',
            item: 'https://scopewise.assessiq.in/compare/attack-navigator-alternative',
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
          ScopeWise vs the MITRE ATT&CK Navigator
        </h1>
        <p className="text-lg text-muted-foreground mb-12">
          The ATT&CK Navigator is a free, open-source tool for viewing and
          annotating ATT&CK layers. ScopeWise&apos;s MITRE ATT&CK Coverage
          module is a paid assessment that builds the scored layer from a
          detection rule export and an environment inventory, then exports
          a Navigator layer as one of its outputs. The two are
          complementary, not competing: this page explains why.
        </p>
        <p className="text-sm text-muted-foreground mb-12">
          Every Navigator claim below is quoted or paraphrased from the
          project&apos;s own GitHub repository and its hosted documentation
          as they read on 2026-09-12. Where a capability is not part of
          its documented feature set, the cell says so rather than
          guessing at what a general-purpose visualization tool might also
          happen to do.
        </p>

        <h2 className="text-2xl font-bold mb-6">The comparison</h2>
        <div className="overflow-x-auto mb-12">
          <table className="w-full text-sm border-collapse">
            <caption className="sr-only">
              Comparison of the ATT&CK Navigator and ScopeWise across what
              each is, how layer data gets in, applicability and gaps,
              deliverables, and cost.
            </caption>
            <thead>
              <tr className="border-b">
                <th scope="col" className="text-left font-semibold py-3 pr-4">Criterion</th>
                <th scope="col" className="text-left font-semibold py-3 pr-4">ATT&CK Navigator</th>
                <th scope="col" className="text-left font-semibold py-3">ScopeWise</th>
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

        <h2 className="text-2xl font-bold mb-4">Where the Navigator still wins</h2>
        <p className="text-muted-foreground mb-6">
          Navigator is free, runs entirely in a browser (or self-hosted),
          and needs no data upload of any kind — a red team or blue team
          can sketch a layer by hand in minutes for a one-off exercise,
          which is more than ScopeWise&apos;s pipeline is built for.
        </p>
        <p className="text-muted-foreground mb-6">
          It is also the tool most ATT&CK content already targets: threat
          intel reports, other vendors&apos; overlays and community layers
          are commonly shared as Navigator files. That is exactly why
          ScopeWise exports one — an assessment that could only be opened
          in ScopeWise&apos;s own viewer would be less useful to a team
          already living in Navigator.
        </p>
        <p className="text-muted-foreground mb-12">
          Coverage percentages, from either tool, describe presence of a
          detection, not its efficacy against a live intrusion — that
          caveat applies to a hand-built layer as much as a generated one.
        </p>

        <h2 className="text-2xl font-bold mb-4">Where the assessment is measured</h2>
        <p className="text-muted-foreground mb-12">
          A deterministic pre-pass over the rule export cuts the AI tagging
          calls needed to reach a scored layer by 63%, with zero false
          positives introduced by that pre-pass (ScopeWise engineering
          measurement). The{' '}
          <Link href="/product/mitre-coverage" className="underline hover:no-underline">
            product page
          </Link>{' '}
          covers the full ingest-to-roadmap pipeline.
        </p>

        <h2 className="text-2xl font-bold mb-4">How to decide</h2>
        <p className="text-muted-foreground mb-12">
          If a layer already exists — from a red-team exercise, a
          vendor&apos;s threat report, or a colleague&apos;s manual
          annotation — and the job is to view or lightly edit it, the
          Navigator is free and already does that well. If the job is
          building that layer in the first place from a real rule export
          and a real environment, with applicability reasons a reviewer
          can check, ranked gaps and a roadmap, and exports beyond the
          layer file itself, that is a different job, and it is the one
          ScopeWise&apos;s assessment does. Most teams end up using both:
          ScopeWise to generate the scored layer, the Navigator to view
          and share it alongside everything else already in that format.
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
            Start an assessment
          </Link>
          <p className="text-sm text-muted-foreground">
            See the{' '}
            <Link href="/product/mitre-coverage" className="underline hover:no-underline">
              MITRE ATT&CK Coverage product page
            </Link>{' '}
            or{' '}
            <Link href="/contact" className="underline hover:no-underline">
              contact us
            </Link>
            .
          </p>
        </div>

        <p className="text-xs text-muted-foreground">
          MITRE ATT&CK and ATT&CK Navigator are trademarks of The MITRE
          Corporation. ScopeWise is not affiliated with or endorsed by
          MITRE.
        </p>
      </main>

      <MarketingFooter />
    </div>
  );
}

import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'For AppSec Consultants',
  description:
    'ScopeWise for application security consultants: run the open-source scanner on your side, upload findings only, deliver a register, exploit chains and a fix plan.',
  alternates: { canonical: '/solutions/for-appsec-consultants' },
};

const FAQS = [
  {
    q: 'Who pays for the scan?',
    a: 'The scanner bills your own OpenRouter key, and the kit shows a cost estimate before anything runs. A small repository costs a few dollars; the exact figure depends on repository size and the models you choose.',
  },
  {
    q: 'Can I upload SARIF from another tool?',
    a: 'ScopeWise ingests findings.json and SARIF produced by the supported scanner. Output from other tools is not supported in this version.',
  },
  {
    q: 'Does ScopeWise verify the findings?',
    a: "The scanner includes its own verifier pass and ScopeWise shows that verdict per finding. Final verification is your reviewer's job; the findings are triage candidates, not a completed assessment.",
  },
  {
    q: 'Can the client run the scan?',
    a: 'Not in this version. The consultant runs the kit and owns the API key and the scan authorization.',
  },
];

export default function ForAppsecConsultantsPage() {
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
          {
            '@type': 'ListItem',
            position: 2,
            name: 'Solutions',
            item: 'https://scopewise.assessiq.in/solutions/for-procurement',
          },
          {
            '@type': 'ListItem',
            position: 3,
            name: 'For AppSec Consultants',
            item: 'https://scopewise.assessiq.in/solutions/for-appsec-consultants',
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
        <h1 className="text-3xl md:text-4xl font-bold mb-4">ScopeWise for application security consultants</h1>
        <p className="text-lg text-muted-foreground mb-12">
          Scanner output is where a code review engagement starts, not
          where it ends. ScopeWise turns the findings file into the
          deliverable: a plain-language register, the exploit chains an
          attacker would follow, and the smallest set of fixes that breaks
          every chain.
        </p>

        <h2 className="text-2xl font-bold mb-4">From raw hits to a report the client can act on</h2>
        <p className="text-muted-foreground mb-6">
          A scanner run on a mid-sized repository returns dozens of raw
          hits. Most engagements then spend their time deduplicating,
          verifying, explaining each finding in language a product owner
          understands, and deciding which fix to recommend first. That
          work is the deliverable, and it is rebuilt by hand every time.
        </p>
        <p className="text-muted-foreground mb-12">
          ScopeWise ingests the findings file and does the structural
          part: severity ordering, deduplication, plain-language
          explanations, chain detection and the minimal fix set. Your
          reviewer spends the time on judgement instead of formatting.
        </p>

        <h2 className="text-2xl font-bold mb-4">How an engagement runs</h2>
        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Scan where the code lives</h3>
            <p className="text-sm text-muted-foreground">
              Download the kit, run the cost estimate, then the scan, on
              your own machine or on a jump box inside the client
              network, on your own API key. Only findings.json leaves.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Register and drawer</h3>
            <p className="text-sm text-muted-foreground">
              Severity-sorted findings with the code location, evidence,
              verifier verdict and proposed fix, in the browser.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Exploit chains and fix plan</h3>
            <p className="text-sm text-muted-foreground">
              Which findings link together and the fewest fixes that
              break every chain, ordered for the client.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">XLSX tracker and PPTX deck</h3>
            <p className="text-sm text-muted-foreground">
              An editable remediation tracker with owner, target date and
              notes columns, and a briefing deck with scan coverage,
              chains and the fix plan.
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mb-4">What the scanner is, and is not</h2>
        <p className="text-muted-foreground mb-12">
          The scanner is Visa&apos;s open-source Vulnerability Agentic
          Harness, an LLM-driven static analysis tool released under
          Apache-2.0. It threat-models the repository first and uses
          multi-agent voting, so it can find logic flaws that pattern
          rules miss. It is not deterministic, it publishes no precision
          or recall figures, and its findings are triage candidates for
          your reviewer. It never tests running systems. ScopeWise is not
          affiliated with or endorsed by Visa, Inc., never runs the
          scanner on its servers, and calls no AI model after upload.
        </p>

        <h2 className="text-2xl font-bold mb-4">Your client&apos;s code never leaves their network</h2>
        <p className="text-muted-foreground mb-12">
          The scan runs where the code is. ScopeWise receives the
          findings file only, stores it encrypted, and scopes it to your
          organization. The kit refuses working folders that contain
          dependency or build trees, so a scan cannot silently balloon in
          cost or scope.{' '}
          <Link href="/privacy" className="underline hover:no-underline">
            Read the privacy policy
          </Link>
          .
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
            <Link href="/product/code-security-review" className="underline hover:no-underline">
              Code Security Review product page
            </Link>{' '}
            or check{' '}
            <Link href="/pricing" className="underline hover:no-underline">
              pricing
            </Link>
            .
          </p>
        </div>
      </main>

      <MarketingFooter />
    </div>
  );
}

import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'Code Security Review',
  description:
    'Run the open-source scanner on your side, upload findings only. ScopeWise turns them into a plain-language register, exploit chains, an XLSX tracker and a briefing deck.',
  alternates: { canonical: '/product/code-security-review' },
};

const STEPS = [
  'Download the scan kit from ScopeWise. It installs the scanner in a sandbox on your machine.',
  'Run the estimate, then the scan, on your own OpenRouter key. The cost estimate is shown before anything is spent.',
  'Upload the findings.json zip the kit produces. No source code leaves your network.',
  'Work the register in the browser, open the drawer for any finding, review exploit chains, and export the XLSX tracker and PPTX briefing deck.',
];

const WHAT_YOU_GET = [
  {
    title: 'Findings register',
    body: 'Severity-sorted, deduplicated, each with a plain-language explanation and the code location.',
  },
  {
    title: 'Finding drawer',
    body: 'Evidence, exploitability notes, verifier verdict, proposed fix.',
  },
  {
    title: 'Exploit chains',
    body: 'Which findings an attacker links together, with the smallest set of fixes that breaks every chain.',
  },
  {
    title: 'XLSX tracker',
    body: 'Owner, target date and notes columns for the remediation plan.',
  },
  {
    title: 'PPTX briefing deck',
    body: '16 slides, scan coverage, chains and fix plan.',
  },
];

const FAQS = [
  {
    q: 'Does my code leave my network?',
    a: "No. The scanner runs where the code is, on your machine or on a jump box inside the client's network. Only the findings file is uploaded to ScopeWise.",
  },
  {
    q: 'What does a scan cost?',
    a: 'The scanner bills your own OpenRouter key. The kit runs a cost estimate before the scan starts. The NodeGoat benchmark, 63 files, cost about $4 and took 103 minutes; a large repository with dependency folders left in the scan path can take hours, which is why the kit refuses folders that contain them.',
  },
  {
    q: 'Which languages are supported?',
    a: 'Whatever the scanner can read as source code; the run manifest reports lines scanned per language, and the deck shows that breakdown so the client sees exactly what was and was not covered.',
  },
  {
    q: 'Can the client run the scan themselves?',
    a: 'Not in this version. The consultant runs the kit and owns the API key and the scan authorization. Client-run scanning is not offered.',
  },
];

export default function CodeSecurityReviewPage() {
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
        '@type': 'SoftwareApplication',
        name: 'ScopeWise Code Security Review',
        applicationCategory: 'SecurityApplication',
        operatingSystem: 'Web',
        url: 'https://scopewise.assessiq.in/product/code-security-review',
        description:
          'Turns findings from a locally-run open-source code scanner into a severity-ranked register, exploit chains, an XLSX remediation tracker, and a PPTX briefing deck.',
      },
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://scopewise.assessiq.in/' },
          {
            '@type': 'ListItem',
            position: 2,
            name: 'Products',
            item: 'https://scopewise.assessiq.in/product/sow-review',
          },
          {
            '@type': 'ListItem',
            position: 3,
            name: 'Code Security Review',
            item: 'https://scopewise.assessiq.in/product/code-security-review',
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
          AI-assisted code security review that never sees your client&apos;s code
        </h1>
        <p className="text-lg text-muted-foreground mb-12">
          The scanner runs on your machine, on your own API key. Only the
          findings file is uploaded. ScopeWise turns it into the deliverable:
          a severity-ranked register with plain-language explanations, the
          exploit chains that link findings together, and the fewest fixes
          that break every chain.
        </p>

        <h2 className="text-2xl font-bold mb-4">The problem</h2>
        <p className="text-muted-foreground mb-4">
          A manual internal penetration-test engagement typically costs
          $7,000 to $35,000 and runs for weeks (Bright Defense, penetration
          testing pricing guide). The average data
          breach now costs $4.99M globally and $11.5M in the United States
          (IBM, Cost of a Data Breach Report 2026).
        </p>
        <p className="text-muted-foreground mb-12">
          Scanner output is not a deliverable. A client cannot act on a JSON
          file of a hundred raw hits; they need the verified findings, what
          an attacker could chain them into, and where to start.
        </p>

        <h2 className="text-2xl font-bold mb-4">How it works</h2>
        <ol className="space-y-4 mb-12">
          {STEPS.map((step, i) => (
            <li key={step} className="flex gap-4">
              <span className="flex-none flex items-center justify-center h-8 w-8 rounded-full border font-semibold text-sm">
                {i + 1}
              </span>
              <p className="text-muted-foreground pt-1">{step}</p>
            </li>
          ))}
        </ol>

        <h2 className="text-2xl font-bold mb-4">What a real scan looks like</h2>
        <div className="rounded-lg border p-6 mb-12">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
            <div className="rounded-lg border p-4 text-center">
              <div className="text-xl font-bold">88 &rarr; 29</div>
              <div className="text-sm text-muted-foreground">raw hits to verified findings</div>
            </div>
            <div className="rounded-lg border p-4 text-center">
              <div className="text-xl font-bold">6</div>
              <div className="text-sm text-muted-foreground">exploit chains</div>
            </div>
            <div className="rounded-lg border p-4 text-center">
              <div className="text-xl font-bold">&asymp; $4</div>
              <div className="text-sm text-muted-foreground">model cost on OpenRouter</div>
            </div>
            <div className="rounded-lg border p-4 text-center">
              <div className="text-xl font-bold">103 min</div>
              <div className="text-sm text-muted-foreground">wall-clock on 63 files</div>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            Golden benchmark: OWASP NodeGoat (Apache-2.0), a deliberately
            vulnerable training application, scanned with the ScopeWise kit
            on 2026-09-11. A small repository costs a few dollars and takes
            30 to 120 minutes.
          </p>
        </div>

        <h2 className="text-2xl font-bold mb-4">What you get</h2>
        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          {WHAT_YOU_GET.map((item) => (
            <div key={item.title} className="rounded-lg border p-5">
              <h3 className="font-semibold mb-2">{item.title}</h3>
              <p className="text-sm text-muted-foreground">{item.body}</p>
            </div>
          ))}
        </div>

        <h2 className="text-2xl font-bold mb-4">Built on an open-source scanner</h2>
        <p className="text-muted-foreground mb-4">
          Built on Visa&apos;s open-source Vulnerability Agentic Harness
          (Apache-2.0). ScopeWise is not affiliated with or endorsed by
          Visa, Inc.
        </p>
        <p className="text-muted-foreground mb-4">
          The scanner is LLM-driven static analysis. It reads source code at
          rest, threat-models the repository first and uses multi-agent
          voting, so it can find logic flaws that pattern rules miss. It is
          not deterministic, it has no published precision or recall
          figures, and its findings are triage candidates for a human
          reviewer, not a completed security assessment. It never tests
          running systems: it is not a DAST, vulnerability-management or
          network scanner.
        </p>
        <p className="text-muted-foreground mb-12">
          ScopeWise never clones a repository or runs the scanner on its
          servers. Everything after upload is deterministic code: no AI
          model is called anywhere in this module.
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
            <Link href="/solutions/for-appsec-consultants" className="underline hover:no-underline">
              See it for AppSec consultants
            </Link>
            {' '}&middot;{' '}
            <Link href="/pricing" className="underline hover:no-underline">
              Pricing
            </Link>
          </p>
        </div>
      </main>

      <MarketingFooter />
    </div>
  );
}

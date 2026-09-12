import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'ScopeWise vs Semgrep',
  description:
    'How ScopeWise Code Security Review compares with Semgrep: CI scanning vs a consultant deliverable built on Visa’s open-source VVAH scanner.',
  alternates: { canonical: '/compare/semgrep-alternative' },
};

// Source for every "Semgrep" cell: semgrep.dev (homepage) and
// semgrep.dev/pricing, fetched 2026-09-12.
const ROWS = [
  {
    criterion: 'What it is',
    them: 'An application security platform combining static analysis (SAST), software composition analysis and secrets detection, described as pairing "deterministic static analysis with AI reasoning."',
    us: 'A deliverable layer on top of an open-source agentic scanner, turning its raw output into a client-ready register.',
  },
  {
    criterion: 'Where it runs',
    them: 'Developer tooling: CLI, CI/CD and IDEs (VS Code, JetBrains), with PR checks in GitHub, GitLab, Bitbucket and Azure — built to sit "where developers work."',
    us: 'The scanner (Visa’s open-source Vulnerability Agentic Harness) runs on the consultant’s own machine against their own OpenRouter key. Only the resulting findings.json is uploaded — the client’s code never leaves their network.',
  },
  {
    criterion: 'Fixing findings',
    them: 'Generates "tailored remediation and upgrade guidance directly in PRs and IDEs," aimed at a developer acting inline as they code.',
    us: 'No auto-fix. Findings are grouped into exploit chains, and the deliverable highlights the fewest fixes that break every chain, for a person to action.',
  },
  {
    criterion: 'Deliverable format',
    them: 'Findings delivered through PR comments and IDE integrations; a plain-language register or office-format (XLSX/PPTX) export for a non-technical stakeholder is not stated publicly.',
    us: 'A plain-language findings register, exploit chains, an XLSX tracker and a PPTX deck — built for handing to a client who did not run the scan.',
  },
  {
    criterion: 'Pricing (as of 2026-09-12)',
    them: 'Free edition for up to 10 contributors; Teams "starting at $30/month per contributor" for Code (Supply Chain and Secrets priced separately); Enterprise is custom, "contact us."',
    us: 'Quote-based, sized to the engagement; a small repository scan through the open-source harness itself typically costs a few dollars in model spend.',
  },
];

const FAQS = [
  {
    q: 'Is ScopeWise a replacement for Semgrep?',
    a: 'Not for continuous scanning. Semgrep runs in CI on every commit and blocks or comments on pull requests. ScopeWise’s Code Security Review is a point-in-time deliverable a consultant produces for a client, from a scan the consultant runs themselves.',
  },
  {
    q: 'Does ScopeWise scan code on its own servers?',
    a: 'No. Scanning happens on the Apache-2.0 open-source Vulnerability Agentic Harness, run locally by whoever is doing the review. ScopeWise only ever receives the findings.json output, not the source code.',
  },
  {
    q: 'What is the Vulnerability Agentic Harness?',
    a: 'Built on Visa’s open-source Vulnerability Agentic Harness (Apache-2.0). ScopeWise is not affiliated with or endorsed by Visa, Inc.',
  },
  {
    q: 'Does the register include exploit chains, not just a findings list?',
    a: 'Yes. Findings are linked into exploit chains where one leads to another, and the deliverable highlights the smallest set of fixes that breaks every chain rather than a flat list ranked only by severity.',
  },
];

export default function SemgrepAlternativePage() {
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
            name: 'ScopeWise vs Semgrep',
            item: 'https://scopewise.assessiq.in/compare/semgrep-alternative',
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
          ScopeWise vs Semgrep, side by side
        </h1>
        <p className="text-lg text-muted-foreground mb-6">
          Semgrep is a scanner developers run in CI, with fixes suggested
          inline in a pull request. ScopeWise&apos;s Code Security Review
          is a different kind of product: a consultant-facing deliverable
          layer built on top of an open-source agentic scanner, producing
          the plain-language register, exploit chains and office-format
          exports a client engagement needs.
        </p>
        <p className="text-sm text-muted-foreground mb-12">
          Built on Visa&apos;s open-source Vulnerability Agentic Harness
          (Apache-2.0). ScopeWise is not affiliated with or endorsed by
          Visa, Inc.
        </p>
        <p className="text-sm text-muted-foreground mb-12">
          Every Semgrep claim below is quoted or paraphrased from
          semgrep.dev and semgrep.dev/pricing as they read on 2026-09-12.
          Where its site does not state something publicly, such as
          whether it produces a plain-language register for a
          non-technical stakeholder, the cell says so rather than
          assuming it either does or doesn&apos;t.
        </p>

        <h2 className="text-2xl font-bold mb-6">The comparison</h2>
        <div className="overflow-x-auto mb-12">
          <table className="w-full text-sm border-collapse">
            <caption className="sr-only">
              Comparison of Semgrep and ScopeWise across what each is,
              where it runs, how it handles fixes, deliverable format and
              pricing.
            </caption>
            <thead>
              <tr className="border-b">
                <th scope="col" className="text-left font-semibold py-3 pr-4">Criterion</th>
                <th scope="col" className="text-left font-semibold py-3 pr-4">Semgrep</th>
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

        <h2 className="text-2xl font-bold mb-4">Where Semgrep still wins</h2>
        <p className="text-muted-foreground mb-6">
          Semgrep runs on every commit, in the pipeline a development team
          already has, and can block a pull request the moment a rule
          fires. ScopeWise&apos;s Code Security Review does not do
          continuous CI scanning or PR blocking — it is a review produced
          for a point in time, typically a client engagement, not a gate
          in a team&apos;s own build.
        </p>
        <p className="text-muted-foreground mb-6">
          Its remediation guidance lands directly in the IDE and the PR,
          in the same place a developer is already working. ScopeWise
          produces no auto-fix; the register and exploit chains are meant
          for a person to work from, not a bot to apply.
        </p>
        <p className="text-muted-foreground mb-12">
          Findings are LLM-driven static analysis without a published
          precision or recall figure; they are triage candidates for a
          reviewer to confirm, not a substitute for dynamic testing (DAST)
          or a manual penetration test.
        </p>

        <h2 className="text-2xl font-bold mb-4">Where the scan is measured</h2>
        <p className="text-muted-foreground mb-12">
          On the NodeGoat reference application, a full scan-to-deliverable
          run went from 88 raw findings to 29 verified findings across 6
          exploit chains, for roughly $4 in model spend and about 103
          minutes end to end (ScopeWise engineering measurement). The{' '}
          <Link href="/product/code-security-review" className="underline hover:no-underline">
            product page
          </Link>{' '}
          has the full pipeline and its stated caveats.
        </p>

        <h2 className="text-2xl font-bold mb-4">How to decide</h2>
        <p className="text-muted-foreground mb-12">
          If the job is catching issues on every commit, in the pipeline a
          team already runs, with a fix suggested right where a developer
          is working, that is squarely what Semgrep is built for and it
          has years of rule coverage behind it. If the job is a discrete
          engagement — an external code security review a consultancy
          delivers to a client who is not going to read a PR comment —
          the deliverable has to look different: a register in plain
          language, exploit chains showing how findings compound, and an
          XLSX or PPTX the client can act on without installing anything.
          The two are not mutually exclusive: a team can run Semgrep in
          its own CI and still commission a ScopeWise review as an
          independent, point-in-time deliverable for a client or auditor.
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
            <Link href="/product/code-security-review" className="underline hover:no-underline">
              Code Security Review product page
            </Link>{' '}
            or{' '}
            <Link href="/contact" className="underline hover:no-underline">
              contact us
            </Link>
            .
          </p>
        </div>

        <p className="text-xs text-muted-foreground">
          Semgrep is a trademark of its owner. ScopeWise is not affiliated
          with Semgrep.
        </p>
      </main>

      <MarketingFooter />
    </div>
  );
}

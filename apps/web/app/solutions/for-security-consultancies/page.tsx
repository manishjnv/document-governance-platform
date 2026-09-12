import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'For Security Consultancies & MDR',
  description:
    'ScopeWise for security consultancies and MDR providers: MITRE ATT&CK coverage assessments and code security reviews as repeatable, evidence-backed deliverables.',
  alternates: { canonical: '/solutions/for-security-consultancies' },
};

const FAQS = [
  {
    q: 'Can we white-label the deliverables?',
    a: 'The PPTX and XLSX exports are editable files, so you can add your own cover and branding before delivery. ScopeWise does not currently offer a fully white-labeled portal.',
  },
  {
    q: 'Which SIEMs are supported?',
    a: 'Microsoft Sentinel and Splunk have live read-only connectors. Any other SIEM works from a file export in xlsx, csv, pdf or docx.',
  },
  {
    q: 'Does the client need a ScopeWise account?',
    a: 'No. The consultant runs the assessment and delivers the exports. Client accounts can be added to an organization if you want them to view results directly.',
  },
  {
    q: 'Is this a substitute for a red-team or purple-team exercise?',
    a: 'No. ScopeWise measures whether detections exist and how strong they look on paper. Validating that they fire is what a purple-team exercise is for, and the gap list is a good place to start one.',
  },
];

export default function ForSecurityConsultanciesPage() {
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
            name: 'Solutions',
            item: 'https://scopewise.assessiq.in/solutions/for-procurement',
          },
          {
            '@type': 'ListItem',
            position: 3,
            name: 'For Security Consultancies & MDR',
            item: 'https://scopewise.assessiq.in/solutions/for-security-consultancies',
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
          ScopeWise for security consultancies and MDR providers
        </h1>
        <p className="text-lg text-muted-foreground mb-12">
          Two of the assessments clients ask for most, detection coverage
          and code security, are usually delivered as a spreadsheet and a
          deck built by hand for every engagement. ScopeWise generates
          both from scored data, so the second engagement costs the same
          effort as the tenth.
        </p>

        <h2 className="text-2xl font-bold mb-4">The deliverable problem</h2>
        <p className="text-muted-foreground mb-6">
          A SOC maturity or detection-coverage engagement ends with a
          mapping of the client&apos;s rules to MITRE ATT&CK, a coverage
          figure per tactic, a gap list and a roadmap. Built by hand, the
          mapping depends on who did it, the coverage figure is hard to
          defend when the client asks how not-applicable was decided, and
          none of it survives the next rule change.
        </p>
        <p className="text-muted-foreground mb-12">
          Code review engagements have the same shape: raw scanner output
          on one side, a client who needs verified findings, exploit
          chains and a fix order on the other, and a consultant in
          between turning one into the other by hand.
        </p>

        <h2 className="text-2xl font-bold mb-4">What ScopeWise produces for each engagement</h2>
        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">MITRE ATT&amp;CK coverage assessment</h3>
            <p className="text-sm text-muted-foreground mb-3">
              Upload the rule export and a one-workbook environment
              inventory; get coverage by tactic and technique, derived and
              declared not-applicable reported separately, ranked gaps and
              a 90-day roadmap.
            </p>
            <Link href="/product/mitre-coverage" className="text-sm underline hover:no-underline">
              Product details
            </Link>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Board deck, tracker and Navigator layer</h3>
            <p className="text-sm text-muted-foreground">
              The PPTX briefing deck, the XLSX tracker with reference KQL
              for Sentinel gaps, and an ATT&amp;CK Navigator layer are
              generated from the same scored data, so the numbers match
              everywhere.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Code security review</h3>
            <p className="text-sm text-muted-foreground mb-3">
              Run the open-source scanner on your side, upload findings
              only, and get a severity-ranked register, exploit chains and
              the fewest fixes that break every chain.
            </p>
            <Link href="/product/code-security-review" className="text-sm underline hover:no-underline">
              Product details
            </Link>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Repeat runs and trend</h3>
            <p className="text-sm text-muted-foreground">
              Connect Sentinel or Splunk read-only for scheduled re-runs,
              and show the client what improved and what regressed since
              the last assessment.
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mb-4">Honest by construction</h2>
        <p className="text-muted-foreground mb-12">
          Coverage numbers are computed by code, never by a language
          model. The report always shows two figures, your client&apos;s
          own rules and their tooling&apos;s native claims, and never
          merges them. Coverage means a detection exists; detection
          strength is reported alongside it. Every not-applicable
          technique carries its reason. The scanner&apos;s findings are
          triage candidates for your reviewer, not a completed
          assessment, and the page says so.
        </p>

        <h2 className="text-2xl font-bold mb-4">Your client&apos;s data</h2>
        <p className="text-muted-foreground mb-12">
          No raw logs and no source code are uploaded. Rule metadata and
          environment inventory only for the coverage assessment; the
          findings file only for the code review. SIEM credentials are
          encrypted with AES-256-GCM, write-only after saving, and every
          connection is read-only.{' '}
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
            Start an assessment
          </Link>
          <p className="text-sm text-muted-foreground">
            See{' '}
            <Link href="/product/mitre-coverage" className="underline hover:no-underline">
              MITRE ATT&amp;CK coverage
            </Link>
            ,{' '}
            <Link href="/product/code-security-review" className="underline hover:no-underline">
              code security review
            </Link>
            , or{' '}
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

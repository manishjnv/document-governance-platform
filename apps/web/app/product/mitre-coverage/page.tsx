import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'MITRE ATT&CK Coverage Assessment',
  description:
    'Upload your SIEM detection rules and environment inventory. ScopeWise maps them to MITRE ATT&CK v19.1, scores coverage by tactic, ranks gaps and builds the deck.',
  alternates: { canonical: '/product/mitre-coverage' },
};

const FAQS = [
  {
    q: 'Do you need my logs?',
    a: 'No. ScopeWise reads rule metadata and your environment inventory. It never ingests raw log data, and it never asks for credentials to do a file-based assessment.',
  },
  {
    q: 'Is it Sentinel and Splunk only?',
    a: 'Live connectors exist for Microsoft Sentinel and Splunk. Any other SIEM works through a file export in xlsx, csv, pdf or docx; the column mapping is auto-detected.',
  },
  {
    q: 'How is a technique decided to be not applicable?',
    a: 'Two ways, reported separately. Derived: the technique needs a platform your inventory says you do not run. Declared: you excluded it and gave a reason, which the report prints verbatim so the coverage figure is never misread.',
  },
  {
    q: 'Is coverage percentage the same as detection quality?',
    a: 'No. Coverage records that at least one detection exists for a technique. Detection strength is reported alongside it, and a disabled rule never scores better than partial.',
  },
];

const STEPS = [
  {
    title: 'Ingest',
    desc: 'Rules and inventory parsed, columns auto-detected.',
  },
  {
    title: 'Applicability',
    desc: 'Techniques that cannot occur on your platforms are marked not applicable, and your declared exclusions are recorded separately with their reason.',
  },
  {
    title: 'Tagging ladder',
    desc: 'Existing tags first, then deterministic keyword mapping, then AI tagging only for what remains, each with a confidence score listed under Assumptions.',
  },
  {
    title: 'Coverage and detection strength',
    desc: 'Coverage by tactic and technique, with a disabled rule counting as partial at best.',
  },
  {
    title: 'Ranked gaps and roadmap',
    desc: 'Gaps ordered by attacker prevalence and your crown jewels, grouped into a 90-day roadmap.',
  },
];

const DELIVERABLES = [
  { title: 'PDF report', desc: 'Executive and detailed versions.' },
  {
    title: 'XLSX tracker',
    desc: 'Every rule, mapping, gap and reference KQL for Sentinel gaps.',
  },
  {
    title: 'PPTX briefing deck',
    desc: '18 slides, methodology and roadmap included.',
  },
  {
    title: 'ATT&CK Navigator layer',
    desc: 'Import into the official Navigator.',
  },
  {
    title: 'Live connectors',
    desc: 'Microsoft Sentinel and Splunk, read-only, scheduled re-runs.',
  },
  {
    title: 'Trend between runs',
    desc: 'What improved and what regressed since the last assessment.',
  },
];

export default function MitreCoveragePage() {
  const ld = {
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
        name: 'ScopeWise MITRE ATT&CK Coverage',
        applicationCategory: 'SecurityApplication',
        operatingSystem: 'Web',
        url: 'https://scopewise.assessiq.in/product/mitre-coverage',
        description:
          'Maps detection rules to MITRE ATT&CK, scores coverage by tactic and technique, and generates a gap-ranked roadmap and briefing deck.',
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
            name: 'Products',
            item: 'https://scopewise.assessiq.in/product/sow-review',
          },
          {
            '@type': 'ListItem',
            position: 3,
            name: 'MITRE ATT&CK Coverage',
            item: 'https://scopewise.assessiq.in/product/mitre-coverage',
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
        dangerouslySetInnerHTML={{ __html: JSON.stringify(ld) }}
      />

      <MarketingHeader />

      <main className="max-w-4xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">
          MITRE ATT&amp;CK coverage assessment, from rule export to board deck
        </h1>
        <p className="text-lg text-muted-foreground mb-12">
          Export your detection rules, fill in a one-workbook environment
          inventory, and ScopeWise maps every rule to ATT&amp;CK, decides
          what is not applicable to your estate, scores coverage by tactic
          and hands you the gap list, the roadmap and the deck.
        </p>

        <h2 className="text-2xl font-bold mb-4">The problem</h2>
        <p className="text-muted-foreground mb-4">
          Enterprise SIEMs detect about 21% of ATT&amp;CK techniques on
          average, even though the telemetry they already ingest could cover
          more than 90% (CardinalOps, 2025 State of SIEM Detection Risk).
        </p>
        <p className="text-muted-foreground mb-12">
          Mapping hundreds of rules to techniques in a spreadsheet takes
          days, depends on who did the tagging, and is stale by the next
          rule change. The deck that follows is assembled by hand every
          time.
        </p>

        <h2 className="text-2xl font-bold mb-4">
          What you upload, and what you never upload
        </h2>
        <div className="grid sm:grid-cols-2 gap-6 mb-6">
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">You upload</h3>
            <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-2">
              <li>
                Detection-rule export (xlsx, csv, pdf or docx) with rule
                name, ATT&amp;CK tags where you have them, and the detection
                logic.
              </li>
              <li>
                Environment workbook (assets and platforms, log sources,
                security tooling, crown jewels).
              </li>
              <li>Optional scope exclusions with a reason.</li>
            </ul>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">You never upload</h3>
            <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-2">
              <li>Credentials.</li>
              <li>Raw log data.</li>
              <li>Personal data.</li>
            </ul>
          </div>
        </div>
        <div className="rounded-lg border p-5 mb-4">
          <p className="text-sm text-muted-foreground">
            We never ask for credentials, raw log data, or personal data.
            Upload rule metadata and environment inventory only. Files are
            stored encrypted; only minimal rule excerpts are sent for AI
            tagging.
          </p>
        </div>
        <p className="text-sm text-muted-foreground mb-12">
          Sentinel and Splunk can also be connected read-only instead of
          uploading a file; credentials are encrypted with AES-256-GCM and
          never returned by any endpoint.
        </p>

        <h2 className="text-2xl font-bold mb-6">How the assessment runs</h2>
        <div className="space-y-4 mb-12">
          {STEPS.map((step, i) => (
            <div key={step.title} className="flex gap-4 rounded-lg border p-5">
              <div className="flex-none w-8 h-8 rounded-full border flex items-center justify-center font-semibold text-sm">
                {i + 1}
              </div>
              <div>
                <h3 className="font-semibold mb-1">{step.title}</h3>
                <p className="text-sm text-muted-foreground">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>

        <h2 className="text-2xl font-bold mb-4">Two numbers, never one</h2>
        <p className="text-muted-foreground mb-6">
          Every report shows your own rules&apos; coverage and, separately,
          the coverage your security tooling claims natively. They are
          never merged into one figure. Coverage means a detection exists
          for a technique; it is not a measure of how well that detection
          performs.
        </p>
        <div className="grid sm:grid-cols-3 gap-6 mb-12">
          <div className="rounded-lg border p-5">
            <p className="font-semibold mb-1">ATT&amp;CK v19.1</p>
            <p className="text-sm text-muted-foreground">
              Pinned dataset, never fetched live.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <p className="font-semibold mb-1">858 techniques, 15 tactics</p>
            <p className="text-sm text-muted-foreground">
              Enterprise matrix, with ICS and Mobile gated by your inventory.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <p className="font-semibold mb-1">63% fewer AI calls</p>
            <p className="text-sm text-muted-foreground">
              Deterministic pre-pass on a realistic rule dump, with zero
              false positives on hand-verified mappings (ScopeWise internal
              test, Phase 6).
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mb-6">What you get</h2>
        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          {DELIVERABLES.map((d) => (
            <div key={d.title} className="rounded-lg border p-5">
              <h3 className="font-semibold mb-2">{d.title}</h3>
              <p className="text-sm text-muted-foreground">{d.desc}</p>
            </div>
          ))}
        </div>

        <h2 className="text-2xl font-bold mb-4">
          Replaces the spreadsheet and the deck
        </h2>
        <p className="text-muted-foreground mb-12">
          The manual version of this assessment is a tagging spreadsheet, a
          pivot table and a slide deck rebuilt for every client. ScopeWise
          generates all three from the same scored data, so the numbers in
          the deck are the numbers in the tracker.
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
            <Link
              href="/solutions/for-security-consultancies"
              className="underline hover:no-underline"
            >
              See it for security consultancies
            </Link>
            .{' '}
            <Link href="/contact" className="underline hover:no-underline">
              Contact us
            </Link>
            .
          </p>
        </div>
      </main>

      <MarketingFooter />
    </div>
  );
}

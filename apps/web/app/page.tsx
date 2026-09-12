import type { Metadata } from 'next';
import Link from 'next/link';
import {
  FileSearch,
  Crosshair,
  Bug,
  Upload,
  BadgeCheck,
  FileDown,
  Check,
} from 'lucide-react';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';
import { BLOG_POSTS } from '@/app/resources/blog/data';

export const metadata: Metadata = {
  title: 'ScopeWise: risk reviews for contracts, detections and code',
  description:
    'ScopeWise scores SOWs and RFPs, MITRE ATT&CK detection coverage, and code-scanner findings against named frameworks and produces the client-ready report.',
  alternates: { canonical: '/' },
};

const PRODUCTS = [
  {
    key: 'sow',
    href: '/product/sow-review',
    icon: FileSearch,
    iconClass: 'text-primary',
    title: 'SOW & RFP Review',
    desc: 'Six specialist AI reviewers plus a deterministic rule engine. Risk score, evidence quoted per finding, fix-verification on re-review.',
  },
  {
    key: 'mitre',
    href: '/product/mitre-coverage',
    icon: Crosshair,
    iconClass: 'text-violet-700',
    title: 'MITRE ATT&CK Coverage',
    desc: 'Upload your detection rules and environment inventory. Get coverage by tactic, ranked gaps, a 90-day roadmap, and the PPTX, XLSX and Navigator layer to present it.',
  },
  {
    key: 'codereview',
    href: '/product/code-security-review',
    icon: Bug,
    iconClass: 'text-amber-700',
    title: 'Code Security Review',
    desc: 'Run the open-source scanner on your side. Upload findings only. Get a plain-language register, exploit chains and the fewest fixes that break every chain.',
  },
] as const;

const STEPS = [
  {
    icon: Upload,
    title: 'Upload the artifact',
    desc: 'SOW or RFP, SIEM rule export plus environment workbook, or scanner findings.json.',
  },
  {
    icon: BadgeCheck,
    title: 'Scored, evidence-backed review',
    desc: 'Every finding is tied to the clause, rule or code location it came from; numbers are computed by code, not by the model.',
  },
  {
    icon: FileDown,
    title: 'Client-ready exports',
    desc: 'PDF, XLSX, PPTX, ATT&CK Navigator layer.',
  },
];

const STATS = [
  {
    number: '~9%',
    claim: 'of annual revenue lost to poor contract management',
    source: 'Source: World Commerce & Contracting (WorldCC)',
  },
  {
    number: '21%',
    claim:
      'of MITRE ATT&CK techniques detected by the average enterprise SIEM, while telemetry exists for over 90%',
    source: 'Source: CardinalOps, 2025 State of SIEM Detection Risk',
  },
  {
    number: '$7k–$35k',
    claim: 'typical cost of a manual internal penetration-test engagement',
    source: 'Source: Bright Defense, penetration testing pricing guide',
  },
];

const TRUST_BULLETS = [
  'No raw logs, no source code: you upload rule metadata, environment inventory or scanner findings only.',
  'Only minimal rule excerpts are sent for AI tagging; the model never emits a coverage number.',
  'SIEM credentials are encrypted with AES-256-GCM, write-only after saving, and every SIEM connection is read-only.',
  'AI calls go through a single provider (OpenRouter); your data is not used to train models.',
  'Data is encrypted at rest and in transit and scoped to your organization.',
];

const AUDIENCES = [
  {
    href: '/solutions/for-procurement',
    title: 'Procurement & Legal',
    desc: 'Triage vendor SOWs and RFP responses by actual risk before award.',
  },
  {
    href: '/solutions/for-security-consultancies',
    title: 'Security consultancies & MDR',
    desc: 'Detection-coverage assessments and code reviews as repeatable deliverables.',
  },
  {
    href: '/solutions/for-appsec-consultants',
    title: 'AppSec consultants',
    desc: 'Turn scanner output into a register, exploit chains and a fix plan the client can act on.',
  },
];

const RECENT_POSTS = [...BLOG_POSTS]
  .filter((p) => !p.pendingReview)
  .sort((a, b) => (a.publishedDate < b.publishedDate ? 1 : -1))
  .slice(0, 3);

export default function HomePage() {
  const baseUrl = 'https://scopewise.assessiq.in';
  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        name: 'ScopeWise',
        url: baseUrl,
        logo: `${baseUrl}/icons/icon-512.png`,
        sameAs: ['https://github.com/manishjnv/document-governance-platform'],
        contactPoint: {
          '@type': 'ContactPoint',
          contactType: 'sales',
          url: `${baseUrl}/contact`,
        },
        description:
          'ScopeWise builds evidence-based risk reviews for contracts, detection coverage and code security findings.',
      },
      {
        '@type': 'WebSite',
        name: 'ScopeWise',
        url: baseUrl,
      },
      {
        '@type': 'SoftwareApplication',
        name: 'ScopeWise SOW & RFP Review',
        applicationCategory: 'BusinessApplication',
        operatingSystem: 'Web',
        url: `${baseUrl}/product/sow-review`,
        description:
          'Six specialist AI reviewers plus a deterministic rule engine score SOWs and RFPs for risk before signature.',
      },
      {
        '@type': 'SoftwareApplication',
        name: 'ScopeWise MITRE ATT&CK Coverage',
        applicationCategory: 'SecurityApplication',
        operatingSystem: 'Web',
        url: `${baseUrl}/product/mitre-coverage`,
        description:
          'Scores detection rule sets against MITRE ATT&CK and produces a ranked gap roadmap and presentation-ready exports.',
      },
      {
        '@type': 'SoftwareApplication',
        name: 'ScopeWise Code Security Review',
        applicationCategory: 'SecurityApplication',
        operatingSystem: 'Web',
        url: `${baseUrl}/product/code-security-review`,
        description:
          'Turns open-source scanner findings into a plain-language register with exploit chains and a minimal fix plan.',
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

      <main>
        <section className="max-w-6xl mx-auto px-4 py-20 text-center">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-6">
            Evidence-based risk reviews for contracts, detections and code
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
            ScopeWise reads the SOW, the SIEM rule set or the scanner output,
            scores the gaps against named frameworks, and hands you the
            client-ready report. Deterministic numbers. AI only where it is
            honest.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link
              href="/login"
              className="rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90"
            >
              Start a review
            </Link>
            <Link
              href="#products"
              className="rounded-md border px-6 py-3 font-medium hover:bg-muted"
            >
              See the three products
            </Link>
          </div>
        </section>

        <section id="products" className="max-w-6xl mx-auto px-4 py-16">
          <div className="grid md:grid-cols-3 gap-6">
            {PRODUCTS.map((p) => (
              <Link
                key={p.key}
                href={p.href}
                data-product={p.key}
                className="rounded-lg border p-6 hover:border-primary transition-colors"
              >
                <p.icon className={`h-8 w-8 mb-4 ${p.iconClass}`} />
                <h2 className="font-semibold text-lg mb-2">{p.title}</h2>
                <p className="text-sm text-muted-foreground mb-3">{p.desc}</p>
                <span className="text-sm font-medium text-primary">Learn more &rarr;</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="border-t bg-muted/30">
          <div className="max-w-6xl mx-auto px-4 py-16">
            <h2 className="text-2xl font-bold text-center mb-10">How it works</h2>
            <div className="grid md:grid-cols-3 gap-8 text-center">
              {STEPS.map((s) => (
                <div key={s.title}>
                  <s.icon className="h-8 w-8 text-primary mx-auto mb-3" />
                  <h3 className="font-semibold mb-2">{s.title}</h3>
                  <p className="text-sm text-muted-foreground">{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="max-w-6xl mx-auto px-4 py-16">
          <h2 className="text-2xl font-bold text-center mb-2">Why consultancies use it</h2>
          <p className="text-muted-foreground text-center max-w-2xl mx-auto mb-10">
            ScopeWise replaces the spreadsheet-and-deck workflow behind each
            of these assessments. The report is generated, not assembled.
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            {STATS.map((s) => (
              <div key={s.claim} className="rounded-lg border p-6 text-center">
                <div className="text-3xl font-bold mb-2">{s.number}</div>
                <p className="mb-3">{s.claim}</p>
                <p className="text-sm text-muted-foreground">{s.source}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="border-t bg-muted/30">
          <div className="max-w-6xl mx-auto px-4 py-16">
            <h2 className="text-2xl font-bold mb-6 text-center">Your data stays yours</h2>
            <ul className="max-w-2xl mx-auto space-y-3 mb-6">
              {TRUST_BULLETS.map((b) => (
                <li key={b} className="flex items-start gap-3">
                  <Check className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                  <span className="text-muted-foreground">{b}</span>
                </li>
              ))}
            </ul>
            <p className="text-center">
              <Link href="/privacy" className="text-primary hover:underline">
                Read the privacy policy
              </Link>
            </p>
          </div>
        </section>

        <section className="max-w-6xl mx-auto px-4 py-16">
          <h2 className="text-2xl font-bold text-center mb-10">Who it is for</h2>
          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6 mb-6">
            {AUDIENCES.map((a) => (
              <Link key={a.href} href={a.href} className="rounded-lg border p-5 hover:border-primary transition-colors">
                <h3 className="font-semibold mb-1">{a.title}</h3>
                <p className="text-sm text-muted-foreground">{a.desc}</p>
              </Link>
            ))}
          </div>
          <p className="text-center text-sm text-muted-foreground">
            Also see ScopeWise for{' '}
            <Link href="/solutions/for-legal" className="underline hover:no-underline">
              legal teams
            </Link>{' '}
            and{' '}
            <Link href="/solutions/for-agencies" className="underline hover:no-underline">
              agencies
            </Link>
            .
          </p>
        </section>

        <section className="border-t bg-muted/30">
          <div className="max-w-6xl mx-auto px-4 py-16">
            <h2 className="text-2xl font-bold mb-8 text-center">From the blog</h2>
            <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6 mb-8">
              {RECENT_POSTS.map((post) => (
                <div key={post.slug}>
                  <Link
                    href={`/resources/blog/${post.slug}`}
                    className="font-semibold text-primary hover:underline"
                  >
                    {post.title}
                  </Link>
                  <p className="text-sm text-muted-foreground mt-1">{post.dek}</p>
                </div>
              ))}
            </div>
            <p className="text-center text-sm text-muted-foreground">
              <Link href="/resources/blog" className="underline hover:no-underline">
                All posts
              </Link>{' '}
              &middot;{' '}
              <Link href="/resources/glossary" className="underline hover:no-underline">
                Glossary
              </Link>
            </p>
          </div>
        </section>

        <section className="border-t">
          <div className="max-w-6xl mx-auto px-4 py-16 text-center">
            <h2 className="text-2xl font-bold mb-4">Ready to run your first review?</h2>
            <div className="flex items-center justify-center gap-4 flex-wrap mb-3">
              <Link
                href="/login"
                className="rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90"
              >
                Start a review
              </Link>
            </div>
            <Link href="/contact" className="text-sm text-primary hover:underline">
              Talk to us
            </Link>
          </div>
        </section>
      </main>

      <MarketingFooter />
    </div>
  );
}

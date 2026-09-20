import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'Compare ScopeSense',
  description:
    'ScopeSense compared with manual review and with the tools closest to each of its three products: SOWaudit, the ATT&CK Navigator and Semgrep.',
  alternates: { canonical: '/compare' },
};

const PAGES = [
  {
    href: '/compare/scopesense-vs-manual-review',
    title: 'ScopeSense vs manual SOW review',
    description:
      'What changes when a first-pass SOW read is done by six reviewer agents and a rule engine instead of one person, and where a human reviewer still wins.',
  },
  {
    href: '/compare/sowaudit-alternative',
    title: 'ScopeSense vs SOWaudit.com',
    description:
      'SOWaudit reviews one SOW at a time with a 3-pass forensic architecture. ScopeSense adds RFP support, six specialist agents, projects and rollups.',
  },
  {
    href: '/compare/attack-navigator-alternative',
    title: 'ScopeSense vs the ATT&CK Navigator',
    description:
      'The free Navigator visualizes a layer you build by hand. ScopeSense builds the scored layer from your rule export and environment, and exports one for the Navigator too.',
  },
  {
    href: '/compare/semgrep-alternative',
    title: 'ScopeSense vs Semgrep',
    description:
      'Semgrep is a CI scanner with inline auto-fix. ScopeSense is a consultant deliverable layer on Visa’s open-source VVAH scanner, with a register, exploit chains and exports.',
  },
];

export default function ComparePage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://scopesense.in/' },
      { '@type': 'ListItem', position: 2, name: 'Compare', item: 'https://scopesense.in/compare' },
    ],
  };

  return (
    <div className="min-h-screen bg-background">
      {/* eslint-disable-next-line react/no-danger */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <MarketingHeader />

      <main className="max-w-4xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">Compare ScopeSense</h1>
        <p className="text-lg text-muted-foreground mb-12">
          Every comparison below is sourced from the compared product&apos;s
          own public site and cites what it says about itself, not our
          characterization of it.
        </p>

        <div className="grid gap-6 sm:grid-cols-2">
          {PAGES.map((p) => (
            <Link
              key={p.href}
              href={p.href}
              className="block rounded-lg border p-6 hover:border-primary transition-colors"
            >
              <h2 className="font-semibold mb-2">{p.title}</h2>
              <p className="text-sm text-muted-foreground">{p.description}</p>
            </Link>
          ))}
        </div>

        <div className="text-center mt-12">
          <p className="text-sm text-muted-foreground">
            Have a specific tool in mind?{' '}
            <Link href="/contact" className="underline hover:no-underline">
              Contact us
            </Link>{' '}
            and we will tell you honestly whether ScopeSense fits.
          </p>
        </div>
      </main>

      <MarketingFooter />
    </div>
  );
}

import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';
import { TemplatesGate } from './TemplatesGate';

export const metadata: Metadata = {
  title: 'Templates',
  description:
    'Free SOW review checklist, RFP evaluation criteria worksheet and MITRE ATT&CK environment inventory template. Enter your work email to download.',
  alternates: { canonical: '/resources/templates' },
};

const TEMPLATES = [
  {
    title: 'SOW review checklist',
    desc: 'Ten-point pre-signature checklist: deliverables, acceptance criteria, exclusions, change control, dependencies, liability cap, payment terms, MSA precedence.',
    href: '/templates/sow-review-checklist.pdf',
    format: 'PDF',
  },
  {
    title: 'RFP evaluation criteria worksheet',
    desc: 'Weighted scoring sheet mirroring the FAR Part 15 structure: requirements, evaluation factors and weights, submission instructions, basis for award.',
    href: '/templates/rfp-evaluation-criteria-worksheet.xlsx',
    format: 'XLSX',
  },
  {
    title: 'MITRE ATT&CK environment inventory template',
    desc: 'The four-sheet workbook the coverage assessment reads: Assets and platforms, Log Sources, Security Tooling, Crown Jewels.',
    href: '/templates/mitre-environment-template.xlsx',
    format: 'XLSX',
  },
];

const BREADCRUMB_JSON_LD = {
  '@context': 'https://schema.org',
  '@type': 'BreadcrumbList',
  itemListElement: [
    { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://scopesense.in/' },
    { '@type': 'ListItem', position: 2, name: 'Resources', item: 'https://scopesense.in/resources/blog' },
    { '@type': 'ListItem', position: 3, name: 'Templates', item: 'https://scopesense.in/resources/templates' },
  ],
};

export default function TemplatesPage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />

      <main className="max-w-3xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">Templates and checklists</h1>
        <p className="text-lg text-muted-foreground mb-12">
          Three working files we use ourselves. Leave your name and work email and the
          download links appear below; we may follow up once about ScopeSense and nothing
          else.
        </p>

        <TemplatesGate templates={TEMPLATES} />

        <p className="text-sm text-muted-foreground mt-8">
          What we do with the form:{' '}
          <Link href="/privacy" className="underline hover:no-underline">
            see the privacy policy
          </Link>
          .
        </p>
      </main>

      <MarketingFooter />

      {/* eslint-disable-next-line react/no-danger */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(BREADCRUMB_JSON_LD) }}
      />
    </div>
  );
}

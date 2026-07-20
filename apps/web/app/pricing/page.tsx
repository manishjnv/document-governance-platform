import type { Metadata } from 'next';
import Link from 'next/link';
import { Check } from 'lucide-react';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'Pricing',
  description: 'ScopeWise pricing -- talk to us about your team\'s document review volume.',
  alternates: { canonical: '/pricing' },
};

const INCLUDED = [
  'AI review by all six specialist agents',
  'Rule-engine risk checks',
  'Document versioning and fix-verification',
  'Project-level organization and rollup reporting',
  'PDF/DOCX/DOC/XLSX/XLS/CSV document support',
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />

      <main className="max-w-3xl mx-auto px-4 py-16 text-center">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">Pricing</h1>
        <p className="text-lg text-muted-foreground mb-10">
          ScopeWise is in early access. Pricing is tailored to your team&apos;s
          document volume and review needs -- talk to us and we&apos;ll work out
          a plan that fits.
        </p>

        <div className="rounded-lg border p-8 text-left mb-10">
          <h2 className="font-semibold mb-4">Every plan includes</h2>
          <ul className="space-y-3">
            {INCLUDED.map((item) => (
              <li key={item} className="flex items-start gap-2 text-sm">
                <Check className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <Link
          href="/contact"
          className="inline-block rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90"
        >
          Contact us for pricing
        </Link>
      </main>

      <MarketingFooter />
    </div>
  );
}

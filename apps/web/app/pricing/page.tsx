import type { Metadata } from 'next';
import Link from 'next/link';
import { Check } from 'lucide-react';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'Pricing',
  description: 'ScopeWise pricing is quote-based: contract review, MITRE ATT&CK coverage assessments and code security reviews, sized to your engagement volume.',
  alternates: { canonical: '/pricing' },
};

const INCLUDED = [
  'SOW & RFP Review: six specialist agents, rule-engine checks, versioning and fix-verification, project rollups',
  'MITRE ATT&CK Coverage: file or read-only Sentinel/Splunk intake, PDF, XLSX, PPTX and Navigator exports, scheduled re-runs',
  'Code Security Review: scan kit, findings register, exploit chains, XLSX tracker and PPTX deck',
  'Organization accounts with member management',
  'Email support during early access',
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />

      <main className="max-w-3xl mx-auto px-4 py-16 text-center">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">Pricing</h1>
        <p className="text-lg text-muted-foreground mb-10">
          ScopeWise is in early access and pricing is quote-based. Tell us
          which of the three products you need and roughly how many reviews
          or assessments a month, and we will send a plan that fits.
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

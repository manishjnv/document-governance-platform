import type { Metadata } from 'next';
import { Mail } from 'lucide-react';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'Contact',
  description: 'Get in touch with the ScopeWise team.',
  alternates: { canonical: '/contact' },
};

export default function ContactPage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />

      <main className="max-w-3xl mx-auto px-4 py-16 text-center">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">Contact us</h1>
        <p className="text-lg text-muted-foreground mb-8">
          Evaluating ScopeWise for your team, or have a question about a
          review? Reach out and we'll get back to you.
        </p>
        <a
          href="mailto:hello@scopewise.assessiq.in"
          className="inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90"
        >
          <Mail className="h-4 w-4" />
          hello@scopewise.assessiq.in
        </a>
      </main>

      <MarketingFooter />
    </div>
  );
}

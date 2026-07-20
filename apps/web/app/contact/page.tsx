import type { Metadata } from 'next';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';
import { ContactForm } from './ContactForm';

export const metadata: Metadata = {
  title: 'Contact',
  description: 'Get in touch with the ScopeWise team.',
  alternates: { canonical: '/contact' },
};

export default function ContactPage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />

      <main className="max-w-md mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4 text-center">Contact us</h1>
        <p className="text-lg text-muted-foreground mb-8 text-center">
          Evaluating ScopeWise for your team, or have a question about a
          review? Send us a message and we&apos;ll get back to you.
        </p>
        <ContactForm />
      </main>

      <MarketingFooter />
    </div>
  );
}

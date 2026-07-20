import type { Metadata } from 'next';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'About',
  description: 'Why ScopeWise exists: catching contract risk before signature, not managing it after.',
  alternates: { canonical: '/about' },
};

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />

      <main className="max-w-3xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-6">About ScopeWise</h1>
        <p className="text-lg text-muted-foreground mb-6">
          A Statement of Work or RFP is usually reviewed once, quickly, by
          someone who is not a lawyer, under time pressure to get a deal
          moving. Vague scope language, missing liability caps, and undefined
          acceptance criteria slip through -- and become expensive months
          later, once a project is already underway.
        </p>
        <p className="text-lg text-muted-foreground mb-6">
          ScopeWise exists to catch that risk before signature, not manage it
          after. It's built specifically for the pre-signature review of SOWs
          and RFPs -- not as a general contract-lifecycle-management tool,
          and not as a tool for drafting or responding to an RFP. Just: is
          this document safe to sign, and if not, exactly where is the risk.
        </p>
        <p className="text-lg text-muted-foreground">
          ScopeWise is built by a small team and is in early access -- if
          you're evaluating it for your organization, we'd like to hear from
          you.
        </p>
      </main>

      <MarketingFooter />
    </div>
  );
}

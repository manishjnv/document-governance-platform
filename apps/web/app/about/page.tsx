import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'About',
  description: 'Why ScopeSense exists and what the name means: scope is what is in and out of a contract, a detection estate and a codebase.',
  alternates: { canonical: '/about' },
};

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />

      <main className="max-w-3xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-6">About ScopeSense</h1>
        <p className="text-lg text-muted-foreground mb-6">
          A Statement of Work or RFP is usually reviewed once, quickly, by
          someone who is not a lawyer, under time pressure to get a deal
          moving. Vague scope language, missing liability caps, and undefined
          acceptance criteria slip through -- and become expensive months
          later, once a project is already underway.
        </p>
        <p className="text-lg text-muted-foreground mb-6">
          ScopeSense exists to catch that risk before signature, not manage it
          after. It started as a pre-signature review of SOWs and RFPs -- not
          a contract-lifecycle-management tool, and not a tool for drafting
          or responding to an RFP. Just: is this document safe to sign, and
          if not, exactly where is the risk.
        </p>
        <p className="text-lg text-muted-foreground mb-6">
          The name stuck because the same question kept coming up in two
          other assessments consultancies deliver by hand. &quot;Scope&quot; is
          what is in and out of a contract; it is also what is in and out of a
          detection estate (which ATT&amp;CK techniques your SIEM rules cover,
          and which are out of scope for your platforms) and of a codebase
          (which files a security scan read, and which findings an attacker
          can chain). ScopeSense now covers all three:{' '}
          <Link href="/product/sow-review" className="text-primary underline hover:no-underline">SOW &amp; RFP Review</Link>,{' '}
          <Link href="/product/mitre-coverage" className="text-primary underline hover:no-underline">MITRE ATT&amp;CK Coverage</Link>{' '}
          and{' '}
          <Link href="/product/code-security-review" className="text-primary underline hover:no-underline">Code Security Review</Link>.
          In each one the numbers are computed by code, every finding quotes
          its evidence, and a model is used only where judgment is honest.
        </p>
        <p className="text-lg text-muted-foreground">
          ScopeSense is built by a small team and is in early access -- if
          you&apos;re evaluating it for your organization, we&apos;d like to hear from
          you.
        </p>
      </main>

      <MarketingFooter />
    </div>
  );
}

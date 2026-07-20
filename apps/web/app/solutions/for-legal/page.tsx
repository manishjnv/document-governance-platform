import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'For Legal Teams',
  description:
    'ScopeWise for legal and legal-ops: triage which SOWs and RFPs need full attorney review and which are low-risk, so attorney time goes where it matters.',
  alternates: { canonical: '/solutions/for-legal' },
};

export default function ForLegalPage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />

      <main className="max-w-4xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">ScopeWise for legal teams</h1>
        <p className="text-lg text-muted-foreground mb-12">
          Not every SOW that lands in the legal queue needs a full attorney
          review. Some are boilerplate variations of a template you&apos;ve
          approved a dozen times; a few have real exposure -- an uncapped
          liability clause, undefined IP ownership, termination language
          with no cure period. The problem is that from the outside, both
          look the same: a document waiting in the queue.
        </p>

        <h2 className="text-2xl font-bold mb-4">The triage problem</h2>
        <p className="text-muted-foreground mb-6">
          Legal and legal-ops teams are usually the bottleneck in a
          contract-signing process, not because attorneys are slow but
          because every document gets the same treatment regardless of
          actual risk. A low-risk vendor SOW and a high-exposure master
          services agreement both sit in the same review queue, and
          without reading each one first there&apos;s no way to prioritize.
        </p>
        <p className="text-muted-foreground mb-12">
          ScopeWise doesn&apos;t replace that judgment. It reads every document
          first, flags exactly what needs attorney eyes and why, and lets
          the rest move through faster -- so the queue is sorted by actual
          risk instead of first-in-first-out.
        </p>

        <h2 className="text-2xl font-bold mb-4">What the Legal agent checks</h2>
        <p className="text-muted-foreground mb-6">
          A dedicated Legal reviewer -- distinct from the Commercial and
          PMO agents, which cover pricing and governance separately --
          extracts and flags:
        </p>
        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Liability &amp; indemnification</h3>
            <p className="text-sm text-muted-foreground">
              Whether a limitation-of-liability clause and cap exist, and
              whether indemnification is defined -- which party covers
              whom, for what.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">IP ownership</h3>
            <p className="text-sm text-muted-foreground">
              Who owns the work product, whether background IP and
              third-party/open-source obligations are addressed, or left
              undefined.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Termination &amp; warranty</h3>
            <p className="text-sm text-muted-foreground">
              Whether termination-for-cause has a defined cure period,
              what happens to in-progress work on termination, and whether
              a warranty clause or disclaimer exists at all.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Ambiguous legal language</h3>
            <p className="text-sm text-muted-foreground">
              Phrases like &quot;reasonable efforts&quot; or &quot;as applicable&quot; are
              flagged explicitly as findings, not silently accepted --
              exactly the kind of language a fast read tends to skim past.
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mb-4">Every finding is traceable</h2>
        <p className="text-muted-foreground mb-12">
          Findings are tied back to the exact clause they came from and
          rated by severity, so an attorney reviewing a flagged document
          isn&apos;t starting from scratch -- they&apos;re starting from a specific
          list of what to look at and why. On revised versions, ScopeWise
          re-checks prior findings against the new draft automatically, so
          a &quot;fixed&quot; clause is verified, not just marked done by whoever
          uploaded it.
        </p>

        <div className="text-center mb-6">
          <Link
            href="/login"
            className="inline-block rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90"
          >
            Get started
          </Link>
        </div>
        <p className="text-center text-sm text-muted-foreground">
          See how ScopeWise handles{' '}
          <Link href="/use-cases/sow-review" className="underline">
            SOW review
          </Link>
          .
        </p>
      </main>

      <MarketingFooter />
    </div>
  );
}

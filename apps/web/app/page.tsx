import type { Metadata } from 'next';
import Link from 'next/link';
import { FileSearch, AlertTriangle, Users } from 'lucide-react';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'AI-Powered SOW & RFP Review',
  description:
    'Catch contract risk before you sign. ScopeWise reviews your Statement of Work or RFP for scope, delivery, commercial, security, PMO, and legal risk -- in minutes, not days.',
  alternates: { canonical: '/' },
};

const AGENTS = [
  { name: 'Scope', desc: 'Vague deliverables, undefined boundaries, missing acceptance criteria.' },
  { name: 'Delivery', desc: 'Unrealistic timelines, missing milestones, dependency risk.' },
  { name: 'Commercial', desc: 'Payment terms, liability caps, penalty clauses.' },
  { name: 'Security', desc: 'Data handling, access control, compliance gaps.' },
  { name: 'PMO', desc: 'Governance, reporting cadence, change-control process.' },
  { name: 'Legal', desc: 'Ambiguous language, indemnification, termination terms.' },
];

export default function HomePage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        name: 'ScopeWise',
        url: 'https://scopewise.assessiq.in',
        description: 'AI-powered review of SOWs and RFPs for scope, delivery, commercial, security, PMO, and legal risk.',
      },
      {
        '@type': 'WebSite',
        name: 'ScopeWise',
        url: 'https://scopewise.assessiq.in',
      },
      {
        '@type': 'SoftwareApplication',
        name: 'ScopeWise',
        applicationCategory: 'BusinessApplication',
        operatingSystem: 'Web',
        description: 'AI-powered review of Statements of Work and RFPs for risk before you sign.',
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
            Catch contract risk before you sign
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
            ScopeWise reviews your Statement of Work or RFP with six specialist AI
            agents and a rule engine -- flagging scope, delivery, commercial,
            security, PMO, and legal risk before you commit.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              href="/login"
              className="rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90"
            >
              Get started
            </Link>
            <Link
              href="/product"
              className="rounded-md border px-6 py-3 font-medium hover:bg-muted"
            >
              See how it works
            </Link>
          </div>
        </section>

        <section className="border-t bg-muted/30">
          <div className="max-w-6xl mx-auto px-4 py-16">
            <div className="grid md:grid-cols-3 gap-8 text-center">
              <div>
                <FileSearch className="h-8 w-8 text-primary mx-auto mb-3" />
                <h3 className="font-semibold mb-2">Upload your document</h3>
                <p className="text-sm text-muted-foreground">
                  PDF, DOCX, DOC, XLSX, XLS, or CSV -- any SOW or RFP you&apos;ve received or are about to send.
                </p>
              </div>
              <div>
                <AlertTriangle className="h-8 w-8 text-primary mx-auto mb-3" />
                <h3 className="font-semibold mb-2">Get a risk-scored review</h3>
                <p className="text-sm text-muted-foreground">
                  Six AI agents plus a rule engine flag ambiguous language, missing
                  clauses, and scope gaps -- with a risk score per finding.
                </p>
              </div>
              <div>
                <Users className="h-8 w-8 text-primary mx-auto mb-3" />
                <h3 className="font-semibold mb-2">Fix it before you sign</h3>
                <p className="text-sm text-muted-foreground">
                  Re-review a new version and see exactly which issues were
                  resolved, which are new, and which are still open.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="max-w-6xl mx-auto px-4 py-16">
          <h2 className="text-2xl font-bold text-center mb-2">Six specialist AI reviewers</h2>
          <p className="text-muted-foreground text-center mb-10">
            Each one looks for a different category of risk, backed by a deterministic rule engine.
          </p>
          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6">
            {AGENTS.map((agent) => (
              <div key={agent.name} className="rounded-lg border p-5">
                <h3 className="font-semibold mb-1">{agent.name}</h3>
                <p className="text-sm text-muted-foreground">{agent.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="border-t bg-muted/30">
          <div className="max-w-6xl mx-auto px-4 py-16 text-center">
            <h2 className="text-2xl font-bold mb-6">Reviewing a specific document type?</h2>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <Link href="/use-cases/sow-review" className="rounded-md border px-6 py-3 font-medium hover:bg-muted">
                SOW review
              </Link>
              <Link href="/use-cases/rfp-review" className="rounded-md border px-6 py-3 font-medium hover:bg-muted">
                RFP review
              </Link>
              <Link href="/use-cases/scope-creep-prevention" className="rounded-md border px-6 py-3 font-medium hover:bg-muted">
                Scope creep prevention
              </Link>
            </div>
          </div>
        </section>

        <section className="border-t">
          <div className="max-w-6xl mx-auto px-4 py-16 text-center">
            <h2 className="text-2xl font-bold mb-4">Ready to review your first document?</h2>
            <Link
              href="/login"
              className="inline-block rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90"
            >
              Get started
            </Link>
          </div>
        </section>
      </main>

      <MarketingFooter />
    </div>
  );
}

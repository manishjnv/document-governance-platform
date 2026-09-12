import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'Terms of Service',
  description:
    'The terms for using ScopeWise: your account, your content, acceptable use, AI-generated output, and liability.',
  alternates: { canonical: '/terms' },
};

const SECTIONS = [
  {
    h: 'The service',
    body: [
      'ScopeWise is a web service that reviews documents, detection-rule exports and code-scanner findings you choose to upload, and produces reports.',
      'It is provided by the ScopeWise team on an early-access basis; features may change.',
    ],
  },
  {
    h: 'Your account',
    body: [
      'You sign in with Google or an emailed one-time code.',
      "You are responsible for activity under your account and for keeping your organization's membership current.",
    ],
  },
  {
    h: 'Your content',
    body: [
      'You keep all rights to what you upload and to the reports generated from it.',
      'You confirm you are authorised to upload it (including any client material) and to run any scan whose output you upload.',
      <>
        We process it only to provide the service, as described in the{' '}
        <Link href="/privacy" className="text-primary hover:underline">
          Privacy Policy
        </Link>
        .
      </>,
    ],
  },
  {
    h: 'Acceptable use',
    body: [
      'No uploading of malware.',
      "No attempts to access other organizations' data.",
      'No use of the service to break the law or a contract you are bound by.',
      'No automated scraping of the service.',
    ],
  },
  {
    h: 'AI-generated output',
    body: [
      'Reviews, severity ratings, coverage figures and findings are produced by software, in part by AI models, and can be wrong or incomplete.',
      'They are decision support for a qualified reviewer.',
      'ScopeWise does not provide legal, security-assurance or audit opinions, and no output is a certification of any kind.',
    ],
  },
  {
    h: 'Availability and changes',
    body: [
      'Early-access service, provided as is, with no uptime commitment.',
      'We may change or withdraw features with notice where practical.',
    ],
  },
  {
    h: 'Liability',
    body: [
      'To the extent permitted by law, ScopeWise is not liable for indirect or consequential loss.',
      'Total liability is limited to the fees you paid in the twelve months before the claim.',
    ],
  },
  {
    h: 'Termination',
    body: [
      'You can stop using the service and ask for deletion at any time via the contact page.',
      'We may suspend accounts that breach these terms.',
    ],
  },
  {
    h: 'Contact',
    body: [
      <>
        Questions about these terms via the{' '}
        <Link href="/contact" className="text-primary hover:underline">
          contact page
        </Link>
        .
      </>,
    ],
  },
];

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />
      <main className="max-w-4xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-2">Terms of Service</h1>
        <p className="text-sm text-muted-foreground mb-10">Last updated: 12 September 2026</p>
        {SECTIONS.map((s) => (
          <section key={s.h} className="mb-10">
            <h2 className="text-2xl font-bold mb-3">{s.h}</h2>
            <ul className="space-y-2">
              {s.body.map((line, i) => (
                <li key={i} className="text-muted-foreground">
                  {line}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </main>
      <MarketingFooter />
    </div>
  );
}

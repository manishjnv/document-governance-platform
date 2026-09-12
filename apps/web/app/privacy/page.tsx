import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description:
    'How ScopeWise collects, uses, stores, and protects your data — accounts, uploaded documents, and SIEM connection data.',
  alternates: { canonical: '/privacy' },
};

const SECTIONS = [
  {
    h: 'What we collect',
    body: [
      'Account data: your email address and name, provided when you sign in with Google or verify an email one-time code. We do not store passwords.',
      'Documents you upload for review (SOWs, RFPs, and similar), and the review results generated from them.',
      'For the MITRE coverage module: detection-rule metadata pulled read-only from your SIEM (rule names, descriptions, queries, ATT&CK tags, enabled state) or uploaded as a file, and optional environment inventory you provide.',
      'Basic usage analytics (page views, feature usage) via standard analytics cookies.',
    ],
  },
  {
    h: 'How we use it',
    body: [
      'To run the reviews and assessments you request, produce reports, and show your history and trends back to you.',
      'Document and rule text is analyzed by AI models. Only the minimal excerpts needed for analysis are sent to our AI processing provider; your data is not used to train models by us.',
      'We do not sell your data. We do not share it with third parties except the processors needed to run the service (hosting, AI analysis).',
    ],
  },
  {
    h: 'How it is protected',
    body: [
      'Data is stored encrypted at rest and transmitted over TLS.',
      'SIEM credentials (client secrets, API tokens) are encrypted with AES-256-GCM, are write-only after saving (no endpoint ever returns them), and all SIEM access is read-only.',
      'Access to your data is scoped to your organization account.',
    ],
  },
  {
    h: 'Retention and deletion',
    body: [
      'Your documents, assessments, and account data are retained while your account is active so your history and trends keep working.',
      'You can delete individual documents and assessments in the product. To delete your account and all associated data, contact us and we will complete the deletion.',
    ],
  },
  {
    h: 'Contact',
    body: [
      'For any privacy question, data-deletion request, or complaint, reach us via the contact page. We respond to verified requests without undue delay.',
    ],
  },
];

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />
      <main className="max-w-4xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-2">Privacy Policy</h1>
        <p className="text-sm text-muted-foreground mb-10">Last updated: 20 August 2026</p>
        <p className="text-lg text-muted-foreground mb-10">
          ScopeWise reviews the documents and detection rules you choose to
          share with it. This page explains what we collect, why, how it is
          protected, and how to get it removed. The short version: we collect
          only what the product needs, we never sell it, and SIEM access is
          always read-only.
        </p>
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
        <p className="text-muted-foreground">
          Questions?{' '}
          <Link href="/contact" className="text-primary hover:underline">
            Contact us
          </Link>
          .
        </p>
      </main>
      <MarketingFooter />
    </div>
  );
}

import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';
import { GLOSSARY_ENTRIES } from './data';

export const metadata: Metadata = {
  title: 'Glossary',
  description:
    'Plain-English definitions of SOW, RFP, and contract terms -- liability caps, indemnification, scope creep, MSAs, and more.',
  alternates: { canonical: '/resources/glossary' },
};

export default function GlossaryIndexPage() {
  const entries = [...GLOSSARY_ENTRIES].sort((a, b) => a.term.localeCompare(b.term));

  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />

      <main className="max-w-3xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">Glossary</h1>
        <p className="text-lg text-muted-foreground mb-12">
          Plain-English definitions of the SOW, RFP, and contract terms that
          matter most when reviewing a document before you sign.
        </p>

        <ul className="space-y-6">
          {entries.map((entry) => (
            <li key={entry.slug} className="rounded-lg border p-5">
              <h2 className="font-semibold mb-1">
                <Link href={`/resources/glossary/${entry.slug}`} className="hover:underline">
                  {entry.term}
                </Link>
              </h2>
              <p className="text-sm text-muted-foreground">{entry.shortDefinition}</p>
            </li>
          ))}
        </ul>
      </main>

      <MarketingFooter />
    </div>
  );
}

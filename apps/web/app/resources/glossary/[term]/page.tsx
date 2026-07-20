import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';
import { GLOSSARY_ENTRIES, getGlossaryEntry } from '../data';

type Params = { term: string };

export function generateStaticParams() {
  return GLOSSARY_ENTRIES.map((entry) => ({ term: entry.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { term } = await params;
  const entry = getGlossaryEntry(term);
  if (!entry) return {};

  return {
    title: entry.term,
    description: entry.shortDefinition,
    alternates: { canonical: `/resources/glossary/${entry.slug}` },
  };
}

export default async function GlossaryTermPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { term } = await params;
  const entry = getGlossaryEntry(term);
  if (!entry) notFound();

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'DefinedTerm',
    name: entry.term,
    description: entry.shortDefinition,
    inDefinedTermSet: 'ScopeWise Glossary',
  };

  return (
    <div className="min-h-screen bg-background">
      {/* eslint-disable-next-line react/no-danger */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <MarketingHeader />

      <main className="max-w-3xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">{entry.term}</h1>
        <p className="text-lg text-muted-foreground mb-8">{entry.shortDefinition}</p>

        <div className="space-y-6 mb-12">
          {entry.body.map((paragraph, i) => (
            <p key={i} className="text-muted-foreground">
              {paragraph}
            </p>
          ))}
        </div>

        <div className="rounded-lg border p-5 mb-12">
          <h2 className="font-semibold mb-2">Related reading</h2>
          <Link href={entry.relatedUseCase} className="text-primary hover:underline">
            See how ScopeWise reviews this in practice &rarr;
          </Link>
        </div>

        <div className="text-center">
          <Link
            href="/login"
            className="inline-block rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90"
          >
            Get started
          </Link>
        </div>
      </main>

      <MarketingFooter />
    </div>
  );
}

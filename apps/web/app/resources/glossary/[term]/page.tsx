import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { CheckCircle2, Sparkles } from 'lucide-react';
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

/** Bolds each keyword's occurrences in `text` so scanning readers can spot
 * the defined terms at a glance, without storing markup in the content. */
function highlight(text: string, keywords: string[]): ReactNode {
  if (keywords.length === 0) return text;
  const pattern = new RegExp(`(${keywords.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
  const parts = text.split(pattern);
  return parts.map((part, i) =>
    keywords.some((k) => k.toLowerCase() === part.toLowerCase()) ? (
      <strong key={i}>{part}</strong>
    ) : (
      part
    )
  );
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

        <div className="rounded-lg border bg-muted/30 p-5 mb-10">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
            In short
          </h2>
          <ul className="space-y-2">
            {entry.keyPoints.map((point, i) => (
              <li key={i} className="flex gap-2 text-sm">
                <CheckCircle2 className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <span>{highlight(point, entry.keywords)}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-8 mb-10">
          {entry.sections.map((section) => (
            <div key={section.heading}>
              <h2 className="text-xl font-bold mb-2">{section.heading}</h2>
              <p className="text-muted-foreground">{highlight(section.body, entry.keywords)}</p>
            </div>
          ))}
        </div>

        <div className="rounded-lg border border-primary/30 bg-primary/5 p-5 mb-12">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h2 className="font-semibold">How ScopeWise checks this</h2>
          </div>
          <p className="text-sm text-muted-foreground">{entry.scopewiseNote}</p>
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

import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Sparkles } from 'lucide-react';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';
import { BLOG_POSTS, getBlogPost } from '../data';

type Params = { slug: string };

export function generateStaticParams() {
  return BLOG_POSTS.map((post) => ({ slug: post.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = getBlogPost(slug);
  if (!post) return {};

  return {
    title: post.title,
    description: post.dek,
    alternates: { canonical: `/resources/blog/${post.slug}` },
  };
}

/** Renders `[text](/path)` markdown-style links as real Link components,
 * so body content can cross-link to the glossary without storing JSX. */
function renderContent(text: string): ReactNode {
  const pattern = /\[([^\]]+)\]\(([^)]+)\)/g;
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));
    parts.push(
      <Link key={i++} href={match[2]} className="text-primary hover:underline">
        {match[1]}
      </Link>
    );
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts;
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { slug } = await params;
  const post = getBlogPost(slug);
  if (!post) notFound();

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: post.title,
    description: post.dek,
    datePublished: post.publishedDate,
    author: { '@type': 'Organization', name: 'ScopeWise' },
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
        <h1 className="text-3xl md:text-4xl font-bold mb-4">{post.title}</h1>
        <p className="text-lg text-muted-foreground mb-4">{post.dek}</p>
        <p className="text-sm text-muted-foreground mb-10">
          {new Date(post.publishedDate).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}{' '}
          &middot; By {post.author}
        </p>

        <div className="space-y-8 mb-10">
          {post.body.map((section) => (
            <div key={section.heading}>
              <h2 className="text-xl font-bold mb-2">{section.heading}</h2>
              <p className="text-muted-foreground">{renderContent(section.content)}</p>
            </div>
          ))}
        </div>

        <div className="rounded-lg border border-primary/30 bg-primary/5 p-5 mb-12">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h2 className="font-semibold">Related reading</h2>
          </div>
          <Link href={post.relatedUseCase} className="text-primary hover:underline">
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

import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';
import { BLOG_POSTS } from './data';

export const metadata: Metadata = {
  title: 'Blog',
  description:
    'Practical guides on SOW review, RFP evaluation, and contract risk -- liability caps, scope creep, acceptance criteria, and more.',
  alternates: { canonical: '/resources/blog' },
};

export default function BlogIndexPage() {
  const posts = [...BLOG_POSTS].sort((a, b) => b.publishedDate.localeCompare(a.publishedDate));

  return (
    <div className="min-h-screen bg-background">
      <MarketingHeader />

      <main className="max-w-3xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">Blog</h1>
        <p className="text-lg text-muted-foreground mb-12">
          Practical guides on reviewing SOWs and RFPs before you sign --
          scope, commercial terms, and the clauses that carry the most risk.
        </p>

        <ul className="space-y-6">
          {posts.map((post) => (
            <li key={post.slug} className="rounded-lg border p-5">
              <h2 className="font-semibold mb-1">
                <Link href={`/resources/blog/${post.slug}`} className="hover:underline">
                  {post.title}
                </Link>
              </h2>
              <p className="text-sm text-muted-foreground mb-2">{post.dek}</p>
              <p className="text-xs text-muted-foreground">
                {new Date(post.publishedDate).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            </li>
          ))}
        </ul>
      </main>

      <MarketingFooter />
    </div>
  );
}

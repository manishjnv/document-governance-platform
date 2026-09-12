import type { Metadata } from 'next';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';
import { BLOG_POSTS } from './data';
import { BlogList } from './BlogList';

export const metadata: Metadata = {
  title: 'Blog',
  description:
    'Practical guides on SOW and RFP review, MITRE ATT&CK detection coverage and code security review deliverables.',
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
          Practical guides on contract review, MITRE ATT&amp;CK detection
          coverage and code security deliverables. Filter by product.
        </p>

        <BlogList posts={posts} />
      </main>

      <MarketingFooter />
    </div>
  );
}

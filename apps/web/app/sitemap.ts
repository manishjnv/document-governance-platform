import type { MetadataRoute } from 'next';
import { GLOSSARY_ENTRIES } from './resources/glossary/data';
import { BLOG_POSTS } from './resources/blog/data';

const BASE_URL = 'https://scopesense.in';

// Real last-modified date per static page. Bump the date when the page's
// content changes; never use new Date() here (Google ignores a lastmod that
// moves on every build).
const PAGES: Record<string, string> = {
  '': '2026-09-12',
  '/product/sow-review': '2026-09-12',
  '/product/mitre-coverage': '2026-09-12',
  '/product/code-security-review': '2026-09-12',
  '/about': '2026-07-20',
  '/contact': '2026-07-20',
  '/privacy': '2026-08-20',
  '/terms': '2026-09-12',
  '/use-cases/sow-review': '2026-07-20',
  '/use-cases/rfp-review': '2026-07-20',
  '/use-cases/scope-creep-prevention': '2026-07-20',
  '/solutions/for-procurement': '2026-07-20',
  '/solutions/for-legal': '2026-07-20',
  '/solutions/for-agencies': '2026-07-20',
  '/solutions/for-security-consultancies': '2026-09-12',
  '/solutions/for-appsec-consultants': '2026-09-12',
  '/resources/glossary': '2026-07-20',
  '/resources/templates': '2026-09-12',
  '/compare': '2026-09-12',
  '/compare/scopesense-vs-manual-review': '2026-09-12',
  '/compare/sowaudit-alternative': '2026-09-12',
  '/compare/attack-navigator-alternative': '2026-09-12',
  '/compare/semgrep-alternative': '2026-09-12',
  '/resources/blog': '2026-08-01',
};

const GLOSSARY_LAST_MODIFIED = '2026-07-20';

export default function sitemap(): MetadataRoute.Sitemap {
  const pages = Object.entries(PAGES).map(([route, date]) => ({
    url: `${BASE_URL}${route}`,
    lastModified: new Date(date),
    changeFrequency: 'monthly' as const,
    priority: route === '' ? 1 : 0.7,
  }));

  const glossary = GLOSSARY_ENTRIES.map((entry) => ({
    url: `${BASE_URL}/resources/glossary/${entry.slug}`,
    lastModified: new Date(GLOSSARY_LAST_MODIFIED),
    changeFrequency: 'monthly' as const,
    priority: 0.6,
  }));

  // pendingReview posts are live at their URL but noindexed pending
  // editorial sign-off -- keep them out of the sitemap until reviewed.
  const blog = BLOG_POSTS.filter((post) => !post.pendingReview).map((post) => ({
    url: `${BASE_URL}/resources/blog/${post.slug}`,
    lastModified: new Date(post.publishedDate),
    changeFrequency: 'monthly' as const,
    priority: 0.6,
  }));

  return [...pages, ...glossary, ...blog];
}

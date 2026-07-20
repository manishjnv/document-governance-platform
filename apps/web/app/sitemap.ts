import type { MetadataRoute } from 'next';
import { GLOSSARY_ENTRIES } from './resources/glossary/data';
import { BLOG_POSTS } from './resources/blog/data';

const BASE_URL = 'https://scopewise.assessiq.in';

export default function sitemap(): MetadataRoute.Sitemap {
  const routes = [
    '',
    '/product',
    '/about',
    '/contact',
    '/use-cases/sow-review',
    '/use-cases/rfp-review',
    '/use-cases/scope-creep-prevention',
    '/solutions/for-procurement',
    '/solutions/for-legal',
    '/solutions/for-agencies',
    '/resources/glossary',
    ...GLOSSARY_ENTRIES.map((entry) => `/resources/glossary/${entry.slug}`),
    '/resources/blog',
    ...BLOG_POSTS.map((post) => `/resources/blog/${post.slug}`),
  ];

  return routes.map((route) => ({
    url: `${BASE_URL}${route}`,
    lastModified: new Date(),
    changeFrequency: 'monthly',
    priority: route === '' ? 1 : 0.7,
  }));
}

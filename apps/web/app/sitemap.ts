import type { MetadataRoute } from 'next';
import { GLOSSARY_ENTRIES } from './resources/glossary/data';

const BASE_URL = 'https://scopewise.assessiq.in';

export default function sitemap(): MetadataRoute.Sitemap {
  const routes = [
    '',
    '/product',
    '/pricing',
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
  ];

  return routes.map((route) => ({
    url: `${BASE_URL}${route}`,
    lastModified: new Date(),
    changeFrequency: 'monthly',
    priority: route === '' ? 1 : 0.7,
  }));
}

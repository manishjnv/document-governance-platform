import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        // Authenticated app shells only -- every marketing page stays crawlable.
        disallow: [
          '/dashboard',
          '/upload',
          '/search',
          '/results',
          '/projects',
          '/versions',
          '/mitre',
          '/codereview',
          '/admin',
          '/login',
          '/api',
        ],
      },
    ],
    sitemap: 'https://scopewise.assessiq.in/sitemap.xml',
  };
}

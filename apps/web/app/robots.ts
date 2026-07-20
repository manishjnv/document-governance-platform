import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/dashboard', '/upload', '/search', '/results', '/projects', '/versions', '/pricing'],
      },
    ],
    sitemap: 'https://scopewise.assessiq.in/sitemap.xml',
  };
}

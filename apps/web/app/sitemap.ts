import type { MetadataRoute } from 'next';

const BASE_URL = 'https://scopewise.assessiq.in';

export default function sitemap(): MetadataRoute.Sitemap {
  const routes = ['', '/product', '/pricing', '/about', '/contact'];

  return routes.map((route) => ({
    url: `${BASE_URL}${route}`,
    lastModified: new Date(),
    changeFrequency: 'monthly',
    priority: route === '' ? 1 : 0.7,
  }));
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  swcMinify: true,
  compiler: {
    removeConsole: process.env.NODE_ENV === "production",
  },
  env: {
    // Empty string is a valid, deliberate value: relative "/api/..." URLs make the
    // browser call the API on whatever host the page was served from, so the same
    // build works on scopewise.assessiq.in and scopesense.in during the dual-run
    // (2026-09-12). Only an UNSET variable falls back to the local dev API.
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  },
  async redirects() {
    return [
      { source: '/product', destination: '/product/sow-review', permanent: true },
      // product renamed ScopeWise -> ScopeSense (2026-09-20): keep the old comparison URL working
      { source: '/compare/scopewise-vs-manual-review', destination: '/compare/scopesense-vs-manual-review', permanent: true },
    ];
  },
};

module.exports = nextConfig;

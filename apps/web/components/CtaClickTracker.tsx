'use client';

import { useEffect } from 'react';

/** Fires a GA4 event for every click on a /login link (the "Get started" /
 * "Sign in" CTAs across all marketing pages). One global listener instead of
 * per-page onClick wiring, so new CTAs are tracked automatically.
 * No-ops when GA isn't configured (gtag undefined). */
export function CtaClickTracker() {
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const anchor = (e.target as HTMLElement).closest?.('a[href="/login"]');
      if (!anchor) return;
      const gtag = (window as any).gtag;
      if (typeof gtag !== 'function') return;
      gtag('event', 'cta_click', {
        cta_text: (anchor.textContent || '').trim().slice(0, 50),
        page_path: window.location.pathname,
      });
    };
    document.addEventListener('click', handler, true);
    return () => document.removeEventListener('click', handler, true);
  }, []);

  return null;
}

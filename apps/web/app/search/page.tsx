/**
 * T-703: Global search moved onto /dashboard (SOW Review). This route is kept
 * only so old bookmarks/links to /search don't 404 -- redirect straight there.
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SearchPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard');
  }, [router]);

  return null;
}

'use client';

import { useEffect } from 'react';
import './globals.css';

// A tab opened before a deploy still holds the old build's page; its next
// client-side navigation asks for JS chunks the new build no longer has and
// Next shows "Application error: a client-side exception" (2026-09-23, after
// uploading a scan right after a deploy). Reload once to pick up the new build.
const RELOAD_KEY = 'chunk-reload-at';

function isStaleBuild(error: Error): boolean {
  return (
    error?.name === 'ChunkLoadError' ||
    /Loading (CSS )?chunk [\w-]+ failed|Failed to fetch dynamically imported module/i.test(error?.message ?? '')
  );
}

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    if (!isStaleBuild(error)) return;
    try {
      const last = Number(sessionStorage.getItem(RELOAD_KEY) || 0);
      if (Date.now() - last < 30_000) return; // already reloaded just now: show the message instead of looping
      sessionStorage.setItem(RELOAD_KEY, String(Date.now()));
    } catch {
      // storage blocked: reloading once is still the right call
    }
    window.location.reload();
  }, [error]);

  return (
    <html lang="en">
      <body className="flex min-h-[100dvh] items-center justify-center bg-background p-4 text-foreground">
        <div className="max-w-sm space-y-3 text-center">
          <h1 className="text-lg font-semibold">Something went wrong</h1>
          <p className="text-[13px] text-muted-foreground">
            {isStaleBuild(error)
              ? 'ScopeSense was just updated. Reload to get the new version.'
              : 'The page hit an unexpected error. Reloading usually fixes it.'}
          </p>
          <div className="flex justify-center gap-2">
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="h-9 rounded-lg bg-primary px-3 text-[13px] font-medium text-primary-foreground hover:opacity-90"
            >
              Reload
            </button>
            <button
              type="button"
              onClick={() => reset()}
              className="h-9 rounded-lg border border-border px-3 text-[13px] font-medium hover:bg-muted"
            >
              Try again
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}

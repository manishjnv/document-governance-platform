'use client';

import { useCallback, useEffect, useState } from 'react';

const MIN_WIDTH = 360;
const STORAGE_KEY = 'mitre-sheet-width';

/** Mouse-resizable right-side sheets: drag the left edge to give the panel
 * more room; the width is shared and remembered across all mitre panels.
 * Keyboard: arrow keys on the handle resize in 40px steps. On phones the
 * sheet is already full-width, so the stored width is clamped to 100vw. */
export function useSheetResize() {
  const [width, setWidth] = useState<number | null>(null);

  useEffect(() => {
    const stored = Number(localStorage.getItem(STORAGE_KEY));
    if (stored >= MIN_WIDTH) setWidth(stored);
  }, []);

  const apply = useCallback((next: number) => {
    const clamped = Math.round(
      Math.min(Math.max(next, MIN_WIDTH), window.innerWidth * 0.95)
    );
    setWidth(clamped);
    localStorage.setItem(STORAGE_KEY, String(clamped));
  }, []);

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      const onMove = (ev: PointerEvent) => apply(window.innerWidth - ev.clientX);
      const onUp = () => window.removeEventListener('pointermove', onMove);
      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', onUp, { once: true });
    },
    [apply]
  );

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
      e.preventDefault();
      const current = width ?? MIN_WIDTH + 88; // sm:max-w-md default
      apply(current + (e.key === 'ArrowLeft' ? 40 : -40));
    },
    [width, apply]
  );

  // min() keeps phones full-width regardless of the stored desktop width.
  const style = width
    ? { width: `min(${width}px, 100vw)`, maxWidth: `min(${width}px, 100vw)` }
    : undefined;

  const handle = (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize panel (drag, or use arrow keys)"
      tabIndex={0}
      onPointerDown={onPointerDown}
      onKeyDown={onKeyDown}
      className="absolute left-0 top-0 z-10 h-full w-2 cursor-ew-resize touch-none hover:bg-primary/20 focus-visible:bg-primary/20 focus-visible:outline-none"
    />
  );

  return { style, handle };
}

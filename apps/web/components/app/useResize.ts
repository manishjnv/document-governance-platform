'use client';

import {
  useCallback,
  useEffect,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from 'react';

export type ResizeEdge = 'left' | 'right';

/** Shared drag-to-resize hook for a panel with a grip on one edge.
 * Pointer capture means no window listeners are needed. Persists to
 * localStorage under `storageKey`, read once on mount. */
export function useResize(opts: {
  storageKey: string;
  min: number;
  max?: number | (() => number);
  edge?: ResizeEdge;
  step?: number;
  fallback?: number;
}) {
  const { storageKey, min, max, edge = 'left', step = 40, fallback } = opts;
  const [width, setWidthState] = useState<number | null>(null);
  const [resizing, setResizing] = useState(false);

  const getMax = useCallback(() => {
    if (typeof max === 'function') return max();
    if (typeof max === 'number') return max;
    return window.innerWidth * 0.95;
  }, [max]);

  useEffect(() => {
    const stored = Number(localStorage.getItem(storageKey));
    if (stored >= min) setWidthState(Math.round(Math.min(stored, getMax())));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setWidth = useCallback(
    (next: number) => {
      const clamped = Math.round(Math.min(Math.max(next, min), getMax()));
      setWidthState(clamped);
      try {
        localStorage.setItem(storageKey, String(clamped));
      } catch {
        // ignore (private window / storage disabled)
      }
    },
    [min, getMax, storageKey]
  );

  const onPointerDown = useCallback((e: ReactPointerEvent<HTMLElement>) => {
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    setResizing(true);
  }, []);

  const onPointerMove = useCallback(
    (e: ReactPointerEvent<HTMLElement>) => {
      if (!resizing) return;
      const next = edge === 'right' ? e.clientX : window.innerWidth - e.clientX;
      setWidth(next);
    },
    [resizing, edge, setWidth]
  );

  const onPointerUp = useCallback((e: ReactPointerEvent<HTMLElement>) => {
    e.currentTarget.releasePointerCapture(e.pointerId);
    setResizing(false);
  }, []);

  const onKeyDown = useCallback(
    (e: ReactKeyboardEvent<HTMLElement>) => {
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
      e.preventDefault();
      const base = width ?? fallback ?? min;
      const grows = edge === 'left' ? e.key === 'ArrowLeft' : e.key === 'ArrowRight';
      setWidth(base + (grows ? step : -step));
    },
    [width, fallback, min, edge, step, setWidth]
  );

  return {
    width,
    setWidth,
    resizing,
    gripProps: {
      role: 'separator' as const,
      'aria-orientation': 'vertical' as const,
      tabIndex: 0,
      onPointerDown,
      onPointerMove,
      onPointerUp,
      onPointerCancel: onPointerUp,
      onKeyDown,
    },
  };
}

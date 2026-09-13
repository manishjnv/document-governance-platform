'use client';

import { useResize } from '@/components/app/useResize';

const MIN_WIDTH = 360;
const STORAGE_KEY = 'mitre-sheet-width';

/** Mouse-resizable right-side sheets: drag the left edge to give the panel
 * more room; the width is shared and remembered across all mitre panels.
 * Keyboard: arrow keys on the handle resize in 40px steps. On phones the
 * sheet is already full-width, so the stored width is clamped to 100vw. */
export function useSheetResize() {
  const { width, gripProps } = useResize({
    storageKey: STORAGE_KEY,
    min: MIN_WIDTH,
    edge: 'left',
    fallback: 448, // MIN_WIDTH + 88 (sm:max-w-md default)
  });

  // min() keeps phones full-width regardless of the stored desktop width.
  const style = width
    ? { width: `min(${width}px, 100vw)`, maxWidth: `min(${width}px, 100vw)` }
    : undefined;

  const handle = (
    <div
      {...gripProps}
      aria-label="Resize panel (drag, or use arrow keys)"
      title="Drag to resize"
      className="absolute left-0 top-0 z-10 flex h-full w-3 cursor-ew-resize touch-none items-center justify-center focus-visible:outline-none group"
    >
      <i className="block h-10 w-1 rounded-full bg-line2 transition-colors duration-150 ease-app group-hover:bg-primary group-focus-visible:bg-primary" />
    </div>
  );

  return { style, handle };
}

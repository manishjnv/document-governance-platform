# App redesign canvas — 2026-09-12 (design only, no code)

Live, editable canvas: https://claude.ai/code/artifact/f3b280f4-455c-49e4-9d4e-33cf9088d7fa

- `gen.py` generates the artboards from one shared shell. Tokens are lifted from
  `apps/web/app/globals.css`, `tailwind.config.ts` and `components/ui/*` (Inter,
  #0066CC primary, #0F1729 foreground, 8px radius, 224px sidebar, 40/36px controls).
- `*.dc.html` are the artboards (Direction A hi-fi: SOW dashboard = `Main`,
  `MitreList`, `MitreDetail`, `CodeReviewDetail`, `Admin`; low-fi alternates
  `DirectionB` dark ops console, `DirectionC` airy editorial).
- `canvas.json` is the layout plus the critique sticky notes per screen.
- `*.png` are 1440×900 renders of four artboards for quick reference.

Regenerate: `python gen.py` then reseed the canvas from the design skill.

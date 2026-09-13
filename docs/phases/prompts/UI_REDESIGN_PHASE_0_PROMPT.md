# Kickoff prompt — UI redesign Phase 0 (theme, fonts, shell, login)

Copy everything below the line into a fresh Claude Code session at `E:\code\DocumentGovernancePlatform`.

---

Build Phase 0 of `docs/planning/UI_REDESIGN_BUILD_PLAN.md`. Read it fully first, then `CLAUDE.md`,
`docs/design/complete-app-2026-09-12/README.md` and `dc.py` (token values and primitives), and the
`Main`, `Login` and `Dashboard` artboards: render them with
`python harness.py --screens Main,Login,Dashboard --out <scratch>` and again with `--phone`
(`DC_RUNTIME` per the README), then Read the PNGs. Design canvas for reference:
https://claude.ai/code/artifact/9f120be7-d49e-4651-8ea3-a103269b5e24

Deliver, in this order, one commit each:

1. `scripts/generate_app_theme.py` producing `apps/web/app/app-theme.css` from the `TOKENS` dict in
   `dc.py` (hex to HSL for the shadcn variables, plus the semantic ones in plan §2), the Tailwind
   additions (`fontFamily.app` and `fontFamily.mono`, `colors.ink3`, `colors.sev.*`, `colors.ok`,
   `colors.violet`, `transitionTimingFunction.app`), IBM Plex Sans and Mono via `next/font/google`
   in `app/layout.tsx`, and `.app-theme font-app` on the `AppShell` root and the login root.
   Marketing pages must be visually unchanged: `/` still Inter, old `:root` variables untouched.
   Also `docs/design/complete-app-2026-09-12/check_app_labels.py` per plan §6.2.
   Route both scripts to Tier 2 (`node C:/Users/manis/bin/or.mjs dsf`), reviewed by Opus.
2. `AppShell` restyle plus `components/app/useResize.ts` (moved from `useSheetResize`, re-exported
   there) per plan §2.4, and the shadcn primitive tweaks per §2.6. One Sonnet builder.
3. Login page per the `Login` artboard, every step and message kept. Same builder, after step 2.

Gates before each commit: `npx tsc --noEmit`, the accessibility test, and the label check against
`labels/Login.json` and the `_shell` block of `labels.json`. Then deploy with the standard loop and
run the Haiku smoke in plan §6.4. Update plan §0, the progress index, the RCA log if anything was
fixed, and write a handoff with the 4-line agent-utilization footer. Never edit `apps/api`. Never
`git add docs/` wholesale.

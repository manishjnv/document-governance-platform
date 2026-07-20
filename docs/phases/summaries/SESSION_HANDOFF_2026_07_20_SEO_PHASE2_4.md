# Session Handoff — 2026-07-20: SEO Phase 2-4, Pricing/Contact/Signout Fixes, GA4

**Headline:** Implemented SEO Phase 2 in full (use-case pillars, solution
persona pages, complete 15-term glossary, blog engine + 3 published
posts) plus the buildable slices of Phase 3-4, fixed three product bugs
found along the way (pricing exposed publicly when it should be internal,
sign-out landing on `/login` instead of home, a dead `hello@` mailto with
no real inbox behind it), and closed out the two human-blocked SEO items
from the previous handoff — GSC sitemap submission and GA4 install — now
that dashboard access was available this session.

**Commits (chronological):** `fa463b1` (SEO Phase 2: use-cases +
solutions + glossary) → `24d1972` (drop public `/pricing` links) →
`5e9cb71` (sign-out → homepage) → `9888fc5` (contact form replaces dead
mailto) → `da4a3e6` (glossary readability redesign: bullets/sections/
callout) → `4e77f18` (glossary batch complete, +10 terms) → `8ef5a14`
(blog engine + 3 demo posts, unindexed) → `0cc9c2d` (publish blog posts:
index/sitemap/nav) → `d859f54` (GA4 wiring) → `3ecc474` (roadmap doc
catch-up). All pushed to `master`, all deployed to
`scopewise.assessiq.in`.

---

## What shipped

### SEO Phase 2 — Expansion (full)
- **3 use-case pillar pages**: `/use-cases/sow-review`, `/rfp-review`,
  `/scope-creep-prevention` — static Server Components (not a dynamic
  `[slug]` template; 3 fixed pages didn't justify one), each with
  `FAQPage` JSON-LD and internal links to `/solutions/for-*` per
  `docs/planning/seo/SITE_STRUCTURE.md`'s linking matrix.
- **3 solution persona pages**: `/solutions/for-procurement`, `/for-legal`,
  `/for-agencies` — same pattern, linking back to matching `/use-cases/*`.
- **Glossary system, all 15 terms** (was 5, now complete per
  `CONTENT_CALENDAR.md`'s batch): liability cap, indemnification clause,
  scope creep, MSA, SOW, RFP, RFI, deliverable acceptance criteria,
  fixed-price contract, time-and-materials contract, force majeure,
  termination for convenience, SLA, warranty clause, limitation of
  liability. Dynamic route (`generateStaticParams` + `generateMetadata`)
  backed by `apps/web/app/resources/glossary/data.ts`.
- **Glossary readability redesign** (user-reported: "very boring,
  monotonous"): rebuilt the data model from flat paragraph arrays to
  `keyPoints` (bulleted "In short" summary) + `sections` (2 short
  subheaded sections) + `scopewiseNote` (highlighted callout box) +
  `keywords` (bolded inline via a small regex-based highlight helper in
  `[term]/page.tsx`). Applied to all 15 entries.
- **Internal linking pass**: homepage → use-cases row, `/product` →
  `/use-cases/sow-review`, nav/footer updated (Use Cases, Solutions,
  Glossary, Blog links added).
- Content grounded throughout in `docs/planning/4_AI_AGENT_SPECS.md` —
  no fabricated stats, testimonials, or customer counts (hard project
  rule, verified per page during Phase 3 review of each subagent's diff).

### SEO Phase 3-4 — buildable slices only
- **Blog engine + 3 posts**: `/resources/blog`, `/resources/blog/[slug]`,
  `BlogPosting` JSON-LD (`author` is `{"@type":"Organization","name":
  "ScopeWise"}`, not a named Person — no fabricated reviewer credentials).
  CMS decision made: hand-coded TypeScript data file, no MDX/headless
  CMS, same lazy pattern as the glossary. 3 of the Month 1-2 calendar's 8
  posts drafted (SOW vs. MSA, 10-point SOW checklist, liability cap
  explainer) as a demo batch, initially shipped `noindex` + excluded from
  sitemap/nav pending review (per `CONTENT_CALENDAR.md`'s named-reviewer
  editorial rule), then indexed and published after user approval in
  `0cc9c2d`. **Open note for whoever picks this up next:** that rule
  specifically asks for a *named* human reviewer with procurement/
  legal-ops credibility — these went live under general approval, not
  that specific process. Worth tightening if a real reviewer gets
  assigned. Posts #4-8 of the Month 1-2 batch and all of #9-16 not
  drafted.
- **Lighthouse baseline**: homepage 79 (LCP 2.9s, TBT 650ms), `/product`
  89 (LCP 2.5s), CLS 0 on both. Local `lighthouse` CLI against the live
  VPS, not CrUX field data — recorded in the roadmap's baseline table.
- **`FAQPage` schema** already covered on `/use-cases/*` from Phase 2 (no
  separate Phase 3 work needed); still open on `/compare/*` since those
  pages don't exist yet.
- **Still blocked, not attempted**: `/compare/*` (needs legal sign-off
  before drafting), case study (needs a real, consenting customer),
  `/resources/templates` gated lead-gen flow, Phase 4 authority-content
  items (all correctly left alone — see "What NOT to do" in
  `CONTENT_CALENDAR.md`).

### GSC + GA4 (the two items blocked in the previous handoff)
- **GSC**: existing `assessiq.in` **Domain property** already covers
  `scopewise.assessiq.in` (domain properties verify at the DNS level and
  cover every subdomain — no separate property/verification needed, this
  wasn't obvious to the user going in). Submitted
  `https://scopewise.assessiq.in/sitemap.xml`. Initial status showed
  "Couldn't fetch" with a blank "Last read" column — verified server-side
  everything is fine (200, valid XML, correct `robots.txt`, confirmed
  even spoofing a Googlebot user-agent), so this reads as Google not
  having retried the fetch yet, not a real problem. **User chose to
  wait** rather than force a resubmit; check the Sitemaps page in GSC
  after 2026-07-21 to confirm it flipped to "Success".
- **GA4**: user created the property and provided Measurement ID
  `G-BS21BGYW3B`. Wired via a plain `next/script` gtag.js snippet in
  `app/layout.tsx` — **deliberately did not add `@next/third-parties`**
  as a dependency, a few lines of `next/script` covers the same need
  (lazy-dependency rule). Threaded the ID through as a build arg:
  `apps/web/Dockerfile.prod` → `docker-compose.vps.yml` →
  `NEXT_PUBLIC_GA_MEASUREMENT_ID` set in the VPS `.env`. Confirmed live
  (ID present in page source, gtag script loads). **Not done yet:**
  per-CTA event tracking on the "Get started" buttons specifically — only
  the base pageview/config call fires right now.

### Three bugs found and fixed mid-session (user-reported, not from a
planned checklist)
1. **`/pricing` was publicly linked and indexed, but it's internal-use
   only** (user: "not for customer in the market"). Removed from nav,
   footer, every page's CTA (swapped for `/login`), and `sitemap.ts`.
   Added `robots: { index: false, follow: false }` to the page itself and
   disallowed it in `robots.ts` — page still works if navigated to
   directly, just not surfaced or crawled. `24d1972`.
2. **Sign-out redirected to `/login` instead of the homepage.** One-line
   fix in `apps/web/components/AppShell.tsx`'s `handleLogout`. `5e9cb71`.
3. **`/contact` showed `hello@scopewise.assessiq.in` as a mailto link,
   but that inbox doesn't exist** (user: "I dont have hello@... to
   receive query", real email is `manishjnvk@gmail.com` but "dont expose
   it"). Built a public `POST /api/v1/contact` endpoint
   (`apps/api/app/routers/contact.py`) that emails
   `settings.contact_email` server-side via the existing `send_email()`
   SMTP helper — the real address is never sent to the frontend. Replaced
   the static mailto with a client-side form
   (`apps/web/app/contact/ContactForm.tsx`) that posts to it. `9888fc5`.

---

## Architecture/pattern notes for future sessions

- **Glossary and blog both follow the same shape**: a typed data array in
  `data.ts` + a `[slug]/page.tsx` dynamic route using
  `generateStaticParams()` + `generateMetadata()` + `notFound()`. If
  `/resources/guides` gets built next, copy this pattern rather than
  inventing a third approach — it's now the established convention for
  "list of similar content pages" in this codebase.
- **`sitemap.ts` is fully dynamic** for glossary and blog — it maps over
  `GLOSSARY_ENTRIES` and `BLOG_POSTS` directly, so adding a new term or
  post never requires a manual sitemap edit.
- **The `[term]/page.tsx` `highlight()` helper** (regex-based keyword
  bolding) is currently local to the glossary page. If blog posts or
  other content pages need the same treatment, consider extracting it to
  a shared `lib/` util rather than copy-pasting — it wasn't extracted
  yet because only one consumer existed at the time.
- **Noindex-then-publish is now a proven pattern** for AI-drafted content
  pending review: ship with `robots: { index: false }` and excluded from
  `sitemap.ts`/nav, live at the URL for review, then flip both once
  approved (see blog posts: `8ef5a14` → `0cc9c2d`). Reuse this for any
  future AI-drafted content batch rather than either blocking on review
  before shipping anything, or publishing unreviewed content live.

---

## Open items for next session

1. **Confirm GSC sitemap fetch succeeded** — check the Sitemaps page in
   Search Console after 2026-07-21; if still "Couldn't fetch" after a
   few days, try removing and resubmitting to force a fresh attempt.
2. **Per-CTA GA4 event tracking** — currently only base pageviews fire.
   Wire `gtag('event', ...)` calls on the homepage/use-case/solution
   pages' "Get started" buttons if conversion-funnel visibility matters
   before more content work.
3. **Blog posts #4-8** (Month 1-2 batch) and **#9-16** (Month 3-4 batch)
   — not drafted. Also revisit the named-human-reviewer gap noted above.
4. **`/compare/*`** — needs legal sign-off before any drafting starts,
   per `CONTENT_CALENDAR.md`. Don't draft speculatively.
5. **Core Web Vitals**: homepage TBT is 650ms, on the high side — worth
   investigating (likely the six-agent grid or homepage JS bundle) before
   more marketing pages get added on top of it, though not urgent.
6. **`/resources/guides`, `/resources/templates`** — not started, no
   blockers noted beyond scheduling.

---

## Agent-utilization footer

- Opus/main session: all planning, scoping questions, code review of
  every subagent diff, all doc/roadmap updates, all git operations and
  VPS deploys, the GA4/Dockerfile/compose wiring, and all three
  mid-session bugfixes (pricing removal, sign-out redirect, contact
  form + backend endpoint).
- Sonnet: `fa463b1`'s 3 use-case pages, 3 solution pages, and glossary
  system (3 parallel agents) — no rework needed, diffs reviewed clean.
  `4e77f18`'s 10 additional glossary terms — no rework needed.
  `8ef5a14`'s blog engineering scaffold + 3 draft posts — no rework
  needed. All Sonnet output landed as-is after Opus diff review; zero
  Phase 3→4 revision loops this session.
- Haiku: n/a — not used this session.
- codex:rescue: n/a — not invoked. No security/auth/AI-classifier-path
  changes this session; the contact-form endpoint is public but
  low-risk (no auth bypass surface, no PII beyond what the submitter
  chooses to type), reviewed directly instead.

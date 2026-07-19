# ScopeWise — Site Structure & Internal Linking

**Companion to:** `docs/planning/SEO_STRATEGY.md` Section 4 (summary
version). This is the full URL list + internal-linking matrix for
implementation.

---

## Full public URL list (all new — none of these exist today)

```
/                                          Homepage
/product                                   Product overview
/product/how-it-works                      How the review pipeline works
/product/agents                            The 6 AI reviewers (Scope/Delivery/Commercial/Security/PMO/Legal)
/product/security                          Data handling / security posture (build once real, don't pre-announce)
/solutions/for-procurement                 Procurement team persona page
/solutions/for-legal                       Legal team persona page
/solutions/for-agencies                    Agency/consultancy persona page
/use-cases/sow-review                      SOW review use case (primary pillar)
/use-cases/rfp-review                      RFP review use case (primary pillar)
/use-cases/scope-creep-prevention          Scope creep use case
/pricing                                   Pricing page
/compare/scopewise-vs-manual-review        Comparison: ScopeWise vs. doing it manually
/compare/scopewise-vs-[competitor]         Comparison pages -- legal review required before each ships
/resources/blog                            Blog index
/resources/blog/[slug]                     Individual posts
/resources/guides                          Guides index
/resources/guides/[slug]                   Individual guides (SOW checklist, RFP red flags, etc.)
/resources/templates                       Downloadable templates (lead-gen)
/resources/glossary                        Glossary index
/resources/glossary/[term]                 Individual glossary entries
/customers                                 Case studies index (DO NOT populate until real customers exist)
/customers/[slug]                          Individual case studies
/about
/contact
/login, /dashboard, /upload, /search,
  /results/[reviewId], /projects/[id],
  /versions/diff                            Existing app -- stays behind auth, no change needed
```

## Internal linking matrix

The rule: **every content page has an explicit path to `/pricing` or a
signup CTA.** No page is a dead end.

| From | Links to | Why |
|---|---|---|
| `/resources/glossary/[term]` | Relevant `/use-cases/*` page | Long-tail visitor → primary pillar |
| `/resources/blog/[slug]` | Relevant `/use-cases/*` + 1-2 other blog posts | Top-of-funnel → mid-funnel, topic clustering |
| `/resources/guides/[slug]` | Relevant `/use-cases/*` + `/resources/templates` | Guide reader → lead magnet or use-case |
| `/use-cases/*` | `/pricing` + `/solutions/for-*` (matching persona) | Pillar page → conversion path |
| `/solutions/for-*` | `/pricing` + relevant `/use-cases/*` | Persona page → conversion path |
| `/compare/*` | `/pricing` + `/use-cases/*` | Comparison reader is bottom-of-funnel, shortest path to conversion |
| `/product/*` | `/pricing` + `/use-cases/sow-review` | Feature reader → primary use case |
| Homepage | `/product`, `/use-cases/sow-review`, `/use-cases/rfp-review`, `/pricing` | Top-level nav to all pillars |

## Breadcrumb structure (for `BreadcrumbList` schema)

```
Home > Resources > Guides > SOW Review Checklist
Home > Use Cases > SOW Review
Home > Compare > ScopeWise vs Manual Review
```

## URL conventions

- All lowercase, hyphen-separated, no trailing slash (set canonical
  redirect for whichever variant isn't chosen).
- Glossary terms: `/resources/glossary/liability-cap`, not
  `/resources/glossary?term=liability-cap` (query params don't get indexed
  as distinct pages reliably).
- No date-stamped blog URLs (`/blog/2026/07/title`) — plain
  `/resources/blog/title` so evergreen posts don't look stale by URL alone.

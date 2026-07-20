export type BlogSection = {
  heading: string;
  content: string;
};

export type BlogPost = {
  slug: string;
  title: string;
  dek: string;
  publishedDate: string;
  author: string;
  body: BlogSection[];
  relatedUseCase: '/use-cases/sow-review' | '/use-cases/rfp-review' | '/use-cases/scope-creep-prevention';
};

export const BLOG_POSTS: BlogPost[] = [
  {
    slug: 'sow-vs-msa',
    title: "Statement of Work vs. MSA: What's the Difference?",
    dek: 'SOWs and MSAs get used interchangeably in conversation but do very different jobs in a contract stack -- here is how each one works and why the distinction matters when you are reviewing either one.',
    publishedDate: '2026-07-20',
    author: 'ScopeWise Team',
    relatedUseCase: '/use-cases/sow-review',
    body: [
      {
        heading: 'Two documents, two jobs',
        content:
          "A Master Service Agreement (MSA) sets the general legal and commercial terms that govern a relationship between two parties -- payment terms, IP ownership, liability caps, termination rights, dispute resolution, governing law. A Statement of Work (SOW) defines a specific project: scope, deliverables, timeline, and price. The MSA is the foundation you build once; the SOW is the project you build on top of it. Confusing the two leads to two common mistakes -- negotiating liability terms fresh in every SOW instead of once in the MSA, or assuming a SOW inherits protections the MSA never actually granted.",
      },
      {
        heading: 'When you only get a SOW',
        content:
          "Not every engagement has an MSA. Smaller vendors and one-off projects often run on a standalone SOW that folds in the legal terms an MSA would normally carry -- liability caps, IP assignment, confidentiality, termination. When that is the case, treat the SOW with the same scrutiny you would give an MSA: those terms are not backstopped by anything else, so if the SOW's liability section is thin or missing, there is no fallback document to catch it.",
      },
      {
        heading: 'How they interact once both exist',
        content:
          "Once an MSA is signed, each subsequent SOW should reference it and stay inside the boundaries it sets -- adding project-specific scope, deliverables, and price without re-litigating legal terms. The failure mode to watch for is a SOW that quietly tries to change MSA terms (a different liability cap, a different IP assignment) without an explicit amendment. Most MSAs include an order-of-precedence clause for exactly this conflict, but that clause only helps if someone actually checks the SOW against it rather than assuming the MSA automatically wins.",
      },
      {
        heading: 'What to check in each',
        content:
          'In an MSA: liability caps and carve-outs, IP ownership defaults, termination rights (for convenience vs. for cause), confidentiality duration, and the order-of-precedence clause. In a SOW: deliverable definitions with acceptance criteria, explicit exclusions, timeline and milestones, pricing structure, and whether it references an MSA correctly or silently contradicts one. If a SOW touches liability, IP, or payment terms that differ from its MSA, that difference should be flagged and confirmed as intentional -- not caught after signature.',
      },
    ],
  },
  {
    slug: 'sow-review-checklist',
    title: 'The 10-Point SOW Review Checklist Before You Sign',
    dek: 'A Statement of Work usually gets reviewed by whoever needs the project started, not a lawyer -- this checklist covers the ten places risk most often hides.',
    publishedDate: '2026-07-20',
    author: 'ScopeWise Team',
    relatedUseCase: '/use-cases/sow-review',
    body: [
      {
        heading: 'Scope and deliverables (points 1-3)',
        content:
          '1. Are deliverables concrete and testable -- "a responsive site with these 12 named pages" rather than "a modern website"? Vague deliverable language is the single biggest source of scope creep. 2. Does every deliverable have defined acceptance criteria -- a stated process for how it gets reviewed and signed off? Without this, "done" is a matter of opinion. 3. Are exclusions stated explicitly -- what is NOT included -- rather than left to be inferred from what is?',
      },
      {
        heading: 'Timeline and process (points 4-6)',
        content:
          '4. Is there a change-control clause requiring any scope addition to go through a written, priced amendment before work starts on it? Without one, "just one more thing" additions have no friction. 5. Are milestones and dependencies dated, with clear ownership of who delivers what by when? 6. Are assumptions and client-side dependencies (approvals, access, third-party data) explicitly listed, since a SOW timeline that assumes instant client turnaround rarely survives contact with reality.',
      },
      {
        heading: 'Commercial and legal terms (points 7-9)',
        content:
          '7. Is there a liability cap, and does it have a defined amount and carve-out list -- or is liability left unbounded? 8. Are payment terms and milestones tied to deliverables rather than calendar dates alone, so payment and delivery stay linked? 9. Does the SOW reference an MSA correctly, or does it quietly restate (and possibly contradict) terms the MSA already covers -- see our companion piece on SOW vs. MSA for how that relationship should work.',
      },
      {
        heading: 'The final check (point 10)',
        content:
          "10. Read it as the other side would. A SOW written entirely from the vendor's perspective, or entirely from the client's, tends to have gaps the other party will surface later -- during the project, not before it starts. Reviewing under time pressure is normal; reviewing without a structured pass through the terms above is where risk slips through. This is the exact ten-point pass a fast SOW turnaround usually skips.",
      },
    ],
  },
  {
    slug: 'what-is-a-liability-cap',
    title: 'What Is a Liability Cap, and Why Your SOW Needs One',
    dek: 'A liability cap bounds how much one party can be forced to pay the other if something goes wrong -- here is what it covers, what it typically excludes, and why the exclusions matter as much as the number.',
    publishedDate: '2026-07-20',
    author: 'ScopeWise Team',
    relatedUseCase: '/use-cases/sow-review',
    body: [
      {
        heading: 'What a liability cap does',
        content:
          "A [liability cap](/resources/glossary/liability-cap) is a contract clause that sets a ceiling on the total amount one party can be required to pay the other in damages. It usually applies as a multiple of fees paid (twelve months of fees is common) or as a fixed dollar figure. Without one, a party is in theory exposed to the full extent of a claimed loss -- lost profits, delay costs, rework -- however large that turns out to be. The cap does not eliminate risk, it bounds it to a known, negotiated number.",
      },
      {
        heading: 'Why the carve-outs matter more than the number',
        content:
          'Almost every liability cap comes with a list of carve-outs -- categories of loss that stay uncapped regardless of the headline number. Common carve-outs include confidentiality breaches, gross negligence, willful misconduct, IP infringement, and indemnification obligations. A cap of "12 months of fees" sounds protective until you notice indemnification is carved out entirely, at which point the real exposure is whatever the indemnification clause covers, uncapped. Reading the cap amount without reading the carve-out list gives a false sense of the actual protection in place.',
      },
      {
        heading: 'Mutuality: does it run both ways?',
        content:
          "A liability cap that only protects one party is a red flag worth raising even if the number looks reasonable. In a healthy SOW, the cap applies symmetrically -- both the vendor and the client are protected by the same ceiling, with the same carve-outs. One-sided caps usually show up when one party's legal team drafted the document and the other side did not push back during negotiation, which is common when a SOW is reviewed quickly by whoever needs the project started rather than by legal counsel.",
      },
      {
        heading: 'What a missing liability cap means',
        content:
          "If a SOW has no liability cap at all, both parties are exposed to unbounded damages claims for anything that goes wrong on the engagement -- a missed deadline that cascades into a client's own downstream losses, a security incident, a defect that causes business disruption. This is more common in smaller or rushed engagements than most people expect, precisely because a missing clause does not visually stand out the way a bad clause does. It has to be actively checked for, not just read past.",
      },
      {
        heading: 'How to review one',
        content:
          "Check three things in order: is there a cap at all, what is the amount and how is it calculated (fixed figure vs. multiple of fees), and what is carved out. Then check mutuality -- does the same cap and carve-out list apply to both parties. ScopeWise's Commercial agent runs this exact check on every SOW it reviews, flagging missing caps, unusually asymmetric terms, and carve-out lists broad enough to functionally uncap the clause -- alongside the five other review agents (Scope, Delivery, Security, PMO, Legal) and the rule engine that scan the rest of the document.",
      },
    ],
  },
];

export function getBlogPost(slug: string): BlogPost | undefined {
  return BLOG_POSTS.find((post) => post.slug === slug);
}

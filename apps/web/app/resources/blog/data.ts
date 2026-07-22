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
  /** True until an editor has reviewed the post for accuracy/tone. Blocks indexing. */
  pendingReview?: boolean;
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
  {
    slug: 'scope-creep-clauses',
    title: '5 Scope Creep Clauses That Cost Enterprises Money',
    dek: 'Scope creep rarely starts with a dramatic ask -- it starts with five specific clause patterns that quietly leave the door open. Here is how to spot each one before you sign.',
    publishedDate: '2026-07-20',
    author: 'ScopeWise Team',
    relatedUseCase: '/use-cases/scope-creep-prevention',
    pendingReview: true,
    body: [
      {
        heading: 'Open-ended deliverable language',
        content:
          'The phrase "including but not limited to" attached to a deliverable list is the single most common source of [scope creep](/resources/glossary/scope-creep). It signals that the listed items are examples, not the full commitment -- which means anything a client can plausibly argue is "similar" to what is listed can be requested under the same line item, at no additional cost. A deliverable list should be exhaustive and closed. If flexibility is genuinely needed, it belongs in a change-control process, not in open-ended list language that leaves the boundary undefined from day one.',
      },
      {
        heading: 'Missing change-control process',
        content:
          "A SOW without a change-control clause has no defined mechanism for handling new requests once work starts -- so every addition becomes a negotiation from scratch, usually under time pressure and often without a price attached before work begins. A working change-control clause specifies who can request a change, how it gets scoped and priced, and that no additional work starts until both sides sign off in writing. Without this, \"can you also just add...\" requests accumulate informally, and by the time anyone tallies the effort, the original scope and the delivered scope have quietly diverged.",
      },
      {
        heading: 'Absent exclusions',
        content:
          'Most SOWs describe what is included and stop there, leaving what is excluded to be inferred. That inference gap is exactly where scope creep lives -- a client reasonably assumes a related task is covered because the SOW never said it was not. Explicit exclusions ("does not include third-party integrations beyond the two named systems," "does not include content authoring") close that gap. A SOW that only lists inclusions is incomplete by design, even if every included item is described well.',
      },
      {
        heading: 'Undefined acceptance criteria',
        content:
          'When a deliverable has no stated definition of "done," acceptance becomes a matter of opinion, and revision requests can continue indefinitely under the umbrella of "this is not what we asked for" -- even when the original ask was fully met. Acceptance criteria should be specific enough that both sides can independently check them off: a stated review process, a defined number of revision rounds, and a concrete pass/fail standard rather than a subjective one like "client satisfaction."',
      },
      {
        heading: 'Silent assumption of client-side dependencies',
        content:
          "A project timeline that assumes the client will provide approvals, access, data, or content on a certain schedule -- without stating that assumption in the SOW -- sets up a trap. When the client runs late, the vendor either absorbs the delay for free or has an awkward conversation asking to be paid for time spent waiting. SOWs should list client-side dependencies explicitly and state what happens to the timeline and price if they slip. This is exactly the kind of hidden dependency ScopeWise's Delivery and PMO agents are built to surface during review, alongside the SOW rule engine's checks for exclusions and change-control language -- see how it works in practice on our [scope creep prevention](/use-cases/scope-creep-prevention) page.",
      },
    ],
  },
  {
    slug: 'how-to-evaluate-rfp-response',
    title: 'How to Evaluate an RFP Response: A Procurement Guide',
    dek: 'Scoring a stack of RFP responses against each other is harder than it looks -- vendors format pricing differently, answer questions selectively, and write proposals to sound compliant. Here is a practical way to evaluate them.',
    publishedDate: '2026-07-20',
    author: 'ScopeWise Team',
    relatedUseCase: '/use-cases/rfp-review',
    pendingReview: true,
    body: [
      {
        heading: 'Score against your criteria, not the vendor\'s pitch',
        content:
          "Every RFP response is written to be persuasive, and a well-written proposal can make weak substance read as strong. The fix is mechanical: score each response against the evaluation criteria stated in your own RFP, section by section, before reading it as a narrative. If your RFP asked for named team members with relevant experience and a vendor answered with generic bios, that is a scoring gap regardless of how confident the surrounding prose sounds. Evaluating against your own criteria first, then reading holistically second, keeps a strong pitch from masking a weak fit.",
      },
      {
        heading: 'Watch for reworded, not answered, requirements',
        content:
          'A common pattern in RFP responses is restating a requirement back in confident language without actually committing to it -- "our team is well-versed in industry-standard security practices" in response to a question that asked for specific certifications. This reads as an answer on a skim but is not one. The check is simple: for each requirement in your RFP, can you point to the specific sentence in the response that commits to it, or only to a sentence that sounds related? If it is the latter, that is a gap, not a soft yes.',
      },
      {
        heading: 'Comparing pricing that is not apples-to-apples',
        content:
          "Vendors structure pricing differently -- fixed fee vs. time-and-materials, different assumptions about scope included in the base price, different treatment of expenses and travel. Comparing headline numbers across responses without first normalizing what each number actually includes will favor whichever vendor priced the narrowest scope, not whichever vendor is actually cheaper for the work you need done. Before comparing totals, list what each proposal's price assumes is included and excluded, and adjust for the gaps.",
      },
      {
        heading: 'Check proposed terms against the RFP, not just the price',
        content:
          "A response can be commercially attractive and still propose terms that conflict with what your RFP required -- a shorter warranty period, a different liability position, payment terms tied to different milestones than you specified. These deviations are sometimes disclosed explicitly and sometimes buried in an appendix or a vendor's standard terms attached at the end. Every proposed term should be checked against your RFP's stated requirements, and any deviation should be flagged for negotiation rather than discovered after award. ScopeWise's RFP review checks exactly this -- vendor responses against your evaluation criteria and required terms -- see the [RFP review](/use-cases/rfp-review) use case for how it fits into a procurement workflow.",
      },
    ],
  },
  {
    slug: 'rfp-red-flags',
    title: 'RFP Red Flags: 8 Warning Signs in a Vendor Response',
    dek: 'Some vendor responses signal trouble before the project even starts. Here are eight concrete warning signs worth checking for in every RFP response you evaluate.',
    publishedDate: '2026-07-20',
    author: 'ScopeWise Team',
    relatedUseCase: '/use-cases/rfp-review',
    pendingReview: true,
    body: [
      {
        heading: 'Pricing that does not follow your requested format',
        content:
          "1. Non-conforming pricing format. If your RFP asked for a fixed-fee breakdown by phase and a vendor returns a time-and-materials estimate with a range instead, that is worth noting on its own -- it makes the response harder to compare and can signal the vendor is unwilling or unable to commit to a firm number for the described scope. 2. Vague staffing commitments -- role titles without named individuals or stated experience levels, especially for key roles the RFP asked about by name.",
      },
      {
        heading: 'Silence on requirements the RFP explicitly asked about',
        content:
          '3. No response to required security or compliance standards. If your RFP specified a certification, framework, or audit requirement and the response does not address it directly, that is a gap, not an oversight to assume away. 4. Reworded-not-answered requirements -- confident language that restates a requirement without committing to specifics, covered in more depth in our companion piece on [evaluating RFP responses](/resources/blog/how-to-evaluate-rfp-response).',
      },
      {
        heading: 'Promises that do not match reality',
        content:
          '5. Unrealistic timeline promises -- a delivery schedule notably faster than every other response, with no explanation of what makes it achievable (more staff, a different methodology, prior reusable work). Fast is not automatically a red flag, but fast without justification is worth a direct follow-up question. 6. Missing or unverifiable references -- no references provided, or references for projects that do not resemble the scope of your RFP.',
      },
      {
        heading: 'Contract-level warning signs',
        content:
          "7. Proposed terms that contradict the RFP's stated requirements -- a different liability position, different payment milestones, or a warranty period shorter than what was specified, without it being flagged as a deviation. 8. Heavy subcontracting that is not disclosed. If a vendor plans to deliver most of the work through subcontractors, that changes who you are actually contracting with for quality and accountability, and it should be stated plainly rather than surfacing after award.",
      },
      {
        heading: 'Why these are worth checking systematically',
        content:
          "None of these eight signs alone disqualifies a vendor -- context matters, and a direct follow-up question can resolve most of them. The risk is not catching any one of them in isolation, it is missing several at once because a proposal reads well on a skim. ScopeWise's RFP review checks vendor responses against your stated requirements and flags exactly this kind of gap -- unanswered requirements, undisclosed subcontracting, terms that conflict with the RFP -- see the [RFP review](/use-cases/rfp-review) use case for details.",
      },
    ],
  },
  {
    slug: 'ambiguous-contract-language',
    title: 'Ambiguous Contract Language: 12 Real Examples',
    dek: 'Certain phrases show up in contract after contract because they sound reasonable and commit to almost nothing. Here are 12 of the most common, what makes each one risky, and what to write instead.',
    publishedDate: '2026-07-20',
    author: 'ScopeWise Team',
    relatedUseCase: '/use-cases/sow-review',
    pendingReview: true,
    body: [
      {
        heading: 'Undefined effort and quality standards',
        content:
          '"Reasonable efforts" and "best effort" commit a party to trying, not to a result -- and "reasonable" is judged after the fact, often in a dispute, rather than defined up front. "Industry standard" has the same problem: standards vary by industry and by who you ask, so the phrase resolves nothing on its own. Write instead a specific, checkable standard -- a named framework, a response-time SLA, a defined process -- so both sides can independently verify whether it was met.',
      },
      {
        heading: 'Open-ended scope qualifiers',
        content:
          '"As needed" and "as appropriate" attached to scope or obligations leave the trigger for action undefined -- needed by whose judgment, appropriate by what standard. "Including but not limited to" turns a specific list into an open-ended one, since anything arguably similar to a listed item can be claimed as covered. Write instead a closed list with explicit exclusions, or a defined trigger condition ("if X occurs, then Y") rather than a discretionary qualifier.',
      },
      {
        heading: 'Placeholders and vague timing',
        content:
          '"TBD" left in a signed contract means a term was never actually agreed -- it should be resolved before signature, not carried into the executed document. "Approximately" attached to a date, quantity, or price introduces a range without stating what the range is. "Promptly" has no enforceable meaning without a number attached to it -- promptly could mean same-day to one party and two weeks to another. Write instead a specific date, a stated range with bounds, or a defined number of business days.',
      },
      {
        heading: 'Conditional and discretionary phrases',
        content:
          '"As applicable" quietly makes an obligation conditional without stating the condition, letting either party argue later that it did not apply. "Mutually agreed" for a term that was never actually negotiated defers a real decision to some future point, often under worse conditions than exist during the original negotiation. "From time to time" describing frequency of an obligation (reporting, audits, updates) sets no actual cadence. Write instead the specific condition, the agreed term itself, or a stated frequency.',
      },
      {
        heading: 'Undefined breach and satisfaction standards',
        content:
          '"Material breach" used without a definition leaves what counts as material -- and therefore what triggers termination rights -- open to interpretation exactly when it matters most, mid-dispute. "Satisfactory to client" as an acceptance standard is fully subjective and gives one party unilateral, unreviewable discretion over whether the other party gets paid or the contract proceeds. Write instead specific examples or thresholds that define a material breach, and objective, checkable acceptance criteria in place of a subjective satisfaction standard. ScopeWise\'s ambiguous-language scan is a deterministic rule-based check that runs against every uploaded document and flags exactly these phrase patterns -- not an LLM guess, but a direct scan for the language above -- see how it fits into a [full SOW review](/use-cases/sow-review).',
      },
    ],
  },
  {
    slug: 'ai-contract-review',
    title: "AI Contract Review: What It Can (and Can't) Catch",
    dek: "AI-assisted contract review is genuinely useful and genuinely limited -- here is an honest breakdown of what it catches reliably, what it cannot do, and why that gap is worth designing around rather than ignoring.",
    publishedDate: '2026-07-20',
    author: 'ScopeWise Team',
    relatedUseCase: '/use-cases/sow-review',
    pendingReview: true,
    body: [
      {
        heading: 'What AI review does well',
        content:
          "AI review is strong at exhaustive checklist coverage -- reading every clause of a long document against a fixed set of questions (is there a liability cap, is there a change-control clause, are acceptance criteria defined) without skipping sections due to time pressure or fatigue, which is a real failure mode in manual review of a document under deadline. It is also strong at ambiguity detection -- flagging vague phrases like \"reasonable efforts\" or \"as needed\" systematically rather than catching only the ones a reviewer happens to notice -- and at cross-clause consistency, noticing when a payment milestone referenced in one section does not match the schedule defined in another. It is fast: a pass that would take a reviewer an hour completes in minutes.",
      },
      {
        heading: 'What AI review cannot do',
        content:
          "AI review cannot exercise legal judgment -- deciding whether a particular liability position is acceptable for your organization's specific risk tolerance is a business decision, not a pattern match, and it depends on context the document itself does not contain. It cannot supply business context it was not given -- whether a vendor's proposed timeline is realistic depends on things like your internal approval speed and prior experience with that vendor, not just what is on the page. It cannot set negotiation strategy -- what to push back on first, what to concede, and how hard to push are calls that depend on leverage and relationship, not document content. And it cannot reliably interpret a genuinely novel clause structure it has not seen a pattern for, the way an experienced lawyer reasoning from first principles can.",
      },
      {
        heading: 'Why the honest answer is a strength, not a weakness',
        content:
          'A tool that claimed to fully replace legal judgment would be overselling and would eventually fail on exactly the kind of document where it mattered most. The useful framing is division of labor: AI review handles the exhaustive, mechanical, easy-to-miss-under-deadline work, and a human handles the judgment calls the machine is not positioned to make. That division only works if the tool is honest about where the line sits -- surfacing findings with the specific clause and reasoning behind them, rather than a black-box score, so a reviewer can quickly agree, disagree, or escalate rather than trusting a verdict blind.',
      },
      {
        heading: 'How ScopeWise draws that line',
        content:
          "ScopeWise pairs six specialized review agents (Scope, Delivery, Commercial, Security, PMO, Legal) with a deterministic rule engine rather than relying on a single model's output. The rule engine handles the mechanical, checklist-style checks -- missing clauses, undefined terms, ambiguous-language patterns -- where a fixed, auditable rule is more reliable than a model's judgment call. The agents handle the more contextual review -- summarizing risk, explaining why a clause is a problem, connecting findings across sections. Every finding cites the specific text it is based on, which is what lets a human reviewer verify it quickly rather than take it on faith. See the full breakdown on our [SOW review](/use-cases/sow-review) page.",
      },
    ],
  },
];

export function getBlogPost(slug: string): BlogPost | undefined {
  return BLOG_POSTS.find((post) => post.slug === slug);
}

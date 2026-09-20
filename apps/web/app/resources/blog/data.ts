export type BlogSection = {
  heading: string;
  content: string;
};

export type BlogPost = {
  slug: string;
  title: string;
  dek: string;
  publishedDate: string;
  /** ISO date of the last substantive edit; feeds BlogPosting.dateModified. */
  updatedDate?: string;
  author: string;
  body: BlogSection[];
  relatedUseCase: RelatedPath;
  /** Product pillar the post belongs to; drives the blog index filter chips. */
  pillar?: Pillar;
  /** True until an editor has reviewed the post for accuracy/tone. Blocks indexing. */
  pendingReview?: boolean;
};

export type Pillar = 'sow' | 'mitre' | 'codereview';

export type RelatedPath =
  | '/use-cases/sow-review'
  | '/use-cases/rfp-review'
  | '/use-cases/scope-creep-prevention'
  | '/product/sow-review'
  | '/product/mitre-coverage'
  | '/product/code-security-review';

export const PILLAR_LABELS: Record<Pillar, string> = {
  sow: 'SOW & RFP Review',
  mitre: 'MITRE ATT&CK Coverage',
  codereview: 'Code Security Review',
};

/** Human label for the "related reading" link, derived from the path. */
export const RELATED_LABELS: Record<RelatedPath, string> = {
  '/use-cases/sow-review': 'See how ScopeSense reviews a SOW in practice',
  '/use-cases/rfp-review': 'See how ScopeSense reviews an RFP in practice',
  '/use-cases/scope-creep-prevention': 'See how ScopeSense catches scope creep in practice',
  '/product/sow-review': 'See the SOW & RFP Review product',
  '/product/mitre-coverage': 'See the MITRE ATT&CK Coverage product',
  '/product/code-security-review': 'See the Code Security Review product',
};

export const BLOG_POSTS: BlogPost[] = [
  {
    slug: 'sow-vs-msa',
    title: "Statement of Work vs. MSA: What's the Difference?",
    dek: 'SOWs and MSAs get used interchangeably in conversation but do very different jobs in a contract stack -- here is how each one works and why the distinction matters when you are reviewing either one.',
    publishedDate: '2026-07-20',
    author: 'ScopeSense Team',
    pillar: 'sow',
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
    author: 'ScopeSense Team',
    pillar: 'sow',
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
    author: 'ScopeSense Team',
    pillar: 'sow',
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
          "Check three things in order: is there a cap at all, what is the amount and how is it calculated (fixed figure vs. multiple of fees), and what is carved out. Then check mutuality -- does the same cap and carve-out list apply to both parties. ScopeSense's Commercial agent runs this exact check on every SOW it reviews, flagging missing caps, unusually asymmetric terms, and carve-out lists broad enough to functionally uncap the clause -- alongside the five other review agents (Scope, Delivery, Security, PMO, Legal) and the rule engine that scan the rest of the document.",
      },
    ],
  },
  {
    slug: 'scope-creep-clauses',
    title: '5 Scope Creep Clauses That Cost Enterprises Money',
    dek: 'Scope creep rarely starts with a dramatic ask -- it starts with five specific clause patterns that quietly leave the door open. Here is how to spot each one before you sign.',
    publishedDate: '2026-07-20',
    author: 'ScopeSense Team',
    pillar: 'sow',
    relatedUseCase: '/use-cases/scope-creep-prevention',
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
          "A project timeline that assumes the client will provide approvals, access, data, or content on a certain schedule -- without stating that assumption in the SOW -- sets up a trap. When the client runs late, the vendor either absorbs the delay for free or has an awkward conversation asking to be paid for time spent waiting. SOWs should list client-side dependencies explicitly and state what happens to the timeline and price if they slip. This is exactly the kind of hidden dependency ScopeSense's Delivery and PMO agents are built to surface during review, alongside the SOW rule engine's checks for exclusions and change-control language -- see how it works in practice on our [scope creep prevention](/use-cases/scope-creep-prevention) page.",
      },
    ],
  },
  {
    slug: 'how-to-evaluate-rfp-response',
    title: 'How to Evaluate an RFP Response: A Procurement Guide',
    dek: 'Scoring a stack of RFP responses against each other is harder than it looks -- vendors format pricing differently, answer questions selectively, and write proposals to sound compliant. Here is a practical way to evaluate them.',
    publishedDate: '2026-07-20',
    author: 'ScopeSense Team',
    pillar: 'sow',
    relatedUseCase: '/use-cases/rfp-review',
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
          "A response can be commercially attractive and still propose terms that conflict with what your RFP required -- a shorter warranty period, a different liability position, payment terms tied to different milestones than you specified. These deviations are sometimes disclosed explicitly and sometimes buried in an appendix or a vendor's standard terms attached at the end. Every proposed term should be checked against your RFP's stated requirements, and any deviation should be flagged for negotiation rather than discovered after award. ScopeSense's RFP review checks exactly this -- vendor responses against your evaluation criteria and required terms -- see the [RFP review](/use-cases/rfp-review) use case for how it fits into a procurement workflow.",
      },
    ],
  },
  {
    slug: 'rfp-red-flags',
    title: 'RFP Red Flags: 8 Warning Signs in a Vendor Response',
    dek: 'Some vendor responses signal trouble before the project even starts. Here are eight concrete warning signs worth checking for in every RFP response you evaluate.',
    publishedDate: '2026-07-20',
    author: 'ScopeSense Team',
    pillar: 'sow',
    relatedUseCase: '/use-cases/rfp-review',
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
          "None of these eight signs alone disqualifies a vendor -- context matters, and a direct follow-up question can resolve most of them. The risk is not catching any one of them in isolation, it is missing several at once because a proposal reads well on a skim. ScopeSense's RFP review checks vendor responses against your stated requirements and flags exactly this kind of gap -- unanswered requirements, undisclosed subcontracting, terms that conflict with the RFP -- see the [RFP review](/use-cases/rfp-review) use case for details.",
      },
    ],
  },
  {
    slug: 'ambiguous-contract-language',
    title: 'Ambiguous Contract Language: 12 Real Examples',
    dek: 'Certain phrases show up in contract after contract because they sound reasonable and commit to almost nothing. Here are 12 of the most common, what makes each one risky, and what to write instead.',
    publishedDate: '2026-07-20',
    author: 'ScopeSense Team',
    pillar: 'sow',
    relatedUseCase: '/use-cases/sow-review',
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
          '"Material breach" used without a definition leaves what counts as material -- and therefore what triggers termination rights -- open to interpretation exactly when it matters most, mid-dispute. "Satisfactory to client" as an acceptance standard is fully subjective and gives one party unilateral, unreviewable discretion over whether the other party gets paid or the contract proceeds. Write instead specific examples or thresholds that define a material breach, and objective, checkable acceptance criteria in place of a subjective satisfaction standard. ScopeSense\'s ambiguous-language scan is a deterministic rule-based check that runs against every uploaded document and flags exactly these phrase patterns -- not an LLM guess, but a direct scan for the language above -- see how it fits into a [full SOW review](/use-cases/sow-review).',
      },
    ],
  },
  {
    slug: 'ai-contract-review',
    title: "AI Contract Review: What It Can (and Can't) Catch",
    dek: "AI-assisted contract review is genuinely useful and genuinely limited -- here is an honest breakdown of what it catches reliably, what it cannot do, and why that gap is worth designing around rather than ignoring.",
    publishedDate: '2026-07-20',
    author: 'ScopeSense Team',
    pillar: 'sow',
    relatedUseCase: '/use-cases/sow-review',
    body: [
      {
        heading: 'What AI review does well',
        content:
          "AI review is strong at exhaustive checklist coverage -- reading every clause of a long document against a fixed set of questions (is there a liability cap, is there a change-control clause, are acceptance criteria defined) without skipping sections due to time pressure or fatigue, which is a real failure mode in manual review of a document under deadline. It is also strong at ambiguity detection -- flagging vague phrases like \"reasonable efforts\" or \"as needed\" systematically rather than catching only the ones a reviewer happens to notice -- and at cross-clause consistency, noticing when a payment milestone referenced in one section does not match the schedule defined in another. It is fast: a pass that would take a reviewer an hour completes in minutes.",
      },
      {
        heading: 'What AI review cannot do',
        content:
          "AI review cannot exercise legal judgment -- deciding whether a particular liability position is acceptable for your organization's specific risk tolerance is a business decision, not a pattern match, and it depends on context the document itself does not contain. It cannot supply business context it was not given -- whether a vendor's proposed timeline is realistic depends on things like your internal approval speed and prior experience with that vendor, not just what is on the page. It cannot set negotiation strategy -- what to push back on first, what to concede, and how hard to push are calls that depend on bargaining position and relationship, not document content. And it cannot reliably interpret a genuinely novel clause structure it has not seen a pattern for, the way an experienced lawyer reasoning from first principles can.",
      },
      {
        heading: 'Why the honest answer is a strength, not a weakness',
        content:
          'A tool that claimed to fully replace legal judgment would be overselling and would eventually fail on exactly the kind of document where it mattered most. The useful framing is division of labor: AI review handles the exhaustive, mechanical, easy-to-miss-under-deadline work, and a human handles the judgment calls the machine is not positioned to make. That division only works if the tool is honest about where the line sits -- surfacing findings with the specific clause and reasoning behind them, rather than a black-box score, so a reviewer can quickly agree, disagree, or escalate rather than trusting a verdict blind.',
      },
      {
        heading: 'How ScopeSense draws that line',
        content:
          "ScopeSense pairs six specialized review agents (Scope, Delivery, Commercial, Security, PMO, Legal) with a deterministic rule engine rather than relying on a single model's output. The rule engine handles the mechanical, checklist-style checks -- missing clauses, undefined terms, ambiguous-language patterns -- where a fixed, auditable rule is more reliable than a model's judgment call. The agents handle the more contextual review -- summarizing risk, explaining why a clause is a problem, connecting findings across sections. Every finding cites the specific text it is based on, which is what lets a human reviewer verify it quickly rather than take it on faith. See the full breakdown on our [SOW review](/use-cases/sow-review) page.",
      },
    ],
  },
  {
    slug: 'how-much-mitre-attack-does-your-siem-cover',
    title: 'How Much of MITRE ATT&CK Does Your SIEM Really Cover?',
    dek: "Most detection rule sets cover a small slice of MITRE ATT&CK while the telemetry to cover far more already sits in the SIEM. Here is why the number is smaller than teams assume, and how a MITRE ATT&CK coverage assessment gets you an honest one.",
    publishedDate: '2026-09-12',
    author: 'ScopeSense Team',
    pillar: 'mitre',
    relatedUseCase: '/product/mitre-coverage',
    body: [
      {
        heading: 'The gap between what you log and what you detect',
        content:
          "CardinalOps' 2025 State of SIEM Detection Risk report found that enterprise SIEMs detect about 21% of MITRE ATT&CK techniques on average, even though the telemetry those same SIEMs already ingest could cover more than 90%. That is not a logging problem. The logs are there. What is missing is the mapping between the rules a team has written and the technique list those rules are supposed to defend against. Nobody sits down and decides to cover 21%. It happens because rule sets grow one alert at a time, tagging is optional, and no one re-checks the total against the full ATT&CK matrix once a quarter, let alone after every rule change. A MITRE ATT&CK coverage assessment exists to close that gap: take the rules as they are, take the ATT&CK matrix as published, and produce an honest count of what is actually covered instead of what a rule name implies.",
      },
      {
        heading: 'Four states, not two',
        content:
          'A rule set does not sort cleanly into "covered" and "not covered." A technique is covered when at least one enabled rule maps to it with a confident mapping. It is partial when the only mapping is a disabled rule, or the mapping confidence is low, or a parent technique has no direct rule of its own but at least one of its sub-techniques is covered. It is not covered when nothing maps to it at all. And it is not applicable when the technique cannot occur in the environment being assessed in the first place. Collapsing partial into covered flatters the number; collapsing it into not-covered ignores real intent behind a disabled rule. Keeping all four states separate is what makes a coverage percentage mean something specific rather than something optimistic.',
      },
      {
        heading: 'Why not-applicable has to leave the denominator, with a reason',
        content:
          'ATT&CK v19.1 lists 858 Enterprise techniques across 15 tactics, plus separate ICS and Mobile matrices. Not every technique applies to every environment: a macOS-specific technique is meaningless with no macOS in the inventory, and the ICS matrix should not be in play for an estate with no OT or industrial control assets. Marking those as not applicable and removing them from the denominator is correct, but only if the reason is visible. There are two kinds. Derived: the platform or domain the technique needs is absent from the declared inventory. Customer-declared: someone excluded the technique on purpose and gave a reason, printed verbatim in the report. An executive reading "78% coverage" needs to know whether that 78% is measured against the full 858 or against a narrowed set someone chose, and why it was narrowed. A coverage number with no visible N/A reasons is a number nobody can audit.',
      },
      {
        heading: 'Two numbers, never one',
        content:
          'A second reporting discipline matters as much as the four states: the coverage a customer\'s own rules provide, and the coverage a security tool claims to provide natively, are always reported as two separate figures. Merging them produces a number that overstates what the customer team actually built and maintains, and understates what buying or enabling a vendor feature would add. Keeping them apart also protects the audit trail — a rule the customer wrote and owns behaves differently under a product update than a vendor-native detection does, and a report that blends the two loses that distinction the moment it is printed.',
      },
      {
        heading: 'Coverage is presence, not efficacy',
        content:
          'A technique being "covered" only means a qualifying rule exists for it. It says nothing about whether that rule fires correctly, or at all. Detection strength is scored separately, from provenance (was the mapping written by a person, matched by keyword, or assigned by a language model), whether the rule is enabled, whether real detection logic is present rather than a placeholder, and whether the rule\'s log source actually matches the telemetry the technique requires. A disabled rule can satisfy the coverage state as partial, but it can never score as a strong detection — a rule nobody has turned on is not defending anything yet, no matter what it would catch if it were live. Splitting these two questions apart is why a report can honestly say "covered, but weak" instead of collapsing it into one comforting label.',
      },
      {
        heading: 'A worked example',
        content:
          'Picture a hypothetical 120-rule Sentinel workspace covering Windows endpoints, Entra ID, and AWS, with no macOS and no OT in the inventory. Applicability first removes every macOS-only technique (derived, platform absent) and the entire ICS matrix (derived, no OT assets declared), which might shrink the denominator from 858 to something closer to 640 applicable techniques for that specific estate. Against that narrower denominator, the 120 rules might land at 96 covered, 40 partial (mostly disabled rules kept for tuning, plus a few low-confidence tags), and the rest not covered — a strict figure near 15% and a weighted figure, crediting partial at half value, closer to 21%. Of those 96 covered techniques, detection-strength scoring might flag a third as merely moderate because the rule\'s log source only loosely matches the technique\'s expected telemetry. None of these numbers are real; they are illustrative of how the four states and the two-number split turn a single "here is our coverage" claim into something a security lead can actually interrogate.',
      },
      {
        heading: 'What to do with the gap list',
        content:
          'A list of not-covered and partial techniques is not useful until it is ordered. Gaps get ranked by how often real attackers use the technique and by whether it touches a declared crown jewel, then split by feasibility: short-term gaps are covered by telemetry already onboarded, mid-term gaps need tooling the team already owns but has not wired up, and long-term gaps need new capability entirely. That ranked list is the actual deliverable — a SIEM detection coverage percentage on its own tells you where you stand, but a feasibility-sorted gap list tells you what to build next quarter versus what to defer. If you want to see this run against your own rule export and environment inventory, [ScopeSense\'s MITRE ATT&CK coverage assessment](/product/mitre-coverage) produces the coverage numbers, the detection-strength scoring, and the ranked gap list from the same run.',
      },
    ],
  },
  {
    slug: 'reading-an-attack-navigator-layer',
    title: 'Reading an ATT&CK Navigator Layer Without Fooling Yourself',
    dek: "A Navigator layer looks like a finished picture of your detection coverage, but the colors are a summary of choices someone made upstream -- here is what to check before you trust the grid.",
    publishedDate: '2026-09-12',
    author: 'ScopeSense Team',
    pillar: 'mitre',
    relatedUseCase: '/product/mitre-coverage',
    body: [
      {
        heading: 'What a layer file actually is',
        content:
          "An ATT&CK Navigator layer is a JSON file the MITRE ATT&CK Navigator loads to draw its grid. Current Navigator builds read layer format 4.5, which fixes the shape of the file: a name, a domain (enterprise-attack, ics-attack, or mobile-attack), a version block recording the ATT&CK version and the layer format itself, and a techniques array. Each entry in that array names a techniqueID, ties it to a tactic column, carries a color, and optionally a score, a comment, and an enabled flag. Everything the Navigator renders comes from those fields -- there is no hidden computation happening in the viewer, which is exactly why the file is worth reading on its own terms rather than trusting the picture it produces.",
      },
      {
        heading: 'Color and score are two different mechanisms',
        content:
          "Navigator supports two ways of coloring cells. One is a gradient tied to a numeric score, useful when the underlying data is genuinely continuous, like a percentage or a count. The other is a fixed color assigned per state, useful when the data is categorical. ScopeSense writes fixed colors: covered, partial, not covered, and not applicable each get one color, matching the palette used in the PDF report, so a technique that reads amber in the Navigator reads amber on the page too. This matters because a gradient layer and a fixed-color layer can look superficially similar at a glance but mean different things -- a gradient answers 'how much,' a fixed-color layer answers 'which bucket,' and mixing up the two when reading someone else's layer is an easy way to misjudge what a shade is telling you.",
      },
      {
        heading: 'Not applicable is a decision, not a blank',
        content:
          "A greyed-out, disabled cell in a layer is not a technique nobody looked at. The convention is enabled:false paired with a comment carrying the reason: either the technique needs a platform absent from the inventory (a derived exclusion) or the customer reviewed it and declared it out of scope with a stated reason. Reading a layer without opening the comment field turns a documented decision back into an unexplained gap, which defeats the purpose of recording it that way in the first place. If a layer you receive has disabled cells with empty or generic comments, that is worth asking about before treating the coverage percentage as final -- a real exclusion and a lazy default look identical without the comment.",
      },
      {
        heading: 'Comparing two layers across runs',
        content:
          "The useful comparison is two layers from the same estate, generated against the same ATT&CK version, months apart. What changed at the per-technique level is the signal: a cell that moved from not covered to covered reflects a new or improved rule, and that is a real gain worth confirming, not just accepting on sight. But a cell can also change because ATT&CK itself re-mapped a technique between versions, split a technique into new sub-techniques, or revised a tactic assignment -- a shift that has nothing to do with your rules changing. Navigator has a built-in layer-comparison feature that overlays two layers and highlights the diff directly, which is faster than eyeballing two grids side by side, but it still will not tell you which of those two causes produced a given change -- that judgment call is still yours, usually by checking whether the rule set actually changed or only the ATT&CK version did.",
      },
      {
        heading: 'Where a quick read goes wrong',
        content:
          "A handful of misreadings show up often enough to name. Sub-technique rollup is the most common: a parent technique can render as covered in the grid because one of its several sub-techniques is covered, while the rest sit uncovered -- a detection gap analysis that only counts parent techniques will systematically overstate coverage, so both levels need counting. Revoked and deprecated techniques cause a second kind of confusion: a revoked techniqueID is retired and redirected to its successor, so it will not appear in a current register at all, while a deprecated one is marked not applicable with that reason -- either way, a layer built against an older ATT&CK version will not line up cell for cell against one built against a newer one, and that mismatch is a version artifact, not a coverage change. A third trap is multi-tactic techniques, which legitimately appear in more than one tactic column, so counting the same colored cell twice across columns inflates the picture. And the broadest trap is reading color density as detection quality -- a covered cell means a rule exists for that technique, nothing about whether the rule is well-tuned, current, or would actually fire in a real intrusion.",
      },
      {
        heading: 'A worked example',
        content:
          "Take a hypothetical mid-size estate assessed twice, three months apart, both runs against the same pinned ATT&CK version. The first layer shows the Lateral Movement and Credential Access tactics mostly red, with a scattering of amber. The second layer shows several of those same techniqueIDs shifted from not covered to partial, and two shifted all the way to covered -- that is the detection gap analysis doing its job, because the underlying rule set actually grew between runs. But the second layer also shows three techniqueIDs in Initial Access that flipped from covered to not applicable, each with a comment reading that the corresponding cloud platform was decommissioned during that quarter. Read superficially, the coverage percentage barely moved between the two layers. Read technique by technique with the comments open, the real story is a genuine detection improvement in two tactics plus a legitimate shrinking of the estate's applicable surface -- two different, both good, developments that a single headline number would have hidden from each other.",
      },
      {
        heading: 'What the layer is for',
        content:
          "A Navigator layer is a picture of presence: which techniques have a rule, which do not, and which were excluded and why. It is not a verdict on how strong those rules are, and it is not a substitute for reading the gap list behind it. The gap list, ranked by what it says about your exposure, and the detection-strength notes attached to each covered cell are the parts of the assessment that turn into work -- the layer is just the map that points at where to look. See how ScopeSense builds this whole picture, from rule ingest through the layer export, on the [MITRE ATT&CK Coverage](/product/mitre-coverage) product page.",
      },
    ],
  },
  {
    slug: 'what-a-code-security-review-deliverable-should-contain',
    title: 'What a Code Security Review Deliverable Should Contain',
    dek: 'A scanner produces a JSON file of raw hits. A code security review report is something else -- verified findings, exploit chains, and a fix plan a client can actually work.',
    publishedDate: '2026-09-12',
    author: 'ScopeSense Team',
    pillar: 'codereview',
    relatedUseCase: '/product/code-security-review',
    body: [
      {
        heading: 'A scanner output is not a deliverable',
        content:
          "Run any static analysis scanner against a real codebase and it hands back a JSON file with somewhere between a few dozen and a few hundred hits. Some are duplicates of the same underlying issue reported at three call sites. Some are false positives the scanner cannot tell from a real bug. None of them come pre-sorted by what actually matters, and none of them are written in language a product owner or a client's engineering lead can read and act on without translation. Handing that file over is not a code security review report -- it is the input to one. The consultant's actual value has always been the transformation from raw hits to a decision a client can make, and until that transformation is automated, it gets rebuilt by hand for every single engagement: the same triage spreadsheet, the same severity re-ranking, the same rewritten explanations, over and over.",
      },
      {
        heading: 'The order a finding needs to be read in',
        content:
          "A finding that is useful to a reader has a fixed reading order, and most raw scanner output does not follow it. First, what is wrong -- a plain description of the defect, not a rule ID. Second, why it matters -- the actual consequence if left unfixed, not a generic severity label. Third, how to fix it -- a concrete, specific remediation, not \"sanitize input.\" Fourth, how it is exploited -- the attack path a real adversary would take through this specific piece of code. Fifth, the preconditions an attacker needs -- what has to be true for the exploit to work at all, since a lot of technically-real findings require conditions that never occur in practice. Every finding should also carry a severity rating, a verifier verdict (has this been checked against the actual code, or is it an unconfirmed candidate), and the exact file and line so a developer can go straight to the fix. Skip any one of these five and the reader has to reconstruct it themselves, which is the same manual work the review was supposed to remove.",
      },
      {
        heading: 'Exploit chains change the fix order',
        content:
          "Individual findings rarely tell the full story. The more useful unit is the exploit chain -- a sequence of findings that, linked together, get an attacker somewhere a single finding would not. A moderate authentication weakness combined with an unrelated path traversal bug can add up to full account takeover, even though neither finding alone reads as critical. Once chains are mapped, the remediation question changes from \"what is the highest CVSS score\" to \"what is the fewest number of fixes that breaks every chain.\" That is a set-cover problem, and it has a deterministic answer: order fixes so the one that breaks the most chains goes first, not the one with the scariest score in isolation. A fix plan built this way collapses six chains down to a handful of fixes instead of a flat list of 29 items with no sense of which ones actually matter most.",
      },
      {
        heading: 'The tracker and the deck have to agree',
        content:
          "None of this is useful if it lives only in a PDF nobody updates. The deliverable needs an editable tracker -- one row per finding, plus columns a team will actually use to run remediation: Owner, Status (Open, In progress, Fixed, Accepted risk, False positive), Target date, and Notes. That tracker is the source of truth, and any summary document built on top of it -- a briefing deck for a steering committee, say -- has to pull its numbers from the same rows rather than a separately hand-typed slide. The moment the deck and the tracker can drift apart, someone in a room quotes a stale number and the whole review loses credibility over something that was never actually wrong in the underlying data.",
      },
      {
        heading: 'What this is not',
        content:
          "An AI code security review is worth using precisely because its limits are stated up front, not discovered later. The scanner behind this kind of review is LLM-driven static analysis: it is non-deterministic, and there are no published precision or recall figures for it, the way there might be for a mature rule-based tool. Its output is a set of triage candidates for a human reviewer to work through, not a completed security assessment on its own. It never tests a running system, which means it is not a DAST tool, not a vulnerability-management platform, and not a network scanner -- those check different things and none of them are substitutes here. And operationally, the scan runs on the consultant's own machine, against their own copy of the code; only the resulting findings file is uploaded anywhere, which is a meaningfully different data-handling story than a service that asks for repository access.",
      },
      {
        heading: 'What this looks like on a real codebase',
        content:
          "The clearest way to see the transformation is on a codebase built to have bugs in it. OWASP NodeGoat is a deliberately vulnerable training application, released under Apache-2.0, designed to exercise the OWASP Top Ten. ScopeSense uses it as a golden benchmark: a scan run on 2026-09-11 against NodeGoat's 63 files took 103 minutes of wall-clock time and cost about $4 in model usage on the consultant's own OpenRouter key. The scanner returned 88 raw hits. After deduplication and verification, that came down to 29 confirmed findings, and those findings resolved into 6 distinct exploit chains -- six different ways an attacker could link individual weaknesses into something worse. That gap, 88 down to 29, plus six chains instead of a flat list, is the entire argument for why a code security review report has to be more than a scanner's raw file. For context on what this replaces: a manual internal penetration-test engagement typically costs $7,000 to $35,000 (Bright Defense, penetration testing pricing guide), which is the budget bracket this kind of automated triage is meant to sit ahead of, not replace.",
      },
      {
        heading: 'Where this fits',
        content:
          "Built on Visa's open-source Vulnerability Agentic Harness (Apache-2.0). ScopeSense is not affiliated with or endorsed by Visa, Inc. Everything described here -- the findings register, the exploit chains, the editable tracker, and the briefing deck built from the same numbers -- is what ScopeSense generates once a consultant uploads a findings file from a scan they ran themselves. See the [Code Security Review](/product/code-security-review) product page for how the upload and export flow works end to end.",
      },
    ],
  },
  {
    slug: 'sow-vs-rfp-review-what-changes',
    title: 'SOW vs. RFP Review: What Changes and What Stays the Same',
    dek: "An RFP and a SOW read like cousins but do different jobs -- one asks vendors to propose, the other defines what a winning vendor will deliver. Here is what a review has to check differently in each, and what stays identical.",
    publishedDate: '2026-09-12',
    author: 'ScopeSense Team',
    pillar: 'sow',
    relatedUseCase: '/use-cases/rfp-review',
    body: [
      {
        heading: 'Two documents, two jobs',
        content:
          "A [Statement of Work](/resources/glossary/sow) defines work that has already been agreed to: scope, deliverables, acceptance criteria, timeline, and price. A Request for Proposal does something earlier and different -- it asks vendors to propose a solution and tells them how their proposals will be judged. Nothing has been delivered yet when an RFP is reviewed; the question is whether the document is specific enough to get comparable responses and fair enough to survive a challenge from a losing bidder. A SOW review asks whether the work is defined well enough to execute. An RFP review asks whether the competition is defined well enough to judge.",
      },
      {
        heading: 'What differs for an RFP',
        content:
          "An RFP's structure mirrors FAR Part 15, the part of the U.S. Federal Acquisition Regulation that governs contracting by negotiation: a statement of requirements, evaluation factors and their relative weights, submission instructions, and a stated basis for award. That structure is not a government-only convention -- it is the same discipline any RFP needs to produce responses that can actually be compared. So the review asks whether evaluation criteria are stated, weighted, and measurable rather than left implicit; whether the requirements are specific enough that two vendors answering them produce comparable proposals instead of two different documents; and whether the timeline and Q&A process are fair to every bidder rather than favoring whoever has an inside line to the buyer. ScopeSense runs 7 deterministic RFP rules against 20 SOW rules, and each of the six reviewer agents -- Scope, Delivery, Commercial, Security, PMO, Legal -- has an RFP-specific prompt branch, so the Commercial reviewer on an RFP asks about pricing-format requirements and evaluation weighting instead of the payment milestones it would check on a SOW.",
      },
      {
        heading: 'What stays the same',
        content:
          "Underneath the different rule sets, the review discipline does not change by document type. Every finding quotes the clause it came from, with a confidence score attached to that quote, not to a general impression of the document. Risk is reported by area -- scope, delivery, commercial, security, PMO, legal -- on an RFP exactly as it is on a SOW. The rule engine checks presence deterministically -- is a required section there, is a required term mentioned -- and the model is asked to judge what a rule cannot: quality, mutuality, how one clause interacts with another, and ambiguity, never re-checking what a rule already checked. Ambiguous-language scanning runs on both document types for the same reason: vague evaluation language causes the same downstream dispute as vague scope language, just at a different stage of the relationship.",
      },
      {
        heading: 'Common RFP failure modes',
        content:
          "The failure patterns that show up in RFP review are specific to the document's job. Evaluation criteria that are unweighted or unstated leave vendors guessing what actually wins, and leave the buyer with no defensible basis for the award if a losing bidder pushes back. Requirements written as vendor marketing copy rather than testable specifications produce proposals that are impossible to compare on equal terms. A missing or vague basis for award compounds both problems. Unrealistic response windows shrink the pool to whoever already had a draft ready, which quietly defeats the point of running a competition at all. And mandatory terms buried in an attachment rather than stated in the body of the RFP get missed by vendors who did not read every appendix, then become a dispute later when the buyer tries to enforce them.",
      },
      {
        heading: 'The same engagement, two documents',
        content:
          "Take a hypothetical mid-size IT services engagement: a buyer wants a vendor to migrate an internal ticketing system to a new platform. As an RFP, the buyer's document states the migration requirements, lists evaluation factors -- technical approach, cost, past performance, transition plan -- and assigns each a weight, sets a submission deadline and a Q&A window, and states that award goes to the highest weighted score rather than lowest price. A review of that RFP checks whether those weights are actually stated (not just a line saying technical merit will be considered), whether the requirements are concrete enough that two vendors' technical approaches can be scored against the same yardstick, and whether the Q&A process gives every bidder access to the same answers. Once a vendor wins and the engagement moves to a SOW, the same migration now appears as defined deliverables -- data migrated with a stated record-count reconciliation, a cutover date, a rollback plan -- acceptance criteria for each, a payment schedule tied to milestones, and a liability cap. A review of that SOW checks a completely different set of things: are the deliverables testable, is there a change-control clause, does the liability cap have carve-outs, do payment milestones actually align with delivery. Same engagement, same vendor relationship, two documents that need two different reviews.",
      },
      {
        heading: 'Re-review works the same way for both',
        content:
          "When a document comes back revised -- a buyer restates its evaluation criteria after vendor pushback, or a vendor redlines the SOW's liability section during negotiation -- the re-review runs against the previous findings rather than starting over. A fix is verified by the re-review actually confirming the clause changed, not by a reviewer checking a box that says it was addressed. That holds whether the document under revision is an RFP going back out to bidders or a SOW going back and forth between counsel on both sides.",
      },
      {
        heading: 'The same discipline, applied elsewhere',
        content:
          "The evidence-first discipline behind this -- every finding quotes its source, every number is computed by code, and the model is asked to judge only what code structurally cannot -- is not specific to RFPs and SOWs. It is the same approach behind ScopeSense's MITRE ATT&CK coverage assessment and its code security review module: deterministic checks do what deterministic checks can do reliably, and judgment is reserved for the parts that actually require it. See [RFP review in practice](/use-cases/rfp-review) for how this plays out on a real evaluation-criteria gap.",
      },
    ],
  },
];

export function getBlogPost(slug: string): BlogPost | undefined {
  return BLOG_POSTS.find((post) => post.slug === slug);
}

export type GlossarySection = {
  heading: string;
  body: string;
};

export type GlossaryEntry = {
  slug: string;
  term: string;
  shortDefinition: string;
  keyPoints: string[];
  sections: GlossarySection[];
  scopewiseNote: string;
  keywords: string[];
  relatedUseCase: '/use-cases/sow-review' | '/use-cases/rfp-review' | '/use-cases/scope-creep-prevention';
};

export const GLOSSARY_ENTRIES: GlossaryEntry[] = [
  {
    slug: 'liability-cap',
    term: 'Liability Cap',
    shortDefinition:
      'A liability cap is a contract clause that limits the total amount one party can be required to pay the other if something goes wrong.',
    keyPoints: [
      'Sets a ceiling on how much a vendor or client can be forced to pay in damages.',
      'Usually a multiple of fees paid (e.g. 12 months) or a fixed dollar amount.',
      'Almost always has carve-outs -- categories that stay uncapped.',
      'One of the highest-leverage clauses to check in a SOW or MSA.',
    ],
    sections: [
      {
        heading: 'What it covers',
        body: 'A liability cap (or "limitation of liability") applies to general damages -- lost profits, delays, rework costs. It doesn\'t erase risk, it bounds it: without a cap, a party can in theory be sued for the full extent of a loss, however large.',
      },
      {
        heading: 'Why the carve-outs matter',
        body: 'Most caps exclude specific categories -- confidentiality breaches, gross negligence, willful misconduct, IP infringement, indemnification obligations. An uncapped category can swallow the protection the cap was meant to provide, so the carve-out list matters as much as the cap amount.',
      },
    ],
    scopewiseNote:
      "ScopeWise's Commercial agent checks every SOW for the presence, amount, and carve-out structure of liability caps, flagging missing or unusually asymmetric caps as a finding.",
    keywords: ['liability cap', 'limitation of liability', 'carve-outs', 'general damages'],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'indemnification-clause',
    term: 'Indemnification Clause',
    shortDefinition:
      'An indemnification clause requires one party to compensate the other for losses, damages, or legal claims arising from specific events, such as IP infringement or a data breach.',
    keyPoints: [
      'Shifts financial responsibility for a defined category of loss from one party to the other.',
      'Commonly covers IP infringement, confidentiality breaches, data breaches, and third-party injury or property damage.',
      'Mutuality -- does it run both ways, or only one direction -- determines how fair it is.',
      'Frequently carved out of the liability cap entirely, meaning it can be uncapped.',
    ],
    sections: [
      {
        heading: 'How it works',
        body: "If Party A agrees to indemnify Party B against IP infringement claims, and a third party sues Party B for using material Party A supplied, Party A covers B's losses -- including legal defense costs -- even though B is the one being sued.",
      },
      {
        heading: 'What triggers it',
        body: "SOWs and MSAs commonly indemnify against intellectual property infringement, breach of confidentiality, data breaches and security incidents, and third-party bodily injury or property damage. Some also cover violation of law. What triggers indemnification -- and what's explicitly excluded -- defines how much real protection it provides.",
      },
    ],
    scopewiseNote:
      "ScopeWise's Legal agent reviews indemnification language for scope, mutuality, and how it interacts with the liability cap elsewhere in the document, flagging one-sided or unusually broad obligations.",
    keywords: ['indemnify', 'mutuality', 'liability cap', 'hold harmless'],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'scope-creep',
    term: 'Scope Creep',
    shortDefinition:
      "Scope creep is the uncontrolled expansion of a project's deliverables or requirements beyond what was originally agreed, usually without a corresponding adjustment to budget or timeline.",
    keyPoints: [
      "Uncontrolled expansion of a project's deliverables beyond what was agreed.",
      'Usually happens incrementally -- one small addition at a time, not a single dramatic change.',
      'Rooted in vague deliverable language, missing acceptance criteria, or no change-control process.',
      'Erodes margins, blows through timelines, and creates friction between the parties.',
    ],
    sections: [
      {
        heading: 'Where it comes from',
        body: "A client asks for \"just one more\" feature, a stakeholder assumes something was included that wasn't explicitly excluded, or vague deliverable language gets interpreted more broadly by one side than the other intended. It's a documentation problem before it's a project-management problem.",
      },
      {
        heading: 'How to prevent it',
        body: 'Four defenses: precise, testable deliverable definitions; explicit exclusions (what is not included, not just what is); a defined acceptance-criteria process for each deliverable; and a change-control clause requiring any scope addition to go through a written, priced amendment first.',
      },
    ],
    scopewiseNote:
      "ScopeWise's Scope agent is built to catch the root causes before signature -- vague deliverable language, missing acceptance criteria, absent change-control process -- rather than waiting to catch the symptom after a project is already underway.",
    keywords: ['scope creep', 'acceptance criteria', 'change-control', 'deliverable'],
    relatedUseCase: '/use-cases/scope-creep-prevention',
  },
  {
    slug: 'msa',
    term: 'MSA (Master Service Agreement)',
    shortDefinition:
      'An MSA is a foundational contract between two parties that sets the general legal and commercial terms governing all future work, with specific projects then defined in separate SOWs.',
    keyPoints: [
      'Foundational contract that sets legal and commercial terms for all future work between two parties.',
      'Covers payment terms, IP ownership, liability caps, termination, dispute resolution, governing law.',
      'Individual projects are then defined in separate SOWs that reference it.',
      'Lets repeat engagements turn around in days instead of weeks.',
    ],
    sections: [
      {
        heading: 'How MSA + SOW work together',
        body: "Once an MSA is in place, each SOW adds project-specific scope, deliverables, timeline, and price -- without restating legal boilerplate every time. This only works if the MSA is comprehensive enough that SOWs don't need to re-litigate liability, IP, or termination terms.",
      },
      {
        heading: 'The common failure mode',
        body: 'A SOW tries to change the liability cap or IP ownership terms set in the MSA without an explicit amendment. Most MSAs state an order of precedence for conflicts -- but that precedence clause needs to actually be checked against what the SOW says, not assumed.',
      },
    ],
    scopewiseNote:
      "When ScopeWise reviews a SOW that references an MSA, it's worth confirming the MSA itself has been reviewed for the terms that carry through to every SOW signed under it -- liability, indemnification, IP ownership.",
    keywords: ['MSA', 'SOW', 'liability cap', 'order of precedence'],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'sow',
    term: 'SOW (Statement of Work)',
    shortDefinition:
      'A Statement of Work (SOW) is a document that defines the specific scope, deliverables, timeline, and price for a project, typically issued under a broader MSA or as a standalone contract.',
    keyPoints: [
      'Defines the specific scope, deliverables, timeline, and price for a project.',
      'Turns a general agreement to work together into an executable project.',
      'Usually issued under a broader MSA, or as a standalone contract.',
      'Reviewed fastest and under the most time pressure -- where risk most often slips through.',
    ],
    sections: [
      {
        heading: 'What a well-written SOW looks like',
        body: 'Deliverables are concrete and testable -- "a responsive e-commerce site with these 12 pages and features" rather than "a modern website." It defines acceptance criteria for each deliverable, states explicit exclusions, and includes a change-control process for new requests.',
      },
      {
        heading: 'Where risk slips through',
        body: "Because a SOW is usually reviewed by whoever needs the project started -- not a lawyer -- vague deliverables, missing liability caps, undefined SLAs, and unrealistic timelines commonly slip through unnoticed until a project is already underway.",
      },
    ],
    scopewiseNote:
      'This is the exact document type ScopeWise is built to review: it parses a SOW, runs six specialist AI agents and a rule engine against it, and returns a risk-scored review before you sign.',
    keywords: ['SOW', 'acceptance criteria', 'change-control', 'deliverables'],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'rfp',
    term: 'RFP (Request for Proposal)',
    shortDefinition:
      'An RFP is a formal document a buyer issues to solicit priced, competitive proposals from vendors for a defined piece of work, evaluated against stated criteria.',
    keyPoints: [
      'Solicits competitive, priced proposals from multiple vendors, not a single agreed scope.',
      'States evaluation criteria upfront -- how submissions will be scored and compared.',
      'Defines a submission deadline, Q&A window, and award timeline.',
      'A vendor\'s winning response typically becomes the basis for the eventual SOW.',
    ],
    sections: [
      {
        heading: 'How an RFP differs from a SOW',
        body: 'A SOW defines work both parties have already agreed to; an RFP is issued before that agreement exists, to a pool of vendors who don\'t yet have the engagement. It asks vendors to propose their own approach, timeline, and price against the buyer\'s stated requirements, rather than confirming terms already negotiated.',
      },
      {
        heading: 'What makes an RFP well-structured',
        body: 'A strong RFP states clear evaluation criteria and weighting, a defined submission format, a firm deadline, a structured Q&A process for vendor questions, and enough scope detail that vendors can price accurately. Missing any of these produces proposals that aren\'t comparable to each other, which defeats the point of running a competitive process.',
      },
    ],
    scopewiseNote:
      "ScopeWise's Scope, Delivery, and Commercial agents run doc-type-aware checks for RFPs -- looking for defined evaluation criteria, a submission deadline and Q&A window, and disclosed budget or pricing format -- backed by a separate RFP rule set distinct from the SOW rules.",
    keywords: ['RFP', 'evaluation criteria', 'submission deadline', 'competitive proposal'],
    relatedUseCase: '/use-cases/rfp-review',
  },
  {
    slug: 'rfi',
    term: 'RFI (Request for Information)',
    shortDefinition:
      'An RFI is a preliminary document a buyer sends to vendors to gather information about their capabilities, approach, or market offerings, without asking for a priced proposal.',
    keyPoints: [
      'Informational, not competitive -- there\'s no pricing ask and usually no formal scoring.',
      'Used earlier than an RFP, often to shortlist vendors or scope out a market before a formal solicitation.',
      'Responses feed into how a later RFP or SOW gets written, rather than resulting in an award.',
      'Lighter-weight than an RFP: fewer mandatory sections, less legal boilerplate.',
    ],
    sections: [
        {
          heading: 'Where it fits in the buying process',
          body: 'A buyer unsure which vendors can even do the work, or unsure how to scope it, sends an RFI to gather capability information, rough approach, and sometimes ballpark cost ranges. It\'s a research step, and the vendor responses typically shape the requirements and evaluation criteria the buyer later puts into a formal RFP.',
        },
        {
          heading: 'Why it shouldn\'t be treated like an RFP',
          body: 'Because an RFI doesn\'t ask for a binding price or commit either side to anything, running it through the same lens as a competitive RFP review misses the point -- there\'s no award decision or evaluation-criteria comparison to check, just whether the request gathered the information the buyer actually needed.',
        },
    ],
    scopewiseNote:
      "ScopeWise's RFP review pipeline is built around solicitations that ask vendors for a priced proposal -- the Commercial agent's RFP checks specifically look for budget or pricing-format disclosure, which an RFI by design doesn't include, so RFIs sit outside what that pipeline is tuned to evaluate today.",
    keywords: ['RFI', 'vendor capability', 'market research', 'pre-RFP'],
    relatedUseCase: '/use-cases/rfp-review',
  },
  {
    slug: 'deliverable-acceptance-criteria',
    term: 'Deliverable Acceptance Criteria',
    shortDefinition:
      'Acceptance criteria are the specific, testable conditions a deliverable must meet before the client is obligated to accept it and payment is triggered.',
    keyPoints: [
      'Defines exactly what "done" means for a deliverable, not just what the deliverable is.',
      'Should be testable -- pass/fail, not subjective judgment calls.',
      'Directly tied to payment milestones in most SOWs.',
      'The single most common gap that lets scope creep and payment disputes happen.',
    ],
    sections: [
      {
        heading: 'What good acceptance criteria look like',
        body: 'Instead of "the platform will be tested," good acceptance criteria state "the platform passes UAT with zero critical defects and 99.9% uptime over a 30-day hypercare window." The difference is testability -- either the condition was met or it wasn\'t, with no room for one party to argue it depending on interpretation.',
      },
      {
        heading: 'What happens when they\'re missing',
        body: 'Without defined acceptance criteria, a deliverable can be technically complete by the vendor\'s standard and still get rejected by the client\'s, with no contractual basis to resolve the disagreement. That ambiguity is exactly where payment gets withheld, timelines slip, and relationships sour.',
      },
    ],
    scopewiseNote:
      "ScopeWise's Scope agent explicitly extracts whether acceptance criteria are present for each deliverable, quotes the criteria text when it exists, and flags missing acceptance criteria as a finding -- one of its highest-confidence risk categories since it's based on explicit absence, not inference.",
    keywords: ['acceptance criteria', 'deliverable', 'UAT', 'payment milestone'],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'fixed-price-contract',
    term: 'Fixed-Price Contract',
    shortDefinition:
      'A fixed-price contract sets a single agreed price for a defined scope of work, regardless of how many hours or resources it actually takes to deliver.',
    keyPoints: [
      'One agreed price for a defined scope -- the vendor bears the risk if it takes longer than estimated.',
      'Only works when the scope is precise enough to price accurately upfront.',
      'Out-of-scope work needs its own defined rate or change-order process, since the fixed price doesn\'t cover it.',
      'Puts more pressure on tight deliverable and acceptance-criteria language than T&M does.',
    ],
    sections: [
      {
        heading: 'When it makes sense',
        body: 'Fixed price suits well-understood, well-scoped work where both sides can estimate effort with confidence -- a defined website build, a known data migration. It gives the client budget certainty, and shifts execution-efficiency risk onto the vendor.',
      },
      {
        heading: 'Where it breaks down',
        body: 'If the scope is vague or the requirements are still evolving, a fixed price forces one side to absorb the mismatch: the vendor eats the cost of extra work, or the client gets a rushed, cut-corners result. This is why fixed-price SOWs need the tightest deliverable definitions and the clearest out-of-scope pricing of any pricing model.',
      },
    ],
    scopewiseNote:
      "ScopeWise's Commercial agent extracts the pricing model (fixed price, time-and-materials, or hybrid) from every SOW, and cross-checks fixed-price engagements specifically for whether out-of-scope work has its own defined rate -- since a fixed price with no defined overage rate is a common source of unbilled scope creep.",
    keywords: ['fixed price', 'pricing model', 'out-of-scope pricing', 'change order'],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'time-and-materials-contract',
    term: 'Time-and-Materials Contract',
    shortDefinition:
      'A time-and-materials (T&M) contract bills the client based on actual hours worked and materials used, at agreed rates, rather than a single fixed price for the whole scope.',
    keyPoints: [
      'Client pays for actual effort and materials, at pre-agreed rates -- not a flat sum for the whole job.',
      'Shifts the risk of scope uncertainty onto the client rather than the vendor.',
      'Usually paired with a not-to-exceed cap or periodic budget check-ins to control cost.',
      'Suits work where requirements are expected to evolve, like ongoing development or discovery-phase engagements.',
    ],
    sections: [
      {
        heading: 'How it differs from fixed price',
        body: 'Where a fixed-price contract locks in one number regardless of actual effort, T&M bills for whatever hours and materials the work actually consumes, at a rate card agreed in advance. That flexibility is the point for work whose scope can\'t be fully known upfront -- but it also means the client\'s total cost isn\'t capped unless the contract adds one.',
      },
      {
        heading: 'What to check for',
        body: 'A T&M SOW without a not-to-exceed cap, budget-tracking cadence, or periodic client sign-off on hours can run well past what either side expected, with no contractual point where the client can push back. The rate card itself -- who bills at what rate, and whether it escalates -- also needs to be explicit, not left to a vague "standard rates" reference.',
      },
    ],
    scopewiseNote:
      "ScopeWise's Commercial agent identifies time-and-materials pricing from the pricing model extraction and checks whether an escalation clause or cost-overrun control (like a not-to-exceed cap) is defined, flagging its absence as a commercial risk since uncapped T&M is the clearest path to a runaway bill.",
    keywords: ['time and materials', 'T&M', 'not-to-exceed', 'rate card'],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'force-majeure',
    term: 'Force Majeure',
    shortDefinition:
      'A force majeure clause excuses a party from contractual obligations, without penalty, when performance is prevented by extraordinary events outside its reasonable control.',
    keyPoints: [
      'Covers events like natural disasters, war, government action, or pandemics that make performance impossible, not just harder.',
      'Doesn\'t excuse payment obligations for work already delivered -- only future performance during the event.',
      'The list of covered events, and how "reasonable control" is defined, determines how broadly it can be invoked.',
      'A vaguely worded clause can be stretched to excuse ordinary business risk it was never meant to cover.',
    ],
    sections: [
      {
        heading: 'What it does and doesn\'t excuse',
        body: 'A force majeure clause suspends -- or in extended cases, terminates -- a party\'s obligations when an extraordinary, unforeseeable event outside its control makes performance impossible. It\'s not a general excuse for missed deadlines or cost overruns; most clauses specifically exclude events a party could have reasonably planned around, like routine supplier delays.',
      },
      {
        heading: 'Why the wording matters',
        body: 'A tightly drafted clause lists specific triggering events and requires prompt notice; a loosely drafted one relies on open-ended language like "acts beyond a party\'s reasonable control," which can be argued to cover almost anything. The second version is harder to enforce predictably, and is exactly the kind of phrasing worth flagging rather than assuming it means what it sounds like.',
      },
    ],
    scopewiseNote:
      "Force majeure isn't a dedicated extraction field for ScopeWise's Legal agent today, but the clause language is covered by its broader legal-risk review, and the cross-cutting ambiguous-language scan separately flags undefined trigger phrasing like \"beyond reasonable control\" wherever it appears in the document.",
    keywords: ['force majeure', 'excused performance', 'ambiguous language', 'notice period'],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'termination-for-convenience',
    term: 'Termination for Convenience',
    shortDefinition:
      'A termination-for-convenience clause lets either party end the contract without cause -- for any reason or no reason -- typically subject to a defined notice period.',
    keyPoints: [
      'Doesn\'t require a breach or default -- either party can walk away for any reason.',
      'Almost always requires advance written notice, commonly 30 to 90 days.',
      'Needs clear terms for what happens to in-progress work, payment for work completed, and any wind-down costs.',
      'Distinct from termination for cause, which requires a breach and usually a cure period first.',
    ],
    sections: [
      {
        heading: 'Why it exists',
        body: 'Business circumstances change -- budgets get cut, priorities shift, a project no longer makes sense -- and termination for convenience gives either party an exit that doesn\'t require proving the other side did something wrong. In exchange for that flexibility, it typically comes with a notice period so the other party isn\'t left stranded without warning.',
      },
      {
        heading: 'What needs to be defined alongside it',
        body: 'A convenience-termination clause without clear payment terms for work-in-progress leaves an obvious dispute waiting to happen: does the vendor get paid for partially delivered milestones, unbilled hours, or wind-down costs like reassigning staff? The clause is incomplete if it states the right to terminate without also stating what gets settled when it\'s exercised.',
      },
    ],
    scopewiseNote:
      "ScopeWise's Legal agent explicitly extracts whether termination for convenience is defined and with what notice period -- separate from termination for cause and its cure period -- and flags a missing termination clause as a legal risk category on its own.",
    keywords: ['termination for convenience', 'notice period', 'termination for cause', 'wind-down'],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'sla',
    term: 'SLA (Service Level Agreement)',
    shortDefinition:
      'An SLA is a defined commitment for the level of service a vendor will provide on an ongoing basis, typically stating response times, resolution times, and uptime targets.',
    keyPoints: [
      'States measurable commitments -- response time, resolution time, uptime -- not general quality intentions.',
      'Matters most for ongoing or retainer-style engagements, less for one-time project delivery.',
      'Usually tiered by severity: critical issues get faster response/resolution targets than low-priority ones.',
      'Should specify support hours and, ideally, the penalty or credit if the SLA is missed.',
    ],
    sections: [
      {
        heading: 'What a real SLA states',
        body: 'A usable SLA gives numbers, not adjectives: "critical incidents acknowledged within 1 hour, resolved within 4 hours, 24x7 support" rather than "prompt support." It also defines what counts as each severity tier, since "critical" means nothing without a shared definition of what qualifies.',
      },
      {
        heading: 'Why it\'s easy to miss',
        body: 'SLAs are often assumed to be implicit in an ongoing engagement rather than explicitly written, especially when the SOW is focused on describing the initial build rather than the support period that follows it. That gap surfaces later, when an incident happens and neither side has an agreed standard for how fast a response should be.',
      },
    ],
    scopewiseNote:
      "ScopeWise's PMO agent extracts whether an SLA is defined for the engagement, along with response time, resolution time, and support hours, and flags a missing SLA as an operational risk for any ongoing or retainer-style SOW.",
    keywords: ['SLA', 'response time', 'resolution time', 'uptime'],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'warranty-clause',
    term: 'Warranty Clause',
    shortDefinition:
      'A warranty clause commits the vendor to fixing defects in delivered work, at no extra cost, for a defined period after delivery -- and separately, often disclaims other implied warranties.',
    keyPoints: [
      'Guarantees the vendor will remedy defects found within a set window after delivery, free of charge.',
      'Distinct from a hypercare or support period -- warranty is about fixing defects, not general assistance.',
      'Contracts commonly pair an express warranty with a disclaimer of broader implied warranties.',
      'A short or missing warranty period leaves the client with no contractual recourse once the project closes.',
    ],
    sections: [
      {
        heading: 'What it actually covers',
        body: 'A warranty clause typically states that for some period after go-live -- 30, 60, or 90 days is common -- the vendor will fix defects in the delivered work at no additional charge, as opposed to billing it as new work. It\'s narrower than general support: cosmetic preferences or new feature requests during the warranty window usually aren\'t covered, only genuine defects against what was agreed.',
      },
      {
        heading: 'The disclaimer side',
        body: 'Many contracts pair the express warranty with language disclaiming broader implied warranties -- like fitness for a particular purpose -- that might otherwise apply under general commercial law. Whether that disclaimer is present, and how one-sided it is, matters as much as the warranty period itself.',
      },
    ],
    scopewiseNote:
      "ScopeWise's Legal agent extracts whether a warranty is defined and flags missing warranty language as a legal risk, while the Delivery agent separately checks whether a warranty period is defined alongside the post-go-live hypercare window -- since the two commonly get confused but cover different things.",
    keywords: ['warranty', 'defect remediation', 'implied warranty', 'hypercare'],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'limitation-of-liability',
    term: 'Limitation of Liability',
    shortDefinition:
      'Limitation of liability is the broader category of contract language that restricts what a party can be held responsible for -- of which a dollar-amount liability cap is one specific mechanism, not the whole clause.',
    keyPoints: [
      'A broader clause type than a liability cap alone -- it can also exclude categories of damages entirely, not just cap the dollar amount.',
      'Commonly excludes "consequential" or "indirect" damages (like lost profits) regardless of any dollar cap.',
      'A liability cap is one specific tool within it: the ceiling on damages that remain in scope after exclusions are applied.',
      'A contract can have a strong-looking cap and still leave a party heavily exposed if the exclusions and carve-outs are poorly drafted.',
    ],
    sections: [
      {
        heading: 'How it relates to a liability cap',
        body: 'Limitation of liability is the umbrella: it covers what types of damages are recoverable at all, which categories are carved out and left uncapped, and, within that, what the dollar ceiling is on what remains. A liability cap specifically is that dollar ceiling -- so a document can have a liability cap of "12 months\' fees" while its limitation-of-liability language separately excludes consequential damages entirely, which changes the real exposure far more than the cap number does.',
      },
      {
        heading: 'Why treating them as the same thing is a mistake',
        body: 'Reviewing only the cap amount and assuming that\'s the whole protection misses the exclusions doing most of the real work -- a generous-sounding cap paired with no consequential-damages exclusion can expose a party to far more than a modest cap paired with a well-drafted exclusion list. Both need to be read together, not the cap number in isolation.',
      },
    ],
    scopewiseNote:
      "ScopeWise's Legal agent extracts the limitation-of-liability clause as a whole -- including whether it's missing or uncapped -- while the Commercial agent separately checks the specific cap amount and carve-out structure documented in the liability-cap entry; a finding from either can surface without the other, since they check different parts of the same clause.",
    keywords: ['limitation of liability', 'consequential damages', 'liability cap', 'exclusions'],
    relatedUseCase: '/use-cases/sow-review',
  },
];

export function getGlossaryEntry(slug: string): GlossaryEntry | undefined {
  return GLOSSARY_ENTRIES.find((entry) => entry.slug === slug);
}

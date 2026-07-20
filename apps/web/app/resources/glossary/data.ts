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
];

export function getGlossaryEntry(slug: string): GlossaryEntry | undefined {
  return GLOSSARY_ENTRIES.find((entry) => entry.slug === slug);
}

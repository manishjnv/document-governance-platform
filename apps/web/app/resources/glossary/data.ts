export type GlossaryEntry = {
  slug: string;
  term: string;
  shortDefinition: string;
  body: string[];
  relatedUseCase: '/use-cases/sow-review' | '/use-cases/rfp-review' | '/use-cases/scope-creep-prevention';
};

export const GLOSSARY_ENTRIES: GlossaryEntry[] = [
  {
    slug: 'liability-cap',
    term: 'Liability Cap',
    shortDefinition:
      'A liability cap is a contract clause that limits the total amount one party can be required to pay the other if something goes wrong.',
    body: [
      'A liability cap (or "limitation of liability") sets a ceiling on how much a vendor or client can be forced to pay in damages if the contract is breached or something goes wrong during the engagement. Without one, a party can in theory be sued for the full extent of the loss it causes, however large -- with a cap, the exposure is bounded to a defined amount, most commonly a multiple of fees paid (e.g. 12 months of fees) or a fixed dollar figure.',
      'Liability caps typically apply to general damages -- things like lost profits, delays, or rework costs. Most caps carry carve-outs for specific categories that stay uncapped, such as breaches of confidentiality, gross negligence, willful misconduct, IP infringement, or indemnification obligations. The exact list of carve-outs matters as much as the cap amount itself, since an uncapped category can swallow the protection the cap was meant to provide.',
      'In a SOW or MSA, the liability cap is one of the highest-leverage clauses to review carefully. A missing cap exposes a vendor (or a client, depending on which side the clause runs against) to unlimited liability from a single dispute. A cap set too low relative to project value can leave the counterparty under-protected if the vendor fails badly. Because liability caps interact directly with indemnification and insurance requirements elsewhere in the same document, they need to be read as part of the whole risk picture, not in isolation.',
      'ScopeWise\'s Commercial agent specifically checks for the presence, amount, and carve-out structure of liability caps in every SOW it reviews, flagging missing or unusually asymmetric caps as a finding.',
    ],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'indemnification-clause',
    term: 'Indemnification Clause',
    shortDefinition:
      'An indemnification clause requires one party to compensate the other for losses, damages, or legal claims arising from specific events, such as IP infringement or a data breach.',
    body: [
      'An indemnification clause (also called a "hold harmless" clause) shifts the financial responsibility for a defined category of loss from one party to the other. If Party A agrees to indemnify Party B against IP infringement claims, and a third party sues Party B for using infringing material Party A supplied, Party A covers Party B\'s losses, including legal defense costs, even though B is the one being sued.',
      'Indemnification clauses in SOWs and MSAs commonly cover intellectual property infringement, breach of confidentiality, data breaches and security incidents, and third-party bodily injury or property damage caused by the indemnifying party\'s work. Some contracts also indemnify against the indemnifying party\'s violation of law. The scope of what triggers indemnification -- and what\'s explicitly excluded -- defines how much real protection the clause provides.',
      'Two details determine whether an indemnification clause is fair or one-sided: mutuality (does it run both ways, or only in one direction?) and its interaction with the liability cap. Indemnification obligations are frequently carved out of the liability cap entirely, meaning they\'re uncapped even when the rest of the contract\'s liability is limited -- which is by design for high-severity risks like IP infringement, but worth knowing about going in, since it means the true financial exposure of the contract can be much larger than the stated cap suggests.',
      'ScopeWise\'s Legal agent reviews indemnification language for scope, mutuality, and how it interacts with the liability cap elsewhere in the document, flagging one-sided or unusually broad indemnification obligations.',
    ],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'scope-creep',
    term: 'Scope Creep',
    shortDefinition:
      'Scope creep is the uncontrolled expansion of a project\'s deliverables or requirements beyond what was originally agreed, usually without a corresponding adjustment to budget or timeline.',
    body: [
      'Scope creep happens when a project\'s work grows past its original boundaries incrementally, one small addition at a time, rather than through a single dramatic change. A client asks for "just one more" feature, a stakeholder assumes something was included that wasn\'t explicitly excluded, or ambiguous deliverable language gets interpreted more broadly by one side than the other intended. Individually, each addition seems minor. Collectively, they erode margins, blow through timelines, and create friction between the parties delivering and receiving the work.',
      'Scope creep is fundamentally a documentation problem before it\'s a project-management problem. It happens most often when a SOW defines deliverables vaguely ("provide ongoing support," "design a modern website") instead of concretely (specific features, specific page counts, specific support-hour limits), when acceptance criteria are missing so there\'s no objective test for whether a deliverable is "done," or when the change-control process for handling new requests isn\'t defined, so new asks get absorbed informally instead of going through a scoped, priced change order.',
      'The standard defenses against scope creep are: precise, testable deliverable definitions; explicit exclusions (stating what is *not* included, not just what is); a defined acceptance-criteria process for each deliverable; and a change-control clause that requires any scope addition to go through a written, priced amendment before work starts on it. A SOW that has all four is far less likely to drift than one that has none.',
      'ScopeWise\'s Scope agent is built specifically to catch the root causes of scope creep before signature -- vague deliverable language, missing acceptance criteria, and absent change-control process -- rather than waiting to catch the symptom after a project is already underway.',
    ],
    relatedUseCase: '/use-cases/scope-creep-prevention',
  },
  {
    slug: 'msa',
    term: 'MSA (Master Service Agreement)',
    shortDefinition:
      'An MSA is a foundational contract between two parties that sets the general legal and commercial terms governing all future work, with specific projects then defined in separate SOWs.',
    body: [
      'A Master Service Agreement (MSA) establishes the standing legal relationship between a client and a vendor before any specific project exists. It covers the terms that would otherwise have to be renegotiated for every engagement: payment terms, confidentiality and IP ownership, liability caps and indemnification, termination rights, dispute resolution, insurance requirements, and governing law. Once an MSA is in place, individual projects are defined through Statements of Work (SOWs) that reference the MSA and add project-specific scope, deliverables, timeline, and price, without having to restate the legal boilerplate each time.',
      'The MSA-plus-SOW structure exists to make repeat engagements faster. A client and vendor who expect to work together on multiple projects negotiate the MSA once, carefully, and then each subsequent SOW can be turned around in days rather than weeks because the hard legal terms are already settled. This only works, though, if the MSA is actually comprehensive enough that individual SOWs don\'t need to re-litigate liability, IP, or termination terms -- a thin MSA pushes that negotiation burden back onto every SOW.',
      'A common failure mode is a conflict between the MSA and a later SOW -- for example, a SOW that tries to change the liability cap or IP ownership terms set in the MSA without an explicit amendment. Most MSAs state an order of precedence (which document wins in a conflict), but that precedence clause needs to actually be checked against what the SOW says, not assumed.',
      'When ScopeWise reviews a SOW that references an MSA, it\'s worth confirming the MSA itself has been reviewed for the terms that matter most across every future engagement under it -- liability, indemnification, and IP ownership -- since those terms will carry through to every SOW signed under it unless explicitly overridden.',
    ],
    relatedUseCase: '/use-cases/sow-review',
  },
  {
    slug: 'sow',
    term: 'SOW (Statement of Work)',
    shortDefinition:
      'A Statement of Work (SOW) is a document that defines the specific scope, deliverables, timeline, and price for a project, typically issued under a broader MSA or as a standalone contract.',
    body: [
      'A Statement of Work (SOW) is the document that turns a general agreement to work together into a specific, executable project. It defines what will be delivered (the scope and deliverables), by when (the timeline and milestones), for how much (the price and payment schedule), and who is responsible for what (roles and dependencies). Where an MSA sets the legal ground rules for the relationship, the SOW is where the actual project gets specified.',
      'A well-written SOW makes deliverables concrete and testable rather than aspirational -- "deliver a responsive e-commerce website with the following 12 pages and features" rather than "build a modern website." It defines acceptance criteria for each deliverable (how will both sides agree it\'s done and correct), states explicit exclusions (what is *not* included, to prevent later disputes), and includes a change-control process for handling new requests that arise mid-project without letting them silently expand scope.',
      'Because a SOW is usually the document that gets reviewed fastest and under the most time pressure -- often by whoever needs the project started, not by a lawyer -- it\'s also the document where risk most commonly slips through: vague deliverables, missing liability caps (if not already set by an MSA), undefined SLAs, and unrealistic timelines that set a project up to fail from day one.',
      'This is the exact document type ScopeWise is built to review: it parses a SOW, runs six specialist AI agents and a rule engine against it, and returns a risk-scored review of scope, delivery, commercial, security, PMO, and legal issues before you sign.',
    ],
    relatedUseCase: '/use-cases/sow-review',
  },
];

export function getGlossaryEntry(slug: string): GlossaryEntry | undefined {
  return GLOSSARY_ENTRIES.find((entry) => entry.slug === slug);
}

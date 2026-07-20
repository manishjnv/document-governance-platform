import type { Metadata } from 'next';
import Link from 'next/link';
import { MarketingHeader } from '@/components/MarketingHeader';
import { MarketingFooter } from '@/components/MarketingFooter';

export const metadata: Metadata = {
  title: 'Scope Creep Prevention',
  description:
    'How scope creep starts in vague SOW language, and how ScopeWise catches undefined deliverables and missing acceptance criteria before signature.',
  alternates: { canonical: '/use-cases/scope-creep-prevention' },
};

const FAQS = [
  {
    q: 'Where does scope creep actually come from?',
    a: 'Almost always from the document, not the project. Deliverables described in general terms ("software enhancements"), scope boundaries with no explicit out-of-scope list, and phrases like "and other related work" or "as needed" leave room for either side to argue the current work item is or isn\'t covered.',
  },
  {
    q: 'Can an AI review really prevent scope creep, or just flag it?',
    a: 'ScopeWise flags it, in the document, before signature -- it does not manage scope during a live project. The prevention happens by catching ambiguous deliverable language and a missing change-control process at the review stage, when it\'s cheap to fix, instead of during execution, when it\'s expensive.',
  },
  {
    q: 'What is a change-control process, and why does ScopeWise check for one?',
    a: 'It\'s the documented process for how scope changes get proposed, approved, and priced once work has started. Without one, every "small addition" becomes a negotiation instead of a standard change request -- ScopeWise checks explicitly whether this process is defined in the document at all.',
  },
  {
    q: 'Does this apply to RFPs too, not just SOWs?',
    a: 'Scope creep as a concept is specific to SOWs, since RFPs define an evaluation process rather than delivered work. For RFPs, ScopeWise instead checks that the scope of the requested proposal and evaluation criteria are clearly defined -- see RFP review for that angle.',
  },
];

export default function ScopeCreepPreventionPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: FAQS.map((f) => ({
      '@type': 'Question',
      name: f.q,
      acceptedAnswer: { '@type': 'Answer', text: f.a },
    })),
  };

  return (
    <div className="min-h-screen bg-background">
      {/* eslint-disable-next-line react/no-danger */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <MarketingHeader />

      <main className="max-w-4xl mx-auto px-4 py-16">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">Scope creep prevention</h1>
        <p className="text-lg text-muted-foreground mb-12">
          Scope creep feels like a project-management problem, but it
          almost always starts as a document problem: a deliverable
          described loosely enough that reasonable people can disagree on
          whether a new request is &quot;part of the original work&quot; or
          a change. By the time it&apos;s visible on a status report,
          it&apos;s already too late to fix cheaply -- the fix has to
          happen in the SOW, before signature.
        </p>

        <h2 className="text-2xl font-bold mb-4">How scope creep originates in the SOW</h2>
        <div className="grid sm:grid-cols-2 gap-6 mb-12">
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Ambiguous deliverables</h3>
            <p className="text-sm text-muted-foreground">
              A deliverable like &quot;software enhancements&quot; with no
              specifics has no natural boundary -- there&apos;s no version
              of it that&apos;s obviously &quot;done,&quot; so it keeps
              absorbing new requests.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Undefined scope boundary</h3>
            <p className="text-sm text-muted-foreground">
              Language like &quot;best effort&quot; without limits, or no
              explicit out-of-scope list, means there&apos;s nothing in the
              document to point to when pushing back on a request.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">Open-ended catch-alls</h3>
            <p className="text-sm text-muted-foreground">
              Phrases like &quot;and other related work&quot; or &quot;including
              but not limited to&quot; are the single clearest textual
              signal of scope creep risk -- they explicitly leave the
              boundary open.
            </p>
          </div>
          <div className="rounded-lg border p-5">
            <h3 className="font-semibold mb-2">No change-control process</h3>
            <p className="text-sm text-muted-foreground">
              Without a defined process for proposing, approving, and
              pricing changes, every addition becomes an ad hoc
              negotiation instead of a standard, priced change request.
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-bold mb-4">How ScopeWise catches it before signature</h2>
        <p className="text-muted-foreground mb-4">
          The Scope agent is built specifically around this failure mode.
          For every SOW it reviews, it:
        </p>
        <ul className="list-disc pl-6 text-muted-foreground mb-6 space-y-2">
          <li>
            Extracts every stated deliverable and checks whether each one
            has a corresponding, explicit acceptance criterion -- a
            deliverable with no acceptance criteria is flagged as a
            structural gap, not a stylistic one.
          </li>
          <li>
            Flags language suggesting an open scope boundary --
            &quot;best effort&quot; without limits, &quot;and other related
            work,&quot; and similar catch-alls -- quoting the exact clause
            as evidence.
          </li>
          <li>
            Checks explicitly whether a change-control process is defined
            in the document at all, and flags its absence as a major risk
            when it&apos;s missing -- this is the single highest-leverage
            check for preventing creep once a project is underway.
          </li>
        </ul>
        <p className="text-muted-foreground mb-12">
          Alongside the Scope agent, the ambiguous-language scan
          independently flags open-ended phrases (&quot;as needed,&quot;
          &quot;as appropriate,&quot; &quot;etc.&quot;) anywhere in the
          document, and this framing follows the same deliverables-and-boundaries
          structure that scope-management methodology (PMBOK-style scope
          definition) is built around -- ScopeWise applies it as a
          pre-signature check rather than an in-flight management
          practice.
        </p>

        <div className="rounded-lg border p-6 mb-12">
          <h2 className="text-xl font-bold mb-4">FAQ</h2>
          <div className="space-y-5">
            {FAQS.map((f) => (
              <div key={f.q}>
                <h3 className="font-semibold mb-1">{f.q}</h3>
                <p className="text-sm text-muted-foreground">{f.a}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="text-center">
          <Link
            href="/pricing"
            className="inline-block rounded-md bg-primary text-primary-foreground px-6 py-3 font-medium hover:opacity-90 mb-4"
          >
            See pricing
          </Link>
          <p className="text-sm text-muted-foreground">
            Managing client SOWs at an agency?{' '}
            <Link href="/solutions/for-agencies" className="underline hover:no-underline">
              See ScopeWise for agencies
            </Link>
            .
          </p>
        </div>
      </main>

      <MarketingFooter />
    </div>
  );
}

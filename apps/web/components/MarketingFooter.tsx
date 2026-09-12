import Link from 'next/link';

const COLUMNS = [
  {
    h: 'Products',
    links: [
      { href: '/product/sow-review', label: 'SOW & RFP Review' },
      { href: '/product/mitre-coverage', label: 'MITRE ATT&CK Coverage' },
      { href: '/product/code-security-review', label: 'Code Security Review' },
    ],
  },
  {
    h: 'Solutions',
    links: [
      { href: '/solutions/for-procurement', label: 'For procurement' },
      { href: '/solutions/for-legal', label: 'For legal teams' },
      { href: '/solutions/for-agencies', label: 'For agencies' },
      { href: '/solutions/for-security-consultancies', label: 'For security consultancies' },
      { href: '/solutions/for-appsec-consultants', label: 'For AppSec consultants' },
    ],
  },
  {
    h: 'Resources',
    links: [
      { href: '/resources/blog', label: 'Blog' },
      { href: '/resources/glossary', label: 'Glossary' },
      { href: '/resources/templates', label: 'Templates' },
      { href: '/compare', label: 'Compare' },
      { href: '/use-cases/sow-review', label: 'SOW review' },
      { href: '/use-cases/rfp-review', label: 'RFP review' },
      { href: '/use-cases/scope-creep-prevention', label: 'Scope creep prevention' },
    ],
  },
  {
    h: 'Company',
    links: [
      { href: '/about', label: 'About' },
      { href: '/contact', label: 'Contact' },
      { href: '/privacy', label: 'Privacy' },
      { href: '/terms', label: 'Terms' },
    ],
  },
];

export function MarketingFooter() {
  return (
    <footer className="border-t">
      <div className="max-w-6xl mx-auto px-4 py-12">
        <nav aria-label="Footer" className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {COLUMNS.map((col) => (
            <div key={col.h}>
              <h2 className="text-sm font-semibold mb-3">{col.h}</h2>
              <ul className="space-y-2">
                {col.links.map((l) => (
                  <li key={l.href}>
                    <Link href={l.href} className="text-sm text-muted-foreground hover:text-primary">
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
        <div className="mt-10 pt-6 border-t flex flex-wrap items-center justify-between gap-4 text-sm text-muted-foreground">
          <span>&copy; {new Date().getFullYear()} ScopeWise</span>
          <span>Evidence-based risk reviews. Contracts, detections, code.</span>
        </div>
      </div>
    </footer>
  );
}

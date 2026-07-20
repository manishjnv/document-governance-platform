import Link from 'next/link';

export function MarketingFooter() {
  return (
    <footer className="border-t">
      <div className="max-w-6xl mx-auto px-4 py-8 flex items-center justify-between text-sm text-muted-foreground">
        <span>&copy; {new Date().getFullYear()} ScopeWise</span>
        <div className="flex gap-6">
          <Link href="/use-cases/sow-review" className="hover:text-primary">Use Cases</Link>
          <Link href="/solutions/for-procurement" className="hover:text-primary">Solutions</Link>
          <Link href="/resources/glossary" className="hover:text-primary">Glossary</Link>
          <Link href="/about" className="hover:text-primary">About</Link>
          <Link href="/contact" className="hover:text-primary">Contact</Link>
        </div>
      </div>
    </footer>
  );
}

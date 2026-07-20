import Link from 'next/link';
import { ShieldCheck } from 'lucide-react';

export function MarketingHeader() {
  return (
    <header className="border-b">
      <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <ShieldCheck className="h-5 w-5 text-primary" />
          ScopeWise
        </Link>
        <nav className="flex items-center gap-6 text-sm">
          <Link href="/product" className="hover:text-primary">Product</Link>
          <Link href="/use-cases/sow-review" className="hover:text-primary">Use Cases</Link>
          <Link href="/pricing" className="hover:text-primary">Pricing</Link>
          <Link href="/about" className="hover:text-primary">About</Link>
          <Link href="/login" className="rounded-md bg-primary text-primary-foreground px-4 py-2 hover:opacity-90">
            Sign in
          </Link>
        </nav>
      </div>
    </header>
  );
}

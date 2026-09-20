import Link from 'next/link';
import { ShieldCheck } from 'lucide-react';
import { MarketingNav } from '@/components/MarketingNav';

export function MarketingHeader() {
  return (
    <header className="border-b relative">
      <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <ShieldCheck className="h-5 w-5 text-primary" />
          ScopeSense
        </Link>
        <MarketingNav />
      </div>
    </header>
  );
}

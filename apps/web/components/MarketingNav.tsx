'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ChevronDown, Menu, X } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const PRODUCTS = [
  {
    href: '/product/sow-review',
    label: 'SOW & RFP Review',
    description: 'Contract risk, scored and evidenced',
  },
  {
    href: '/product/mitre-coverage',
    label: 'MITRE ATT&CK Coverage',
    description: 'Detection coverage by tactic, ranked gaps',
  },
  {
    href: '/product/code-security-review',
    label: 'Code Security Review',
    description: 'Scanner findings to client-ready report',
  },
];

const NAV_LINKS = [
  { href: '/solutions/for-procurement', label: 'Solutions' },
  { href: '/resources/blog', label: 'Resources' },
  { href: '/pricing', label: 'Pricing' },
];

const linkClass =
  'text-sm hover:text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary rounded-sm';

export function MarketingNav() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      <nav className="hidden md:flex items-center gap-6 text-sm">
        <DropdownMenu>
          <DropdownMenuTrigger className={`flex items-center gap-1 ${linkClass}`}>
            Products
            <ChevronDown className="h-4 w-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-72">
            {PRODUCTS.map((p) => (
              <DropdownMenuItem key={p.href} asChild>
                <Link href={p.href} className="flex flex-col items-start gap-0.5 py-2">
                  <span>{p.label}</span>
                  <span className="text-xs text-muted-foreground">{p.description}</span>
                </Link>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        {NAV_LINKS.map((l) => (
          <Link key={l.href} href={l.href} className={linkClass}>
            {l.label}
          </Link>
        ))}
        <Link
          href="/login"
          className="rounded-md bg-primary text-primary-foreground px-4 py-2 hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          Sign in
        </Link>
      </nav>

      <div className="flex md:hidden items-center gap-3">
        <Link
          href="/login"
          className="rounded-md bg-primary text-primary-foreground px-3 py-2 text-sm hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          Sign in
        </Link>
        <button
          type="button"
          onClick={() => setMobileOpen((v) => !v)}
          aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={mobileOpen}
          aria-controls="mobile-nav-panel"
          className="focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary rounded-sm"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {mobileOpen && (
        <div
          id="mobile-nav-panel"
          className="md:hidden absolute left-0 right-0 top-full border-b bg-background px-4 py-4 flex flex-col gap-4"
        >
          <div className="flex flex-col gap-2">
            <span className="text-xs font-semibold text-muted-foreground">Products</span>
            {PRODUCTS.map((p) => (
              <Link key={p.href} href={p.href} className={linkClass} onClick={() => setMobileOpen(false)}>
                {p.label}
              </Link>
            ))}
          </div>
          {NAV_LINKS.map((l) => (
            <Link key={l.href} href={l.href} className={linkClass} onClick={() => setMobileOpen(false)}>
              {l.label}
            </Link>
          ))}
        </div>
      )}
    </>
  );
}

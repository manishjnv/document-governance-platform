'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { FileText, LayoutDashboard, Search, Upload, Menu, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Documents', icon: LayoutDashboard },
  { href: '/upload', label: 'Upload', icon: Upload },
  { href: '/search', label: 'Search', icon: Search },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-1">
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname?.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={cn(
              'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              active
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            )}
          >
            <Icon size={16} strokeWidth={2} aria-hidden="true" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const router = useRouter();

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    router.push('/login');
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-56 flex-col border-r bg-background px-3 py-4 md:flex">
        <Link href="/dashboard" className="flex items-center gap-2 px-3 pb-1">
          <FileText size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
          <span className="text-sm font-semibold">ScopeWise</span>
        </Link>
        <p className="px-3 pb-5 text-xs text-muted-foreground">
          Catch contract risk before you sign.
        </p>
        <NavLinks />
        <div className="mt-auto">
          <Button variant="ghost" size="sm" className="w-full justify-start gap-2" onClick={handleLogout}>
            <LogOut size={16} strokeWidth={2} aria-hidden="true" />
            Log out
          </Button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="flex items-center justify-between border-b bg-background px-4 py-3 md:hidden">
        <Link href="/dashboard" className="flex items-center gap-2">
          <FileText size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
          <span className="text-sm font-semibold">ScopeWise</span>
        </Link>
        <Button variant="ghost" size="icon" aria-label="Open navigation menu" onClick={() => setMobileOpen(true)}>
          <Menu size={20} strokeWidth={2} />
        </Button>
      </header>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-64 p-4">
          <SheetTitle className="mb-4 flex items-center gap-2 text-sm">
            <FileText size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
            ScopeWise
          </SheetTitle>
          <NavLinks onNavigate={() => setMobileOpen(false)} />
          <Button
            variant="ghost"
            size="sm"
            className="mt-4 w-full justify-start gap-2"
            onClick={handleLogout}
          >
            <LogOut size={16} strokeWidth={2} aria-hidden="true" />
            Log out
          </Button>
        </SheetContent>
      </Sheet>

      <main className="md:pl-56">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">{children}</div>
      </main>
    </div>
  );
}

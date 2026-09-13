'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Bug, FileText, LayoutDashboard, Target, Menu, LogOut, ChevronLeft, ChevronRight, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { useResize } from '@/components/app/useResize';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/dashboard', label: 'SOW Review', icon: LayoutDashboard },
  { href: '/mitre', label: 'MITRE Assessment', icon: Target },
  { href: '/codereview', label: 'Code Security Review', icon: Bug },
];

const ADMIN_NAV_ITEM = { href: '/admin', label: 'Admin', icon: ShieldCheck };

const MIN_WIDTH = 180;
const MAX_WIDTH = 400;
const COLLAPSED_WIDTH = 56;
const STORAGE_KEY = 'sidebar_width';
const COLLAPSED_KEY = 'sidebar_collapsed';

function NavLinks({
  onNavigate,
  collapsed,
  isAdmin,
}: {
  onNavigate?: () => void;
  collapsed?: boolean;
  isAdmin?: boolean;
}) {
  const pathname = usePathname();
  const items = isAdmin ? [...NAV_ITEMS, ADMIN_NAV_ITEM] : NAV_ITEMS;
  return (
    <nav className="flex flex-col gap-1">
      {items.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname?.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            title={collapsed ? label : undefined}
            className={cn(
              'flex items-center gap-2.5 rounded-[7px] px-2.5 py-2 text-[13.5px] font-medium whitespace-nowrap overflow-hidden transition-colors duration-150 ease-app',
              collapsed && 'justify-center px-0',
              active
                ? 'bg-accent text-primary'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            )}
          >
            <Icon size={16} strokeWidth={2} aria-hidden="true" />
            {!collapsed && label}
          </Link>
        );
      })}
    </nav>
  );
}

export function AppShell({
  children,
  fullWidth = false,
}: {
  children: React.ReactNode;
  fullWidth?: boolean;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  // Default collapsed unless the user has an explicit saved preference.
  const [collapsed, setCollapsed] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const router = useRouter();

  const { width, resizing, gripProps } = useResize({
    storageKey: STORAGE_KEY,
    min: MIN_WIDTH,
    max: MAX_WIDTH,
    edge: 'right',
    fallback: 224,
  });

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((me) => setIsAdmin(me?.is_platform_admin === true))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const savedCollapsed = localStorage.getItem(COLLAPSED_KEY);
    if (savedCollapsed) setCollapsed(savedCollapsed === 'true');
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    router.push('/');
  };

  const toggleCollapsed = () => {
    setCollapsed((c) => {
      localStorage.setItem(COLLAPSED_KEY, String(!c));
      return !c;
    });
  };

  const effectiveWidth = collapsed ? COLLAPSED_WIDTH : width ?? 224;

  return (
    <div className="app-theme font-app min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside
        style={{ width: effectiveWidth }}
        className={cn(
          'fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-border bg-card px-2.5 py-3.5 md:flex',
          !resizing && 'transition-[width] duration-[180ms] ease-app'
        )}
      >
        <div className={cn('flex items-center gap-2.5 px-2 py-1', collapsed && 'justify-center px-0')}>
          <Link href="/dashboard" className="flex items-center gap-2.5 min-w-0">
            <FileText size={18} strokeWidth={2} className="text-primary shrink-0" aria-hidden="true" />
            {!collapsed && <span className="text-sm font-semibold truncate">ScopeWise</span>}
          </Link>
        </div>
        {!collapsed && (
          <p className="px-2 pb-3.5 text-[11.5px] text-ink3 whitespace-nowrap overflow-hidden">
            Catch contract risk before you sign.
          </p>
        )}
        {collapsed && <div className="pb-3.5" />}
        <NavLinks collapsed={collapsed} isAdmin={isAdmin} />
        <div className="mt-auto flex flex-col gap-1">
          {/* Collapse toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleCollapsed}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className={cn('w-full gap-2', collapsed ? 'justify-center px-0' : 'justify-start')}
          >
            {collapsed ? (
              <ChevronRight size={16} strokeWidth={2} aria-hidden="true" />
            ) : (
              <ChevronLeft size={16} strokeWidth={2} aria-hidden="true" />
            )}
            {!collapsed && 'Collapse'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className={cn('w-full gap-2', collapsed ? 'justify-center px-0' : 'justify-start')}
            onClick={handleLogout}
            title={collapsed ? 'Log out' : undefined}
          >
            <LogOut size={16} strokeWidth={2} aria-hidden="true" />
            {!collapsed && 'Log out'}
          </Button>
        </div>

        {/* Drag-to-resize handle */}
        {!collapsed && (
          <div
            {...gripProps}
            aria-label="Resize sidebar"
            className="absolute inset-y-0 right-0 hidden w-1.5 cursor-col-resize touch-none md:block hover:bg-accent focus-visible:bg-accent focus-visible:outline-none"
          />
        )}
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-border bg-card px-3.5 py-2.5 md:hidden">
        <Link href="/dashboard" className="flex items-center gap-2">
          <FileText size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
          <span className="text-sm font-semibold">ScopeWise</span>
        </Link>
        <Button variant="ghost" size="icon" aria-label="Open navigation menu" onClick={() => setMobileOpen(true)}>
          <Menu size={20} strokeWidth={2} />
        </Button>
      </header>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="flex w-64 flex-col bg-card p-4">
          <SheetTitle className="mb-3.5 flex items-center gap-2 text-sm">
            <FileText size={18} strokeWidth={2} className="text-primary" aria-hidden="true" />
            ScopeWise
          </SheetTitle>
          <NavLinks onNavigate={() => setMobileOpen(false)} isAdmin={isAdmin} />
          <Button
            variant="ghost"
            size="sm"
            className="mt-auto w-full justify-start gap-2"
            onClick={handleLogout}
          >
            <LogOut size={16} strokeWidth={2} aria-hidden="true" />
            Log out
          </Button>
        </SheetContent>
      </Sheet>

      <main
        style={{ '--sidebar-w': `${effectiveWidth}px` } as React.CSSProperties}
        className={cn(
          'md:[padding-left:var(--sidebar-w)]',
          !resizing && 'transition-[padding-left] duration-[180ms] ease-app'
        )}
      >
        <div
          className={cn(
            'mx-auto px-4 pb-10 pt-4 sm:px-7 sm:pb-12 sm:pt-6',
            fullWidth ? 'w-full' : 'max-w-[1240px]'
          )}
        >
          {children}
        </div>
      </main>
    </div>
  );
}

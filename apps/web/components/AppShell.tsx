'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Bug, FileText, LayoutDashboard, Target, Menu, LogOut, PanelLeftClose, PanelLeftOpen, Plus, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { useResize } from '@/components/app/useResize';
import { cn } from '@/lib/utils';

// Module-level actions shown under the active module so they stay reachable from detail pages.
// `match` is the pathname prefix that owns the module (e.g. /results/... belongs to SOW Review).
const NAV_ITEMS: NavItem[] = [
  {
    href: '/dashboard',
    label: 'SOW Review',
    icon: LayoutDashboard,
    match: ['/dashboard', '/results', '/upload'],
    actions: [{ href: '/upload', label: 'Upload document', primary: true }],
  },
  {
    href: '/mitre',
    label: 'MITRE Assessment',
    icon: Target,
    actions: [
      { href: '/mitre/new', label: 'New assessment', primary: true },
      { href: '/mitre/connections', label: 'SIEM connections' },
    ],
  },
  {
    href: '/codereview',
    label: 'Code Security Review',
    icon: Bug,
    actions: [
      { href: '/codereview/new', label: 'New review', primary: true },
      { href: '/codereview/new', label: 'Get scanner' },
    ],
  },
];

const ADMIN_NAV_ITEM: NavItem = { href: '/admin', label: 'Admin', icon: ShieldCheck };

type NavItem = {
  href: string;
  label: string;
  icon: typeof Bug;
  match?: string[];
  actions?: { href: string; label: string; primary?: boolean }[];
};

type Me = { email: string; first_name?: string | null; last_name?: string | null; is_platform_admin?: boolean };

function displayName(me: Me) {
  const name = [me.first_name, me.last_name].filter(Boolean).join(' ').trim();
  return name || me.email;
}

function initials(me: Me) {
  const name = displayName(me);
  const parts = name.includes('@') ? [name] : name.split(/\s+/);
  return parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? '').join('');
}

const MIN_WIDTH = 180;
const MAX_WIDTH = 400;
const COLLAPSED_WIDTH = 56;
const STORAGE_KEY = 'sidebar_width';
// v2: key bumped 2026-09-13 so every user starts expanded again; old 'sidebar_collapsed' is ignored.
const COLLAPSED_KEY = 'sidebar_collapsed_v2';

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
      {items.map(({ href, label, icon: Icon, match, actions }) => {
        const roots = match ?? [href];
        const active = roots.some((r) => pathname === r || pathname?.startsWith(`${r}/`));
        return (
          <div key={href} className="flex flex-col">
            <Link
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
            {active && !collapsed && actions && (
              <div className="ml-[15px] mt-0.5 mb-1 flex flex-col gap-0.5 border-l border-border pl-3">
                {actions.map((a) => (
                  <Link
                    key={a.label}
                    href={a.href}
                    onClick={onNavigate}
                    className={cn(
                      'flex items-center gap-1.5 rounded-[6px] px-2 py-1.5 text-[12.5px] whitespace-nowrap transition-colors duration-150 ease-app',
                      a.primary
                        ? 'font-medium text-primary hover:bg-accent'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    )}
                  >
                    {a.primary && <Plus size={13} strokeWidth={2.25} aria-hidden="true" />}
                    {a.label}
                  </Link>
                ))}
              </div>
            )}
          </div>
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
  // Default expanded unless the user has an explicit saved preference.
  const [collapsed, setCollapsed] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const isAdmin = me?.is_platform_admin === true;
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
      .then((data) => setMe(data && typeof data.email === 'string' ? data : null))
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
        <div className={cn('flex items-center gap-2.5 px-2 py-1', collapsed ? 'flex-col px-0' : 'justify-between')}>
          <Link href="/dashboard" className="flex items-center gap-2.5 min-w-0">
            <FileText size={18} strokeWidth={2} className="text-primary shrink-0" aria-hidden="true" />
            {!collapsed && <span className="text-sm font-semibold truncate">ScopeWise</span>}
          </Link>
          {/* Collapse toggle: outlined so it reads as a control, not a nav item */}
          <Button
            variant="outline"
            size="icon"
            onClick={toggleCollapsed}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className="h-7 w-7 shrink-0 text-muted-foreground hover:text-foreground"
          >
            {collapsed ? (
              <PanelLeftOpen size={15} strokeWidth={2} aria-hidden="true" />
            ) : (
              <PanelLeftClose size={15} strokeWidth={2} aria-hidden="true" />
            )}
          </Button>
        </div>
        {!collapsed && (
          <p className="px-2 pb-3.5 text-[11.5px] text-ink3 whitespace-nowrap overflow-hidden">
            Catch contract risk before you sign.
          </p>
        )}
        {collapsed && <div className="pb-3.5" />}
        <NavLinks collapsed={collapsed} isAdmin={isAdmin} />
        <div className="mt-auto flex flex-col gap-1">
          {me && (
            <div
              title={collapsed ? `${displayName(me)} · ${me.email}` : undefined}
              className={cn('flex items-center gap-2.5 border-t border-border pt-3 pb-1', collapsed ? 'justify-center px-0' : 'px-2')}
            >
              <span
                aria-hidden="true"
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent text-[11px] font-semibold text-primary"
              >
                {initials(me)}
              </span>
              {!collapsed && (
                <span className="min-w-0 flex flex-col leading-tight">
                  <span className="truncate text-[12.5px] font-medium text-foreground">{displayName(me)}</span>
                  {displayName(me) !== me.email && (
                    <span className="truncate text-[11px] text-muted-foreground">{me.email}</span>
                  )}
                </span>
              )}
            </div>
          )}
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
            title="Drag to resize"
            className={cn(
              // Always-visible centred pill so the handle is discoverable; whole strip highlights on hover/drag.
              'group absolute inset-y-0 -right-1 hidden w-2.5 cursor-col-resize touch-none md:block focus-visible:outline-none',
              'after:absolute after:left-1/2 after:top-1/2 after:h-9 after:w-1 after:-translate-x-1/2 after:-translate-y-1/2 after:rounded-full after:bg-border after:transition-colors after:duration-150',
              'hover:after:bg-primary focus-visible:after:bg-primary',
              resizing ? 'bg-primary/15 after:bg-primary' : 'hover:bg-primary/10'
            )}
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
          {me && (
            <div className="mt-auto flex items-center gap-2.5 border-t border-border px-2 pt-3 pb-1">
              <span
                aria-hidden="true"
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent text-[11px] font-semibold text-primary"
              >
                {initials(me)}
              </span>
              <span className="min-w-0 flex flex-col leading-tight">
                <span className="truncate text-[12.5px] font-medium text-foreground">{displayName(me)}</span>
                {displayName(me) !== me.email && (
                  <span className="truncate text-[11px] text-muted-foreground">{me.email}</span>
                )}
              </span>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            className={cn('w-full justify-start gap-2', !me && 'mt-auto')}
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

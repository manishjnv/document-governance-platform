'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { FileText, LayoutDashboard, Search, Upload, Menu, LogOut, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Documents', icon: LayoutDashboard },
  { href: '/upload', label: 'Upload', icon: Upload },
  { href: '/search', label: 'Search', icon: Search },
];

const MIN_WIDTH = 180;
const MAX_WIDTH = 400;
const COLLAPSED_WIDTH = 56;
const STORAGE_KEY = 'sidebar_width';
const COLLAPSED_KEY = 'sidebar_collapsed';

function NavLinks({ onNavigate, collapsed }: { onNavigate?: () => void; collapsed?: boolean }) {
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
            title={collapsed ? label : undefined}
            className={cn(
              'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              collapsed && 'justify-center px-0',
              active
                ? 'bg-primary text-primary-foreground'
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
  const [width, setWidth] = useState(224);
  const [collapsed, setCollapsed] = useState(false);
  const [resizing, setResizing] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const savedWidth = localStorage.getItem(STORAGE_KEY);
    const savedCollapsed = localStorage.getItem(COLLAPSED_KEY);
    if (savedWidth) setWidth(Number(savedWidth));
    if (savedCollapsed) setCollapsed(savedCollapsed === 'true');
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    router.push('/login');
  };

  const startResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setResizing(true);
  }, []);

  useEffect(() => {
    if (!resizing) return;

    const onMouseMove = (e: MouseEvent) => {
      const next = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, e.clientX));
      setWidth(next);
    };
    const onMouseUp = () => {
      setResizing(false);
      setWidth((w) => {
        localStorage.setItem(STORAGE_KEY, String(w));
        return w;
      });
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, [resizing]);

  const toggleCollapsed = () => {
    setCollapsed((c) => {
      localStorage.setItem(COLLAPSED_KEY, String(!c));
      return !c;
    });
  };

  const effectiveWidth = collapsed ? COLLAPSED_WIDTH : width;

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside
        style={{ width: effectiveWidth }}
        className={cn(
          'fixed inset-y-0 left-0 z-30 hidden flex-col border-r bg-background px-2 py-4 md:flex',
          !resizing && 'transition-[width] duration-150 ease-out'
        )}
      >
        <div className={cn('flex items-center gap-2 px-1 pb-1', collapsed && 'justify-center px-0')}>
          <Link href="/dashboard" className="flex items-center gap-2 min-w-0">
            <FileText size={18} strokeWidth={2} className="text-primary shrink-0" aria-hidden="true" />
            {!collapsed && <span className="text-sm font-semibold truncate">ScopeWise</span>}
          </Link>
        </div>
        {!collapsed && (
          <p className="px-1 pb-5 text-xs text-muted-foreground">
            Catch contract risk before you sign.
          </p>
        )}
        {collapsed && <div className="pb-5" />}
        <NavLinks collapsed={collapsed} />
        <div className="mt-auto">
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

        {/* Collapse toggle */}
        <button
          type="button"
          onClick={toggleCollapsed}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="absolute -right-3.5 top-8 hidden h-7 w-7 items-center justify-center rounded-full border-2 border-background bg-primary text-primary-foreground shadow-md hover:bg-primary/90 md:flex"
        >
          {collapsed ? <ChevronRight size={16} strokeWidth={2.5} /> : <ChevronLeft size={16} strokeWidth={2.5} />}
        </button>

        {/* Drag-to-resize handle */}
        {!collapsed && (
          <div
            onMouseDown={startResize}
            className="absolute inset-y-0 right-0 hidden w-1 cursor-col-resize hover:bg-primary/30 md:block"
          />
        )}
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

      <main style={{ paddingLeft: 0 }} className="md:[padding-left:var(--sidebar-w)]" data-shell-main>
        <style jsx>{`
          main {
            --sidebar-w: ${effectiveWidth}px;
          }
        `}</style>
        <div className={cn('py-6 px-4 sm:px-6', fullWidth ? 'w-full' : 'mx-auto max-w-7xl')}>{children}</div>
      </main>
    </div>
  );
}

import { useEffect, useRef, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  ChevronsUpDown,
  Clapperboard,
  LayoutDashboard,
  Layers,
  Library,
  LogIn,
  LogOut,
  Menu,
  Settings,
  X,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from '../context/AuthContext';
import Logo from '../components/common/Logo';

const NAV = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/create', icon: Clapperboard, label: 'Create video' },
  { to: '/batch', icon: Layers, label: 'Batch studio' },
  { to: '/library', icon: Library, label: 'Library' },
  { to: '/profile', icon: Settings, label: 'Settings' },
];

const TITLES: [string, string][] = [
  ['/dashboard', 'Dashboard'],
  ['/create', 'Create video'],
  ['/scripts', 'Script'],
  ['/generate-video', 'Render'],
  ['/batch', 'Batch studio'],
  ['/library', 'Library'],
  ['/projects', 'Projects'],
  ['/profile', 'Settings'],
];

function pageTitle(pathname: string) {
  return TITLES.find(([prefix]) => pathname.startsWith(prefix))?.[1] ?? 'Qreate';
}

function AccountMenu() {
  const navigate = useNavigate();
  const { user, isAuthenticated, logout, openAuthModal } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', esc);
    };
  }, [open]);

  if (!isAuthenticated || !user) {
    return (
      <button
        type="button"
        onClick={() => openAuthModal('login')}
        className="w-full flex items-center justify-center gap-2 h-9 rounded-lg border border-border bg-background text-sm font-medium hover:bg-accent"
      >
        <LogIn className="w-4 h-4" />
        Sign in
      </button>
    );
  }

  const name = user.full_name || user.name || user.email.split('@')[0];
  return (
    <div className="relative" ref={ref}>
      {open && (
        <div role="menu" className="absolute bottom-full left-0 right-0 mb-2 rounded-lg border border-border bg-background p-1 shadow-sm">
          <button
            role="menuitem"
            type="button"
            onClick={() => { setOpen(false); navigate('/profile'); }}
            className="w-full flex items-center gap-2 px-2.5 h-9 rounded-md text-sm hover:bg-accent"
          >
            <Settings className="w-4 h-4 text-muted-foreground" />
            Profile & settings
          </button>
          <button
            role="menuitem"
            type="button"
            onClick={() => { setOpen(false); logout(); navigate('/'); }}
            className="w-full flex items-center gap-2 px-2.5 h-9 rounded-md text-sm text-destructive hover:bg-destructive/10"
          >
            <LogOut className="w-4 h-4" />
            Log out
          </button>
        </div>
      )}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="w-full flex items-center gap-2.5 p-2 rounded-lg hover:bg-accent text-left"
      >
        <span className="w-8 h-8 rounded-full bg-primary-soft text-primary text-sm font-semibold flex items-center justify-center shrink-0">
          {name[0].toUpperCase()}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-medium truncate">{name}</span>
          <span className="block text-xs text-muted-foreground truncate">{user.email}</span>
        </span>
        <ChevronsUpDown className="w-4 h-4 text-muted-foreground shrink-0" />
      </button>
    </div>
  );
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const navigate = useNavigate();
  return (
    <div className="flex h-full flex-col">
      <div className="h-14 flex items-center px-4 border-b border-border">
        <button type="button" onClick={() => { navigate('/dashboard'); onNavigate?.(); }} className="flex items-center gap-2 rounded-lg">
          <Logo className="w-7 h-7" />
          <span className="text-base font-semibold tracking-tight">Qreate</span>
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto p-3 space-y-0.5" aria-label="Main">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 h-9 px-2.5 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-primary-soft text-primary font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent'
              )
            }
          >
            <Icon className="w-4 h-4 shrink-0" strokeWidth={2} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="p-3 border-t border-border">
        <AccountMenu />
      </div>
    </div>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  const [drawer, setDrawer] = useState(false);
  const title = pageTitle(pathname);

  useEffect(() => {
    document.title = `${title} · Qreate — AI video studio`;
  }, [title]);

  useEffect(() => setDrawer(false), [pathname]);

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Desktop sidebar */}
      <aside className="hidden lg:block w-60 shrink-0 border-r border-border bg-card">
        <Sidebar />
      </aside>

      {/* Mobile drawer */}
      {drawer && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-foreground/20" onClick={() => setDrawer(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 border-r border-border bg-card">
            <button
              type="button"
              onClick={() => setDrawer(false)}
              className="absolute right-3 top-3.5 p-1 rounded-md text-muted-foreground hover:bg-accent"
              aria-label="Close menu"
            >
              <X className="w-4 h-4" />
            </button>
            <Sidebar onNavigate={() => setDrawer(false)} />
          </aside>
        </div>
      )}

      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="h-14 shrink-0 flex items-center gap-3 px-4 sm:px-8 border-b border-border bg-background">
          <button
            type="button"
            onClick={() => setDrawer(true)}
            className="lg:hidden p-1.5 -ml-1.5 rounded-md text-muted-foreground hover:bg-accent"
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5" />
          </button>
          <h2 className="text-sm font-medium">{title}</h2>
        </header>
        <div className="flex-1 overflow-y-auto">{children}</div>
      </main>
    </div>
  );
}

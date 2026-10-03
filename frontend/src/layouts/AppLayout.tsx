import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderOpen,
  Video,
  Plus,
  Clapperboard,
  Library,
  LogOut,
  LogIn,
} from 'lucide-react';
import { cn } from '../lib/utils';
import ThemeToggle from '../components/common/ThemeToggle';
import { useAuth } from '../context/AuthContext';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/projects', icon: FolderOpen, label: 'Projects' },
  { to: '/create', icon: Clapperboard, label: 'Create Video' },
  { to: '/library', icon: Library, label: 'Video Library' },
];

interface AppLayoutProps {
  children: React.ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate();
  const { user, isAuthenticated, logout, openAuthModal } = useAuth();

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 shrink-0 flex flex-col border-r border-border bg-card">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-border">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2.5 group"
          >
            <div className="w-8 h-8 rounded-lg qreate-gradient flex items-center justify-center shadow-sm">
              <Video className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold tracking-tight">
              Q<span className="qreate-gradient-text">reate</span>
            </span>
          </button>
        </div>

        {/* New Video Button */}
        <div className="p-4">
          <button
            onClick={() => navigate('/create')}
            className="w-full flex items-center gap-2 justify-center h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            New Video
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 space-y-0.5 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary/10 text-primary font-semibold'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                )
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User / Footer */}
        <div className="p-4 border-t border-border space-y-2">
          {isAuthenticated && user ? (
            <div className="flex items-center justify-between p-2 rounded-lg bg-muted/50 border border-border/50">
              <div className="flex items-center gap-2 overflow-hidden">
                <div className="w-7 h-7 rounded-full bg-primary/20 text-primary font-semibold text-xs flex items-center justify-center shrink-0">
                  {user.full_name ? user.full_name[0].toUpperCase() : user.email[0].toUpperCase()}
                </div>
                <div className="overflow-hidden">
                  <p className="text-xs font-medium truncate">{user.full_name || user.email}</p>
                  <p className="text-[10px] text-muted-foreground truncate">{user.email}</p>
                </div>
              </div>
              <button
                onClick={() => logout()}
                title="Log out"
                className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => openAuthModal('login')}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg border border-border bg-background hover:bg-accent text-xs font-medium transition-colors"
            >
              <LogIn className="w-3.5 h-3.5" />
              Sign In to Account
            </button>
          )}

          <p className="text-[11px] text-muted-foreground text-center">
            Powered by Agnes AI & Cloudinary
          </p>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-16 shrink-0 flex items-center justify-between px-8 border-b border-border bg-card/60 backdrop-blur-xs">
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-muted-foreground">AI Video Generation Studio</span>
          </div>

          <div className="flex items-center gap-3">
            {/* Theme Toggle Button */}
            <ThemeToggle />

            {/* User pill or Login button */}
            {isAuthenticated && user ? (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-border bg-card text-xs">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-medium text-foreground">{user.full_name || user.email}</span>
                <button
                  onClick={() => logout()}
                  className="ml-1 text-muted-foreground hover:text-destructive transition-colors"
                  title="Sign Out"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => openAuthModal('login')}
                  className="text-xs font-medium px-3 py-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                >
                  Sign In
                </button>
                <button
                  onClick={() => openAuthModal('register')}
                  className="text-xs font-medium px-3 py-1.5 rounded-lg qreate-gradient text-white shadow-xs hover:opacity-90 transition-opacity"
                >
                  Sign Up
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
      </main>
    </div>
  );
}

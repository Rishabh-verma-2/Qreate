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
  User,
} from 'lucide-react';
import { cn } from '../lib/utils';
import ThemeToggle from '../components/common/ThemeToggle';
import { useAuth } from '../context/AuthContext';

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
        <div className="h-16 flex items-center justify-between px-5 border-b border-border">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2.5 group cursor-pointer"
          >
            <div className="w-9 h-9 rounded-xl qreate-gradient flex items-center justify-center shadow-sm group-hover:scale-105 transition-transform">
              <Video className="w-4 h-4 text-white" />
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-lg font-extrabold tracking-tight">
                Q<span className="qreate-gradient-text">reate</span>
              </span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                v3.0
              </span>
            </div>
          </button>
        </div>

        {/* New Video Button */}
        <div className="p-3.5">
          <button
            onClick={() => navigate('/create')}
            className="w-full flex items-center justify-center gap-2 h-10 px-4 rounded-xl qreate-gradient text-white text-sm font-semibold shadow-sm hover:shadow-md hover:shadow-primary/25 hover:opacity-95 active:scale-[0.98] transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4 stroke-[2.5]" />
            New Video Project
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 space-y-4 overflow-y-auto pt-2">
          {/* Main Navigation */}
          <div>
            <div className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60">
              Studio Workspace
            </div>
            <div className="space-y-1">
              {[
                { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
                { to: '/projects', icon: FolderOpen, label: 'Projects' },
                { to: '/create', icon: Clapperboard, label: 'Create Video', badge: 'AI V3' },
                { to: '/library', icon: Library, label: 'Video Library' },
              ].map(({ to, icon: Icon, label, badge }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    cn(
                      'group relative flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 select-none',
                      isActive
                        ? 'bg-gradient-to-r from-primary/20 via-primary/10 to-transparent text-primary font-semibold shadow-xs before:absolute before:left-0 before:top-2 before:bottom-2 before:w-1 before:rounded-r-full before:bg-primary'
                        : 'text-muted-foreground hover:text-foreground hover:bg-accent/60 hover:translate-x-0.5'
                    )
                  }
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={cn(
                        'w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors',
                        'bg-primary/5 group-hover:bg-primary/10 text-muted-foreground group-hover:text-foreground'
                      )}
                    >
                      <Icon className="w-4 h-4 shrink-0 transition-transform group-hover:scale-110" />
                    </div>
                    <span className="truncate">{label}</span>
                  </div>

                  {badge && (
                    <span className="px-1.5 py-0.5 rounded-md text-[10px] font-bold tracking-wide qreate-gradient text-white shadow-xs">
                      {badge}
                    </span>
                  )}
                </NavLink>
              ))}
            </div>
          </div>

          {/* Account Section */}
          <div>
            <div className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60">
              Account & Studio
            </div>
            <div className="space-y-1">
              <NavLink
                to="/profile"
                className={({ isActive }) =>
                  cn(
                    'group relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 select-none',
                    isActive
                      ? 'bg-gradient-to-r from-primary/20 via-primary/10 to-transparent text-primary font-semibold shadow-xs before:absolute before:left-0 before:top-2 before:bottom-2 before:w-1 before:rounded-r-full before:bg-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-accent/60 hover:translate-x-0.5'
                  )
                }
              >
                <div
                  className={cn(
                    'w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors',
                    'bg-primary/5 group-hover:bg-primary/10 text-muted-foreground group-hover:text-foreground'
                  )}
                >
                  <User className="w-4 h-4 shrink-0 transition-transform group-hover:scale-110" />
                </div>
                <span className="truncate">Profile & Settings</span>
              </NavLink>
            </div>
          </div>
        </nav>

        {/* User / Footer */}
        <div className="p-4 border-t border-border space-y-2">
          {isAuthenticated && user ? (
            <div
              onClick={() => navigate('/profile')}
              className="flex items-center justify-between p-2 rounded-xl bg-muted/40 hover:bg-muted/70 border border-border/50 transition-all cursor-pointer group"
              title="View Profile & Settings"
            >
              <div className="flex items-center gap-2.5 overflow-hidden">
                <div className="w-7 h-7 rounded-full bg-primary/20 text-primary font-semibold text-xs flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                  {user.full_name ? user.full_name[0].toUpperCase() : user.email[0].toUpperCase()}
                </div>
                <div className="overflow-hidden">
                  <p className="text-xs font-semibold truncate group-hover:text-primary transition-colors">
                    {user.full_name || user.email}
                  </p>
                  <p className="text-[10px] text-muted-foreground truncate">{user.email}</p>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  logout();
                }}
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
              <div
                onClick={() => navigate('/profile')}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-border bg-card text-xs hover:border-primary/50 transition-all cursor-pointer group shadow-xs"
                title="View Profile & Settings"
              >
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-medium text-foreground group-hover:text-primary transition-colors">
                  {user.full_name || user.email}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    logout();
                  }}
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

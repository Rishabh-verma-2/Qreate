import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderOpen,
  Video,
  Plus,
  Clapperboard,
  Library,
  Layers,
} from 'lucide-react';
import { cn } from '../lib/utils';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/projects', icon: FolderOpen, label: 'Projects' },
  { to: '/batch', icon: Layers, label: 'Batch Studio' },
  { to: '/create', icon: Clapperboard, label: 'Create Video' },
  { to: '/library', icon: Library, label: 'Video Library' },
];

interface AppLayoutProps {
  children: React.ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate();

  return (
    <div className="flex h-screen bg-background overflow-hidden">
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
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                )
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <p className="text-xs text-muted-foreground text-center">
            Open-source pipeline · 9:16 for Qoneqt
          </p>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-16 shrink-0 flex items-center justify-between px-8 border-b border-border bg-card/50">
          <div />
          <div className="flex items-center gap-4">
            <div className="w-2 h-2 rounded-full bg-green-400 shadow-sm shadow-green-400/50" title="System online" />
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

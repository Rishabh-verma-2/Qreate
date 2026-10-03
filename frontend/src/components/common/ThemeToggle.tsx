import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { cn } from '../../lib/utils';

interface ThemeToggleProps {
  className?: string;
  showLabel?: boolean;
}

export default function ThemeToggle({ className, showLabel = false }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      onClick={toggleTheme}
      type="button"
      title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
      aria-label={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
      className={cn(
        'relative inline-flex items-center justify-center p-2 rounded-xl transition-all duration-200',
        'border border-border bg-card/80 hover:bg-accent text-foreground shadow-xs hover:shadow-sm',
        'focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary/50',
        className
      )}
    >
      <div className="relative w-5 h-5 flex items-center justify-center">
        {/* Sun Icon */}
        <Sun
          className={cn(
            'w-4 h-4 text-amber-500 transition-all duration-300 absolute',
            isDark
              ? 'opacity-0 rotate-90 scale-0 pointer-events-none'
              : 'opacity-100 rotate-0 scale-100'
          )}
        />
        {/* Moon Icon */}
        <Moon
          className={cn(
            'w-4 h-4 text-violet-400 transition-all duration-300 absolute',
            isDark
              ? 'opacity-100 rotate-0 scale-100'
              : 'opacity-0 -rotate-90 scale-0 pointer-events-none'
          )}
        />
      </div>

      {showLabel && (
        <span className="ml-2 text-xs font-medium">
          {isDark ? 'Dark Mode' : 'Light Mode'}
        </span>
      )}
    </button>
  );
}

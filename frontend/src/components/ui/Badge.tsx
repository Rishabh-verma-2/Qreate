import { cn } from '../../lib/utils';
import { type VideoTaskStatus } from '../../types';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'muted';
  className?: string;
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  const variants = {
    default: 'bg-primary-soft text-primary',
    success: 'bg-success/10 text-success',
    warning: 'bg-warning/10 text-warning',
    error: 'bg-destructive/10 text-destructive',
    info: 'bg-warning/10 text-warning',
    muted: 'bg-muted text-muted-foreground',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium',
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: VideoTaskStatus | string }) {
  const config: Record<string, { label: string; variant: BadgeProps['variant'] }> = {
    pending: { label: 'Pending', variant: 'warning' },
    queued: { label: 'Queued', variant: 'muted' },
    in_progress: { label: 'Processing', variant: 'warning' },
    completed: { label: 'Done', variant: 'success' },
    failed: { label: 'Failed', variant: 'error' },
    active: { label: 'Active', variant: 'success' },
    archived: { label: 'Archived', variant: 'muted' },
  };

  const { label, variant } = config[status] || { label: status, variant: 'muted' };
  return <Badge variant={variant}>{label}</Badge>;
}

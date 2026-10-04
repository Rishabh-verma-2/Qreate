import { cn } from '../../lib/utils';

/** Qreate mark: solid violet tile with a play glyph (same shape as the favicon). */
export default function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn('shrink-0', className)} aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#5B21B6" />
      <path d="M12.5 10.2v11.6c0 .8.9 1.3 1.6.9l9.3-5.8c.6-.4.6-1.4 0-1.8l-9.3-5.8c-.7-.4-1.6.1-1.6.9Z" fill="#fff" />
    </svg>
  );
}

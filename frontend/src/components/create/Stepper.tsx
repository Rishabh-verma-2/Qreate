import { Check } from 'lucide-react';
import { cn } from '../../lib/utils';

export const CREATE_STEPS = ['Topic', 'Style', 'Script', 'Render'] as const;

interface StepperProps {
  current: number; // 0-based index into CREATE_STEPS
  onSelect?: (index: number) => void; // only earlier/current steps are clickable
}

/** Topic → Style → Script → Render progress for the create flow. */
export default function Stepper({ current, onSelect }: StepperProps) {
  return (
    <ol className="flex items-center gap-2 text-sm" aria-label="Progress">
      {CREATE_STEPS.map((label, i) => {
        const done = i < current;
        const active = i === current;
        const clickable = !!onSelect && i <= current && !active;
        return (
          <li key={label} className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              disabled={!clickable}
              onClick={() => clickable && onSelect?.(i)}
              aria-current={active ? 'step' : undefined}
              className={cn(
                'flex items-center gap-2 rounded-lg px-1 py-0.5',
                clickable ? 'hover:text-foreground cursor-pointer' : 'cursor-default'
              )}
            >
              <span
                className={cn(
                  'w-6 h-6 rounded-full text-xs font-medium flex items-center justify-center border',
                  done && 'bg-primary border-primary text-primary-foreground',
                  active && 'border-primary text-primary bg-primary-soft',
                  !done && !active && 'border-border text-muted-foreground'
                )}
              >
                {done ? <Check className="w-3.5 h-3.5" /> : i + 1}
              </span>
              <span className={cn(active ? 'text-foreground font-medium' : 'text-muted-foreground hidden sm:inline')}>{label}</span>
            </button>
            {i < CREATE_STEPS.length - 1 && <span className="w-4 sm:w-10 h-px bg-border" aria-hidden="true" />}
          </li>
        );
      })}
    </ol>
  );
}

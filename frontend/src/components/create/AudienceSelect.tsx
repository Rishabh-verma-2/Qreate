import { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, Search } from 'lucide-react';
import { cn } from '../../lib/utils';

export const AUDIENCE_GROUPS: { group: string; options: string[] }[] = [
  { group: 'General', options: ['General audience'] },
  { group: 'Students', options: ['School students (13–17)', 'College students (18–24)', 'Competitive exam aspirants (UPSC, SSC, JEE, NEET)'] },
  { group: 'Professionals', options: ['Working professionals', 'Freshers & job seekers', 'Entrepreneurs & founders', 'Small business owners'] },
  {
    group: 'Interests',
    options: ['Tech enthusiasts', 'Finance & investing beginners', 'Fitness & health', 'Gamers', 'Creators & influencers', 'Travel lovers', 'Foodies'],
  },
  { group: 'Life stage', options: ['Parents', 'Newly married couples', 'Senior citizens'] },
];

const CUSTOM = 'Custom…';

interface AudienceSelectProps {
  value: string;
  onChange: (value: string) => void;
}

/** Searchable grouped dropdown with a "Custom…" option that reveals a text box. */
export default function AudienceSelect({ value, onChange }: AudienceSelectProps) {
  const known = AUDIENCE_GROUPS.some((g) => g.options.includes(value));
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [custom, setCustom] = useState(!known && !!value);
  const ref = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    searchRef.current?.focus();
    const close = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return AUDIENCE_GROUPS
      .map((g) => ({ ...g, options: g.options.filter((o) => !q || o.toLowerCase().includes(q) || g.group.toLowerCase().includes(q)) }))
      .filter((g) => g.options.length);
  }, [query]);

  function pick(option: string) {
    setOpen(false);
    setQuery('');
    if (option === CUSTOM) {
      setCustom(true);
      onChange('');
    } else {
      setCustom(false);
      onChange(option);
    }
  }

  return (
    <div className="space-y-2" ref={ref}>
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-haspopup="listbox"
          aria-expanded={open}
          className="w-full h-10 px-3 rounded-lg border border-input bg-background text-sm flex items-center justify-between text-left"
        >
          <span className={cn(!value && !custom && 'text-muted-foreground')}>
            {custom ? 'Custom audience' : value || 'Choose an audience'}
          </span>
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        </button>
        {open && (
          <div className="absolute z-30 mt-1 w-full rounded-lg border border-border bg-background shadow-sm">
            <div className="flex items-center gap-2 px-3 border-b border-border">
              <Search className="w-4 h-4 text-muted-foreground" />
              <input
                ref={searchRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
                placeholder="Search audiences"
                className="h-10 flex-1 bg-transparent text-sm outline-none"
              />
            </div>
            <ul role="listbox" className="max-h-64 overflow-y-auto p-1">
              {filtered.map((g) => (
                <li key={g.group}>
                  <p className="px-2 pt-2 pb-1 text-xs font-medium text-muted-foreground">{g.group}</p>
                  {g.options.map((o) => (
                    <button
                      key={o}
                      type="button"
                      role="option"
                      aria-selected={o === value}
                      onClick={() => pick(o)}
                      className="w-full flex items-center justify-between px-2 h-9 rounded-md text-sm text-left hover:bg-accent"
                    >
                      {o}
                      {o === value && <Check className="w-4 h-4 text-primary" />}
                    </button>
                  ))}
                </li>
              ))}
              <li>
                <p className="px-2 pt-2 pb-1 text-xs font-medium text-muted-foreground">Other</p>
                <button
                  type="button"
                  role="option"
                  aria-selected={custom}
                  onClick={() => pick(CUSTOM)}
                  className="w-full px-2 h-9 rounded-md text-sm text-left hover:bg-accent"
                >
                  {CUSTOM}
                </button>
              </li>
            </ul>
          </div>
        )}
      </div>
      {custom && (
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          maxLength={100}
          placeholder="e.g. Home bakers in Pune"
          aria-label="Custom audience"
          className="w-full h-10 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
        />
      )}
    </div>
  );
}

import { cn } from '../lib/utils';
import {
  CAPTION_STYLES, FORMATS, MUSIC_MOODS, PACES, THEMES, VISUAL_STYLES, type StyleChoices,
} from '../lib/styleOptions';
import { Select } from './ui/Input';

interface StylePanelProps {
  value: StyleChoices;
  onChange: (next: StyleChoices) => void;
}

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <div>
        <p className="text-sm font-semibold">{title}</p>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      {children}
    </div>
  );
}

function Chip({ active, onClick, children, className }: {
  active: boolean; onClick: () => void; children: React.ReactNode; className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'text-left rounded-xl border p-3 transition-colors',
        active ? 'border-primary bg-primary/10' : 'border-border hover:border-primary/40',
        className
      )}
    >
      {children}
    </button>
  );
}

/** Format, look and feel choices for the video. */
export default function StylePanel({ value, onChange }: StylePanelProps) {
  const set = <K extends keyof StyleChoices>(key: K, v: StyleChoices[K]) => onChange({ ...value, [key]: v });
  const theme = THEMES.find((t) => t.value === value.color_theme) || THEMES[0];
  const highlight = value.accent_color || theme.highlight;

  return (
    <div className="space-y-6">
      <Section title="What type of video?" hint="The writer, footage and edit all follow this format.">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {FORMATS.map((f) => (
            <Chip key={f.value} active={value.video_format === f.value} onClick={() => set('video_format', f.value)}>
              <p className="text-sm font-medium">{f.emoji} {f.label}</p>
              <p className="text-xs text-muted-foreground mt-0.5 leading-snug">{f.desc}</p>
            </Chip>
          ))}
        </div>
      </Section>

      <Section title="Visual style">
        <div className="grid grid-cols-3 gap-2">
          {VISUAL_STYLES.map((v) => (
            <Chip key={v.value} active={value.visual_style === v.value} onClick={() => set('visual_style', v.value)}>
              <p className="text-sm font-medium">{v.label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{v.desc}</p>
            </Chip>
          ))}
        </div>
        {value.visual_style !== 'animated' && (
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none pt-1">
            <input
              type="checkbox"
              checked={value.people_focus}
              onChange={(e) => set('people_focus', e.target.checked)}
              className="accent-[hsl(var(--primary))] w-4 h-4"
            />
            Show more people (faces, reactions, hands) — feels more human
          </label>
        )}
      </Section>

      <Section title="Color theme" hint="Sets caption highlight, hook banner, text cards and the color grade.">
        <div className="flex flex-wrap gap-2">
          {THEMES.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => onChange({ ...value, color_theme: t.value, accent_color: undefined })}
              className={cn(
                'flex items-center gap-2 pl-1.5 pr-3 py-1.5 rounded-full border transition-colors',
                value.color_theme === t.value && !value.accent_color ? 'border-primary bg-primary/10' : 'border-border hover:border-primary/40'
              )}
            >
              <span
                className="w-6 h-6 rounded-full border border-white/20 flex items-center justify-center"
                style={{ background: `linear-gradient(135deg, ${t.from}, ${t.to})` }}
              >
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: t.highlight }} />
              </span>
              <span className="text-xs font-medium">{t.label}</span>
            </button>
          ))}
          <label className="flex items-center gap-2 pl-1.5 pr-3 py-1.5 rounded-full border border-border cursor-pointer hover:border-primary/40">
            <input
              type="color"
              value={value.accent_color || theme.highlight}
              onChange={(e) => set('accent_color', e.target.value)}
              className="w-6 h-6 rounded-full border-0 bg-transparent p-0 cursor-pointer"
            />
            <span className="text-xs font-medium">{value.accent_color ? `Custom ${value.accent_color}` : 'Custom color'}</span>
          </label>
        </div>
      </Section>

      <Section title="Captions">
        <div className="grid grid-cols-3 gap-2">
          {CAPTION_STYLES.map((c) => (
            <Chip
              key={c.value}
              active={value.caption_style === c.value}
              onClick={() => set('caption_style', c.value)}
              className="p-0 overflow-hidden"
            >
              <div
                className="h-16 flex items-center justify-center"
                style={{ background: `linear-gradient(135deg, ${theme.from}, ${theme.to})` }}
              >
                <span
                  className={cn(
                    'font-extrabold text-white',
                    c.value === 'bold' && 'text-base uppercase [text-shadow:_0_2px_0_#000,_0_0_6px_#000]',
                    c.value === 'clean' && 'text-sm [text-shadow:_0_1px_3px_#000]',
                    c.value === 'boxed' && 'text-sm uppercase bg-black/60 px-2 py-0.5 rounded'
                  )}
                >
                  {c.value === 'clean' ? 'This is ' : 'THIS IS '}
                  <span style={{ color: highlight }}>{c.value === 'clean' ? 'huge' : 'HUGE'}</span>
                </span>
              </div>
              <div className="p-2">
                <p className="text-sm font-medium">{c.label}</p>
                <p className="text-xs text-muted-foreground">{c.desc}</p>
              </div>
            </Chip>
          ))}
        </div>
      </Section>

      <div className="grid sm:grid-cols-2 gap-4">
        <Select label="Pace" value={value.pace} onChange={(e) => set('pace', e.target.value)} options={PACES} />
        <Select label="Music" value={value.music_mood} onChange={(e) => set('music_mood', e.target.value)} options={MUSIC_MOODS} />
      </div>
    </div>
  );
}

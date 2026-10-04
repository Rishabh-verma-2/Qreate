import { useEffect, useRef, useState } from 'react';
import { Check, Loader2, Play, Square } from 'lucide-react';
import { voicesApi, VOICE_PREVIEW_URL } from '../services/api';
import { cn } from '../lib/utils';

interface Voice {
  id: string;
  name: string;
  gender: 'male' | 'female';
  vibe: string;
}

interface LanguageVoices {
  language: string;
  voices: Voice[];
}

interface VoicePickerProps {
  language: string;
  voiceId?: string;
  onChange: (language: string, voiceId: string, gender: 'male' | 'female') => void;
}

/** Language + voice selection with instant audio previews. */
export default function VoicePicker({ language, voiceId, onChange }: VoicePickerProps) {
  const [catalog, setCatalog] = useState<LanguageVoices[]>([]);
  const [playing, setPlaying] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    voicesApi.list().then(setCatalog).catch(() => setCatalog([]));
    return () => audioRef.current?.pause();
  }, []);

  const current = catalog.find((c) => c.language === language) || catalog[0];

  // Keep a valid voice selected when the language changes
  useEffect(() => {
    if (current && !current.voices.some((v) => v.id === voiceId)) {
      const v = current.voices[0];
      onChange(current.language, v.id, v.gender);
    }
  }, [current, voiceId, onChange]);

  function preview(v: Voice) {
    audioRef.current?.pause();
    if (playing === v.id) {
      setPlaying(null);
      return;
    }
    const audio = new Audio(VOICE_PREVIEW_URL(v.id, current?.language));
    audioRef.current = audio;
    setLoading(v.id);
    audio.oncanplay = () => setLoading(null);
    audio.onended = () => setPlaying(null);
    audio.onerror = () => { setLoading(null); setPlaying(null); };
    audio.play().then(() => setPlaying(v.id)).catch(() => setLoading(null));
  }

  if (!catalog.length) {
    return <p className="text-xs text-muted-foreground">Loading voices…</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5">
        {catalog.map((c) => (
          <button
            key={c.language}
            type="button"
            onClick={() => onChange(c.language, c.voices[0].id, c.voices[0].gender)}
            className={cn(
              'px-2.5 py-1 rounded-full text-xs font-medium border transition-colors',
              c.language === current?.language
                ? 'bg-primary text-primary-foreground border-primary'
                : 'border-border text-muted-foreground hover:text-foreground hover:border-primary/40'
            )}
          >
            {c.language}
          </button>
        ))}
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {current?.voices.map((v) => {
          const selected = v.id === voiceId;
          return (
            <div
              key={v.id}
              role="button"
              tabIndex={0}
              onClick={() => onChange(current.language, v.id, v.gender)}
              onKeyDown={(e) => e.key === 'Enter' && onChange(current.language, v.id, v.gender)}
              className={cn(
                'flex items-center gap-3 p-2.5 rounded-xl border cursor-pointer transition-colors',
                selected ? 'border-primary bg-primary/10' : 'border-border hover:border-primary/40'
              )}
            >
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); preview(v); }}
                className="w-8 h-8 shrink-0 rounded-full bg-primary/15 text-primary flex items-center justify-center hover:bg-primary/25"
                aria-label={`Preview ${v.name}`}
              >
                {loading === v.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  : playing === v.id ? <Square className="w-3 h-3" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
              </button>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium flex items-center gap-1.5">
                  {v.name}
                  <span className="text-[10px] uppercase tracking-wide text-muted-foreground">{v.gender === 'male' ? 'M' : 'F'}</span>
                </p>
                <p className="text-xs text-muted-foreground truncate">{v.vibe}</p>
              </div>
              {selected && <Check className="w-4 h-4 text-primary shrink-0" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}

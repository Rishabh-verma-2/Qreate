import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft, ArrowRight, Briefcase, Clapperboard, GraduationCap, Laugh, MessageCircle, Monitor, Moon,
  Smartphone, Sparkles, Zap, type LucideIcon,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { useToast } from '../components/ui/Toast';
import Stepper from '../components/create/Stepper';
import AudienceSelect from '../components/create/AudienceSelect';
import PhonePreview from '../components/create/PhonePreview';
import StylePanel from '../components/StylePanel';
import VoicePicker from '../components/VoicePicker';
import { projectsApi, scriptsApi } from '../services/api';
import { FORMATS, THEMES, loadStyle, saveStyle, type StyleChoices } from '../lib/styleOptions';
import { cn, scrollAppToTop } from '../lib/utils';

const TOPIC_MAX = 5000;

const TONES: { id: string; label: string; icon: LucideIcon }[] = [
  { id: 'educational', label: 'Educational', icon: GraduationCap },
  { id: 'entertaining', label: 'Entertaining', icon: Laugh },
  { id: 'inspirational', label: 'Inspirational', icon: Sparkles },
  { id: 'conversational', label: 'Conversational', icon: MessageCircle },
  { id: 'cinematic', label: 'Cinematic', icon: Clapperboard },
  { id: 'professional', label: 'Professional', icon: Briefcase },
  { id: 'mysterious', label: 'Mysterious', icon: Moon },
  { id: 'energetic', label: 'Fast-paced', icon: Zap },
];
const MAX_TONES = 8;

const DURATIONS = ['15', '30', '60', '90', '120', '180'];
const LANGUAGES = ['English', 'Hindi', 'Hinglish'];
const AGES = ['Any age', '13–17', '18–24', '25–34', '35+'];
const REGIONS = ['India', 'Global'];

// Qoneqt community topics
const INSPIRATION = [
  { tag: 'Finance', topic: '5 money habits every college student should know' },
  { tag: 'Tech', topic: 'AI tools that save you 2 hours every day' },
  { tag: 'Fitness', topic: 'A 15-minute home workout that actually works' },
  { tag: 'Food', topic: 'Street food you must try in Mumbai' },
  { tag: 'Lifestyle', topic: 'How to build a morning routine that sticks' },
];

const ASPECTS = [
  { value: '9:16' as const, icon: Smartphone, title: 'Vertical 9:16', desc: 'Qoneqt feed, Reels and Shorts' },
  { value: '16:9' as const, icon: Monitor, title: 'Widescreen 16:9', desc: 'YouTube, presentations, websites' },
];

const LOADING_STEPS = ['Researching trends…', 'Writing the hook…', 'Writing the script…', 'Polishing the script…'];

function Field({ label, hint, htmlFor, children }: { label: string; hint?: string; htmlFor?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor={htmlFor} className="text-sm font-medium">{label}</label>
        {hint && <span className="text-hint text-muted-foreground">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

function Segmented<T extends string>({ options, value, onChange, render, label }: {
  options: T[]; value: T; onChange: (v: T) => void; render?: (v: T) => string; label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex w-full sm:w-auto rounded-lg border border-border bg-muted p-0.5">
      {options.map((o) => (
        <button
          key={o}
          type="button"
          role="radio"
          aria-checked={value === o}
          onClick={() => onChange(o)}
          className={cn(
            'flex-1 sm:flex-none h-8 px-4 rounded-md text-sm transition-colors',
            value === o ? 'bg-background text-foreground font-medium shadow-sm' : 'text-muted-foreground hover:text-foreground'
          )}
        >
          {render ? render(o) : o}
        </button>
      ))}
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 py-2 text-sm border-b border-border last:border-0">
      <span className="text-muted-foreground shrink-0">{label}</span>
      <span className="text-right truncate">{value || '—'}</span>
    </div>
  );
}

export default function CreateVideo() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const toast = useToast();

  const [step, setStep] = useState(0); // 0 = Topic, 1 = Style
  const [topic, setTopic] = useState('');
  const [aspect, setAspect] = useState<'9:16' | '16:9'>(
    () => (localStorage.getItem('qreate_pref_aspect') as '9:16' | '16:9') || '9:16'
  );
  const [tones, setTones] = useState<string[]>(['conversational']);
  const [duration, setDuration] = useState('30');
  const [language, setLanguage] = useState('English');
  const [audience, setAudience] = useState('General audience');
  const [age, setAge] = useState('Any age');
  const [region, setRegion] = useState('India');
  const [notes, setNotes] = useState('');
  const [style, setStyle] = useState<StyleChoices>(loadStyle);
  const [touched, setTouched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Prefill from ?topic= / ?aspect= or navigation state (dashboard, projects)
  useEffect(() => {
    const state = (location.state as Record<string, unknown> | null) || {};
    const t = searchParams.get('topic') || (typeof state.topic === 'string' ? state.topic : '');
    if (t) setTopic(t.slice(0, TOPIC_MAX));
    const a = searchParams.get('aspect');
    if (a === '9:16' || a === '16:9') setAspect(a);
  }, [location.state, searchParams]);

  useEffect(() => saveStyle(style), [style]);
  useEffect(() => localStorage.setItem('qreate_pref_aspect', aspect), [aspect]);
  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  const topicError = touched && !topic.trim() ? 'Topic is required' : '';
  const theme = THEMES.find((t) => t.value === style.color_theme) || THEMES[0];
  const highlight = style.accent_color || theme.highlight;
  const formatLabel = FORMATS.find((f) => f.value === style.video_format)?.label || 'Auto';
  const audienceText = useMemo(
    () => [audience || 'General audience', age !== 'Any age' ? `ages ${age}` : '', region].filter(Boolean).join(', '),
    [audience, age, region]
  );

  const handleVoice = useCallback((_lang: string, voiceId: string, gender: 'male' | 'female') => {
    setStyle((s) => (s.voice_id === voiceId ? s : { ...s, voice_id: voiceId, voice_gender: gender }));
  }, []);

  function toggleTone(id: string) {
    setTones((prev) => {
      if (prev.includes(id)) return prev.filter((t) => t !== id);
      if (prev.length >= MAX_TONES) return [prev[1], id]; // keep the most recent two
      return [...prev, id];
    });
  }

  function goToStyle() {
    setTouched(true);
    if (!topic.trim()) return;
    setStep(1);
    scrollAppToTop();
  }

  async function generate() {
    setTouched(true);
    if (!topic.trim()) {
      setStep(0);
      return;
    }
    setLoading(true);
    setLoadingStep(0);
    timer.current = setInterval(() => setLoadingStep((s) => Math.min(s + 1, LOADING_STEPS.length - 1)), 12000);
    try {
      const clean = topic.trim();
      const name = clean.split(/\s+/).slice(0, 6).join(' ');
      const project = await projectsApi.create({ name: name.charAt(0).toUpperCase() + name.slice(1), topic: clean });
      const script = await scriptsApi.generate({
        project_id: project.id,
        topic: clean,
        duration_seconds: parseInt(duration, 10),
        language,
        tone: tones.length ? tones : ['conversational'],
        audience: audienceText,
        additional_instructions: notes.trim() || undefined,
        ...style,
      });
      toast.success('Script ready — review it before rendering');
      navigate(`/scripts/${script.id}`, { state: { projectId: project.id, aspectRatio: aspect } });
    } catch (err) {
      toast.error((err as Error).message || 'Could not generate the script. Please try again.');
    } finally {
      if (timer.current) clearInterval(timer.current);
      setLoading(false);
    }
  }

  return (
    <div className="px-4 py-8 sm:px-8 max-w-6xl mx-auto">
      <div className="mb-8 space-y-6">
        <Stepper current={step} onSelect={(i) => { setStep(i); scrollAppToTop(); }} />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{step === 0 ? 'What is your video about?' : 'Choose the look and voice'}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {step === 0
              ? 'Describe the topic. Qreate checks what people search for and writes a script with a 3-second hook.'
              : 'Format, visuals, colors, captions and voice. You can review the script before anything is rendered.'}
          </p>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-5">
        {/* Form */}
        <div className="lg:col-span-3 space-y-6">
          {step === 0 ? (
            <section className="rounded-lg border border-border bg-card p-6 space-y-6">
              <Field label="Format">
                <div className="grid sm:grid-cols-2 gap-3" role="radiogroup" aria-label="Format">
                  {ASPECTS.map(({ value, icon: Icon, title, desc }) => (
                    <button
                      key={value}
                      type="button"
                      role="radio"
                      aria-checked={aspect === value}
                      onClick={() => setAspect(value)}
                      className={cn(
                        'flex items-start gap-3 rounded-lg border p-3 text-left transition-colors',
                        aspect === value ? 'border-primary bg-primary-soft' : 'border-border bg-background hover:border-primary/40'
                      )}
                    >
                      <Icon className={cn('w-5 h-5 mt-0.5', aspect === value ? 'text-primary' : 'text-muted-foreground')} />
                      <span>
                        <span className="block text-sm font-medium">{title}</span>
                        <span className="block text-hint text-muted-foreground">{desc}</span>
                      </span>
                    </button>
                  ))}
                </div>
              </Field>

              <Field label="Topic" htmlFor="topic" hint={`${topic.length}/${TOPIC_MAX}`}>
                <textarea
                  id="topic"
                  rows={3}
                  maxLength={TOPIC_MAX}
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  onBlur={() => setTouched(true)}
                  placeholder="e.g. 5 money habits every college student should know"
                  aria-invalid={!!topicError}
                  aria-describedby={topicError ? 'topic-error' : undefined}
                  className={cn(
                    'w-full px-3 py-2.5 rounded-lg border bg-background text-sm resize-none placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
                    topicError ? 'border-destructive' : 'border-input'
                  )}
                />
                {topicError && <p id="topic-error" role="alert" className="text-hint text-destructive">{topicError}</p>}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <span className="text-hint text-muted-foreground">Popular on Qoneqt:</span>
                  {INSPIRATION.map((i) => (
                    <button
                      key={i.tag}
                      type="button"
                      onClick={() => setTopic(i.topic)}
                      title={i.topic}
                      className="h-7 px-2.5 rounded-md border border-border bg-background text-xs text-muted-foreground hover:text-foreground hover:border-primary/40"
                    >
                      {i.tag}
                    </button>
                  ))}
                </div>
              </Field>

              <Field label="Tone" hint={`Pick up to ${MAX_TONES}`}>
                <div className="flex flex-wrap gap-2">
                  {TONES.map(({ id, label, icon: Icon }) => {
                    const on = tones.includes(id);
                    return (
                      <button
                        key={id}
                        type="button"
                        aria-pressed={on}
                        onClick={() => toggleTone(id)}
                        className={cn(
                          'h-8 px-3 rounded-lg border text-sm flex items-center gap-1.5 transition-colors',
                          on ? 'border-primary bg-primary-soft text-primary' : 'border-border bg-background text-muted-foreground hover:text-foreground'
                        )}
                      >
                        <Icon className="w-4 h-4" />
                        {label}
                      </button>
                    );
                  })}
                </div>
              </Field>

              <div className="grid sm:grid-cols-2 gap-6">
                <Field label="Duration">
                  <Segmented label="Duration" options={DURATIONS} value={duration} onChange={setDuration} render={(d) => `${d}s`} />
                </Field>
                <Field label="Language">
                  <Segmented label="Language" options={LANGUAGES} value={language} onChange={setLanguage} />
                </Field>
              </div>

              <Field label="Target audience">
                <AudienceSelect value={audience} onChange={setAudience} />
                <div className="grid grid-cols-2 gap-3">
                  <select aria-label="Age range" value={age} onChange={(e) => setAge(e.target.value)}
                    className="h-10 px-3 rounded-lg border border-input bg-background text-sm">
                    {AGES.map((a) => <option key={a}>{a}</option>)}
                  </select>
                  <select aria-label="Region" value={region} onChange={(e) => setRegion(e.target.value)}
                    className="h-10 px-3 rounded-lg border border-input bg-background text-sm">
                    {REGIONS.map((r) => <option key={r}>{r}</option>)}
                  </select>
                </div>
              </Field>

              <Field label="Director notes" htmlFor="notes" hint="Optional">
                <textarea
                  id="notes"
                  rows={2}
                  maxLength={1000}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. Mention UPI, keep it under 5 tips, end with a question"
                  className="w-full px-3 py-2.5 rounded-lg border border-input bg-background text-sm resize-none placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </Field>
            </section>
          ) : (
            <>
              <section className="rounded-lg border border-border bg-card p-6">
                <StylePanel value={style} onChange={setStyle} />
              </section>
              <section className="rounded-lg border border-border bg-card p-6 space-y-4">
                <div>
                  <h2 className="text-base font-semibold">Voice</h2>
                  <p className="text-hint text-muted-foreground">{language} voices. Press play to preview.</p>
                </div>
                <VoicePicker language={language} voiceId={style.voice_id} onChange={handleVoice} lockLanguage />
              </section>
            </>
          )}

          <div className="flex items-center justify-between gap-3">
            {step === 1 ? (
              <Button variant="outline" onClick={() => { setStep(0); scrollAppToTop(); }} disabled={loading}>
                <ArrowLeft className="w-4 h-4" /> Back
              </Button>
            ) : <span />}
            <div className="flex items-center gap-3">
              <span className="text-hint text-muted-foreground hidden sm:inline">
                {loading ? LOADING_STEPS[loadingStep] : step === 1 ? '~1 min' : ''}
              </span>
              {step === 0 ? (
                <Button onClick={goToStyle} disabled={!topic.trim()}>
                  Next: style <ArrowRight className="w-4 h-4" />
                </Button>
              ) : (
                <Button onClick={generate} loading={loading} disabled={!topic.trim()}>
                  {loading ? 'Generating…' : 'Generate script'}
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Live summary */}
        <aside className="lg:col-span-2">
          <div className="lg:sticky lg:top-8 space-y-6 rounded-lg border border-border bg-card p-6">
            <PhonePreview
              aspect={aspect}
              hook={topic.trim() ? topic.trim().split(/\s+/).slice(0, 6).join(' ') : ''}
              highlight={highlight}
              captionStyle={style.caption_style}
            />
            <div>
              <h2 className="text-base font-semibold mb-2">Summary</h2>
              <SummaryRow label="Topic" value={topic.trim()} />
              <SummaryRow label="Format" value={`${aspect} · ${formatLabel}`} />
              <SummaryRow label="Duration" value={`${duration}s`} />
              <SummaryRow label="Language" value={language} />
              <SummaryRow label="Tone" value={tones.map((t) => TONES.find((x) => x.id === t)?.label).join(', ')} />
              <SummaryRow label="Audience" value={audienceText} />
              <SummaryRow label="Visuals" value={style.visual_style === 'real' ? 'Real footage' : style.visual_style === 'animated' ? 'Animated' : 'Mixed'} />
              <SummaryRow label="Theme" value={style.accent_color ? `Custom ${style.accent_color}` : theme.label} />
            </div>
            <div className="pt-4 border-t border-border/60 text-xs text-muted-foreground flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-primary shrink-0" />
              <span>Agnes AI Script Engine · Purffle & Qreate Reel Engine</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

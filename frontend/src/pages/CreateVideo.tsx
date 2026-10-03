import { useState, useEffect } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import {
  Sparkles,
  ChevronRight,
  Loader2,
  Wand2,
  Smartphone,
  Monitor,
  Clock,
  Globe,
  Users,
  Film,
  Zap,
  Check,
  AlertCircle,
  Lightbulb,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { projectsApi, scriptsApi } from '../services/api';
import { cn } from '../lib/utils';

interface ToneOption {
  id: string;
  name: string;
  emoji: string;
  desc: string;
}

const TONE_OPTIONS: ToneOption[] = [
  { id: 'educational', name: 'Educational', emoji: '🎓', desc: 'Clear, informative & curiosity-driven' },
  { id: 'cinematic', name: 'Cinematic', emoji: '🎬', desc: 'Epic storytelling & dramatic pacing' },
  { id: 'entertaining', name: 'Entertaining', emoji: '🎭', desc: 'Fun, witty & high engagement' },
  { id: 'professional', name: 'Professional', emoji: '💼', desc: 'Authoritative, polished & articulate' },
  { id: 'inspirational', name: 'Inspirational', emoji: '✨', desc: 'Uplifting, motivational & emotive' },
  { id: 'conversational', name: 'Conversational', emoji: '💬', desc: 'Relatable, friendly & natural' },
  { id: 'mysterious', name: 'Mysterious', emoji: '🌌', desc: 'Intriguing, suspenseful & captivating' },
  { id: 'high_energy', name: 'Fast-Paced', emoji: '⚡', desc: 'Punchy hooks & rapid scene changes' },
];

const DURATION_PRESETS = [
  { value: '30', label: '30s', tag: 'Micro Short' },
  { value: '60', label: '60s', tag: 'Standard Reel' },
  { value: '90', label: '90s', tag: 'Extended Story' },
  { value: '120', label: '2 min', tag: 'Explainer' },
  { value: '180', label: '3 min', tag: 'Deep Dive' },
];

const LANGUAGE_OPTIONS = [
  { value: 'English', label: 'English' },
  { value: 'Spanish', label: 'Spanish' },
  { value: 'French', label: 'French' },
  { value: 'German', label: 'German' },
  { value: 'Japanese', label: 'Japanese' },
  { value: 'Chinese', label: 'Chinese' },
  { value: 'Portuguese', label: 'Portuguese' },
  { value: 'Hindi', label: 'Hindi' },
];

const AUDIENCE_CHIPS = ['General Audience', 'Curious Beginners', 'Tech Enthusiasts', 'Students & Researchers', 'Creative Professionals'];

const INSPIRATION_IDEAS = [
  'How Gravitational Lensing Reveals Hidden Galaxies',
  'Why the Human Brain Struggles with Multitasking',
  'How James Webb Space Telescope Captures Deep Space',
  'The Next Revolution in Quantum Computing',
];

interface FormState {
  projectName: string;
  topic: string;
  title: string;
  aspect_ratio: '9:16' | '16:9';
  duration_seconds: string;
  language: string;
  tone: string[];
  audience: string;
  additional_instructions: string;
  general?: string;
}

function extractTopicString(val: unknown): string {
  if (typeof val === 'string') return val;
  if (!val || typeof val !== 'object') return '';
  const obj = val as Record<string, unknown>;
  if (typeof obj.topic === 'string') return obj.topic;
  if (typeof obj.title === 'string') return obj.title;
  if (typeof obj.name === 'string') return obj.name;
  if (typeof obj.value === 'string') return obj.value;
  if (typeof obj.text === 'string') return obj.text;
  if (typeof obj.prompt === 'string') return obj.prompt;
  if (typeof obj.idea === 'string') return obj.idea;
  if (obj.topic && typeof obj.topic === 'object') return extractTopicString(obj.topic);
  return '';
}

function normalizeToneArray(val: unknown): string[] {
  if (Array.isArray(val)) {
    return val
      .map((v) => {
        const str = String(v).trim().toLowerCase();
        const match = TONE_OPTIONS.find((opt) => opt.id === str || opt.name.toLowerCase() === str);
        return match ? match.id : str;
      })
      .filter(Boolean);
  }
  if (typeof val === 'string' && val.trim()) {
    return val
      .split(',')
      .map((s) => {
        const str = s.trim().toLowerCase();
        const match = TONE_OPTIONS.find((opt) => opt.id === str || opt.name.toLowerCase() === str);
        return match ? match.id : str;
      })
      .filter(Boolean);
  }
  return [];
}

export default function CreateVideo() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const [form, setForm] = useState<FormState>(() => ({
    projectName: '',
    topic: '',
    title: '',
    aspect_ratio: (localStorage.getItem('qreate_pref_aspect') as '9:16' | '16:9') || '9:16',
    duration_seconds: '60',
    language: 'English',
    tone: ['educational', 'cinematic'],
    audience: 'General Audience',
    additional_instructions: '',
  }));

  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'idle' | 'creating_project' | 'generating_script'>('idle');

  // Handle prefill from navigation state or query parameters
  useEffect(() => {
    const state = location.state as Record<string, unknown> | null;
    const projectFromState = (state?.project as Record<string, unknown>) || null;

    const rawTopic =
      searchParams.get('topic') ||
      state?.topic ||
      projectFromState?.topic ||
      state?.idea ||
      '';
    const cleanTopic = extractTopicString(rawTopic);

    const initialProjectName =
      (state?.projectName as string) ||
      (projectFromState?.name as string) ||
      (state?.name as string) ||
      '';

    const rawTone = state?.tone || projectFromState?.tone;
    const initialTone = rawTone ? normalizeToneArray(rawTone) : undefined;
    const rawAspect = searchParams.get('aspect') || state?.aspect_ratio;

    if (cleanTopic || initialProjectName || initialTone !== undefined || rawAspect) {
      setForm((prev) => ({
        ...prev,
        topic: cleanTopic || prev.topic,
        projectName: initialProjectName || prev.projectName || (cleanTopic ? cleanTopic.slice(0, 32) : ''),
        tone: initialTone !== undefined ? initialTone : prev.tone,
        aspect_ratio: rawAspect === '16:9' ? '16:9' : rawAspect === '9:16' ? '9:16' : prev.aspect_ratio,
      }));
    }
  }, [location.state, searchParams]);

  const handleTopicChange = (val: string) => {
    setForm((prev) => {
      const next = { ...prev, topic: val };
      // Auto-populate Project Name if still blank
      if (!prev.projectName.trim() && val.trim()) {
        const words = val.trim().split(/\s+/).slice(0, 5).join(' ');
        next.projectName = words.charAt(0).toUpperCase() + words.slice(1);
      }
      return next;
    });
    setErrors((prev) => ({ ...prev, topic: '' }));
  };

  const toggleTone = (toneId: string) => {
    setForm((prev) => {
      const exists = prev.tone.includes(toneId);
      const newTones = exists
        ? prev.tone.filter((t) => t !== toneId)
        : [...prev.tone, toneId];
      return { ...prev, tone: newTones };
    });
  };

  function validate(): boolean {
    const newErrors: Partial<Record<keyof FormState, string>> = {};
    if (!form.projectName.trim()) newErrors.projectName = 'Please give your project a name';
    const cleanTopic = extractTopicString(form.topic).trim();
    if (!cleanTopic) newErrors.topic = 'Please describe the video topic or idea';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      const cleanTopic = extractTopicString(form.topic).trim();

      // Step 1: Create project in MongoDB
      setStep('creating_project');
      const project = await projectsApi.create({
        name: form.projectName.trim(),
        topic: cleanTopic,
      });

      // Step 2: Generate multi-scene script via Agnes AI / Purffle
      setStep('generating_script');
      const script = await scriptsApi.generate({
        project_id: project.id,
        topic: cleanTopic,
        title: form.title.trim() || form.projectName.trim(),
        duration_seconds: parseInt(form.duration_seconds),
        language: form.language,
        tone: form.tone.length > 0 ? form.tone : ['educational'],
        audience: form.audience,
        additional_instructions: form.additional_instructions.trim() || undefined,
      });

      // Navigate to Script Studio
      navigate(`/scripts/${script.id}`, {
        state: {
          projectId: project.id,
          aspectRatio: form.aspect_ratio,
        },
      });
    } catch (err) {
      console.error(err);
      const errMsg = (err as Error).message || 'Failed to generate script. Please try again.';
      if (/additional_instruction/i.test(errMsg)) {
        setErrors({ additional_instructions: errMsg });
      } else if (/topic/i.test(errMsg)) {
        setErrors({ topic: errMsg });
      } else if (/name/i.test(errMsg)) {
        setErrors({ projectName: errMsg });
      } else {
        setErrors({ general: errMsg });
      }
      setStep('idle');
    } finally {
      setLoading(false);
    }
  }

  const stepLabel =
    step === 'creating_project'
      ? 'Setting up project in studio...'
      : step === 'generating_script'
      ? 'Generating AI scenes & narration...'
      : 'Generate Script & Scenes';

  return (
    <div className="p-6 md:p-10 max-w-4xl mx-auto space-y-8 animate-fade-in">
      {/* Header & Step Breadcrumbs */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-xs font-semibold text-primary">
          <span className="w-5 h-5 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-[10px]">
            1
          </span>
          <span>Script Creation</span>
          <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">2. Scene Review</span>
          <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">3. Video Generation</span>
        </div>

        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground flex items-center gap-3">
            <span className="w-9 h-9 rounded-xl qreate-gradient flex items-center justify-center text-white shadow-sm">
              <Wand2 className="w-5 h-5" />
            </span>
            Create New Video Project
          </h1>
          <p className="text-sm text-muted-foreground mt-1.5 max-w-2xl">
            Describe your concept. Our AI will automatically write a compelling multi-scene script, design camera directions, and prepare it for instant video synthesis.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Section 1: Topic & Visual Format */}
        <Card className="p-6 md:p-7 space-y-6 border border-border shadow-xs">
          <div className="border-b border-border pb-3 flex items-center justify-between">
            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
              <Film className="w-4 h-4 text-primary" />
              1. Topic & Video Format
            </h2>
            <span className="text-xs text-muted-foreground">Core Concept</span>
          </div>

          {/* Aspect Ratio Selector */}
          <div className="space-y-2.5">
            <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
              Choose Video Format
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <button
                type="button"
                onClick={() => setForm((prev) => ({ ...prev, aspect_ratio: '9:16' }))}
                className={cn(
                  'p-4 rounded-xl border text-left flex items-start gap-3.5 transition-all cursor-pointer relative overflow-hidden',
                  form.aspect_ratio === '9:16'
                    ? 'border-primary bg-primary/10 text-foreground ring-1 ring-primary shadow-xs'
                    : 'border-border bg-card hover:bg-muted/40 text-muted-foreground'
                )}
              >
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center shrink-0">
                  <Smartphone className="w-5 h-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-foreground">9:16 Vertical Short</span>
                    {form.aspect_ratio === '9:16' && <Check className="w-4 h-4 text-primary" />}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    TikTok, YouTube Shorts, Reels & PurffleShorts V3 procedural motion graphics.
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setForm((prev) => ({ ...prev, aspect_ratio: '16:9' }))}
                className={cn(
                  'p-4 rounded-xl border text-left flex items-start gap-3.5 transition-all cursor-pointer relative overflow-hidden',
                  form.aspect_ratio === '16:9'
                    ? 'border-primary bg-primary/10 text-foreground ring-1 ring-primary shadow-xs'
                    : 'border-border bg-card hover:bg-muted/40 text-muted-foreground'
                )}
              >
                <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center shrink-0">
                  <Monitor className="w-5 h-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-foreground">16:9 Widescreen</span>
                    {form.aspect_ratio === '16:9' && <Check className="w-4 h-4 text-primary" />}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    YouTube longform, presentations, website showcases & cinematic landscape.
                  </p>
                </div>
              </button>
            </div>
          </div>

          {/* Video Topic / Prompt */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label htmlFor="video-topic" className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Video Topic or Prompt <span className="text-destructive">*</span>
              </label>
              <span className="text-[11px] text-muted-foreground">Be as descriptive as you like</span>
            </div>

            <div className="relative">
              <textarea
                id="video-topic"
                rows={3}
                placeholder="What is your video about? (e.g. 'How Black Holes bend light and create gravitational lensing, explained for beginners')..."
                value={form.topic}
                onChange={(e) => handleTopicChange(e.target.value)}
                className={cn(
                  'w-full p-4 rounded-xl border bg-background/80 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all resize-none placeholder:text-muted-foreground/60 shadow-inner',
                  errors.topic ? 'border-destructive focus:ring-destructive' : 'border-border'
                )}
              />
            </div>
            {errors.topic && (
              <p className="text-xs text-destructive flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" /> {errors.topic}
              </p>
            )}

            {/* Inspiration Chips */}
            <div className="pt-1 flex flex-wrap items-center gap-2 text-xs">
              <span className="text-muted-foreground font-medium flex items-center gap-1">
                <Lightbulb className="w-3.5 h-3.5 text-amber-400" /> Need inspiration?
              </span>
              {INSPIRATION_IDEAS.map((idea) => (
                <button
                  key={idea}
                  type="button"
                  onClick={() => handleTopicChange(idea)}
                  className="px-2.5 py-1 rounded-lg border border-border/80 bg-muted/40 hover:bg-accent text-muted-foreground hover:text-foreground transition-all truncate max-w-[280px]"
                >
                  {idea}
                </button>
              ))}
            </div>
          </div>

          {/* Project Name & Title */}
          <div className="grid sm:grid-cols-2 gap-4 pt-1">
            <div className="space-y-1.5">
              <label htmlFor="project-name" className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Project Name <span className="text-destructive">*</span>
              </label>
              <input
                id="project-name"
                type="text"
                placeholder="e.g. Black Holes Explained"
                value={form.projectName}
                onChange={(e) => {
                  setForm((prev) => ({ ...prev, projectName: e.target.value }));
                  setErrors((prev) => ({ ...prev, projectName: '' }));
                }}
                className={cn(
                  'w-full h-11 px-3.5 rounded-xl border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-colors',
                  errors.projectName ? 'border-destructive focus:ring-destructive' : 'border-border'
                )}
              />
              {errors.projectName && <p className="text-xs text-destructive">{errors.projectName}</p>}
            </div>

            <div className="space-y-1.5">
              <label htmlFor="video-title" className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Display Title (Optional)
              </label>
              <input
                id="video-title"
                type="text"
                placeholder="Leave blank to auto-generate"
                value={form.title}
                onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                className="w-full h-11 px-3.5 rounded-xl border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-colors"
              />
            </div>
          </div>
        </Card>

        {/* Section 2: Style, Tone & Pacing */}
        <Card className="p-6 md:p-7 space-y-6 border border-border shadow-xs">
          <div className="border-b border-border pb-3 flex items-center justify-between">
            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-400" />
              2. Style, Tone & Duration
            </h2>
            <span className="text-xs text-muted-foreground">Narrative Directing</span>
          </div>

          {/* Tone Multi-Selector */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Narrative Tone <span className="text-xs font-normal text-muted-foreground/75">(Pick one or blend multiple)</span>
              </label>
              {form.tone.length > 0 && (
                <span className="text-xs font-medium text-primary">
                  {form.tone.length} selected
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
              {TONE_OPTIONS.map((opt) => {
                const isSelected = form.tone.includes(opt.id);
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => toggleTone(opt.id)}
                    className={cn(
                      'p-3 rounded-xl border text-left transition-all duration-150 cursor-pointer select-none flex flex-col justify-between min-h-[72px]',
                      isSelected
                        ? 'border-primary bg-primary/10 text-foreground ring-1 ring-primary shadow-xs'
                        : 'border-border bg-card hover:bg-muted/40 text-muted-foreground hover:text-foreground'
                    )}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-lg">{opt.emoji}</span>
                      {isSelected ? (
                        <div className="w-4 h-4 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-[10px]">
                          <Check className="w-3 h-3 stroke-[3]" />
                        </div>
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border border-muted-foreground/30" />
                      )}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-foreground">{opt.name}</div>
                      <div className="text-[10px] text-muted-foreground truncate opacity-80">{opt.desc}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Duration Presets */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground block flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-blue-400" />
              Target Duration
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
              {DURATION_PRESETS.map((p) => {
                const isSelected = form.duration_seconds === p.value;
                return (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setForm((prev) => ({ ...prev, duration_seconds: p.value }))}
                    className={cn(
                      'p-2.5 rounded-xl border text-center transition-all cursor-pointer',
                      isSelected
                        ? 'border-primary bg-primary/15 text-primary font-bold shadow-xs ring-1 ring-primary/40'
                        : 'border-border bg-card hover:bg-muted/40 text-muted-foreground'
                    )}
                  >
                    <div className="text-sm font-extrabold">{p.label}</div>
                    <div className="text-[10px] opacity-75">{p.tag}</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Language & Audience */}
          <div className="grid sm:grid-cols-2 gap-4">
            {/* Language */}
            <div className="space-y-1.5">
              <label htmlFor="language" className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-emerald-400" />
                Narration Language
              </label>
              <select
                id="language"
                value={form.language}
                onChange={(e) => setForm((prev) => ({ ...prev, language: e.target.value }))}
                className="w-full h-11 px-3.5 rounded-xl border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-colors cursor-pointer"
              >
                {LANGUAGE_OPTIONS.map((l) => (
                  <option key={l.value} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Target Audience */}
            <div className="space-y-1.5">
              <label htmlFor="audience" className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-amber-400" />
                Target Audience
              </label>
              <input
                id="audience"
                type="text"
                placeholder="e.g. General Audience, Students, Tech Enthusiasts"
                value={form.audience}
                onChange={(e) => setForm((prev) => ({ ...prev, audience: e.target.value }))}
                className="w-full h-11 px-3.5 rounded-xl border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-colors"
              />
              <div className="flex flex-wrap gap-1.5 pt-1">
                {AUDIENCE_CHIPS.map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => setForm((prev) => ({ ...prev, audience: chip }))}
                    className="text-[10px] px-2 py-0.5 rounded-md bg-muted/60 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Optional Directing Instructions */}
          <div className="space-y-1.5 pt-1">
            <label htmlFor="additional-instructions" className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
              Director Notes & Custom Guidelines (Optional)
            </label>
            <textarea
              id="additional-instructions"
              rows={2}
              placeholder="e.g. Emphasize visual metaphors, mention recent 2026 data, end with an open question..."
              value={form.additional_instructions}
              onChange={(e) => setForm((prev) => ({ ...prev, additional_instructions: e.target.value }))}
              className="w-full p-3 rounded-xl border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-colors resize-none placeholder:text-muted-foreground/60"
            />
          </div>
        </Card>

        {/* AI Engine Info Box */}
        <div className="rounded-2xl border border-primary/20 bg-gradient-to-r from-primary/5 via-card to-purple-500/5 p-5 text-xs text-muted-foreground flex items-start gap-3.5 shadow-xs">
          <div className="w-8 h-8 rounded-lg qreate-gradient text-white flex items-center justify-center shrink-0 shadow-xs">
            <Zap className="w-4 h-4" />
          </div>
          <div className="space-y-1 flex-1">
            <p className="font-semibold text-foreground text-sm">
              Integrated PurffleShorts V3 & Agnes AI Cloud
            </p>
            <p>
              Your topic is processed through high-level LLM scriptwriting. The engine automatically outputs exact scene timings, visual subject/motion instructions, and keyword highlights. You can review and refine every scene in the interactive editor before final video rendering.
            </p>
          </div>
        </div>

        {errors.general && (
          <div className="rounded-xl border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errors.general}</span>
          </div>
        )}

        {/* Form Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="text-xs text-muted-foreground hover:text-foreground font-medium order-2 sm:order-1"
          >
            ← Back to Dashboard
          </button>

          <div className="flex items-center gap-3 w-full sm:w-auto order-1 sm:order-2">
            <Button
              type="submit"
              disabled={loading}
              className="w-full sm:w-auto h-12 px-8 qreate-gradient text-white font-bold text-sm shadow-md shadow-primary/25 hover:shadow-lg hover:shadow-primary/35 hover:opacity-95 active:scale-[0.98] transition-all cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  {stepLabel}
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Generate AI Script & Scenes
                  <ChevronRight className="w-4 h-4 ml-1.5" />
                </>
              )}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { Sparkles, ChevronRight, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input, Textarea, Select } from '../components/ui/Input';
import { Card } from '../components/ui/Card';
import { projectsApi, scriptsApi } from '../services/api';
import { cn } from '../lib/utils';

const TONE_OPTIONS = [
  'Professional',
  'Educational',
  'Entertaining',
  'Cinematic',
  'Conversational',
  'Inspirational',
];

const DURATION_OPTIONS = [
  { value: '30', label: '30 seconds' },
  { value: '60', label: '1 minute' },
  { value: '90', label: '1.5 minutes' },
  { value: '120', label: '2 minutes' },
  { value: '180', label: '3 minutes' },
  { value: '300', label: '5 minutes' },
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

interface FormState {
  projectName: string;
  topic: string;
  title: string;
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
        const str = String(v).trim();
        const match = TONE_OPTIONS.find((opt) => opt.toLowerCase() === str.toLowerCase());
        return match || str;
      })
      .filter(Boolean);
  }
  if (typeof val === 'string' && val.trim()) {
    return val
      .split(',')
      .map((s) => {
        const str = s.trim();
        const match = TONE_OPTIONS.find((opt) => opt.toLowerCase() === str.toLowerCase());
        return match || str;
      })
      .filter(Boolean);
  }
  return [];
}

export default function CreateVideo() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const [form, setForm] = useState<FormState>({
    projectName: '',
    topic: '',
    title: '',
    duration_seconds: '60',
    language: 'English',
    tone: [],
    audience: 'general',
    additional_instructions: '',
  });
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'idle' | 'creating_project' | 'generating_script'>('idle');

  // Handle reopening / editing or prefilling from navigation state or query params
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

    if (cleanTopic || initialProjectName || initialTone !== undefined) {
      setForm((prev) => ({
        ...prev,
        topic: cleanTopic || prev.topic,
        projectName: initialProjectName || prev.projectName,
        tone: initialTone !== undefined ? initialTone : prev.tone,
      }));
    }
  }, [location.state, searchParams]);

  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setForm((prev) => ({ ...prev, [key]: e.target.value }));
    setErrors((prev) => ({ ...prev, [key]: '' }));
  };

  const handleTopicChange = (e: React.ChangeEvent<HTMLTextAreaElement> | unknown) => {
    const rawVal =
      e && typeof e === 'object' && 'target' in e
        ? (e as React.ChangeEvent<HTMLTextAreaElement>).target.value
        : e;
    const cleanVal = extractTopicString(rawVal);
    setForm((prev) => ({ ...prev, topic: cleanVal }));
    setErrors((prev) => ({ ...prev, topic: '' }));
  };

  const toggleTone = (selectedTone: string) => {
    setForm((prev) => {
      const exists = prev.tone.includes(selectedTone);
      const newTones = exists
        ? prev.tone.filter((t) => t !== selectedTone)
        : [...prev.tone, selectedTone];
      return { ...prev, tone: newTones };
    });
  };

  function validate(): boolean {
    const newErrors: Partial<Record<keyof FormState, string>> = {};
    if (!form.projectName.trim()) newErrors.projectName = 'Project name is required';
    const cleanTopic = extractTopicString(form.topic).trim();
    if (!cleanTopic) newErrors.topic = 'Topic is required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      const cleanTopic = extractTopicString(form.topic).trim();

      // Step 1: Create project
      setStep('creating_project');
      const project = await projectsApi.create({
        name: form.projectName.trim(),
        topic: cleanTopic,
      });

      // Step 2: Generate script
      setStep('generating_script');
      const script = await scriptsApi.generate({
        project_id: project.id,
        topic: cleanTopic,
        title: form.title.trim() || undefined,
        duration_seconds: parseInt(form.duration_seconds),
        language: form.language,
        tone: form.tone,
        audience: form.audience,
        additional_instructions: form.additional_instructions.trim() || undefined,
      });

      // Navigate to script editor
      navigate(`/scripts/${script.id}`, { state: { projectId: project.id } });
    } catch (err) {
      console.error(err);
      const errMsg = (err as Error).message || 'An error occurred. Please try again.';
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

  const stepLabel = step === 'creating_project'
    ? 'Creating project...'
    : step === 'generating_script'
    ? 'Generating script with Agnes AI...'
    : 'Generate Script';

  const displayedTopic = extractTopicString(form.topic);

  return (
    <div className="p-8 max-w-3xl mx-auto animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Create New Video</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Configure your video project and we'll generate a script using Agnes AI
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Project Info */}
        <Card>
          <h2 className="text-base font-semibold mb-4">Project Details</h2>
          <div className="space-y-4">
            <Input
              label="Project Name"
              placeholder="e.g. Product Launch Campaign"
              value={form.projectName}
              onChange={set('projectName')}
              error={errors.projectName}
            />
            <Textarea
              label="Video Topic or Idea"
              placeholder="Describe what your video should be about. The more detail you provide, the better the script."
              rows={3}
              value={displayedTopic}
              onChange={handleTopicChange}
              error={errors.topic}
            />
            <Input
              label="Video Title (optional)"
              placeholder="Leave blank to auto-generate"
              value={form.title}
              onChange={set('title')}
            />
          </div>
        </Card>

        {/* Script Configuration */}
        <Card>
          <h2 className="text-base font-semibold mb-4">Script Configuration</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <Select
              label="Target Duration"
              value={form.duration_seconds}
              onChange={set('duration_seconds')}
              options={DURATION_OPTIONS}
            />
            <Select
              label="Language"
              value={form.language}
              onChange={set('language')}
              options={LANGUAGE_OPTIONS}
            />
            <Input
              label="Target Audience"
              placeholder="e.g. tech enthusiasts, beginners"
              value={form.audience}
              onChange={set('audience')}
            />
          </div>

          {/* Tone Multi-Select */}
          <div className="mt-4 space-y-1.5">
            <label className="block text-sm font-medium text-foreground">
              Tone <span className="text-xs font-normal text-muted-foreground">(Select one or more)</span>
            </label>
            <div className="flex flex-wrap gap-2 pt-1">
              {TONE_OPTIONS.map((opt) => {
                const isSelected = form.tone.includes(opt);
                return (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => toggleTone(opt)}
                    className={cn(
                      'px-3.5 py-2 rounded-lg text-sm font-medium border transition-all duration-150 flex items-center gap-2 cursor-pointer select-none',
                      isSelected
                        ? 'bg-primary/20 border-primary text-primary shadow-sm ring-1 ring-primary/40'
                        : 'bg-background border-input text-muted-foreground hover:border-input/80 hover:text-foreground'
                    )}
                  >
                    <span
                      className={cn(
                        'w-2 h-2 rounded-full transition-colors',
                        isSelected ? 'bg-primary' : 'border border-muted-foreground/40'
                      )}
                    />
                    {opt}
                  </button>
                );
              })}
            </div>
            {form.tone.length > 0 && (
              <p className="text-xs text-muted-foreground mt-1">
                Selected: <span className="text-foreground font-medium">{form.tone.join(', ')}</span>
              </p>
            )}
          </div>

          <div className="mt-4">
            <Textarea
              label="Additional Instructions (optional)"
              placeholder="Any specific requirements, key points to cover, or style guidelines..."
              rows={3}
              value={form.additional_instructions}
              onChange={set('additional_instructions')}
              error={errors.additional_instructions}
            />
          </div>
        </Card>

        {/* Info box */}
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 text-sm text-muted-foreground">
          <div className="flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-primary mt-0.5 shrink-0" />
            <p>
              Agnes 2.5 Flash will generate a scene-by-scene script tailored to your topic. You'll be able to review and edit it before generating the video.
            </p>
          </div>
        </div>

        {errors.general && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
            {errors.general}
          </div>
        )}

        {/* Submit */}
        <div className="flex items-center justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => navigate('/dashboard')}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {stepLabel}
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                {stepLabel}
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}

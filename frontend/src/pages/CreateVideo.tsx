import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, ChevronRight, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input, Textarea, Select } from '../components/ui/Input';
import { Card } from '../components/ui/Card';
import { projectsApi, scriptsApi } from '../services/api';

const TONE_OPTIONS = [
  { value: 'professional', label: 'Professional' },
  { value: 'educational', label: 'Educational' },
  { value: 'entertaining', label: 'Entertaining' },
  { value: 'cinematic', label: 'Cinematic' },
  { value: 'conversational', label: 'Conversational' },
  { value: 'inspirational', label: 'Inspirational' },
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
  tone: string;
  audience: string;
  additional_instructions: string;
}

export default function CreateVideo() {
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>({
    projectName: '',
    topic: '',
    title: '',
    duration_seconds: '60',
    language: 'English',
    tone: 'professional',
    audience: 'general',
    additional_instructions: '',
  });
  const [errors, setErrors] = useState<Partial<FormState>>({});
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'idle' | 'creating_project' | 'generating_script'>('idle');

  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setForm((prev) => ({ ...prev, [key]: e.target.value }));
    setErrors((prev) => ({ ...prev, [key]: '' }));
  };

  function validate(): boolean {
    const newErrors: Partial<FormState> = {};
    if (!form.projectName.trim()) newErrors.projectName = 'Project name is required';
    if (!form.topic.trim()) newErrors.topic = 'Topic is required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      // Step 1: Create project
      setStep('creating_project');
      const project = await projectsApi.create({
        name: form.projectName,
        topic: form.topic,
      });

      // Step 2: Generate script
      setStep('generating_script');
      const script = await scriptsApi.generate({
        project_id: project.id,
        topic: form.topic,
        title: form.title || undefined,
        duration_seconds: parseInt(form.duration_seconds),
        language: form.language,
        tone: form.tone,
        audience: form.audience,
        additional_instructions: form.additional_instructions || undefined,
      });

      // Navigate to script editor
      navigate(`/scripts/${script.id}`, { state: { projectId: project.id } });
    } catch (err) {
      console.error(err);
      setErrors({ topic: (err as Error).message || 'An error occurred. Please try again.' });
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
              value={form.topic}
              onChange={set('topic')}
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
            <Select
              label="Tone"
              value={form.tone}
              onChange={set('tone')}
              options={TONE_OPTIONS}
            />
            <Input
              label="Target Audience"
              placeholder="e.g. tech enthusiasts, beginners"
              value={form.audience}
              onChange={set('audience')}
            />
          </div>
          <div className="mt-4">
            <Textarea
              label="Additional Instructions (optional)"
              placeholder="Any specific requirements, key points to cover, or style guidelines..."
              rows={3}
              value={form.additional_instructions}
              onChange={set('additional_instructions')}
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

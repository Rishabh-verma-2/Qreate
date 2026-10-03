import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, ChevronRight, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input, Textarea, Select } from '../components/ui/Input';
import { Card } from '../components/ui/Card';
import { projectsApi, scriptsApi } from '../services/api';
import { DURATION_OPTIONS, LANGUAGE_OPTIONS, TONE_OPTIONS, VOICE_OPTIONS } from '../lib/options';
import MediaUploader from '../components/MediaUploader';
import type { UserMedia } from '../types';


interface FormState {
  projectName: string;
  topic: string;
  title: string;
  duration_seconds: string;
  language: string;
  tone: string;
  audience: string;
  additional_instructions: string;
  voice_gender: string;
}

export default function CreateVideo() {
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>({
    projectName: '',
    topic: '',
    title: '',
    duration_seconds: '30',
    language: 'English',
    tone: 'energetic',
    audience: 'general',
    additional_instructions: '',
    voice_gender: 'male',
  });
  const [media, setMedia] = useState<UserMedia[]>([]);
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
        voice_gender: form.voice_gender as 'male' | 'female',
        user_media: media,
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
    ? 'Writing hook & script...'
    : 'Generate Script';

  return (
    <div className="p-8 max-w-3xl mx-auto animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Create New Video</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Describe a topic, idea or trend. We write a hook-first script you can edit before rendering.
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
            <Select
              label="Voice"
              value={form.voice_gender}
              onChange={set('voice_gender')}
              options={VOICE_OPTIONS}
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
          <div className="mt-4">
            <MediaUploader value={media} onChange={setMedia} />
          </div>
        </Card>

        {/* Info box */}
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 text-sm text-muted-foreground">
          <div className="flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-primary mt-0.5 shrink-0" />
            <p>
              Every script opens with a 3-second hook, is paced for short-form, and plans real stock footage per scene. Want many videos at once? Use Batch Studio.
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

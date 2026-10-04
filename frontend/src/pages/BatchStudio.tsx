import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AlertCircle, ChevronRight, Loader2, Sparkles, XCircle } from 'lucide-react';
import { batchesApi } from '../services/api';
import type { Batch, BatchItem, UserMedia } from '../types';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Input, Select, Textarea } from '../components/ui/Input';
import { StatusBadge } from '../components/ui/Badge';
import { CopyPostButton, InspirationPanel, VerticalPlayer } from '../components/VideoCard';
import { downloadUrl } from '../lib/video';
import { formatDate } from '../lib/utils';
import { DURATION_OPTIONS, TONE_OPTIONS } from '../lib/options';
import { PageHeader } from '../components/ui/States';
import { loadStyle, saveStyle, type StyleChoices } from '../lib/styleOptions';
import StylePanel from '../components/StylePanel';
import VoicePicker from '../components/VoicePicker';
import MediaUploader from '../components/MediaUploader';


const STAGE_LABELS: Record<string, string> = {
  queued: 'Waiting in queue',
  starting: 'Starting',
  'researching trends': 'Researching trends & searches',
  'writing script': 'Writing hook & script',
  preparing: 'Preparing',
  voiceover: 'Recording voiceover',
  'finding footage': 'Finding real footage',
  'rendering scenes': 'Rendering scenes',
  'captions & audio': 'Captions & audio mix',
  'final edit': 'Final edit',
  uploading: 'Uploading',
  retrying: 'Retrying',
  done: 'Done',
};

function StepTitle({ n, title }: { n: number; title: string }) {
  return (
    <div className="flex items-center gap-2.5 mb-4">
      <span className="w-6 h-6 rounded-full bg-primary/15 text-primary text-xs font-bold flex items-center justify-center">{n}</span>
      <h2 className="text-base font-semibold">{title}</h2>
    </div>
  );
}

export default function BatchStudio() {
  const navigate = useNavigate();
  const [topics, setTopics] = useState('');
  const [name, setName] = useState('');
  const [duration, setDuration] = useState('30');
  const [language, setLanguage] = useState(() => {
    try { return localStorage.getItem('qreate_language') || 'English'; } catch { return 'English'; }
  });
  const [style, setStyle] = useState<StyleChoices>(loadStyle);
  const [tone, setTone] = useState('energetic');
  const [audience, setAudience] = useState('Gen Z & young professionals in India');
    const [instructions, setInstructions] = useState('');
  const [media, setMedia] = useState<UserMedia[]>([]);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [recent, setRecent] = useState<Batch[]>([]);

  useEffect(() => {
    batchesApi.list().then(setRecent).catch(() => setRecent([]));
  }, []);

  useEffect(() => {
    saveStyle(style);
    try { localStorage.setItem('qreate_language', language); } catch { /* ignore */ }
  }, [style, language]);

  const handleVoice = useCallback((lang: string, voiceId: string, gender: 'male' | 'female') => {
    setLanguage(lang);
    setStyle((s) => (s.voice_id === voiceId ? s : { ...s, voice_id: voiceId, voice_gender: gender }));
  }, []);

  const topicList = topics.split('\n').map((t) => t.trim()).filter(Boolean);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (topicList.length === 0) {
      setError('Add at least one topic (one per line)');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const batch = await batchesApi.create({
        name: name || undefined,
        topics: topicList,
        options: {
          duration_seconds: parseInt(duration),
          language,
          tone,
          audience,
          ...style,
          additional_instructions: instructions || undefined,
          user_media: media,
        },
      });
      navigate(`/batch/${batch.id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="px-4 py-8 sm:px-8 max-w-4xl mx-auto">
      <PageHeader
        title="Batch studio"
        description="Paste several topics, one per line. Each becomes its own video with the same style and voice, rendered in parallel."
      />

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <StepTitle n={1} title="Topics" />
          <div className="space-y-4">
            <Textarea
              label={`Topics (${topicList.length})`}
              rows={7}
              placeholder={'Why your phone battery dies faster in winter\n3 money habits every 20-something should start\nThe hidden history of chai in India'}
              value={topics}
              onChange={(e) => { setTopics(e.target.value); setError(''); }}
              error={error}
            />
            <Input label="Batch name (optional)" placeholder="e.g. Monday trend drop" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
        </Card>

        <Card>
          <StepTitle n={2} title="Style" />
          <StylePanel value={style} onChange={setStyle} />
        </Card>

        <Card>
          <StepTitle n={3} title="Voice & language" />
          <VoicePicker language={language} voiceId={style.voice_id} onChange={handleVoice} />
        </Card>

        <Card>
          <StepTitle n={4} title="Details" />
          <div className="space-y-4">
            <div className="grid sm:grid-cols-2 gap-4">
              <Select label="Length" value={duration} onChange={(e) => setDuration(e.target.value)} options={DURATION_OPTIONS} />
              <Select label="Tone" value={tone} onChange={(e) => setTone(e.target.value)} options={TONE_OPTIONS} />
            </div>
            <Input label="Audience" value={audience} onChange={(e) => setAudience(e.target.value)} />
            <Textarea
              label="Extra instructions (optional)"
              rows={2}
              placeholder="e.g. Mention our names Kartik & Gauri, end with a thank-you to family"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
            />
            <MediaUploader value={media} onChange={setMedia} />
          </div>
        </Card>
        <div className="flex justify-end">
          <Button type="submit" loading={submitting}>
            <Sparkles className="w-4 h-4" />
            Generate {topicList.length > 1 ? `${topicList.length} videos` : 'video'}
          </Button>
        </div>
      </form>

      {recent.length > 0 && (
        <section className="mt-10">
          <h2 className="text-base font-semibold mb-3">Recent batches</h2>
          <div className="space-y-2">
            {recent.map((b) => (
              <button
                key={b.id}
                onClick={() => navigate(`/batch/${b.id}`)}
                className="w-full flex items-center justify-between p-4 rounded-lg border border-border bg-card card-hover text-left"
              >
                <div>
                  <p className="font-medium text-sm">{b.name}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {b.summary?.counts?.completed || 0}/{b.summary?.total || b.topics.length} done · {formatDate(b.created_at)}
                  </p>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function BatchItemCard({ item, topic }: { item: BatchItem; topic: string }) {
  const { task, video } = item;
  const url = video?.cloudinary_url;
  const active = task.status === 'queued' || task.status === 'in_progress';
  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden flex flex-col">
      {task.status === 'completed' && url ? (
        <VerticalPlayer url={url} poster={video?.thumbnail_url} className="rounded-none" />
      ) : (
        <div className="aspect-[9/16] bg-muted/40 flex flex-col items-center justify-center gap-3 p-6 text-center">
          {active && <Loader2 className="w-7 h-7 animate-spin text-primary" />}
          {task.status === 'failed' && <XCircle className="w-7 h-7 text-red-400" />}
          <p className="text-sm font-medium">{STAGE_LABELS[task.stage || task.status] || task.stage || task.status}</p>
          {active && (
            <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
              <div className="h-full bg-primary rounded-full transition-all duration-700" style={{ width: `${Math.max(task.progress, 4)}%` }} />
            </div>
          )}
          {task.status === 'failed' && task.error_message && (
            <p className="text-xs text-red-400/80 line-clamp-4">{task.error_message}</p>
          )}
        </div>
      )}
      <div className="p-4 space-y-2 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium line-clamp-2">{video?.title || task.title || topic}</p>
          <StatusBadge status={task.status} />
        </div>
        {video?.post?.caption && <p className="text-xs text-muted-foreground line-clamp-3">{video.post.caption}</p>}
        <InspirationPanel inspiration={video?.inspiration} />
        {url && video && (
          <div className="flex flex-wrap gap-3 pt-1">
            <a href={downloadUrl(url)} className="text-xs text-primary font-medium hover:text-primary/80">Download MP4</a>
            <CopyPostButton video={video} />
          </div>
        )}
      </div>
    </div>
  );
}

export function BatchDetail() {
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const [batch, setBatch] = useState<Batch | null>(null);
  const [error, setError] = useState('');
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const b: Batch = await batchesApi.get(batchId!);
        if (cancelled) return;
        setBatch(b);
        const finished = b.summary && b.summary.done >= b.summary.total;
        if (!finished) timer.current = setTimeout(poll, 4000);
      } catch (err) {
        if (!cancelled) setError((err as Error).message);
      }
    }
    poll();
    return () => {
      cancelled = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [batchId]);

  if (error) {
    return (
      <div className="p-8 max-w-3xl mx-auto">
        <div className="flex items-center gap-2 p-4 rounded-lg border border-destructive/30 bg-destructive/10 text-sm text-red-400">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      </div>
    );
  }
  if (!batch) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const s = batch.summary;
  return (
    <div className="p-8 max-w-6xl mx-auto animate-fade-in">
      <div className="flex items-end justify-between mb-6 gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">{batch.name}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {s?.counts?.completed || 0} of {s?.total} ready
            {s?.counts?.failed ? ` · ${s.counts.failed} failed` : ''}
            {s && s.done < s.total ? ' · updating live' : ''}
          </p>
        </div>
        <Button variant="outline" onClick={() => navigate('/batch')}>New batch</Button>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {(batch.items || []).map((item, i) => (
          <BatchItemCard key={item.task.id} item={item} topic={item.task.topic || batch.topics[i]} />
        ))}
      </div>
    </div>
  );
}

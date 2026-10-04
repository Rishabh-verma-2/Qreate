import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Check, Copy, Download, FileWarning, Library, Loader2, RotateCcw, Video, XCircle } from 'lucide-react';
import { projectsApi, scriptsApi, videosApi } from '../services/api';
import type { Script, VideoTask } from '../types';
import { Button } from '../components/ui/Button';
import { useToast } from '../components/ui/Toast';
import { EmptyState, Skeleton } from '../components/ui/States';
import Stepper from '../components/create/Stepper';
import { downloadVideoFile } from '../lib/download';
import { postText } from '../lib/video';
import { cn } from '../lib/utils';

const POLL_MS = 3000;

const ENGINES = [
  { value: 'qreate', label: 'Qreate reel engine', desc: 'Real footage, trend research, reel-style edit', vertical: true },
  { value: 'purffle', label: 'Motion graphics engine', desc: 'Diagrams and motion graphics, any aspect ratio', vertical: false },
  { value: 'free', label: 'Classic engine', desc: 'Photo slideshow with narration', vertical: false },
];

// Pipeline stages in the order they really run (stage names come from the backend)
const STEPS = [
  { key: 'script', label: 'Script ready' },
  { key: 'voice', label: 'Voiceover' },
  { key: 'visuals', label: 'Finding footage' },
  { key: 'edit', label: 'Editing shots' },
  { key: 'captions', label: 'Captions & sound' },
  { key: 'final', label: 'Final video' },
];

function currentStep(task: VideoTask): { index: number; detail?: string } {
  if (task.status === 'completed') return { index: STEPS.length };
  const stage = (task.stage || '').toLowerCase();
  const count = /(\d+\/\d+)/.exec(stage)?.[1];
  if (stage.startsWith('finding footage')) return { index: 2, detail: count };
  if (stage.startsWith('editing shots')) return { index: 3, detail: count };
  if (stage.startsWith('captions')) return { index: 4 };
  if (stage.startsWith('final') || stage.startsWith('uploading')) return { index: 5 };
  if (stage) return { index: 1 };
  // Engines without stage reporting: estimate from progress
  const p = task.progress || 0;
  return { index: p < 25 ? 1 : p < 50 ? 2 : p < 80 ? 3 : p < 92 ? 4 : 5 };
}

function elapsed(fromIso?: string, toIso?: string) {
  if (!fromIso) return '0:00';
  const end = toIso ? new Date(toIso).getTime() : Date.now();
  const s = Math.max(0, Math.floor((end - new Date(fromIso).getTime()) / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

function PhoneFrame({ children, vertical }: { children: React.ReactNode; vertical: boolean }) {
  return vertical ? (
    <div className="mx-auto w-full max-w-[280px] rounded-[28px] border-[8px] border-foreground bg-foreground overflow-hidden">
      <div className="aspect-[9/16] rounded-[20px] overflow-hidden bg-black">{children}</div>
    </div>
  ) : (
    <div className="rounded-lg border border-border overflow-hidden bg-black aspect-video">{children}</div>
  );
}

export default function GenerateVideo() {
  const { scriptId } = useParams<{ scriptId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const stateAspect = (location.state as { aspectRatio?: string } | null)?.aspectRatio;
  const aspect = stateAspect === '16:9' ? '16:9' : '9:16';
  const vertical = aspect === '9:16';

  const [script, setScript] = useState<Script | null>(null);
  const [loading, setLoading] = useState(true);
  const [engine, setEngine] = useState(vertical ? 'qreate' : 'purffle');
  const [task, setTask] = useState<VideoTask | null>(null);
  const [starting, setStarting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [, setTick] = useState(0);
  const poll = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!scriptId) return;
    (async () => {
      try {
        const s: Script = await scriptsApi.get(scriptId);
        setScript(s);
        // Resume: show a render already running (or finished) for this script after a refresh
        const project = await projectsApi.get(s.project_id).catch(() => null);
        const latest = ((project?.video_tasks || []) as VideoTask[]).find((t) => t.script_id === scriptId);
        if (latest && latest.status !== 'failed') {
          setTask(latest);
          if (latest.status !== 'completed') track(latest.id);
        }
      } catch {
        setScript(null);
      } finally {
        setLoading(false);
      }
    })();
    return () => { if (poll.current) clearTimeout(poll.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scriptId]);

  // Elapsed-time ticker while rendering
  const running = task && ['pending', 'queued', 'in_progress'].includes(task.status);
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, [running]);

  function track(taskId: string) {
    const tick = async () => {
      try {
        const t: VideoTask = await videosApi.getTask(taskId);
        setTask(t);
        if (t.status === 'completed') {
          toast.success('Your video is ready');
          return;
        }
        if (t.status === 'failed') return;
      } catch {
        /* transient network error — keep polling */
      }
      poll.current = setTimeout(tick, POLL_MS);
    };
    poll.current = setTimeout(tick, POLL_MS);
  }

  async function start() {
    if (!script || !scriptId) return;
    setStarting(true);
    try {
      const t: VideoTask = await videosApi.generate({
        project_id: script.project_id,
        script_id: scriptId,
        aspect_ratio: aspect,
        engine,
      });
      setTask(t);
      if (t.status !== 'completed' && t.status !== 'failed') track(t.id);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setStarting(false);
    }
  }

  async function copyPost() {
    if (!script) return;
    await navigator.clipboard.writeText(postText({ post: script.post, title: script.title }));
    setCopied(true);
    toast.success('Caption and hashtags copied');
    setTimeout(() => setCopied(false), 1500);
  }

  async function download(url: string) {
    setDownloading(true);
    try {
      const name = (script?.title || 'qreate_video').replace(/[^a-z0-9]+/gi, '_').toLowerCase();
      await downloadVideoFile(url, `${name}.mp4`);
    } catch (err) {
      toast.error((err as Error).message || 'Download failed');
    } finally {
      setDownloading(false);
    }
  }

  if (loading) {
    return (
      <div className="px-4 py-8 sm:px-8 max-w-5xl mx-auto space-y-4">
        <Skeleton className="h-6 w-80" /><Skeleton className="h-8 w-1/2" /><Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (!script) {
    return (
      <div className="px-4 py-8 sm:px-8 max-w-3xl mx-auto">
        <EmptyState icon={FileWarning} title="Script not found" description="It may have been deleted."
          action={<Button onClick={() => navigate('/create')}>Create a new video</Button>} />
      </div>
    );
  }

  const done = task?.status === 'completed';
  const failed = task?.status === 'failed';
  const videoUrl = task?.cloudinary_url;
  const step = task ? currentStep(task) : null;
  const engines = ENGINES.filter((e) => vertical || !e.vertical);

  return (
    <div className="px-4 py-8 sm:px-8 max-w-5xl mx-auto">
      <div className="mb-8 space-y-6">
        <Stepper current={done ? 4 : 3} onSelect={(i) => i === 2 ? navigate(`/scripts/${scriptId}`, { state: location.state }) : i < 2 && navigate('/create')} />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{done ? 'Your video is ready' : 'Render video'}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {script.title} · {script.scenes.length} scenes · {aspect}
          </p>
        </div>
      </div>

      {/* Not started */}
      {!task && (
        <section className="rounded-lg border border-border bg-card p-6 space-y-6 max-w-2xl">
          <div className="space-y-2">
            <p className="text-sm font-medium">Engine</p>
            <div className="grid gap-2" role="radiogroup" aria-label="Engine">
              {engines.map((e) => (
                <button
                  key={e.value}
                  type="button"
                  role="radio"
                  aria-checked={engine === e.value}
                  onClick={() => setEngine(e.value)}
                  className={cn(
                    'flex items-center justify-between gap-3 rounded-lg border p-3 text-left',
                    engine === e.value ? 'border-primary bg-primary-soft' : 'border-border bg-background hover:border-primary/40'
                  )}
                >
                  <span>
                    <span className="block text-sm font-medium">{e.label}</span>
                    <span className="block text-hint text-muted-foreground">{e.desc}</span>
                  </span>
                  {engine === e.value && <Check className="w-4 h-4 text-primary shrink-0" />}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between gap-3">
            <Button variant="outline" onClick={() => navigate(`/scripts/${scriptId}`, { state: location.state })}>
              <ArrowLeft className="w-4 h-4" /> Edit script
            </Button>
            <div className="flex items-center gap-3">
              <span className="text-hint text-muted-foreground hidden sm:inline">~1–2 min</span>
              <Button onClick={start} loading={starting}>Render video</Button>
            </div>
          </div>
        </section>
      )}

      {/* Rendering / failed */}
      {task && !done && step && (
        <section className="rounded-lg border border-border bg-card p-6 max-w-2xl">
          <div className="flex items-center justify-between mb-2 text-sm">
            <span className="font-medium">
              {failed ? 'Render failed' : task.status === 'queued' ? 'Waiting for a render slot' : 'Rendering'}
            </span>
            <span className="tabular-nums text-muted-foreground">{task.progress || 0}% · {elapsed(task.created_at)}</span>
          </div>
          <div className="h-1.5 rounded-full bg-muted overflow-hidden mb-6" role="progressbar" aria-valuenow={task.progress || 0} aria-valuemin={0} aria-valuemax={100}>
            <div className={cn('h-full transition-all duration-500', failed ? 'bg-destructive' : 'bg-primary')} style={{ width: `${Math.max(task.progress || 0, 3)}%` }} />
          </div>
          <ol className="space-y-3">
            {STEPS.map((s, i) => {
              const isDone = i < step.index || i === 0;
              const isActive = i === step.index && !failed;
              const isFailed = failed && i === step.index;
              return (
                <li key={s.key} className="flex items-center gap-3 text-sm">
                  <span className={cn(
                    'w-5 h-5 rounded-full flex items-center justify-center shrink-0',
                    isDone && 'bg-success text-white',
                    isActive && 'text-primary',
                    isFailed && 'text-destructive',
                    !isDone && !isActive && !isFailed && 'border border-border'
                  )}>
                    {isDone ? <Check className="w-3 h-3" /> : isActive ? <Loader2 className="w-4 h-4 animate-spin" /> : isFailed ? <XCircle className="w-4 h-4" /> : null}
                  </span>
                  <span className={cn(isActive ? 'text-foreground font-medium' : isDone ? 'text-foreground' : 'text-muted-foreground')}>
                    {s.label}{isActive && step.detail ? ` (${step.detail})` : ''}
                  </span>
                </li>
              );
            })}
          </ol>
          {failed && (
            <div className="mt-6 rounded-lg border border-destructive/30 bg-destructive/5 p-4">
              <p className="text-sm text-destructive">{task.error_message || 'Something went wrong while rendering.'}</p>
              <div className="flex gap-2 mt-3">
                <Button size="sm" onClick={() => { setTask(null); start(); }} loading={starting}>
                  <RotateCcw className="w-4 h-4" /> Retry
                </Button>
                <Button size="sm" variant="outline" onClick={() => navigate(`/scripts/${scriptId}`, { state: location.state })}>Edit script</Button>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Result */}
      {done && (
        <section className="grid gap-8 md:grid-cols-[300px_1fr] items-start">
          <PhoneFrame vertical={vertical}>
            {videoUrl ? (
              <video src={videoUrl} poster={task?.thumbnail_url} controls playsInline className="w-full h-full object-contain" />
            ) : (
              <div className="h-full flex items-center justify-center"><Video className="w-8 h-8 text-white/40" /></div>
            )}
          </PhoneFrame>
          <div className="space-y-6">
            <div className="flex flex-wrap gap-2">
              {videoUrl && (
                <Button onClick={() => download(videoUrl)} loading={downloading}>
                  {!downloading && <Download className="w-4 h-4" />} Download MP4
                </Button>
              )}
              <Button variant="outline" onClick={copyPost}>
                {copied ? <Check className="w-4 h-4 text-success" /> : <Copy className="w-4 h-4" />} Copy caption + hashtags
              </Button>
              <Button variant="ghost" onClick={() => navigate('/library')}>
                <Library className="w-4 h-4" /> Library
              </Button>
            </div>
            <div className="rounded-lg border border-border p-4">
              <p className="text-sm font-medium mb-1">Caption</p>
              <p className="text-sm text-muted-foreground whitespace-pre-line">{script.post?.caption || script.title}</p>
              {!!script.post?.hashtags?.length && (
                <p className="text-sm text-primary mt-2">{script.post.hashtags.map((h) => `#${h}`).join(' ')}</p>
              )}
            </div>
            <p className="text-hint text-muted-foreground">
              Rendered in {elapsed(task?.created_at, task?.completed_at)}
              {engine === 'qreate' ? ' · 1080×1920 MP4 with captions and music' : ''}
            </p>
          </div>
        </section>
      )}
    </div>
  );
}

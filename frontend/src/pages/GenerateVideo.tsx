import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  Video,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  ExternalLink,
  ChevronRight,
  Download,
} from 'lucide-react';
import { scriptsApi, videosApi } from '../services/api';
import type { Script, VideoTask } from '../types';
import { downloadVideoFile } from '../lib/download';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Select } from '../components/ui/Input';
import { StatusBadge } from '../components/ui/Badge';

const ASPECT_RATIO_OPTIONS = [
  { value: '16:9', label: '16:9 — Landscape (1280×704)' },
  { value: '9:16', label: '9:16 — Portrait (720×1280)' },
  { value: '1:1', label: '1:1 — Square (720×720)' },
  { value: '4:3', label: '4:3 (960×720)' },
  { value: '3:4', label: '3:4 (720×960)' },
];

const DURATION_OPTIONS = [
  { value: '4', label: '4 seconds' },
  { value: '5', label: '5 seconds' },
  { value: '6', label: '6 seconds' },
  { value: '8', label: '8 seconds' },
  { value: '10', label: '10 seconds' },
  { value: '12', label: '12 seconds' },
];

const ENGINE_OPTIONS = [
  { value: 'free', label: '⚡ Free AI Multi-Scene Engine (Neural Voice + Visuals — 100% Free)' },
  { value: 'auto', label: '🔄 Auto (Try Agnes AI, fallback to Free Engine if rate-limited)' },
  { value: 'agnes', label: '🤖 Agnes Video Generator (Requires Token Plan on Agnes)' },
];

const POLL_INTERVAL = 4000; // ms

export default function GenerateVideo() {
  const { scriptId } = useParams<{ scriptId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const projectId = (location.state as { projectId?: string })?.projectId;

  const [script, setScript] = useState<Script | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [task, setTask] = useState<VideoTask | null>(null);
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [durationSeconds, setDurationSeconds] = useState('5');
  const [engine, setEngine] = useState('free');
  const [error, setError] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!scriptId) return;
    scriptsApi.get(scriptId).then(setScript).catch(console.error).finally(() => setLoading(false));
    return () => stopPolling();
  }, [scriptId]);

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  function startPolling(taskId: string) {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const updated = await videosApi.getTask(taskId);
        setTask(updated);
        if (updated.status === 'completed' || updated.status === 'failed') {
          stopPolling();
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, POLL_INTERVAL);
  }

  async function handleGenerateVideo() {
    if (!script || !scriptId) return;
    setGenerating(true);
    setError('');
    try {
      const createdTask = await videosApi.generate({
        project_id: script.project_id,
        script_id: scriptId,
        mode: 'text',
        duration_seconds: parseInt(durationSeconds),
        aspect_ratio: aspectRatio,
        engine: engine,
      });
      setTask(createdTask);
      if (createdTask.status !== 'completed' && createdTask.status !== 'failed') {
        startPolling(createdTask.id);
      }
    } catch (err) {
      setError((err as Error).message || 'Failed to start video generation');
    } finally {
      setGenerating(false);
    }
  }

  const videoUrl = task?.cloudinary_url || (task?.generation_settings as Record<string, string | undefined>)?.video_url;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Generate Video</h1>
        <p className="text-sm text-muted-foreground mt-1">Configure and generate your AI video</p>
      </div>

      {/* Script Summary */}
      {script && (
        <Card className="mb-6">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Approved Script</h2>
          <p className="font-semibold">{script.title}</p>
          <p className="text-sm text-muted-foreground mt-1">
            {script.scenes.length} scenes · {script.language} · {script.tone}
          </p>
          {script.hook && (
            <p className="text-sm text-muted-foreground mt-2 italic border-l-2 border-primary/30 pl-3">
              "{script.hook}"
            </p>
          )}
        </Card>
      )}

      {/* Video Settings */}
      {!task && (
        <Card className="mb-6">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">Video Settings</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <Select
              label="Aspect Ratio"
              value={aspectRatio}
              onChange={(e) => setAspectRatio(e.target.value)}
              options={ASPECT_RATIO_OPTIONS}
            />
            <Select
              label="Duration"
              value={durationSeconds}
              onChange={(e) => setDurationSeconds(e.target.value)}
              options={DURATION_OPTIONS}
            />
          </div>
          <div className="mt-4">
            <Select
              label="Generation Engine"
              value={engine}
              onChange={(e) => setEngine(e.target.value)}
              options={ENGINE_OPTIONS}
            />
          </div>
          <div className="mt-4 p-3 rounded-lg bg-muted/50 text-sm text-muted-foreground">
            {engine === 'free' ? (
              <span>⚡ <strong className="text-green-400">100% Free Engine:</strong> Generates multi-scene neural narration via Edge-TTS and scene visuals, exported directly to Cloudinary.</span>
            ) : engine === 'auto' ? (
              <span>🔄 <strong className="text-primary">Auto Engine:</strong> Tries Agnes AI GPU rendering; if Agnes rate limits or queue is full, seamlessly uses the Free Engine.</span>
            ) : (
              <span>🤖 <strong className="text-foreground">Agnes AI:</strong> Direct Agnes cloud GPU rendering (requires paid token plan on Agnes platform).</span>
            )}
          </div>
        </Card>
      )}

      {/* Error */}
      {error && (
        <div className="mb-6 flex items-start gap-2 p-4 rounded-lg border border-destructive/30 bg-destructive/10 text-sm text-red-400">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* Task Status */}
      {task && (
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold">Generation Status</h2>
            <StatusBadge status={task.status} />
          </div>

          {/* Progress bar */}
          {(task.status === 'in_progress' || task.status === 'queued') && (
            <div className="mb-4">
              <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
                <span>Processing...</span>
                <span>{task.progress}%</span>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-500"
                  style={{ width: `${Math.max(task.progress, 5)}%` }}
                />
              </div>
            </div>
          )}

          {/* Status messages */}
          {task.status === 'pending' && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="w-4 h-4 animate-pulse" />
              Connecting to Agnes AI...
            </div>
          )}
          {task.status === 'queued' && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              In queue — Agnes is processing your request...
            </div>
          )}
          {task.status === 'in_progress' && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              Generating video... This typically takes 2–3 minutes.
            </div>
          )}
          {task.status === 'completed' && (
            <div className="flex items-center gap-2 text-sm text-green-400">
              <CheckCircle2 className="w-4 h-4" />
              Video generated successfully!
            </div>
          )}
          {task.status === 'failed' && (
            <div className="flex items-center gap-2 text-sm text-red-400">
              <XCircle className="w-4 h-4" />
              {task.error_message || 'Generation failed. Please try again.'}
            </div>
          )}

          {/* Video preview / download */}
          {task.status === 'completed' && videoUrl && (
            <div className="mt-4 space-y-3">
              <video
                src={videoUrl}
                controls
                className="w-full rounded-xl border border-border bg-black shadow-lg"
              />
              <div className="flex flex-wrap items-center gap-3 pt-1">
                <button
                  type="button"
                  onClick={async () => {
                    setIsDownloading(true);
                    try {
                      const cleanTitle = (script?.title || 'video').replace(/[^a-zA-Z0-9_-]/g, '_');
                      await downloadVideoFile(videoUrl, `qreate_${cleanTitle}_${task.id}.mp4`);
                    } finally {
                      setIsDownloading(false);
                    }
                  }}
                  disabled={isDownloading}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-all shadow-xs disabled:opacity-50 cursor-pointer"
                >
                  {isDownloading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Saving Video...</span>
                    </>
                  ) : (
                    <>
                      <Download className="w-3.5 h-3.5" />
                      <span>Download Video (.mp4)</span>
                    </>
                  )}
                </button>

                <a
                  href={videoUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-border bg-card hover:bg-accent text-xs font-medium text-foreground transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5 text-muted-foreground" />
                  <span>Open Direct Link</span>
                </a>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => navigate(`/scripts/${scriptId}`, { state: { projectId } })}>
          ← Back to Script
        </Button>

        <div className="flex items-center gap-3">
          {task?.status === 'completed' && (
            <Button onClick={() => navigate('/library')} variant="outline">
              View Library
            </Button>
          )}
          {!task && (
            <Button
              onClick={handleGenerateVideo}
              loading={generating}
              disabled={!script}
            >
              <Video className="w-4 h-4" />
              Generate Video
            </Button>
          )}
          {task?.status === 'failed' && (
            <Button onClick={() => { setTask(null); setError(''); }}>
              Try Again
            </Button>
          )}
          {task?.status === 'completed' && script?.project_id && (
            <Button onClick={() => navigate(`/projects/${script.project_id}`)}>
              View Project
              <ChevronRight className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

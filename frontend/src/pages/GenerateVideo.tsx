import { useEffect, useState, useRef, useMemo } from 'react';
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
  { value: '9:16', label: '9:16 — Vertical (Shorts, Reels, TikTok)' },
  { value: '16:9', label: '16:9 — Widescreen (YouTube, Landscape)' },
  { value: '1:1', label: '1:1 — Square (720×720)' },
  { value: '4:3', label: '4:3 (960×720)' },
  { value: '3:4', label: '3:4 (720×960)' },
];

const ENGINE_OPTIONS = [
  { value: 'purffle', label: '🎬 PurffleShorts V3 (Animated Motion Graphics — 100% Procedural Diagrams & Physics)' },
  { value: 'qreate', label: '📱 Qreate Reel Engine (Real Stock Footage — CLIP Vision, Whooshes, Beat Cuts)' },
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
  const [aspectRatio, setAspectRatio] = useState(() => {
    const stateAspect = (location.state as { aspectRatio?: string })?.aspectRatio;
    return stateAspect || localStorage.getItem('qreate_pref_aspect') || '9:16';
  });
  const [engine, setEngine] = useState(() => {
    return localStorage.getItem('qreate_pref_engine') || 'purffle';
  });
  const [error, setError] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);

  // Auto-calculate exact runtime from the approved script
  const totalScriptDuration = useMemo(() => {
    if (!script) return 60;
    if (script.duration_seconds && script.duration_seconds > 0) return script.duration_seconds;
    if (script.scenes && script.scenes.length > 0) {
      return script.scenes.reduce((sum, s) => sum + (s.duration_seconds || 6), 0);
    }
    return 60;
  }, [script]);

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
        duration_seconds: totalScriptDuration,
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
        <Card className="mb-6 border border-border/80 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              Approved Script
            </h2>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
              Ready to Render
            </span>
          </div>

          <h3 className="text-lg font-bold text-foreground">{script.title}</h3>

          <div className="flex flex-wrap items-center gap-2 mt-2.5">
            <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-primary/10 text-primary border border-primary/20 flex items-center gap-1.5 shadow-xs">
              <Clock className="w-3.5 h-3.5" />
              Duration: ~{totalScriptDuration}s
            </span>
            <span className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-muted text-foreground">
              {script.scenes.length} Scenes
            </span>
            <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-muted text-muted-foreground">
              {script.language}
            </span>
            <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-muted text-muted-foreground">
              {Array.isArray(script.tone)
                ? script.tone.map((t) => t.charAt(0).toUpperCase() + t.slice(1)).join(', ')
                : typeof script.tone === 'string'
                ? script.tone
                    .split(',')
                    .map((t) => t.trim().charAt(0).toUpperCase() + t.trim().slice(1))
                    .join(', ')
                : 'Professional'}
            </span>
          </div>

          {script.hook && (
            <p className="text-sm text-muted-foreground mt-3 italic border-l-2 border-primary/40 pl-3">
              "{script.hook}"
            </p>
          )}
        </Card>
      )}

      {/* Video Settings */}
      {!task && (
        <Card className="mb-6 border border-border/80 shadow-xs">
          <div className="flex items-center justify-between mb-4 border-b border-border pb-3">
            <h2 className="text-sm font-bold text-foreground uppercase tracking-wider">Video Settings</h2>
            <span className="text-xs text-muted-foreground">Visual Directing</span>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <Select
              label="Aspect Ratio"
              value={aspectRatio}
              onChange={(e) => setAspectRatio(e.target.value)}
              options={ASPECT_RATIO_OPTIONS}
            />

            {/* Synced duration display */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-foreground">Video Duration</label>
              <div className="h-10 px-3.5 rounded-lg border border-border bg-muted/40 flex items-center justify-between text-sm text-foreground">
                <span className="font-semibold flex items-center gap-1.5 text-primary">
                  <Clock className="w-4 h-4" />
                  ~{totalScriptDuration} seconds
                </span>
                <span className="text-[11px] text-muted-foreground font-medium bg-background px-2 py-0.5 rounded border border-border">
                  Synced to script
                </span>
              </div>
            </div>
          </div>

          {/* Engine locked to Purffle V3 */}
          {/* Generation Engine Selector */}
          <div className="mt-4 space-y-1.5">
            <label className="block text-sm font-medium text-foreground">Generation Engine</label>
            <Select
              value={engine}
              onChange={(e) => setEngine(e.target.value)}
              options={ENGINE_OPTIONS}
            />
          </div>

          <div className="mt-4 p-3.5 rounded-xl bg-muted/50 text-sm text-muted-foreground border border-border/60">
            {engine === 'qreate' ? (
              <span>📱 <strong className="text-yellow-400">Qreate Reel Engine:</strong> Real stock footage picked by CLIP vision, ~2s jump cuts with punch-ins, beat-synced cuts, whooshes, word-by-word captions and ducked music. Queued and rendered by scalable workers.</span>
            ) : (
              <span>🎬 <strong className="text-purple-400">PurffleShorts V3:</strong> High-impact procedural animated explainer diagrams, physics simulations, dynamic data charts, and bold synchronised captions — rendered 100% locally with zero slideshows.</span>
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
              <Clock className="w-4 h-4 animate-pulse text-purple-400" />
              Initializing video rendering pipeline...
            </div>
          )}
          {task.status === 'queued' && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
              In queue — sourcing visuals and preparing motion graphics...
            </div>
          )}
          {task.status === 'in_progress' && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              Synthesizing video — building neural audio, visual assets & synced captions...
            </div>
          )}
          {task.status === 'completed' && (
            <div className="flex items-center gap-2 text-sm text-green-400">
              <CheckCircle2 className="w-4 h-4" />
              Video generated and synced successfully!
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
            <Button onClick={() => setTask(null)} variant="outline">
              New Generation
            </Button>
          )}
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

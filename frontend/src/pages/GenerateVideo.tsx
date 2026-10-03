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
} from 'lucide-react';
import { scriptsApi, videosApi, projectsApi } from '../services/api';
import type { Script, VideoTask } from '../types';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Select } from '../components/ui/Input';
import { StatusBadge } from '../components/ui/Badge';

// PurffleShorts V3 — only duration is user-configurable
const DURATION_OPTIONS = [
  { value: '4',  label: '4 seconds'  },
  { value: '5',  label: '5 seconds'  },
  { value: '6',  label: '6 seconds'  },
  { value: '8',  label: '8 seconds'  },
  { value: '10', label: '10 seconds' },
  { value: '12', label: '12 seconds' },
];

// Always fixed — never exposed to the user
const FIXED_ENGINE       = 'purffle' as const;
const FIXED_ASPECT_RATIO = '9:16'    as const;

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
  const [durationSeconds, setDurationSeconds] = useState('5');
  const [error, setError] = useState('');

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!scriptId) return;
    scriptsApi.get(scriptId).then(async (s) => {
      setScript(s);
      if (s?.project_id) {
        try {
          const proj = await projectsApi.get(s.project_id);
          const tasks: VideoTask[] = proj.video_tasks || [];
          const scriptTasks = tasks.filter((t) => t.script_id === scriptId);
          if (scriptTasks.length > 0) {
            const latest = scriptTasks[scriptTasks.length - 1];
            setTask(latest);
            if (latest.status === 'in_progress' || latest.status === 'queued' || latest.status === 'pending') {
              startPolling(latest.id);
            }
          }
        } catch (e) {
          console.error('Failed to load existing task:', e);
        }
      }
    }).catch(console.error).finally(() => setLoading(false));
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
        aspect_ratio: FIXED_ASPECT_RATIO,
        engine: FIXED_ENGINE,
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
            {script.scenes.length} scenes · {script.language} · {Array.isArray(script.tone) ? script.tone.join(', ') : script.tone}
          </p>
          {script.hook && (
            <p className="text-sm text-muted-foreground mt-2 italic border-l-2 border-primary/30 pl-3">
              "{script.hook}"
            </p>
          )}
        </Card>
      )}

      {/* Video Settings — PurffleShorts V3 only */}
      {!task && (
        <Card className="mb-6">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">Video Settings</h2>

          {/* Locked engine badge */}
          <div className="flex items-center gap-3 mb-4 p-3 rounded-lg border border-purple-500/30 bg-purple-500/5">
            <span className="text-xl">🎬</span>
            <div className="flex-1">
              <p className="text-sm font-semibold text-purple-300">PurffleShorts V3</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                9:16 Portrait · Qwen scene generation · V3 motion graphics · Cloudinary delivery
              </p>
            </div>
            <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-medium border border-purple-500/30">
              Active
            </span>
          </div>

          {/* Duration — the only user-configurable setting */}
          <Select
            label="Scene Duration"
            value={durationSeconds}
            onChange={(e) => setDurationSeconds(e.target.value)}
            options={DURATION_OPTIONS}
          />

          <div className="mt-3 text-xs text-muted-foreground">
            Format locked to <strong className="text-foreground">1080×1920 (9:16)</strong> · Engine locked to <strong className="text-foreground">PurffleShorts V3</strong>
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
              Preparing PurffleShorts V3 rendering pipeline...
            </div>
          )}
          {task.status === 'queued' && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
              In queue — PurffleShorts V3 is preparing Qwen scenes & motion graphics...
            </div>
          )}
          {task.status === 'in_progress' && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
              Generating with PurffleShorts V3 — building audio, visuals & motion graphics...
            </div>
          )}
          {task.status === 'completed' && (
            <div className="flex items-center gap-2 text-sm text-green-400">
              <CheckCircle2 className="w-4 h-4" />
              PurffleShorts V3 video generated successfully!
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
                className="w-full max-h-[600px] object-contain rounded-lg border border-border bg-black"
              />
              <div className="flex items-center gap-3">
                <a
                  href={videoUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-primary hover:text-primary/80 font-medium"
                >
                  <ExternalLink className="w-4 h-4" />
                  Open video
                </a>
                <a
                  href={videoUrl}
                  download
                  className="flex items-center gap-2 text-sm text-primary hover:text-primary/80 font-medium"
                >
                  Download
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

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
import { scriptsApi, videosApi } from '../services/api';
import type { Script, VideoTask } from '../types';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { StatusBadge } from '../components/ui/Badge';
import { CopyPostButton, VerticalPlayer } from '../components/VideoCard';
import { downloadUrl } from '../lib/video';


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
  const [error, setError] = useState('');

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

  const videoUrl = task?.cloudinary_url;

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
        <p className="text-sm text-muted-foreground mt-1">Render your script into a publish-ready vertical video</p>
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

      {/* Output format */}
      {!task && (
        <Card className="mb-6">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Output</h2>
          <ul className="text-sm text-muted-foreground space-y-1.5">
            <li>📱 Vertical 1080×1920 (9:16) for the Qoneqt Global Feed</li>
            <li>🎙️ Neural voiceover with word-by-word captions</li>
            <li>🎬 Real stock footage per scene, colour-graded, with smooth transitions</li>
            <li>🎵 Mood-matched royalty-free music, ducked under the voice</li>
          </ul>
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
          {task.status === 'queued' && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="w-4 h-4 animate-pulse" />
              Waiting for a free render worker...
            </div>
          )}
          {task.status === 'in_progress' && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              <span className="capitalize">{task.stage || 'rendering'}</span>… usually under 2 minutes.
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
              <VerticalPlayer url={videoUrl} poster={task.thumbnail_url} className="max-w-xs mx-auto border border-border" />
              <div className="flex items-center justify-center gap-4">
                <a href={videoUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-primary hover:text-primary/80 font-medium">
                  <ExternalLink className="w-4 h-4" />
                  Open video
                </a>
                <a href={downloadUrl(videoUrl)} className="text-sm text-primary hover:text-primary/80 font-medium">
                  Download MP4
                </a>
                {script && <CopyPostButton video={{ post: script.post, title: script.title }} />}
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

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FileText, Video, Plus, ChevronRight, Loader2, Clock } from 'lucide-react';
import { projectsApi } from '../services/api';
import type { Project } from '../types';
import VideoCard from '../components/VideoCard';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/Badge';
import { formatDate } from '../lib/utils';

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    projectsApi.get(projectId)
      .then(setProject)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="p-8 text-center">
        <p className="text-muted-foreground">Project not found</p>
      </div>
    );
  }

  const scripts = project.scripts || [];
  const tasks = project.video_tasks || [];
  const videos = project.generated_videos || [];

  return (
    <div className="p-8 max-w-4xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => navigate('/projects')}
          className="text-sm text-muted-foreground hover:text-foreground mb-3 flex items-center gap-1"
        >
          ← Projects
        </button>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">{project.name}</h1>
            <p className="text-sm text-muted-foreground mt-1 max-w-xl">{project.topic}</p>
            <div className="flex items-center gap-3 mt-2">
              <StatusBadge status={project.status} />
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatDate(project.created_at)}
              </span>
            </div>
          </div>
          <Button onClick={() => navigate('/create')}>
            <Plus className="w-4 h-4" />
            New Video
          </Button>
        </div>
      </div>

      {/* Scripts */}
      <section className="mb-8">
        <h2 className="text-base font-semibold mb-4">Scripts ({scripts.length})</h2>
        {scripts.length === 0 ? (
          <Card className="text-center py-10">
            <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-30" />
            <p className="text-sm text-muted-foreground">No scripts yet</p>
          </Card>
        ) : (
          <div className="space-y-2">
            {scripts.map((script) => (
              <button
                key={script.id}
                onClick={() => navigate(`/scripts/${script.id}`, { state: { projectId: project.id } })}
                className="w-full rounded-xl border border-border bg-card p-4 flex items-center justify-between hover:border-primary/40 transition-colors text-left group"
              >
                <div className="min-w-0">
                  <p className="font-medium text-sm group-hover:text-primary transition-colors">
                    {script.title || 'Untitled Script'}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    v{script.version} · {script.scenes?.length || 0} scenes · {script.language} · {formatDate(script.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-3">
                  {script.approved && <StatusBadge status="active" />}
                  <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary" />
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Video Tasks */}
      <section className="mb-8">
        <h2 className="text-base font-semibold mb-4">Video Tasks ({tasks.length})</h2>
        {tasks.length === 0 ? (
          <Card className="text-center py-10">
            <Video className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-30" />
            <p className="text-sm text-muted-foreground">No video tasks yet</p>
            {scripts.length > 0 && (
              <button
                onClick={() => navigate(`/scripts/${scripts[0].id}`, { state: { projectId: project.id } })}
                className="mt-2 text-sm text-primary hover:underline font-medium"
              >
                Open script and generate video
              </button>
            )}
          </Card>
        ) : (
          <div className="space-y-2">
            {tasks.map((task) => (
              <div
                key={task.id}
                className="rounded-xl border border-border bg-card p-4 flex items-center justify-between"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <StatusBadge status={task.status} />
                    {task.progress > 0 && task.status !== 'completed' && (
                      <span className="text-xs text-muted-foreground">{task.progress}%</span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {task.generation_settings?.aspect_ratio} · {task.generation_settings?.duration_seconds}s · {formatDate(task.created_at)}
                  </p>
                  {task.error_message && (
                    <p className="text-xs text-destructive mt-1">{task.error_message}</p>
                  )}
                </div>
                {task.cloudinary_url && (
                  <a
                    href={task.cloudinary_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:text-primary/80 font-medium shrink-0 ml-3"
                  >
                    View
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Generated Videos */}
      {videos.length > 0 && (
        <section>
          <h2 className="text-base font-semibold mb-4">Generated Videos ({videos.length})</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {videos.map((video) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderOpen, Video, Plus, Clock, TrendingUp, Loader2 } from 'lucide-react';
import { projectsApi, videosApi } from '../services/api';
import type { Project, GeneratedVideo } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/Badge';
import { formatDate, truncate } from '../lib/utils';

export default function Dashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [videos, setVideos] = useState<GeneratedVideo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([projectsApi.list(), videosApi.list()])
      .then(([p, v]) => {
        setProjects(p);
        setVideos(v);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const recentProjects = projects.slice(0, 5);
  const recentVideos = videos.slice(0, 6);

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Manage your video projects and generated content
          </p>
        </div>
        <Button onClick={() => navigate('/create')}>
          <Plus className="w-4 h-4" />
          New Video
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <Card className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <FolderOpen className="w-5 h-5 text-primary" />
          </div>
          <div>
            <p className="text-2xl font-bold">{loading ? '—' : projects.length}</p>
            <p className="text-sm text-muted-foreground">Projects</p>
          </div>
        </Card>
        <Card className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center shrink-0">
            <Video className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <p className="text-2xl font-bold">{loading ? '—' : videos.length}</p>
            <p className="text-sm text-muted-foreground">Videos</p>
          </div>
        </Card>
        <Card className="flex items-center gap-4 col-span-2 lg:col-span-1">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
            <TrendingUp className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <p className="text-2xl font-bold">Agnes AI</p>
            <p className="text-sm text-muted-foreground">Video 2.5 Flash</p>
          </div>
        </Card>
      </div>

      {/* Content area */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : (
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Recent Projects */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold">Recent Projects</h2>
              <button
                onClick={() => navigate('/projects')}
                className="text-sm text-primary hover:text-primary/80 font-medium"
              >
                View all
              </button>
            </div>

            {recentProjects.length === 0 ? (
              <Card className="text-center py-12">
                <FolderOpen className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-40" />
                <p className="text-sm text-muted-foreground">No projects yet</p>
                <button
                  onClick={() => navigate('/create')}
                  className="mt-3 text-sm text-primary hover:underline font-medium"
                >
                  Create your first video
                </button>
              </Card>
            ) : (
              <div className="space-y-2">
                {recentProjects.map((project) => (
                  <button
                    key={project.id}
                    onClick={() => navigate(`/projects/${project.id}`)}
                    className="w-full rounded-xl border border-border bg-card p-4 flex items-center justify-between hover:border-primary/40 transition-colors text-left group"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-sm text-foreground truncate group-hover:text-primary transition-colors">
                        {project.name}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">
                        {truncate(project.topic, 60)}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 shrink-0 ml-3">
                      <StatusBadge status={project.status} />
                      <span className="text-xs text-muted-foreground hidden sm:block">
                        {formatDate(project.created_at)}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Recent Videos */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold">Recent Videos</h2>
              <button
                onClick={() => navigate('/library')}
                className="text-sm text-primary hover:text-primary/80 font-medium"
              >
                View all
              </button>
            </div>

            {recentVideos.length === 0 ? (
              <Card className="text-center py-12">
                <Video className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-40" />
                <p className="text-sm text-muted-foreground">No videos generated yet</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Create a project and generate your first video
                </p>
              </Card>
            ) : (
              <div className="space-y-2">
                {recentVideos.map((video) => (
                  <div
                    key={video.id}
                    className="rounded-xl border border-border bg-card p-4 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                        <Video className="w-4 h-4 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">
                          {video.duration_seconds ? `${video.duration_seconds}s video` : 'Generated video'}
                        </p>
                        <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                          <Clock className="w-3 h-3" />
                          {formatDate(video.created_at)}
                        </p>
                      </div>
                    </div>
                    {video.cloudinary_url || video.original_url ? (
                      <a
                        href={video.cloudinary_url || video.original_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-primary hover:text-primary/80 font-medium shrink-0 ml-3"
                      >
                        View
                      </a>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

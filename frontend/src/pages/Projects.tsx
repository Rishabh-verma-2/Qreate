import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderOpen, Plus, Loader2, Trash2, Clock } from 'lucide-react';
import { projectsApi } from '../services/api';
import type { Project } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/Badge';
import { formatDate, truncate } from '../lib/utils';

export default function Projects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    projectsApi.list()
      .then(setProjects)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm('Delete this project?')) return;
    setDeletingId(id);
    try {
      await projectsApi.delete(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      console.error(err);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="p-8 max-w-4xl mx-auto animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Projects</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {projects.length} project{projects.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Button onClick={() => navigate('/create')}>
          <Plus className="w-4 h-4" />
          New Video
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : projects.length === 0 ? (
        <Card className="text-center py-20">
          <FolderOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-30" />
          <p className="text-muted-foreground font-medium">No projects yet</p>
          <p className="text-sm text-muted-foreground mt-1">
            Create your first video project to get started
          </p>
          <button
            onClick={() => navigate('/create')}
            className="mt-4 text-sm text-primary hover:underline font-medium"
          >
            Create project →
          </button>
        </Card>
      ) : (
        <div className="space-y-3">
          {projects.map((project) => (
            <button
              key={project.id}
              onClick={() => navigate(`/projects/${project.id}`)}
              className="w-full rounded-xl border border-border bg-card p-5 flex items-center justify-between hover:border-primary/40 transition-colors text-left group"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-3 mb-1">
                  <p className="font-semibold text-foreground group-hover:text-primary transition-colors">
                    {project.name}
                  </p>
                  <StatusBadge status={project.status} />
                </div>
                <p className="text-sm text-muted-foreground truncate max-w-md">
                  {truncate(project.topic, 80)}
                </p>
                <p className="text-xs text-muted-foreground mt-1.5 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatDate(project.created_at)}
                </p>
              </div>
              <div className="flex items-center gap-2 ml-4 shrink-0">
                <button
                  onClick={(e) => handleDelete(project.id, e)}
                  className="p-2 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors opacity-0 group-hover:opacity-100"
                  disabled={deletingId === project.id}
                >
                  {deletingId === project.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Clapperboard, FolderOpen, Layers, Plus } from 'lucide-react';
import { projectsApi, videosApi } from '../services/api';
import type { GeneratedVideo, Project, VideoTask } from '../types';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/Button';
import { EmptyState, PageHeader, Skeleton } from '../components/ui/States';
import VideoCard from '../components/VideoCard';
import { formatDate } from '../lib/utils';

function Stat({ label, value, loading }: { label: string; value: string; loading: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-hint text-muted-foreground">{label}</p>
      {loading ? <Skeleton className="h-7 w-16 mt-1" /> : <p className="text-2xl font-semibold mt-1 tabular-nums">{value}</p>}
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [videos, setVideos] = useState<GeneratedVideo[]>([]);
  const [active, setActive] = useState<VideoTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [topic, setTopic] = useState('');

  useEffect(() => {
    Promise.all([projectsApi.list(), videosApi.list(), videosApi.listTasks(true)])
      .then(([p, v, t]) => { setProjects(p); setVideos(v); setActive(t); })
      .catch(() => { /* empty states cover it */ })
      .finally(() => setLoading(false));
  }, []);

  // Keep the "rendering now" list fresh while something is rendering
  useEffect(() => {
    if (!active.length) return;
    const id = setInterval(() => {
      videosApi.listTasks(true).then(setActive).catch(() => {});
    }, 5000);
    return () => clearInterval(id);
  }, [active.length]);

  const name = user?.full_name?.split(' ')[0] || user?.name || user?.email?.split('@')[0] || 'there';
  const minutes = videos.reduce((sum, v) => sum + (v.duration_seconds || 0), 0) / 60;

  function quickStart(e: React.FormEvent) {
    e.preventDefault();
    navigate(topic.trim() ? `/create?topic=${encodeURIComponent(topic.trim())}` : '/create');
  }

  return (
    <div className="px-4 py-8 sm:px-8 max-w-6xl mx-auto space-y-10">
      <div>
        <PageHeader
          title={`Welcome back, ${name}`}
          description="Turn a topic, idea or trend into a publish-ready video for the Qoneqt feed."
          actions={
            <>
              <Button variant="outline" onClick={() => navigate('/batch')}><Layers className="w-4 h-4" /> Batch studio</Button>
              <Button onClick={() => navigate('/create')}><Plus className="w-4 h-4" /> Create video</Button>
            </>
          }
        />
        <form onSubmit={quickStart} className="flex flex-col sm:flex-row gap-2 max-w-2xl -mt-2">
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            maxLength={500}
            placeholder="e.g. 5 money habits every college student should know"
            aria-label="Video topic"
            className="flex-1 h-10 px-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
          <Button type="submit" variant="outline">Start <ArrowRight className="w-4 h-4" /></Button>
        </form>
      </div>

      <section className="grid grid-cols-3 gap-3 sm:gap-4">
        <Stat label="Videos" value={String(videos.length)} loading={loading} />
        <Stat label="Minutes of video" value={minutes.toFixed(1)} loading={loading} />
        <Stat label="Projects" value={String(projects.length)} loading={loading} />
      </section>

      {active.length > 0 && (
        <section>
          <h2 className="text-base font-semibold mb-3">Rendering now</h2>
          <ul className="rounded-lg border border-border divide-y divide-border">
            {active.map((t) => (
              <li key={t.id} className="flex items-center gap-4 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{t.title || t.topic || 'Video'}</p>
                  <p className="text-hint text-muted-foreground capitalize">{t.status === 'queued' ? 'Waiting for a render slot' : t.stage || 'Rendering'}</p>
                </div>
                <div className="w-32 h-1.5 rounded-full bg-muted overflow-hidden" role="progressbar" aria-valuenow={t.progress || 0} aria-valuemin={0} aria-valuemax={100}>
                  <div className="h-full bg-primary transition-all" style={{ width: `${Math.max(t.progress || 0, 3)}%` }} />
                </div>
                <span className="text-sm tabular-nums text-muted-foreground w-10 text-right">{t.progress || 0}%</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold">Recent videos</h2>
          {videos.length > 4 && (
            <button type="button" onClick={() => navigate('/library')} className="text-sm text-primary hover:underline">View all</button>
          )}
        </div>
        {loading ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="aspect-[9/16] w-full" />)}
          </div>
        ) : videos.length === 0 ? (
          <EmptyState icon={Clapperboard} title="No videos yet" description="Your rendered videos will show up here."
            action={<Button onClick={() => navigate('/create')}>Create your first video</Button>} />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {videos.slice(0, 4).map((v) => <VideoCard key={v.id} video={v} />)}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-base font-semibold mb-3">Recent projects</h2>
        {loading ? (
          <div className="space-y-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
        ) : projects.length === 0 ? (
          <EmptyState icon={FolderOpen} title="No projects yet" description="Each video you create starts a project." />
        ) : (
          <ul className="rounded-lg border border-border divide-y divide-border">
            {projects.slice(0, 5).map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => navigate(`/projects/${p.id}`)}
                  className="w-full flex items-center justify-between gap-4 px-4 py-3 text-left hover:bg-accent"
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-medium truncate">{p.name}</span>
                    <span className="block text-hint text-muted-foreground truncate">{p.topic}</span>
                  </span>
                  <span className="text-hint text-muted-foreground shrink-0">{formatDate(p.created_at)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

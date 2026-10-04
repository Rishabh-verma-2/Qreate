import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FolderOpen,
  Video,
  Plus,
  Clock,
  TrendingUp,
  Loader2,
  Sparkles,
  ArrowRight,
  Play,
  Film,
  Download,
  Zap,
  CheckCircle2,
  Smartphone,
} from 'lucide-react';
import { projectsApi, videosApi } from '../services/api';
import type { Project, GeneratedVideo } from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/Badge';
import { formatDate, truncate } from '../lib/utils';
import { useAuth } from '../context/AuthContext';
import { downloadVideoFile } from '../lib/download';

const SAMPLE_TOPICS = [
  'How Black Holes Distort Space and Time',
  'The James Webb Telescope’s Deepest Secrets',
  'The Science Behind Photosynthesis',
  'How Quantum Computers Beat Classical Supercomputers',
];

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();

  const [projects, setProjects] = useState<Project[]>([]);
  const [videos, setVideos] = useState<GeneratedVideo[]>([]);
  const [loading, setLoading] = useState(true);
  const [quickTopic, setQuickTopic] = useState('');
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([projectsApi.list(), videosApi.list()])
      .then(([p, v]) => {
        setProjects(p);
        setVideos(v);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleQuickCreate = (e: React.FormEvent) => {
    e.preventDefault();
    const topic = quickTopic.trim();
    if (topic) {
      navigate(`/create?topic=${encodeURIComponent(topic)}`);
    } else {
      navigate('/create');
    }
  };

  const handleDownload = async (video: GeneratedVideo, e: React.MouseEvent) => {
    e.stopPropagation();
    const url = video.cloudinary_url || video.original_url;
    if (!url) return;
    try {
      setDownloadingId(video.id);
      await downloadVideoFile(url, `qreate_video_${video.id.slice(0, 8)}.mp4`);
    } catch (err) {
      console.error('Download failed:', err);
    } finally {
      setDownloadingId(null);
    }
  };

  // Calculate greetings & stats
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  const userName = user?.full_name?.split(' ')[0] || user?.name || (user?.email ? user.email.split('@')[0] : 'Creator');

  const totalRuntimeSeconds = videos.reduce((acc, v) => acc + (v.duration_seconds || 0), 0);
  const totalRuntimeMinutes = (totalRuntimeSeconds / 60).toFixed(1);

  const recentProjects = projects.slice(0, 6);
  const recentVideos = videos.slice(0, 6);

  return (
    <div className="p-6 md:p-10 space-y-8 max-w-6xl mx-auto animate-fade-in">
      {/* Welcome Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-r from-card via-card to-primary/10 p-6 md:p-8 shadow-sm">
        <div className="absolute top-0 right-0 -mt-12 -mr-12 w-64 h-64 bg-primary/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
              <Sparkles className="w-3.5 h-3.5" />
              <span>PurffleShorts V3 & Agnes AI Engine Active</span>
            </div>

            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
              {greeting}, <span className="qreate-gradient-text">{isAuthenticated ? userName : 'Creator'}</span>!
            </h1>

            <p className="text-sm text-muted-foreground max-w-xl">
              Turn any topic into captivating 9:16 vertical shorts or widescreen cinematic videos with procedural diagrams, NASA imagery, and word-by-word synced captions.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <Button
              onClick={() => navigate('/create')}
              className="qreate-gradient text-white shadow-sm hover:opacity-95"
            >
              <Plus className="w-4 h-4 mr-1.5" />
              New Video Project
            </Button>
            <Button
              variant="outline"
              onClick={() => navigate('/library')}
              className="bg-card/70 backdrop-blur-xs"
            >
              <Film className="w-4 h-4 mr-1.5" />
              Video Library
            </Button>
          </div>
        </div>

        {/* Quick Idea Launcher Bar */}
        <div className="mt-6 pt-6 border-t border-border/60">
          <form onSubmit={handleQuickCreate} className="flex flex-col sm:flex-row items-stretch gap-2.5">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="What video would you like to create today? (e.g. 'How Black Holes Form')..."
                value={quickTopic}
                onChange={(e) => setQuickTopic(e.target.value)}
                className="w-full h-11 pl-4 pr-10 rounded-xl border border-border bg-background/80 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all shadow-inner placeholder:text-muted-foreground/70"
              />
              {quickTopic && (
                <button
                  type="button"
                  onClick={() => setQuickTopic('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground hover:text-foreground"
                >
                  ✕
                </button>
              )}
            </div>
            <Button type="submit" className="h-11 px-5 qreate-gradient text-white font-medium shrink-0">
              Generate Script <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
          </form>

          {/* Quick Idea Chips */}
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className="font-medium text-foreground/80 flex items-center gap-1">
              <Zap className="w-3.5 h-3.5 text-amber-400" /> Ideas:
            </span>
            {SAMPLE_TOPICS.map((topic) => (
              <button
                key={topic}
                type="button"
                onClick={() => setQuickTopic(topic)}
                className="px-2.5 py-1 rounded-lg bg-muted/60 hover:bg-accent border border-border/60 text-muted-foreground hover:text-foreground transition-all truncate max-w-[260px]"
              >
                {topic}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Projects Metric */}
        <Card className="p-5 flex items-center gap-4 hover:border-primary/40 transition-all hover:shadow-xs group">
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
            <FolderOpen className="w-6 h-6 text-primary" />
          </div>
          <div className="min-w-0">
            <p className="text-2xl font-bold text-foreground tracking-tight">{loading ? '—' : projects.length}</p>
            <p className="text-xs text-muted-foreground font-medium truncate">Total Projects</p>
          </div>
        </Card>

        {/* Videos Metric */}
        <Card className="p-5 flex items-center gap-4 hover:border-emerald-500/40 transition-all hover:shadow-xs group">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
            <Video className="w-6 h-6 text-emerald-500" />
          </div>
          <div className="min-w-0">
            <p className="text-2xl font-bold text-foreground tracking-tight">{loading ? '—' : videos.length}</p>
            <p className="text-xs text-muted-foreground font-medium truncate">Generated Videos</p>
          </div>
        </Card>

        {/* Runtime Metric */}
        <Card className="p-5 flex items-center gap-4 hover:border-blue-500/40 transition-all hover:shadow-xs group">
          <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
            <Clock className="w-6 h-6 text-blue-400" />
          </div>
          <div className="min-w-0">
            <p className="text-2xl font-bold text-foreground tracking-tight">
              {loading ? '—' : `${totalRuntimeMinutes}m`}
            </p>
            <p className="text-xs text-muted-foreground font-medium truncate">Content Rendered</p>
          </div>
        </Card>

        {/* Engines Metric */}
        <Card className="p-5 flex items-center gap-4 hover:border-purple-500/40 transition-all hover:shadow-xs group">
          <div className="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
            <TrendingUp className="w-6 h-6 text-purple-400" />
          </div>
          <div className="min-w-0">
            <p className="text-base font-bold text-foreground tracking-tight truncate">Purffle V3 + Agnes</p>
            <p className="text-xs text-emerald-500 font-medium flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Ready to Render
            </p>
          </div>
        </Card>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 space-y-3">
          <Loader2 className="w-9 h-9 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading your creative workspace...</p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Recent Projects Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FolderOpen className="w-4 h-4 text-primary" />
                <h2 className="text-base font-semibold text-foreground">Recent Projects</h2>
              </div>
              <button
                onClick={() => navigate('/projects')}
                className="text-xs text-primary hover:text-primary/80 font-medium flex items-center gap-1 group"
              >
                View all ({projects.length})
                <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
              </button>
            </div>

            {recentProjects.length === 0 ? (
              <Card className="text-center py-12 px-6 border-dashed">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3">
                  <FolderOpen className="w-6 h-6 text-primary opacity-60" />
                </div>
                <h3 className="text-sm font-semibold text-foreground">No projects created yet</h3>
                <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                  Start your first video project to generate scripts, visuals, and professional voice narration.
                </p>
                <Button
                  size="sm"
                  onClick={() => navigate('/create')}
                  className="mt-4 qreate-gradient text-white"
                >
                  <Plus className="w-3.5 h-3.5 mr-1" /> Create Your First Project
                </Button>
              </Card>
            ) : (
              <div className="space-y-2.5">
                {recentProjects.map((project) => (
                  <button
                    key={project.id}
                    onClick={() => navigate(`/projects/${project.id}`)}
                    className="w-full rounded-xl border border-border bg-card p-4 flex items-center justify-between hover:border-primary/50 hover:bg-muted/30 transition-all text-left group shadow-xs cursor-pointer"
                  >
                    <div className="min-w-0 pr-3">
                      <p className="font-semibold text-sm text-foreground truncate group-hover:text-primary transition-colors">
                        {project.name}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">
                        {truncate(project.topic, 65)}
                      </p>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <StatusBadge status={project.status} />
                      <span className="text-xs text-muted-foreground hidden sm:block">
                        {formatDate(project.created_at)}
                      </span>
                      <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Recent Videos Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Video className="w-4 h-4 text-emerald-500" />
                <h2 className="text-base font-semibold text-foreground">Latest Rendered Videos</h2>
              </div>
              <button
                onClick={() => navigate('/library')}
                className="text-xs text-primary hover:text-primary/80 font-medium flex items-center gap-1 group"
              >
                View Library ({videos.length})
                <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
              </button>
            </div>

            {recentVideos.length === 0 ? (
              <Card className="text-center py-12 px-6 border-dashed">
                <div className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-3">
                  <Video className="w-6 h-6 text-emerald-500 opacity-60" />
                </div>
                <h3 className="text-sm font-semibold text-foreground">No videos rendered yet</h3>
                <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                  Once your script is ready, pick PurffleShorts V3 or the Free Engine to export full MP4 videos.
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => navigate('/create')}
                  className="mt-4"
                >
                  Start Video Creation
                </Button>
              </Card>
            ) : (
              <div className="space-y-2.5">
                {recentVideos.map((video) => {
                  const videoUrl = video.cloudinary_url || video.original_url;
                  const isDownloading = downloadingId === video.id;

                  return (
                    <div
                      key={video.id}
                      className="rounded-xl border border-border bg-card p-3.5 flex items-center justify-between hover:border-emerald-500/40 transition-all shadow-xs"
                    >
                      <div className="flex items-center gap-3.5 min-w-0">
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0">
                          <Play className="w-5 h-5 fill-emerald-500/20" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-foreground truncate">
                            {video.duration_seconds ? `${video.duration_seconds}s Video` : 'Generated Video'}
                          </p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {formatDate(video.created_at)}
                            </span>
                            <span>•</span>
                            <span className="px-1.5 py-0.2 rounded bg-muted text-[10px] uppercase font-mono">
                              MP4
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 ml-3">
                        {videoUrl ? (
                          <>
                            <a
                              href={videoUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-2.5 py-1.5 rounded-lg border border-border bg-background hover:bg-accent text-xs font-medium text-foreground transition-colors flex items-center gap-1"
                            >
                              <Play className="w-3 h-3" />
                              Watch
                            </a>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={(e) => handleDownload(video, e)}
                              disabled={isDownloading}
                              className="text-xs h-7 px-2.5"
                              title="Download video file directly"
                            >
                              {isDownloading ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                <Download className="w-3 h-3" />
                              )}
                            </Button>
                          </>
                        ) : (
                          <span className="text-xs text-muted-foreground">Processing</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Feature Spotlight: PurffleShorts V3 */}
      <Card className="p-6 md:p-8 bg-gradient-to-r from-purple-950/20 via-card to-background border-purple-500/30 relative overflow-hidden">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-500/20 text-purple-400 border border-purple-500/30">
                NEW FEATURE
              </span>
              <span className="text-xs text-muted-foreground">PurffleShorts V3 Engine</span>
            </div>
            <h3 className="text-lg md:text-xl font-bold text-foreground">
              Create 9:16 Vertical Shorts with NASA Visuals & Procedural Diagrams
            </h3>
            <p className="text-xs md:text-sm text-muted-foreground">
              PurffleShorts automatically builds high-engagement short-form videos with word-by-word synced kinetic subtitles and animated data charts. Perfect for TikTok, Instagram Reels, and YouTube Shorts.
            </p>
          </div>

          <Button
            onClick={() => navigate('/create?aspect=9:16&engine=purffle')}
            className="qreate-gradient text-white shadow-sm shrink-0"
          >
            <Smartphone className="w-4 h-4 mr-2" />
            Create 9:16 Short
          </Button>
        </div>
      </Card>
    </div>
  );
}

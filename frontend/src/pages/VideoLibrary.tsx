import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Library, Plus, Search } from 'lucide-react';
import { videosApi } from '../services/api';
import type { GeneratedVideo } from '../types';
import VideoCard from '../components/VideoCard';
import { Button } from '../components/ui/Button';
import { EmptyState, PageHeader, Skeleton } from '../components/ui/States';

export default function VideoLibrary() {
  const navigate = useNavigate();
  const [videos, setVideos] = useState<GeneratedVideo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  useEffect(() => {
    videosApi.list()
      .then(setVideos)
      .catch((err) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, []);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? videos.filter((v) => (v.title || '').toLowerCase().includes(q)) : videos;
  }, [videos, query]);

  return (
    <div className="px-4 py-8 sm:px-8 max-w-6xl mx-auto">
      <PageHeader
        title="Library"
        description={loading ? 'Your rendered videos' : `${videos.length} rendered ${videos.length === 1 ? 'video' : 'videos'}`}
        actions={<Button onClick={() => navigate('/create')}><Plus className="w-4 h-4" /> Create video</Button>}
      />

      {!loading && videos.length > 0 && (
        <div className="relative max-w-sm mb-6">
          <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by title"
            aria-label="Search videos"
            className="w-full h-10 pl-9 pr-3 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="aspect-[9/16] w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </div>
      ) : error ? (
        <EmptyState icon={Library} title="Couldn't load your videos" description={error}
          action={<Button variant="outline" onClick={() => window.location.reload()}>Try again</Button>} />
      ) : videos.length === 0 ? (
        <EmptyState icon={Library} title="No videos yet" description="Videos you render will appear here."
          action={<Button onClick={() => navigate('/create')}>Create your first video</Button>} />
      ) : shown.length === 0 ? (
        <p className="text-sm text-muted-foreground">No videos match "{query}".</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {shown.map((video) => <VideoCard key={video.id} video={video} />)}
        </div>
      )}
    </div>
  );
}

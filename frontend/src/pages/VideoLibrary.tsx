import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Library } from 'lucide-react';
import { videosApi } from '../services/api';
import type { GeneratedVideo } from '../types';
import { Card } from '../components/ui/Card';
import VideoCard from '../components/VideoCard';

export default function VideoLibrary() {
  const navigate = useNavigate();
  const [videos, setVideos] = useState<GeneratedVideo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    videosApi.list()
      .then(setVideos)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-6xl mx-auto animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Video Library</h1>
        <p className="text-sm text-muted-foreground mt-1">
          All your generated videos in one place
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : videos.length === 0 ? (
        <Card className="text-center py-20">
          <Library className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-30" />
          <p className="text-muted-foreground font-medium">No videos yet</p>
          <p className="text-sm text-muted-foreground mt-1">
            Create a project and generate your first video
          </p>
          <button
            onClick={() => navigate('/create')}
            className="mt-4 text-sm text-primary hover:underline font-medium"
          >
            Create video →
          </button>
        </Card>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {videos.map((video) => (
            <VideoCard key={video.id} video={video} />
          ))}
        </div>
      )}
    </div>
  );
}

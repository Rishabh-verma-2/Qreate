import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Video, Download, ExternalLink, Loader2, Library } from 'lucide-react';
import { videosApi } from '../services/api';
import type { GeneratedVideo } from '../types';
import { Card } from '../components/ui/Card';
import { formatDate } from '../lib/utils';

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
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {videos.map((video) => {
            const url = video.cloudinary_url || video.original_url;
            return (
              <Card key={video.id} className="overflow-hidden p-0">
                {/* Video preview */}
                <div className="aspect-video bg-muted relative">
                  {url ? (
                    <video
                      src={url}
                      className="w-full h-full object-cover"
                      preload="metadata"
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Video className="w-10 h-10 text-muted-foreground opacity-30" />
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="p-4 space-y-3">
                  <div>
                    <p className="font-medium text-sm">
                      {video.duration_seconds ? `${video.duration_seconds}s video` : 'Generated video'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {formatDate(video.created_at)}
                    </p>
                  </div>

                  {url && (
                    <div className="flex items-center gap-3">
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-xs text-primary hover:text-primary/80 font-medium"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        View
                      </a>
                      <a
                        href={url}
                        download
                        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground font-medium"
                      >
                        <Download className="w-3.5 h-3.5" />
                        Download
                      </a>
                    </div>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

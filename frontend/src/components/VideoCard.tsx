import { useState } from 'react';
import { Check, Copy, Download, Loader2, Play, Video } from 'lucide-react';
import type { GeneratedVideo, Inspiration } from '../types';
import { cn, formatDate } from '../lib/utils';
import { postText, thumbnailFor } from '../lib/video';
import { downloadVideoFile } from '../lib/download';
import { useToast } from './ui/Toast';
import { StatusBadge } from './ui/Badge';

/** Thumbnail first (cheap), real <video> only once the viewer presses play. */
export function VerticalPlayer({ url, poster, className }: { url?: string; poster?: string; className?: string }) {
  const [playing, setPlaying] = useState(false);
  return (
    <div className={cn('aspect-[9/16] bg-muted relative overflow-hidden rounded-lg', className)}>
      {url && (playing || !poster) ? (
        <video src={url} poster={poster} controls playsInline autoPlay={playing} preload="metadata" className="w-full h-full object-cover bg-black" />
      ) : url && poster ? (
        <button type="button" onClick={() => setPlaying(true)} className="group w-full h-full" aria-label="Play video">
          <img src={poster} alt="" loading="lazy" className="w-full h-full object-cover" />
          <span className="absolute inset-0 flex items-center justify-center">
            <span className="w-11 h-11 rounded-full bg-black/55 text-white flex items-center justify-center group-hover:bg-black/70">
              <Play className="w-5 h-5 ml-0.5" />
            </span>
          </span>
        </button>
      ) : (
        <div className="absolute inset-0 flex items-center justify-center">
          <Video className="w-8 h-8 text-muted-foreground" />
        </div>
      )}
    </div>
  );
}

export function CopyPostButton({ video }: { video: Pick<GeneratedVideo, 'post' | 'title'> }) {
  const [copied, setCopied] = useState(false);
  const toast = useToast();
  const text = postText(video);
  if (!text) return null;
  return (
    <button
      type="button"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        toast.success('Caption and hashtags copied');
        setTimeout(() => setCopied(false), 1500);
      }}
      className="inline-flex items-center gap-1.5 h-8 px-2.5 rounded-md text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? 'Copied' : 'Copy caption'}
    </button>
  );
}

/** "Why this video": the real trend signals the script was built on. */
export function InspirationPanel({ inspiration }: { inspiration?: Inspiration }) {
  if (!inspiration || (!inspiration.searches?.length && !inspiration.news?.length && !inspiration.top_shorts?.length)) {
    return null;
  }
  return (
    <details className="text-sm text-muted-foreground">
      <summary className="cursor-pointer select-none font-medium text-foreground">
        Built on real trends{inspiration.niche ? ` · ${inspiration.niche}` : ''}
      </summary>
      <div className="mt-3 space-y-3">
        {inspiration.emotion && <p>Target emotion: <span className="text-foreground">{inspiration.emotion}</span></p>}
        {!!inspiration.searches?.length && (
          <div>
            <p className="text-xs font-medium text-foreground mb-0.5">People search</p>
            <p>{inspiration.searches.slice(0, 4).join(' · ')}</p>
          </div>
        )}
        {!!inspiration.news?.length && (
          <div>
            <p className="text-xs font-medium text-foreground mb-0.5">Facts from</p>
            <ul className="space-y-0.5">
              {inspiration.news.slice(0, 3).map((n) => (
                <li key={n.url}>
                  <a href={n.url} target="_blank" rel="noopener noreferrer" className="hover:text-foreground line-clamp-1">
                    {n.source}: {n.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
        {!!inspiration.top_shorts?.length && (
          <div>
            <p className="text-xs font-medium text-foreground mb-0.5">Top Shorts in this niche</p>
            <ul className="space-y-0.5">
              {inspiration.top_shorts.slice(0, 3).map((v) => (
                <li key={v.url}>
                  <a href={v.url} target="_blank" rel="noopener noreferrer" className="hover:text-foreground line-clamp-1">
                    {v.views.toLocaleString()} views · {v.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </details>
  );
}

export default function VideoCard({ video }: { video: GeneratedVideo }) {
  const url = video.cloudinary_url || video.original_url;
  const toast = useToast();
  const [downloading, setDownloading] = useState(false);

  async function download() {
    if (!url) return;
    setDownloading(true);
    try {
      const name = (video.title || 'qreate_video').replace(/[^a-z0-9]+/gi, '_').toLowerCase();
      await downloadVideoFile(url, `${name}.mp4`);
    } catch (err) {
      toast.error((err as Error).message || 'Download failed');
    } finally {
      setDownloading(false);
    }
  }

  return (
    <article className="rounded-lg border border-border bg-background overflow-hidden flex flex-col">
      <VerticalPlayer url={url} poster={thumbnailFor(url, video.thumbnail_url)} className="rounded-none" />
      <div className="p-3 space-y-1.5 flex-1 flex flex-col">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium line-clamp-2">{video.title || 'Untitled video'}</p>
          <StatusBadge status="completed" />
        </div>
        <p className="text-xs text-muted-foreground">
          {formatDate(video.created_at)}{video.duration_seconds ? ` · ${Math.round(video.duration_seconds)}s` : ''}
        </p>
        <div className="flex items-center gap-1 pt-1 mt-auto -ml-2.5">
          {url && (
            <button
              type="button"
              onClick={download}
              disabled={downloading}
              className="inline-flex items-center gap-1.5 h-8 px-2.5 rounded-md text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent disabled:opacity-50"
            >
              {downloading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              Download
            </button>
          )}
          <CopyPostButton video={video} />
        </div>
      </div>
    </article>
  );
}

import { useState } from 'react';
import { Check, Copy, Download, ExternalLink, Video } from 'lucide-react';
import type { GeneratedVideo, Inspiration } from '../types';
import { cn, formatDate } from '../lib/utils';
import { downloadUrl, postText } from '../lib/video';

export function VerticalPlayer({ url, poster, className }: { url?: string; poster?: string; className?: string }) {
  return (
    <div className={cn('aspect-[9/16] bg-muted relative overflow-hidden rounded-lg', className)}>
      {url ? (
        <video src={url} poster={poster} controls playsInline preload="metadata" className="w-full h-full object-cover" />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center">
          <Video className="w-10 h-10 text-muted-foreground opacity-30" />
        </div>
      )}
    </div>
  );
}

export function CopyPostButton({ video }: { video: Pick<GeneratedVideo, 'post' | 'title'> }) {
  const [copied, setCopied] = useState(false);
  const text = postText(video);
  if (!text) return null;
  return (
    <button
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground font-medium"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
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
    <details className="text-xs text-muted-foreground group">
      <summary className="cursor-pointer select-none font-medium text-primary/90 hover:text-primary">
        Inspired by real trends{inspiration.niche ? ` · ${inspiration.niche}` : ''}
      </summary>
      <div className="mt-2 space-y-2">
        {inspiration.emotion && <p>Target emotion: <span className="text-foreground">{inspiration.emotion}</span></p>}
        {!!inspiration.searches?.length && (
          <div>
            <p className="font-medium text-foreground/80">People search</p>
            <p>{inspiration.searches.slice(0, 4).join(' · ')}</p>
          </div>
        )}
        {!!inspiration.news?.length && (
          <div>
            <p className="font-medium text-foreground/80">Facts from</p>
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
            <p className="font-medium text-foreground/80">Top Shorts in this niche</p>
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
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <VerticalPlayer url={url} poster={video.thumbnail_url} className="rounded-none" />
      <div className="p-4 space-y-2">
        <p className="font-medium text-sm line-clamp-2">{video.title || 'Generated video'}</p>
        <p className="text-xs text-muted-foreground">
          {video.duration_seconds ? `${Math.round(video.duration_seconds)}s · ` : ''}1080×1920 · {formatDate(video.created_at)}
        </p>
        {video.post?.caption && (
          <p className="text-xs text-muted-foreground line-clamp-3">{video.post.caption}</p>
        )}
        <InspirationPanel inspiration={video.inspiration} />
        {url && (
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <a href={url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-xs text-primary hover:text-primary/80 font-medium">
              <ExternalLink className="w-3.5 h-3.5" /> View
            </a>
            <a href={downloadUrl(url)} className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground font-medium">
              <Download className="w-3.5 h-3.5" /> Download
            </a>
            <CopyPostButton video={video} />
          </div>
        )}
      </div>
    </div>
  );
}

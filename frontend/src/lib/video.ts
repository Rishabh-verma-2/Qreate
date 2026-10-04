import type { GeneratedVideo } from '../types';

/** Cloudinary delivery URL that forces a file download instead of inline playback. */
export function downloadUrl(url: string) {
  return url.includes('/upload/') ? url.replace('/upload/', '/upload/fl_attachment/') : url;
}

export function postText(video: Pick<GeneratedVideo, 'post' | 'title'>) {
  const caption = video.post?.caption || video.title || '';
  const tags = (video.post?.hashtags || []).map((h) => `#${h}`).join(' ');
  return [caption, tags].filter(Boolean).join('\n\n');
}

/** Poster image for a Cloudinary video URL (frame at 1s, 360px wide) when none was stored. */
export function thumbnailFor(url?: string, stored?: string): string | undefined {
  if (stored) return stored;
  if (!url || !url.includes('res.cloudinary.com') || !url.includes('/upload/')) return undefined;
  return url.replace('/upload/', '/upload/so_1.0,w_360/').replace(/\.(mp4|mov|webm)(\?.*)?$/i, '.jpg');
}

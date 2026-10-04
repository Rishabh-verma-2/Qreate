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

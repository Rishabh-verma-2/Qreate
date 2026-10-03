import { useRef, useState } from 'react';
import { ImagePlus, Loader2, Video, X } from 'lucide-react';
import { uploadsApi } from '../services/api';
import type { UserMedia } from '../types';

interface MediaUploaderProps {
  value: UserMedia[];
  onChange: (media: UserMedia[]) => void;
}

/** Creator's own photos/clips. When present they replace stock footage entirely. */
export default function MediaUploader({ value, onChange }: MediaUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError('');
    try {
      const uploaded = await uploadsApi.upload(Array.from(files).slice(0, 15 - value.length));
      onChange([...value, ...uploaded]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium">Your photos & videos (optional)</label>
      <p className="text-xs text-muted-foreground">
        For personal stories — weddings, trips, launches. Your media is used for every scene instead of stock footage, in upload order.
      </p>
      <div className="flex flex-wrap gap-2">
        {value.map((m, i) => (
          <div key={m.url} className="relative w-16 h-28 rounded-md overflow-hidden border border-border bg-muted">
            {m.kind === 'video' ? (
              <div className="w-full h-full flex items-center justify-center"><Video className="w-5 h-5 text-muted-foreground" /></div>
            ) : (
              <img src={m.url.replace('/upload/', '/upload/w_160/')} alt={m.name || ''} className="w-full h-full object-cover" />
            )}
            <button
              type="button"
              onClick={() => onChange(value.filter((_, j) => j !== i))}
              className="absolute top-0.5 right-0.5 w-5 h-5 rounded-full bg-black/70 flex items-center justify-center"
              aria-label="Remove"
            >
              <X className="w-3 h-3 text-white" />
            </button>
          </div>
        ))}
        {value.length < 15 && (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="w-16 h-28 rounded-md border border-dashed border-border flex flex-col items-center justify-center gap-1 text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors"
          >
            {uploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <ImagePlus className="w-5 h-5" />}
            <span className="text-[10px]">{uploading ? 'Uploading' : 'Add'}</span>
          </button>
        )}
      </div>
      <input ref={inputRef} type="file" accept="image/*,video/*" multiple hidden onChange={(e) => handleFiles(e.target.files)} />
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

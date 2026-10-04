import { cn } from '../../lib/utils';

interface PhonePreviewProps {
  aspect: '9:16' | '16:9';
  hook?: string;
  highlight: string;      // caption highlight colour (theme)
  captionStyle: string;   // bold | clean | boxed
}

/** A static mock of the first frame: hook banner + caption in the chosen style. */
export default function PhonePreview({ aspect, hook, highlight, captionStyle }: PhonePreviewProps) {
  const vertical = aspect === '9:16';
  const word = captionStyle === 'clean' ? 'this' : 'THIS';
  return (
    <div className={cn('mx-auto', vertical ? 'w-44' : 'w-full max-w-xs')}>
      <div className={cn('rounded-[20px] border-[6px] border-foreground bg-foreground', !vertical && 'rounded-xl border-4')}>
        <div
          className={cn('relative overflow-hidden rounded-[14px]', vertical ? 'aspect-[9/16]' : 'aspect-video rounded-lg')}
          style={{ background: '#27272A' }}
        >
          {hook && (
            <div className="absolute top-[12%] left-3 right-3 flex justify-center">
              <span
                className="px-2 py-1 text-[10px] font-bold text-center leading-tight line-clamp-2"
                style={{ background: highlight, color: isLight(highlight) ? '#000' : '#fff' }}
              >
                {hook.toUpperCase()}
              </span>
            </div>
          )}
          <p className="absolute inset-x-0 top-[42%] text-center text-[10px] text-white/40">Your footage here</p>
          <div className="absolute top-[64%] left-2 right-2 flex justify-center">
            <span
              className={cn(
                'text-white text-center leading-tight',
                captionStyle === 'bold' && 'text-sm font-extrabold [text-shadow:_0_1px_0_#000,_0_0_4px_#000]',
                captionStyle === 'clean' && 'text-xs font-semibold [text-shadow:_0_1px_2px_#000]',
                captionStyle === 'boxed' && 'text-xs font-bold bg-black/60 px-1.5 py-0.5'
              )}
            >
              {captionStyle === 'clean' ? 'Watch ' : 'WATCH '}
              <span style={{ color: highlight }}>{word}</span>
            </span>
          </div>
        </div>
      </div>
      <p className="text-center text-xs text-muted-foreground mt-2">{vertical ? '9:16 · 1080×1920' : '16:9 · widescreen'}</p>
    </div>
  );
}

function isLight(hex: string) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex);
  if (!m) return false;
  const n = parseInt(m[1], 16);
  const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  return 0.299 * r + 0.587 * g + 0.114 * b > 160;
}

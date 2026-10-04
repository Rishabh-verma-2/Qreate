"""Video composition with FFmpeg: 1080x1920 scenes → crossfaded edit → captions → mixed audio."""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import List, Optional

from PIL import Image, ImageEnhance, ImageFilter

from app.core.config import get_settings
from app.services.media.ffmpeg import FFmpegError, probe_duration, run_ffmpeg
from app.services.media.stock import MediaAsset, create_gradient_background

logger = logging.getLogger(__name__)

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "fonts")
# "Studio mic" chain: remove rumble, add chest warmth + presence, gentle compression.
# Makes TTS sit in the mix like a recorded voiceover instead of a dry synthetic read.
VOICE_CHAIN = (
    "highpass=f=75,equalizer=f=170:t=q:w=1.1:g=2,equalizer=f=3200:t=q:w=1.3:g=2.5,"
    "equalizer=f=7500:t=q:w=2:g=-1.5,acompressor=threshold=0.09:ratio=3:attack=6:release=120:makeup=1.8"
)
# Gentle "graded" look: a touch of contrast and saturation (no vignette — phone footage has none).
GRADE = "eq=contrast=1.04:saturation=1.07:brightness=0.01"


@dataclass
class SceneRender:
    path: str
    duration: float  # on-screen duration excluding the transition overlap


def _esc(path: str) -> str:
    """Escape a path for use inside an FFmpeg filter argument."""
    return path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def _x264_args(crf: Optional[int] = None) -> List[str]:
    s = get_settings()
    args = ["-c:v", "libx264", "-preset", s.X264_PRESET, "-crf", str(crf or s.X264_CRF), "-pix_fmt", "yuv420p"]
    if s.FFMPEG_THREADS:
        args += ["-threads", str(s.FFMPEG_THREADS)]
    return args


def _prepare_still(src: str, dest: str, scale: float = 1.5) -> str:
    """Build an oversized 9:16 still for the camera move.

    Near-portrait photos are cover-cropped. Wide photos are placed full-width over a
    blurred, darkened copy of themselves (the native "blur fill" look) instead of
    being cropped to a sliver or stretched.
    """
    s = get_settings()
    W, H = int(s.VIDEO_WIDTH * scale), int(s.VIDEO_HEIGHT * scale)
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        target = W / H
        crop_factor = (w / h) / target

        def cover(img):
            iw, ih = img.size
            r = max(W / iw, H / ih)
            img = img.resize((max(W, int(iw * r + 0.5)), max(H, int(ih * r + 0.5))), Image.Resampling.LANCZOS)
            left, top = (img.width - W) // 2, (img.height - H) // 2
            return img.crop((left, top, left + W, top + H))

        if crop_factor <= 1.45:
            out = cover(im)
        else:
            bg = cover(im).filter(ImageFilter.GaussianBlur(40))
            bg = ImageEnhance.Brightness(bg).enhance(0.55)
            fg_w = W
            fg_h = int(h * fg_w / w)
            fg = im.resize((fg_w, fg_h), Image.Resampling.LANCZOS)
            bg.paste(fg, (0, (H - fg_h) // 2))
            out = bg
        out.save(dest, "JPEG", quality=94)
    return dest


def _is_latin(text: str) -> bool:
    return all(ord(c) < 0x250 for c in text)


def make_text_card(text: str, dest: str, background: Optional[str] = None, seed: int = 0) -> str:
    """Bold kinetic-typography card (the "fact card" style creators use between shots).

    Background is a heavily blurred, darkened version of a neighbouring real shot when
    available, otherwise a soft gradient. Non-Latin text is skipped (Pillow here has no
    complex-script shaping); the burned-in captions still carry the words.
    """
    from PIL import ImageDraw, ImageFont

    s = get_settings()
    W, H = s.VIDEO_WIDTH, s.VIDEO_HEIGHT
    if background and os.path.exists(background):
        with Image.open(background) as im:
            im = im.convert("RGB")
            r = max(W / im.width, H / im.height)
            im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.Resampling.LANCZOS)
            left, top = (im.width - W) // 2, (im.height - H) // 2
            bg = im.crop((left, top, left + W, top + H)).filter(ImageFilter.GaussianBlur(45))
            bg = ImageEnhance.Brightness(bg).enhance(0.45)
    else:
        bg = Image.open(create_gradient_background(dest, seed=seed)).convert("RGB")

    text = (text or "").strip().upper()
    if text and _is_latin(text):
        draw = ImageDraw.Draw(bg)
        font_path = os.path.join(FONTS_DIR, "Poppins-ExtraBold.ttf")
        size = 150
        while size > 70:
            font = ImageFont.truetype(font_path, size)
            words, lines, cur = text.split(), [], ""
            for w in words:
                trial = f"{cur} {w}".strip()
                if draw.textlength(trial, font=font) <= W * 0.82:
                    cur = trial
                else:
                    if cur:
                        lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            if len(lines) <= 3 and all(draw.textlength(l, font=font) <= W * 0.86 for l in lines):
                break
            size -= 10
        line_h = int(size * 1.15)
        y = int(H * 0.40) - (line_h * len(lines)) // 2
        # Accent bar above the text
        draw.rounded_rectangle([(W // 2 - 60, y - 50), (W // 2 + 60, y - 38)], radius=6, fill=(255, 229, 0))
        for line in lines:
            tw = draw.textlength(line, font=font)
            draw.text(((W - tw) / 2, y), line, font=font, fill=(255, 255, 255),
                      stroke_width=4, stroke_fill=(0, 0, 0))
            y += line_h
    bg.save(dest, "JPEG", quality=93)
    return dest


def _ken_burns(index: int, frames: int, W: int, H: int, fps: int) -> str:
    n = max(frames - 1, 1)
    center_x, center_y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    motion = index % 4
    if motion == 0:    # slow push-in
        z, x, y = f"1+0.10*on/{n}", center_x, center_y
    elif motion == 1:  # pan left → right
        z, x, y = "1.12", f"(iw-iw/zoom)*on/{n}", center_y
    elif motion == 2:  # slow pull-out
        z, x, y = f"1.10-0.10*on/{n}", center_x, center_y
    else:              # drift upward
        z, x, y = "1.12", center_x, f"(ih-ih/zoom)*(1-on/{n})"
    return f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={fps}"


PUNCH_FRAMES = 6      # quick zoom "snap" at the start of every shot (~0.2s)


async def render_scene(asset: MediaAsset, duration: float, out_path: str, index: int, work_dir: str,
                       variant: int = 0) -> str:
    """Render one silent 1080x1920 shot of exactly `duration` seconds.

    `variant` > 0 means the same source is reused for another shot: take a later part
    of the clip and a tighter framing (a classic jump cut) or a different camera move.
    """
    s = get_settings()
    W, H, fps = s.VIDEO_WIDTH, s.VIDEO_HEIGHT, s.VIDEO_FPS
    dur = f"{duration:.3f}"
    frames = max(int(round(duration * fps)), 1)

    if asset.kind == "video":
        clip_len = asset.duration or await probe_duration(asset.path)
        base = min(1.0, max(clip_len - duration, 0) / 3) if clip_len else 0.0  # skip shaky first frames
        offset = base + variant * (duration + 0.4)
        if clip_len and offset + duration > clip_len:
            offset = max(clip_len - duration - 0.05, 0.0) if variant else base
        loop = ["-stream_loop", "-1"] if clip_len and clip_len < duration + offset + 0.2 else []
        zoom = 1.0 + 0.12 * (variant % 2)  # alternate wide / punched-in framing
        punch = (f"zoompan=z='if(lt(on,{PUNCH_FRAMES}),{zoom}+0.06*(1-on/{PUNCH_FRAMES}),{zoom})':"
                 f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={fps}")
        vf = (
            f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
            f"fps={fps},{punch},setsar=1,{GRADE},format=yuv420p"
        )
        args = [*loop, "-ss", f"{offset:.2f}", "-i", asset.path, "-t", dur, "-vf", vf,
                "-frames:v", str(frames), "-an", *_x264_args(18), out_path]
    else:
        still = _prepare_still(asset.path, os.path.join(work_dir, f"still_{index}.jpg"))
        vf = f"{_ken_burns(index + variant, frames, W, H, fps)},setsar=1,{GRADE},format=yuv420p"
        args = ["-loop", "1", "-framerate", str(fps), "-i", still, "-vf", vf, "-frames:v", str(frames), "-an", *_x264_args(18), out_path]

    try:
        await run_ffmpeg(args, timeout=240)
    except FFmpegError as e:
        logger.warning(f"Shot {index + 1} render failed ({asset.source}): {e}; using fallback background")
        fallback = create_gradient_background(os.path.join(work_dir, f"fallback_{index}.jpg"), seed=index)
        vf = f"{_ken_burns(index, frames, W, H, fps)},setsar=1,format=yuv420p"
        await run_ffmpeg(["-loop", "1", "-framerate", str(fps), "-i", fallback, "-vf", vf,
                          "-frames:v", str(frames), "-an", *_x264_args(20), out_path], timeout=240)
    return out_path


SFX_DIR = os.path.join(os.path.dirname(FONTS_DIR), "sfx")
SFX_VOLUME = 0.30


async def compose_final(
    shots: List[SceneRender],
    voice_path: str,
    captions_path: str,
    out_path: str,
    music_path: Optional[str] = None,
    sfx_times: Optional[List[float]] = None,
) -> float:
    """Hard-cut the shots together, burn captions, mix voice + ducked music + whooshes."""
    s = get_settings()
    total = sum(sc.duration for sc in shots)
    inputs: List[str] = []
    for sc in shots:
        inputs += ["-i", sc.path]
    voice_idx = len(shots)
    inputs += ["-i", voice_path]
    next_idx = voice_idx + 1
    music_idx = None
    if music_path:
        music_idx = next_idx
        inputs += ["-stream_loop", "-1", "-i", music_path]
        next_idx += 1
    sfx_files = sorted(f for f in os.listdir(SFX_DIR) if f.endswith(".mp3")) if os.path.isdir(SFX_DIR) else []
    sfx_times = [t for t in (sfx_times or []) if 0.2 < t < total - 0.3] if sfx_files else []
    sfx_idx = []
    for f in sfx_files:
        sfx_idx.append(next_idx)
        inputs += ["-i", os.path.join(SFX_DIR, f)]
        next_idx += 1

    # Video: hard cuts (how real reels are edited), captions, short fade-out at the very end
    parts = ["".join(f"[{i}:v]" for i in range(len(shots))) + f"concat=n={len(shots)}:v=1:a=0[cat]"]
    parts.append(
        f"[cat]ass='{_esc(captions_path)}':fontsdir='{_esc(FONTS_DIR)}',"
        f"fade=t=out:st={max(total - 0.35, 0):.3f}:d=0.35,format=yuv420p[vout]"
    )

    # Audio: processed voice, ducked music, whooshes slightly ahead of each scene change
    mix = []
    voice_in = f"[{voice_idx}:a]aresample=48000,{VOICE_CHAIN},apad,atrim=0:{total:.3f},aformat=channel_layouts=stereo"
    if music_idx is not None:
        parts.append(f"{voice_in},asplit=2[voice][sc]")
        parts.append(
            f"[{music_idx}:a]aresample=48000,aformat=channel_layouts=stereo,volume={s.MUSIC_VOLUME},"
            f"atrim=0:{total:.3f},afade=t=in:d=0.4,afade=t=out:st={max(total - 1.2, 0):.3f}:d=1.2[music]"
        )
        parts.append("[music][sc]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[ducked]")
        mix += ["[voice]", "[ducked]"]
    else:
        parts.append(f"{voice_in}[voice]")
        mix.append("[voice]")
    if sfx_times:
        per_file: dict = {}
        for k, t in enumerate(sfx_times):
            per_file.setdefault(k % len(sfx_idx), []).append(t)
        labels = []
        for fi, times in per_file.items():
            src = sfx_idx[fi]
            split = "".join(f"[s{fi}_{j}]" for j in range(len(times)))
            parts.append(f"[{src}:a]aresample=48000,aformat=channel_layouts=stereo,volume={SFX_VOLUME},asplit={len(times)}{split}")
            for j, t in enumerate(times):
                ms = int(max(t - 0.18, 0) * 1000)
                parts.append(f"[s{fi}_{j}]adelay={ms}|{ms}[d{fi}_{j}]")
                labels.append(f"[d{fi}_{j}]")
        # No apad/atrim here: amix→apad→atrim never terminates in FFmpeg. The final
        # amix (duration=first, i.e. the voice) already fixes the length.
        parts.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0[sfx]")
        mix.append("[sfx]")
    if len(mix) > 1:
        parts.append("".join(mix) + f"amix=inputs={len(mix)}:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    else:
        parts.append("[voice]loudnorm=I=-14:TP=-1.5:LRA=11[aout]")

    args = [
        *inputs,
        "-filter_complex", ";".join(parts),
        "-map", "[vout]", "-map", "[aout]",
        *_x264_args(), "-profile:v", "high", "-r", str(s.VIDEO_FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", f"{total:.3f}", "-movflags", "+faststart",
        out_path,
    ]
    await run_ffmpeg(args, timeout=900)
    return total


async def render_scenes_parallel(jobs, limit: int) -> List[str]:
    """Run render_scene coroutines with bounded parallelism (CPU-bound FFmpeg)."""
    sem = asyncio.Semaphore(max(limit, 1))

    async def guarded(coro):
        async with sem:
            return await coro

    return await asyncio.gather(*(guarded(j) for j in jobs))

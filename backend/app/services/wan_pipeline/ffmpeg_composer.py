"""FFmpeg composition for the Wan2.1 pipeline.

Concatenates scene clips, muxes per-scene TTS audio, and adds transitions.
Reuses the low-level FFmpeg utilities from services/media/ffmpeg.py
and the x264 encoding parameters from services/media/composer.py.

Key differences from the existing compose_final():
- Each scene has its own audio file (not one continuous TTS take)
- Transitions between scenes (xfade + acrossfade)
- No ASS captions (handled separately if needed)
- Works for any aspect ratio (not just 9:16)
"""

import asyncio
import logging
import os
from typing import List, Optional

from app.core.config import get_settings
from app.services.media.composer import _x264_args
from app.services.media.ffmpeg import run_ffmpeg, probe_duration

logger = logging.getLogger(__name__)

# Transition duration in seconds (overlap between clips)
TRANSITION_DURATION = 0.3


async def wan_compose(
    scene_clips: List[str],
    scene_audio: List[str],
    scene_durations: List[float],
    output_path: str,
    transitions: Optional[List[str]] = None,
    music_mood: str = "none",
    work_dir: str = "",
) -> float:
    """Compose scene clips + audio into a final MP4.

    Args:
        scene_clips: List of paths to per-scene silent MP4 clips.
        scene_audio: List of paths to per-scene TTS audio (or "" if none).
        scene_durations: Actual durations of each clip in seconds.
        output_path: Where to write the final output MP4.
        transitions: List of transition types ("cut", "fade", "dissolve", "wipe").
        music_mood: Background music mood (passed to fetch_music if "none" not set).
        work_dir: Temp directory for intermediate files.

    Returns:
        Total duration of the final video in seconds.
    """
    if not scene_clips:
        raise ValueError("No scene clips to compose")

    n = len(scene_clips)
    transitions = transitions or ["cut"] * n
    s = get_settings()

    # ── Step 1: Mux each scene clip with its audio ────────────────────────────
    muxed_clips = []
    for i, (clip, audio) in enumerate(zip(scene_clips, scene_audio)):
        muxed = os.path.join(work_dir, f"muxed_{i:03d}.mp4")
        if audio and os.path.exists(audio):
            # Mux video + audio; trim to clip duration
            dur = scene_durations[i]
            await run_ffmpeg([
                "-i", clip,
                "-i", audio,
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "128k",
                "-t", f"{dur:.3f}",
                "-map", "0:v:0", "-map", "1:a:0",
                "-shortest",
                "-movflags", "+faststart",
                muxed,
            ], timeout=120)
        else:
            # No audio — generate silent audio
            dur = scene_durations[i]
            await run_ffmpeg([
                "-i", clip,
                "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "128k",
                "-t", f"{dur:.3f}",
                "-map", "0:v:0", "-map", "1:a:0",
                "-shortest",
                "-movflags", "+faststart",
                muxed,
            ], timeout=120)
        muxed_clips.append(muxed)

    # ── Step 2: Concatenate (with or without transitions) ─────────────────────
    use_transitions = any(t in ("fade", "dissolve") for t in transitions)

    if n == 1:
        # Single scene — just copy it
        import shutil
        shutil.copy2(muxed_clips[0], output_path)
    elif not use_transitions:
        # Fast path: FFmpeg concat demuxer (hard cuts, no re-encoding of video)
        concat_list = os.path.join(work_dir, "concat.txt")
        with open(concat_list, "w") as f:
            for clip in muxed_clips:
                f.write(f"file '{clip.replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n")
        await run_ffmpeg([
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            "-movflags", "+faststart",
            output_path,
        ], timeout=600)
    else:
        # Transition path: re-encode with xfade filter
        await _compose_with_transitions(
            muxed_clips, scene_durations, transitions, output_path, work_dir
        )

    # Verify output
    total = await probe_duration(output_path)
    if total <= 0:
        total = sum(scene_durations)

    logger.info(f"wan_compose: final video {total:.1f}s at {output_path}")
    return total


async def _compose_with_transitions(
    clips: List[str],
    durations: List[float],
    transitions: List[str],
    output_path: str,
    work_dir: str,
) -> None:
    """Compose clips with xfade transitions via FFmpeg filter graph."""
    n = len(clips)
    td = TRANSITION_DURATION

    # Build filter graph
    inputs = []
    for clip in clips:
        inputs += ["-i", clip]

    filter_parts = []
    video_labels = [f"[{i}:v]" for i in range(n)]
    audio_labels = [f"[{i}:a]" for i in range(n)]

    # Chain xfade filters
    current_video = video_labels[0]
    current_audio = audio_labels[0]
    offset = durations[0] - td

    for i in range(1, n):
        v_out = f"[v{i}]"
        a_out = f"[a{i}]"
        trans = transitions[i] if i < len(transitions) else "cut"
        xfade_type = "fade" if trans in ("fade", "dissolve") else "fade"

        filter_parts.append(
            f"{current_video}{video_labels[i]}xfade=transition={xfade_type}:duration={td}:offset={offset:.3f}{v_out}"
        )
        filter_parts.append(
            f"{current_audio}{audio_labels[i]}acrossfade=d={td}{a_out}"
        )
        current_video = v_out
        current_audio = a_out
        offset += durations[i] - td

    filter_parts.append(f"{current_video}format=yuv420p[vout]")
    filter_parts.append(f"{current_audio}loudnorm=I=-14:TP=-1.5:LRA=11[aout]")

    s = get_settings()
    args = [
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "[vout]", "-map", "[aout]",
        *_x264_args(), "-r", str(s.VIDEO_FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        output_path,
    ]
    await run_ffmpeg(args, timeout=900)

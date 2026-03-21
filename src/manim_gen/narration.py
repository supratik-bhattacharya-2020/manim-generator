"""Local TTS narration using Windows SAPI5 (no external API)."""

from __future__ import annotations

import os
import struct
import tempfile
import wave
from pathlib import Path

import win32com.client


def _generate_clip(text: str, out_path: str, rate: int = 1) -> float:
    """Generate a WAV clip using SAPI5. Returns duration in seconds."""
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    stream = win32com.client.Dispatch("SAPI.SpFileStream")

    stream.Open(out_path, 3)  # SSFMCreateForWrite
    speaker.AudioOutputStream = stream
    speaker.Rate = rate  # -10 (slow) to 10 (fast), 0 = default
    speaker.Speak(text)
    stream.Close()

    with wave.open(out_path, "rb") as w:
        return w.getnframes() / w.getframerate()


def _generate_silence(duration: float, out_path: str, sample_rate: int = 22050) -> None:
    """Generate a silent WAV file of given duration."""
    n_frames = int(sample_rate * duration)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n_frames)


def _concat_wavs(wav_files: list[str], out_path: str) -> float:
    """Concatenate WAV files into one. Returns total duration."""
    if not wav_files:
        return 0.0

    with wave.open(wav_files[0], "rb") as first:
        params = first.getparams()

    with wave.open(out_path, "wb") as out:
        out.setparams(params)
        for f in wav_files:
            with wave.open(f, "rb") as w:
                out.writeframes(w.readframes(w.getnframes()))

    with wave.open(out_path, "rb") as w:
        return w.getnframes() / w.getframerate()


def generate_narration(
    steps: list[dict],
    output_dir: str,
    rate: int = 1,
) -> tuple[str, list[float]]:
    """Generate narration audio for animation steps.

    Args:
        steps: List of dicts with 'narration' (text) and 'duration' (target seconds).
        output_dir: Directory to write audio files.
        rate: SAPI5 speech rate (-10 to 10).

    Returns:
        (path_to_combined_audio, list_of_actual_clip_durations)
    """
    os.makedirs(output_dir, exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix="manim_narr_")

    clips = []
    durations = []

    for i, step in enumerate(steps):
        text = step.get("narration", "")
        target_dur = step.get("duration", 2.0)

        if not text.strip():
            # Silent step
            silence_path = os.path.join(tmp_dir, f"silence_{i}.wav")
            _generate_silence(target_dur, silence_path)
            clips.append(silence_path)
            durations.append(target_dur)
            continue

        # Generate speech clip
        clip_path = os.path.join(tmp_dir, f"clip_{i}.wav")
        speech_dur = _generate_clip(text, clip_path, rate=rate)

        # Add padding silence if speech is shorter than target
        if speech_dur < target_dur:
            pad_path = os.path.join(tmp_dir, f"pad_{i}.wav")
            _generate_silence(target_dur - speech_dur, pad_path)
            clips.append(clip_path)
            clips.append(pad_path)
            durations.append(target_dur)
        else:
            clips.append(clip_path)
            durations.append(speech_dur)

    # Concatenate all clips
    combined_path = os.path.join(output_dir, "narration.wav")
    total_dur = _concat_wavs(clips, combined_path)

    # Cleanup temp files
    for f in clips:
        try:
            os.remove(f)
        except OSError:
            pass
    try:
        os.rmdir(tmp_dir)
    except OSError:
        pass

    return combined_path, durations


def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> str:
    """Merge audio and video using ffmpeg (via imageio-ffmpeg)."""
    import subprocess

    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        ffmpeg = "ffmpeg"

    cmd = [
        ffmpeg,
        "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg merge failed: {result.stderr[:500]}")

    return output_path

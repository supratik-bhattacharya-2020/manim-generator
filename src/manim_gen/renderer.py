"""Render Manim code to video."""

from __future__ import annotations

import platform
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

_QUALITY_FLAGS = {
    "low": "l",
    "medium": "m",
    "high": "h",
}

_RENDER_TIMEOUT = 120  # seconds


def render_scene(
    code: str,
    *,
    quality: str = "medium",
    output: str | None = None,
) -> Path:
    """Write code to a temp file, invoke manim, and return the output video path."""
    quality_flag = _QUALITY_FLAGS.get(quality, "m")

    # Write code to a temp file (UTF-8 for Unicode math symbols)
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", prefix="manim_gen_", delete=False, encoding="utf-8",
    )
    tmp.write(code)
    tmp.close()
    tmp_path = Path(tmp.name)

    console.print(f"  [dim]Temp file: {tmp_path}[/dim]")
    console.print(f"  [dim]Rendering at {quality} quality...[/dim]")

    cmd = [
        "manim", "render",
        f"-q{quality_flag}",
        "--disable_caching",
        str(tmp_path),
        "GeneratedScene",
    ]

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Rendering..."),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("render", total=None)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_RENDER_TIMEOUT,
            )

        if result.returncode != 0:
            console.print("[red]Manim render failed:[/red]")
            console.print(result.stderr)
            raise RuntimeError(f"manim exited with code {result.returncode}")

        # Find the output video
        video_path = _find_output_video(tmp_path, quality_flag)

        if output:
            dest = Path(output)
            dest.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.move(str(video_path), str(dest))
            video_path = dest

        console.print(f"  [bold green]Video saved:[/bold green] {video_path}")
        return video_path

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Render timed out after {_RENDER_TIMEOUT}s")
    finally:
        # Clean up temp file
        tmp_path.unlink(missing_ok=True)


def open_video(path: Path) -> None:
    """Open the video with the system default player."""
    system = platform.system()
    try:
        if system == "Windows":
            import os
            os.startfile(str(path))  # noqa: S606
        elif system == "Darwin":
            subprocess.Popen(["open", str(path)])  # noqa: S603, S607
        else:
            subprocess.Popen(["xdg-open", str(path)])  # noqa: S603, S607
    except OSError as exc:
        console.print(f"  [red]Could not open video: {exc}[/red]")


def _find_output_video(tmp_path: Path, quality_flag: str) -> Path:
    """Locate the video Manim produced in its media directory."""
    # Manim puts output in ./media/videos/<filename_without_ext>/<quality>/GeneratedScene.mp4
    quality_dirs = {
        "l": "480p15",
        "m": "720p30",
        "h": "1080p60",
    }
    quality_dir = quality_dirs.get(quality_flag, "720p30")
    stem = tmp_path.stem

    media_root = Path("media") / "videos" / stem / quality_dir
    mp4 = media_root / "GeneratedScene.mp4"

    if mp4.exists():
        return mp4

    # Fallback: search for any mp4 in the media tree
    for candidate in Path("media").rglob("GeneratedScene.mp4"):
        return candidate

    raise FileNotFoundError(
        f"Could not find rendered video. Expected at {mp4}. "
        "Check manim output above for details."
    )

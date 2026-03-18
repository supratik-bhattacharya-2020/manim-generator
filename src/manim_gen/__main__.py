"""CLI entry point: python -m manim_gen"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys

from rich.console import Console

console = Console()


def _latex_available() -> bool:
    """Check if a LaTeX compiler is available on PATH."""
    return shutil.which("latex") is not None or shutil.which("xelatex") is not None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="manim-gen",
        description="Generate Manim math animations from natural language descriptions.",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help='What to animate (e.g., "Show the Pythagorean theorem")',
    )
    parser.add_argument(
        "-q", "--quality",
        choices=["low", "medium", "high"],
        default="medium",
        help="Render quality (default: medium)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: auto in ./output/)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        dest="open_video",
        help="Open video after rendering",
    )
    parser.add_argument(
        "--model",
        help="Override LLM model",
    )
    parser.add_argument(
        "--base-url",
        help="Override API base URL",
    )
    parser.add_argument(
        "--no-latex",
        action="store_true",
        help="Force no-LaTeX mode (use Text() instead of MathTex/Tex). Auto-detected if omitted.",
    )
    return parser.parse_args()


async def run(args: argparse.Namespace) -> int:
    # Lazy imports to keep CLI startup fast
    from .safety import check_input
    from .planner import generate_plan
    from .cli import interactive_edit
    from .codegen import generate_code
    from .renderer import render_scene, open_video

    # Apply overrides via env vars
    import os
    if args.base_url:
        os.environ["MANIM_GEN_BASE_URL"] = args.base_url
    if args.model:
        os.environ["MANIM_GEN_MODEL"] = args.model

    # LaTeX detection
    if args.no_latex:
        latex = False
    else:
        latex = _latex_available()

    if not latex:
        console.print("[yellow]LaTeX not found — using Text() mode (no MathTex/Tex).[/yellow]")
    else:
        console.print("[dim]LaTeX detected.[/dim]")

    # Get prompt
    prompt = args.prompt
    if not prompt:
        from rich.prompt import Prompt
        prompt = Prompt.ask("[bold cyan]What would you like to animate?[/bold cyan]")

    if not prompt or not prompt.strip():
        console.print("[red]No prompt provided.[/red]")
        return 1

    # Safety check input
    error = check_input(prompt)
    if error:
        console.print(f"[red]Input rejected:[/red] {error}")
        return 1

    # Generate plan
    console.print()
    console.print("[bold blue]Planning animation...[/bold blue]")
    try:
        plan = await generate_plan(prompt, model=args.model, latex_available=latex)
    except Exception as exc:
        console.print(f"[red]Planning failed:[/red] {exc}")
        return 1

    # Override quality from CLI if specified
    if args.quality:
        plan.config.quality = args.quality  # type: ignore[assignment]

    # Interactive TUI
    plan = interactive_edit(plan)
    if plan is None:
        console.print("[yellow]Cancelled.[/yellow]")
        return 0

    # Generate code
    console.print("[bold blue]Generating Manim code...[/bold blue]")
    try:
        code = await generate_code(plan, model=args.model, latex_available=latex)
    except RuntimeError as exc:
        console.print(f"[red]Code generation failed:[/red] {exc}")
        return 1

    # Render
    console.print("[bold blue]Rendering video...[/bold blue]")
    try:
        video_path = render_scene(code, quality=plan.config.quality, output=args.output)
    except (RuntimeError, FileNotFoundError) as exc:
        console.print(f"[red]Render failed:[/red] {exc}")
        return 1

    if args.open_video:
        open_video(video_path)

    console.print()
    console.print("[bold green]Done![/bold green]")
    return 0


def main() -> None:
    args = parse_args()
    sys.exit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()

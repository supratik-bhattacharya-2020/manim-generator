"""Rich TUI for reviewing and editing animation plans."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from .types import AnimationPlan, AnimationStep

console = Console()

_QUALITY_CYCLE = ["low", "medium", "high"]


def display_plan(plan: AnimationPlan) -> None:
    """Print the current plan as a formatted table."""
    console.print()

    title_text = Text(f"  Manim Generator — Animation Plan", style="bold cyan")
    console.print(Panel(title_text, expand=False))

    console.print(f"  [bold]Title:[/bold] {plan.title}")
    console.print(f"  [dim]{plan.description}[/dim]")
    console.print(f"  [bold]Quality:[/bold] {plan.config.quality}    "
                  f"[bold]BG:[/bold] {plan.config.background_color}")
    console.print()

    table = Table(show_header=True, header_style="bold magenta", padding=(0, 1))
    table.add_column("#", style="bold", width=4, justify="right")
    table.add_column("Description", min_width=36)
    table.add_column("Objects", style="dim", min_width=14)
    table.add_column("Region", style="green", width=12)
    table.add_column("Animation", style="cyan", width=14)
    table.add_column("Duration", justify="right", width=8)

    for step in plan.steps:
        table.add_row(
            str(step.order),
            step.description,
            ", ".join(step.objects) if step.objects else "—",
            step.region,
            step.animation_type,
            f"{step.duration:.1f}s",
        )

    console.print(table)
    console.print()


def _print_help() -> None:
    console.print("  [bold green]Commands:[/bold green]")
    console.print("    [bold]e <n>[/bold]     — edit step n")
    console.print("    [bold]d <n>[/bold]     — delete step n")
    console.print("    [bold]a <n>[/bold]     — add step after n (0 = beginning)")
    console.print("    [bold]u <n>[/bold]     — move step n up")
    console.print("    [bold]w <n>[/bold]     — move step n down")
    console.print("    [bold]q[/bold]         — cycle quality (low > medium > high)")
    console.print("    [bold]enter[/bold]     — confirm & generate")
    console.print("    [bold]esc / x[/bold]   — cancel")
    console.print("    [bold]h / ?[/bold]     — show this help")
    console.print()


def interactive_edit(plan: AnimationPlan) -> AnimationPlan | None:
    """Show the plan and let user edit it interactively. Returns None if cancelled."""
    while True:
        display_plan(plan)
        _print_help()

        raw = Prompt.ask("  [bold yellow]>[/bold yellow]", default="").strip()

        if raw == "" or raw.lower() == "enter":
            # Confirm
            if Confirm.ask("  Generate animation?", default=True):
                return plan
            continue

        if raw.lower() in ("esc", "x", "cancel"):
            if Confirm.ask("  Cancel?", default=False):
                return None
            continue

        if raw.lower() in ("h", "?", "help"):
            continue  # help is printed every loop

        if raw.lower() == "q":
            idx = _QUALITY_CYCLE.index(plan.config.quality)
            plan.config.quality = _QUALITY_CYCLE[(idx + 1) % len(_QUALITY_CYCLE)]  # type: ignore[assignment]
            console.print(f"  Quality set to [bold]{plan.config.quality}[/bold]")
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "e" and arg.isdigit():
            _edit_step(plan, int(arg))
        elif cmd == "d" and arg.isdigit():
            _delete_step(plan, int(arg))
        elif cmd == "a" and arg.isdigit():
            _add_step(plan, int(arg))
        elif cmd == "u" and arg.isdigit():
            _move_step(plan, int(arg), -1)
        elif cmd == "w" and arg.isdigit():
            _move_step(plan, int(arg), 1)
        else:
            console.print("  [red]Unknown command. Type 'h' for help.[/red]")


def _edit_step(plan: AnimationPlan, n: int) -> None:
    step = _get_step(plan, n)
    if not step:
        return

    console.print(f"  Editing step {n}: [dim]{step.description}[/dim]")

    desc = Prompt.ask("  New description", default=step.description)
    region = Prompt.ask("  Region (top/center/bottom/left/right/top-left/top-right/bottom-left/bottom-right)", default=step.region)
    dur_str = Prompt.ask("  Duration (seconds)", default=str(step.duration))
    anim = Prompt.ask("  Animation type", default=step.animation_type)

    step.description = desc
    step.region = region
    try:
        step.duration = float(dur_str)
    except ValueError:
        console.print("  [red]Invalid duration, keeping original.[/red]")
    step.animation_type = anim

    console.print("  [green]Step updated.[/green]")


def _delete_step(plan: AnimationPlan, n: int) -> None:
    step = _get_step(plan, n)
    if not step:
        return
    if Confirm.ask(f"  Delete step {n} ({step.description})?", default=False):
        plan.steps.remove(step)
        plan.reorder()
        console.print("  [green]Step deleted.[/green]")


def _add_step(plan: AnimationPlan, after: int) -> None:
    if after < 0 or after > len(plan.steps):
        console.print(f"  [red]Invalid position. Use 0–{len(plan.steps)}.[/red]")
        return

    desc = Prompt.ask("  Step description")
    if not desc:
        return
    region = Prompt.ask("  Region", default="center")
    dur_str = Prompt.ask("  Duration (seconds)", default="1.0")
    anim = Prompt.ask("  Animation type", default="Create")

    try:
        dur = float(dur_str)
    except ValueError:
        dur = 1.0

    new_step = AnimationStep(
        order=after + 1,
        description=desc,
        objects=[],
        animation_type=anim,
        duration=dur,
        region=region,
    )
    plan.steps.insert(after, new_step)
    plan.reorder()
    console.print("  [green]Step added.[/green]")


def _move_step(plan: AnimationPlan, n: int, direction: int) -> None:
    """Move step n up (direction=-1) or down (direction=+1)."""
    idx = n - 1
    new_idx = idx + direction
    if idx < 0 or idx >= len(plan.steps) or new_idx < 0 or new_idx >= len(plan.steps):
        console.print("  [red]Cannot move step there.[/red]")
        return
    plan.steps[idx], plan.steps[new_idx] = plan.steps[new_idx], plan.steps[idx]
    plan.reorder()
    console.print(f"  [green]Step moved {'up' if direction < 0 else 'down'}.[/green]")


def _get_step(plan: AnimationPlan, n: int) -> AnimationStep | None:
    for step in plan.steps:
        if step.order == n:
            return step
    console.print(f"  [red]No step #{n}. Valid range: 1–{len(plan.steps)}.[/red]")
    return None

"""AnimationPlan → Manim Python code via LLM."""

from __future__ import annotations

from rich.console import Console
from rich.syntax import Syntax

from .llm import chat_completion
from .safety import check_code
from .types import AnimationPlan

console = Console()

_MAX_RETRIES = 2

_SYSTEM_PROMPT_BASE = """\
You are a Manim code generator. Given a structured animation plan (JSON), produce a single
Python file that renders the animation using Manim Community Edition.

Rules:
1. Start with EXACTLY: `from manim import *`
2. NO other imports — no os, sys, subprocess, pathlib, math, numpy etc.
   Use Manim's built-in constants (PI, TAU, DEGREES, RIGHT, LEFT, UP, DOWN, etc.)
   and its NumPy wrapper (e.g., np.array is available through manim's namespace).
3. Define ONE class: `class GeneratedScene(Scene):`
4. Implement `def construct(self):` with self.play() and self.wait() calls.
5. Each plan step maps to one or more self.play() calls.
6. Add `self.wait(0.5)` between major steps for visual pacing.
7. Use `self.camera.background_color` for the background color from config.
8. Use descriptive variable names.
9. Keep code under 4500 characters.

Manim quick reference:
- Shapes: Circle(), Square(), Triangle(), Polygon(*vertices), Rectangle(width, height),
  Line(start, end), Arrow(start, end), Dot(point), Arc(angle, radius)
{text_ref}
- Groups: VGroup(*mobjects), .arrange(), .next_to(), .shift(), .scale()
- Positioning: UP, DOWN, LEFT, RIGHT, ORIGIN, UL, UR, DL, DR; .to_edge(), .to_corner()
- Animations: Create(), Write(), FadeIn(), FadeOut(), GrowFromCenter(),
  DrawBorderThenFill(), Transform(a, b), ReplacementTransform(a, b),
  Indicate(), MoveToTarget(), GrowArrow(), ShowPassingFlash()
- self.play(anim, run_time=N) controls duration
- self.wait(N) pauses
- Colors: RED, BLUE, GREEN, YELLOW, WHITE, GOLD, TEAL, PURPLE, ORANGE, PINK, etc.
- Constants: PI, TAU, DEGREES, np (numpy is available as np through manim)

Output ONLY the Python code. No markdown fences, no explanation.
"""

_TEXT_REF_LATEX = '- Text: Tex("LaTeX"), MathTex("x^2"), Text("plain text")'

_TEXT_REF_NO_LATEX = """\
- Text: Text("plain text") — use Text() for ALL text and labels
- CRITICAL: Do NOT use MathTex or Tex — LaTeX is NOT installed.
  Use Text() with Unicode math symbols instead. Examples:
    Text("a² + b² = c²")  instead of  MathTex("a^2 + b^2 = c^2")
    Text("θ = π/4")        instead of  MathTex("\\\\theta = \\\\frac{\\\\pi}{4}")
    Text("∑ xᵢ")           instead of  MathTex("\\\\sum x_i")
  Common Unicode: ² ³ ⁿ ₀ ₁ ₂ π θ α β γ Δ ∑ ∫ √ ∞ ≠ ≤ ≥ ± × ÷ · ∈ ∉ ∅ ∪ ∩"""


def _build_system_prompt(latex_available: bool) -> str:
    text_ref = _TEXT_REF_LATEX if latex_available else _TEXT_REF_NO_LATEX
    return _SYSTEM_PROMPT_BASE.format(text_ref=text_ref)


async def generate_code(
    plan: AnimationPlan,
    *,
    model: str | None = None,
    latex_available: bool = True,
) -> str:
    """Generate Manim code from an AnimationPlan. Retries on safety failure."""
    system_prompt = _build_system_prompt(latex_available)
    plan_json = plan.model_dump_json(indent=2)

    latex_note = ""
    if not latex_available:
        latex_note = (
            "\n\nIMPORTANT: LaTeX is NOT installed. "
            "Use Text() for ALL text — never use MathTex() or Tex()."
        )

    messages = [{"role": "user", "content": f"Generate Manim code for this plan:\n\n{plan_json}{latex_note}"}]

    for attempt in range(1, _MAX_RETRIES + 1):
        console.print(f"  [dim]Generating code (attempt {attempt}/{_MAX_RETRIES})...[/dim]")

        raw = await chat_completion(messages, system=system_prompt, model=model, temperature=0.4)
        code = _clean_code(raw)

        error = check_code(code)
        if error is None:
            console.print()
            console.print(Syntax(code, "python", theme="monokai", line_numbers=True))
            console.print()
            return code

        console.print(f"  [red]Safety check failed: {error}[/red]")

        # Feed the error back and retry
        messages.append({"role": "assistant", "content": raw})
        messages.append({
            "role": "user",
            "content": (
                f"The code failed safety validation: {error}\n"
                "Fix the issue. Remember: ONLY 'from manim import *' is allowed, "
                "no other imports, no os/sys/subprocess/open/exec/eval calls."
            ),
        })

    raise RuntimeError(
        f"Code generation failed safety checks after {_MAX_RETRIES} attempts. "
        "Try simplifying your plan."
    )


def _clean_code(raw: str) -> str:
    """Strip markdown fences, add UTF-8 coding declaration."""
    code = raw.strip()
    if code.startswith("```"):
        # Remove opening fence
        first_newline = code.index("\n")
        code = code[first_newline + 1:]
    if code.endswith("```"):
        code = code[:-3]
    code = code.strip()

    # Ensure UTF-8 coding declaration for Unicode math symbols
    if not code.startswith("# -*- coding"):
        code = "# -*- coding: utf-8 -*-\n" + code

    return code

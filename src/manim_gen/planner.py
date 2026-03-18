"""LLM-powered animation planner: prompt → structured AnimationPlan."""

from __future__ import annotations

import json
import re

from .llm import chat_completion
from .types import AnimationPlan

_SYSTEM_PROMPT_BASE = """\
You are a Manim animation planner for math and educational content.
Your job is to turn a user's natural-language description into a structured JSON animation plan.

Output ONLY valid JSON matching this schema (no markdown fences, no commentary):

{{
  "title": "Short title",
  "description": "One-sentence summary of the animation",
  "steps": [
    {{
      "order": 1,
      "description": "What to show in this step",
      "objects": ["ManimClass1", "ManimClass2"],
      "animation_type": "Create",
      "duration": 1.5
    }}
  ],
  "config": {{
    "quality": "medium",
    "background_color": "#1e1e2e"
  }}
}}

Rules:
- 3 to 8 steps. Each step is one visual beat.
- Use ONLY standard Manim Community objects: Circle, Square, Triangle, Polygon, Line, Arrow,
  Dot, NumberLine, Axes, {text_objects}, VGroup, SurroundingRectangle, Brace, etc.
{text_rule}
- animation_type must be a real Manim animation: Create, Write, FadeIn, FadeOut, Transform,
  ReplacementTransform, GrowFromCenter, DrawBorderThenFill, Indicate, MoveToTarget, etc.
- duration between 0.5 and 3.0 seconds per step.
- Keep it visually clear and educational—think 3Blue1Brown style.

Examples:

User: "Show the Pythagorean theorem with a right triangle"
{{
  "title": "Pythagorean Theorem",
  "description": "Visual proof showing a² + b² = c² with a right triangle and squares on each side",
  "steps": [
    {{"order": 1, "description": "Draw a right triangle with sides a=3, b=4, c=5", "objects": ["Polygon", "RightAngle"], "animation_type": "Create", "duration": 1.5}},
    {{"order": 2, "description": "Label the sides a, b, c", "objects": ["{label_obj}"], "animation_type": "Write", "duration": 1.0}},
    {{"order": 3, "description": "Construct a square on side a", "objects": ["Square"], "animation_type": "GrowFromCenter", "duration": 1.5}},
    {{"order": 4, "description": "Construct a square on side b", "objects": ["Square"], "animation_type": "GrowFromCenter", "duration": 1.5}},
    {{"order": 5, "description": "Construct a square on side c (hypotenuse)", "objects": ["Square"], "animation_type": "GrowFromCenter", "duration": 1.5}},
    {{"order": 6, "description": "Show equation a² + b² = c²", "objects": ["{label_obj}"], "animation_type": "Write", "duration": 1.0}}
  ],
  "config": {{"quality": "medium", "background_color": "#1e1e2e"}}
}}

User: "Explain the unit circle"
{{
  "title": "The Unit Circle",
  "description": "Interactive tour of the unit circle showing angles, coordinates, and trig functions",
  "steps": [
    {{"order": 1, "description": "Draw x-y axes", "objects": ["Axes"], "animation_type": "Create", "duration": 1.0}},
    {{"order": 2, "description": "Draw a unit circle centered at origin", "objects": ["Circle"], "animation_type": "Create", "duration": 1.5}},
    {{"order": 3, "description": "Draw radius line to angle θ = π/4", "objects": ["Line", "Dot"], "animation_type": "Create", "duration": 1.0}},
    {{"order": 4, "description": "Show angle arc and label θ", "objects": ["Arc", "{label_obj}"], "animation_type": "Write", "duration": 1.0}},
    {{"order": 5, "description": "Project onto x-axis and label cos(θ)", "objects": ["DashedLine", "{label_obj}"], "animation_type": "Create", "duration": 1.5}},
    {{"order": 6, "description": "Project onto y-axis and label sin(θ)", "objects": ["DashedLine", "{label_obj}"], "animation_type": "Create", "duration": 1.5}},
    {{"order": 7, "description": "Display sin²(θ) + cos²(θ) = 1", "objects": ["{label_obj}"], "animation_type": "Write", "duration": 1.0}}
  ],
  "config": {{"quality": "medium", "background_color": "#1e1e2e"}}
}}
"""


def _build_planner_prompt(latex_available: bool) -> str:
    if latex_available:
        return _SYSTEM_PROMPT_BASE.format(
            text_objects="MathTex, Tex, Text",
            text_rule="",
            label_obj="MathTex",
        )
    return _SYSTEM_PROMPT_BASE.format(
        text_objects="Text",
        text_rule="- IMPORTANT: LaTeX is NOT available. Use ONLY Text() for all text and labels — never MathTex or Tex.\n",
        label_obj="Text",
    )


async def generate_plan(
    prompt: str,
    *,
    model: str | None = None,
    latex_available: bool = True,
) -> AnimationPlan:
    """Generate an AnimationPlan from a natural-language prompt."""
    system_prompt = _build_planner_prompt(latex_available)
    messages = [{"role": "user", "content": prompt}]

    raw = await chat_completion(messages, system=system_prompt, model=model, temperature=0.7)

    # Strip markdown code fences if present
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    data = json.loads(raw)
    plan = AnimationPlan.model_validate(data)
    plan.reorder()
    return plan

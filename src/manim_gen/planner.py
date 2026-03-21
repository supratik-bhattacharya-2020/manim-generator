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
      "duration": 1.5,
      "region": "center",
      "narration": "Conversational voiceover for this step"
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

NARRATION — voiceover text:
- Each step MUST include a "narration" field with conversational voiceover text.
- Write as if you are a teacher explaining to a student — natural, friendly, clear.
- Keep each narration to 1-2 sentences (aim for ~3-5 seconds of speech per step).
- duration should be long enough for the narration to be spoken (roughly 1 second per 2-3 words).
- Do NOT include mathematical notation in narration — spell it out
  (e.g., "a squared plus b squared equals c squared", NOT "a² + b² = c²").

LAYOUT — region field (CRITICAL for avoiding overlaps):
- Each step MUST include a "region" field indicating where its primary objects should appear.
- Valid regions: "top", "center", "bottom", "left", "right", "top-left", "top-right", "bottom-left", "bottom-right"
- Titles and final equations go in "top" or "bottom" — NOT "center" where the main diagram lives.
- Labels/annotations should use "top", "bottom", or a side region — separate from the main geometry.
- If two steps place objects in the same region, the later step should either Transform/replace the
  earlier objects, or the earlier objects should be cleared (FadeOut) first.
- No two SIMULTANEOUS visible text/equation objects should share the same region.

Examples:

User: "Show the Pythagorean theorem with a right triangle"
{{
  "title": "Pythagorean Theorem",
  "description": "Visual proof showing a² + b² = c² with a right triangle and squares on each side",
  "steps": [
    {{"order": 1, "description": "Show title: Pythagorean Theorem", "objects": ["{label_obj}"], "animation_type": "Write", "duration": 2.0, "region": "top", "narration": "Let's explore one of the most famous results in mathematics, the Pythagorean theorem."}},
    {{"order": 2, "description": "Draw a right triangle with sides a=3, b=4, c=5", "objects": ["Polygon", "RightAngle"], "animation_type": "Create", "duration": 3.0, "region": "center", "narration": "We start with a right triangle. The two shorter sides are a and b, and the longest side is the hypotenuse, c."}},
    {{"order": 3, "description": "Label the sides a, b, c", "objects": ["{label_obj}"], "animation_type": "Write", "duration": 1.5, "region": "center", "narration": "Let's label each side."}},
    {{"order": 4, "description": "Construct a square on side a", "objects": ["Square"], "animation_type": "GrowFromCenter", "duration": 2.5, "region": "left", "narration": "Now, if we build a square on side a, its area is a squared."}},
    {{"order": 5, "description": "Construct a square on side b", "objects": ["Square"], "animation_type": "GrowFromCenter", "duration": 2.5, "region": "bottom", "narration": "And a square on side b gives us b squared."}},
    {{"order": 6, "description": "Construct a square on side c (hypotenuse)", "objects": ["Square"], "animation_type": "GrowFromCenter", "duration": 2.5, "region": "right", "narration": "The square on the hypotenuse has area c squared."}},
    {{"order": 7, "description": "Show equation a² + b² = c²", "objects": ["{label_obj}"], "animation_type": "Write", "duration": 3.0, "region": "bottom", "narration": "And the theorem tells us that a squared plus b squared always equals c squared."}}
  ],
  "config": {{"quality": "medium", "background_color": "#1e1e2e"}}
}}

User: "Explain the unit circle"
{{
  "title": "The Unit Circle",
  "description": "Interactive tour of the unit circle showing angles, coordinates, and trig functions",
  "steps": [
    {{"order": 1, "description": "Draw x-y axes", "objects": ["Axes"], "animation_type": "Create", "duration": 2.5, "region": "center", "narration": "Let's start by drawing our coordinate axes."}},
    {{"order": 2, "description": "Draw a unit circle centered at origin", "objects": ["Circle"], "animation_type": "Create", "duration": 3.0, "region": "center", "narration": "Now we draw a circle with radius one, centered at the origin. This is the unit circle."}},
    {{"order": 3, "description": "Draw radius line to angle θ = π/4", "objects": ["Line", "Dot"], "animation_type": "Create", "duration": 2.5, "region": "center", "narration": "Let's pick an angle, say theta equals pi over four, and draw a radius to that point."}},
    {{"order": 4, "description": "Show angle arc and label θ", "objects": ["Arc", "{label_obj}"], "animation_type": "Write", "duration": 2.0, "region": "center", "narration": "We mark this angle theta."}},
    {{"order": 5, "description": "Project onto x-axis and label cos(θ)", "objects": ["DashedLine", "{label_obj}"], "animation_type": "Create", "duration": 3.0, "region": "bottom", "narration": "If we project down to the x axis, this horizontal distance is cosine of theta."}},
    {{"order": 6, "description": "Project onto y-axis and label sin(θ)", "objects": ["DashedLine", "{label_obj}"], "animation_type": "Create", "duration": 3.0, "region": "left", "narration": "And projecting to the y axis gives us sine of theta."}},
    {{"order": 7, "description": "Display sin²(θ) + cos²(θ) = 1", "objects": ["{label_obj}"], "animation_type": "Write", "duration": 3.0, "region": "top", "narration": "Since the radius is one, the Pythagorean theorem tells us that sine squared plus cosine squared always equals one."}}
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

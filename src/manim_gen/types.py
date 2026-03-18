"""Pydantic models for animation plans."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SceneConfig(BaseModel):
    """Configuration for the rendered scene."""

    quality: Literal["low", "medium", "high"] = "medium"
    background_color: str = "#1e1e2e"


class AnimationStep(BaseModel):
    """A single step in the animation plan."""

    order: int
    description: str = Field(description="What this step does, e.g. 'Draw a right triangle'")
    objects: list[str] = Field(
        default_factory=list,
        description="Manim objects used, e.g. ['Polygon', 'MathTex']",
    )
    animation_type: str = Field(
        default="Create",
        description="Manim animation class, e.g. 'Create', 'Write', 'Transform'",
    )
    duration: float = Field(default=1.0, ge=0.1, le=10.0)


class AnimationPlan(BaseModel):
    """Complete animation plan produced by the planner LLM."""

    title: str
    description: str
    steps: list[AnimationStep]
    config: SceneConfig = Field(default_factory=SceneConfig)

    def reorder(self) -> None:
        """Re-number steps sequentially starting from 1."""
        for i, step in enumerate(self.steps, start=1):
            step.order = i

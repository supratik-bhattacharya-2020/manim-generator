"""Non-interactive runner: plan -> narrate -> codegen -> render -> merge audio."""
import asyncio
import os
import sys

# Force UTF-8 output on Windows
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from manim_gen.planner import generate_plan
from manim_gen.codegen import generate_code
from manim_gen.renderer import render_scene, open_video
from manim_gen.narration import generate_narration, merge_audio_video

PROMPT = (
    "Visualize how a single neuron in a neural network works, in the style of 3Blue1Brown: "
    "Show a neuron receiving multiple inputs (x1, x2, x3) as circles on the left connected "
    "by weighted edges (w1, w2, w3) to a single neuron circle on the right. Then show the "
    "weighted sum equation: w1*x1 + w2*x2 + w3*x3 + bias. Finally show the sigmoid activation "
    "function squishing the result into 0 to 1 range, with the sigmoid curve plotted."
)


async def main():
    os.makedirs("output", exist_ok=True)

    # --- Step 1: Plan ---
    print("=== Planning ===")
    plan = await generate_plan(PROMPT, latex_available=False)
    plan.config.quality = "low"

    for step in plan.steps:
        print(f"  [{step.order}] ({step.region:>12}) {step.description}")
        if step.narration:
            print(f"       narration: \"{step.narration}\"")

    # --- Step 2: Generate narration audio ---
    print("\n=== Generating Narration ===")
    narr_steps = [
        {"narration": step.narration, "duration": step.duration}
        for step in plan.steps
    ]
    audio_path, actual_durations = generate_narration(narr_steps, "output")
    print(f"  Audio: {audio_path}")
    print(f"  Clip durations: {[f'{d:.1f}s' for d in actual_durations]}")

    # Update plan durations to match actual speech durations
    for step, dur in zip(plan.steps, actual_durations):
        step.duration = max(dur, step.duration)
    print(f"  Adjusted step durations: {[f'{s.duration:.1f}s' for s in plan.steps]}")

    # --- Step 3: Generate code ---
    print("\n=== Generating Code ===")
    code = await generate_code(plan, latex_available=False)

    with open("output/neuron_scene.py", "w", encoding="utf-8") as f:
        f.write(code)
    print(f"  Code saved to output/neuron_scene.py")

    # --- Step 4: Render video (silent) ---
    print("\n=== Rendering Video ===")
    silent_video = render_scene(code, quality="low", output="output/neuron_silent.mp4")
    print(f"  Silent video: {silent_video}")

    # --- Step 5: Merge audio + video ---
    print("\n=== Merging Audio + Video ===")
    final_path = merge_audio_video(
        str(silent_video), audio_path, "output/neuron_narrated.mp4"
    )
    print(f"  Final video: {final_path}")

    # Open the final video
    from pathlib import Path
    open_video(Path(final_path))
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())

<p align="center">
  <img src="assets/demo.gif" alt="Manim Generator Demo" width="640">
</p>

<h1 align="center">Manim Generator</h1>

<p align="center">
  <strong>Natural language to math animation, powered by LLMs and <a href="https://www.manim.community/">Manim</a></strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/manim-0.18%2B-brightgreen" alt="Manim 0.18+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

---

Describe what you want to see in plain English. Manim Generator plans the animation, shows you an interactive preview, generates Manim code, and renders an MP4 — all in one command.

## How It Works

```
Prompt ─── Safety Check ─── LLM Planner ─── Interactive TUI ─── LLM Codegen ─── Manim Render ─── .mp4
                                                 ↕
                                         edit / reorder / tweak
```

1. **You describe** what to animate (e.g., *"Show the Pythagorean theorem with a right triangle"*)
2. **Planner LLM** breaks it into structured animation steps
3. **Interactive TUI** lets you edit, reorder, add, or delete steps before generating
4. **Codegen LLM** produces clean Manim Python code
5. **Safety checks** validate both input and generated code (AST analysis)
6. **Manim renders** the final video

## Quick Start

### Prerequisites

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) (required by Manim)
- LaTeX (optional — auto-detected; uses Unicode text fallback if missing)
- A running [copilot-api](https://github.com/ericc-ch/copilot-api) proxy (default: `localhost:4141`)

### Install

```bash
git clone https://github.com/supratik-bhattacharya-2020/manim-generator.git
cd manim-generator
pip install -e .
```

### Run

```bash
# Interactive prompt
python -m manim_gen

# Direct prompt
python -m manim_gen "Draw a circle and transform it into a square"

# High quality, auto-open
python -m manim_gen "Explain the unit circle" --quality high --open
```

## CLI Options

```
python -m manim_gen [PROMPT] [OPTIONS]

Arguments:
  PROMPT                   What to animate

Options:
  -q, --quality TEXT       low / medium / high (default: medium)
  -o, --output PATH        Output file path
  --open                   Open video after rendering
  --model TEXT             Override LLM model
  --base-url TEXT          Override API base URL
  --no-latex               Force Text() mode (auto-detected if LaTeX is missing)
```

## Interactive TUI

After the planner generates steps, you get a Rich terminal UI to refine them:

```
╭──────────────────────────────────────────╮
│  Manim Generator — Animation Plan        │
╰──────────────────────────────────────────╯

  Title: Pythagorean Theorem Visualization

  ┌─────┬──────────────────────────────────────────┬──────────┐
  │  #  │ Description                              │ Duration │
  ├─────┼──────────────────────────────────────────┼──────────┤
  │  1  │ Draw right triangle (a=3, b=4, c=5)     │   1.5s   │
  │  2  │ Label sides with a, b, c                 │   1.0s   │
  │  3  │ Construct square on side a               │   1.5s   │
  └─────┴──────────────────────────────────────────┴──────────┘

  [e] edit step   [d] delete step   [a] add step
  [u/w] move step [q] set quality   [Enter] generate   [Esc] cancel
```

## Safety

Two-layer protection against prompt injection and code execution:

**Input layer** — blocklist patterns (`exec`, `eval`, `import`, `os.`, `subprocess`), topic guard (violence/NSFW), length limit (500 chars), rate limit (10/hour)

**Output layer** — full AST analysis of generated code:
- Only `from manim import *` allowed
- Blocks calls to `os`, `sys`, `subprocess`, `open`, `exec`, `eval`
- Rejects dunder attribute access and `global`/`nonlocal` statements
- Max code length enforcement

## Configuration

Create a `.env` file (see `.env.example`):

```bash
MANIM_GEN_BASE_URL=http://localhost:4141/v1   # LLM API endpoint
MANIM_GEN_API_KEY=                             # API key (optional for local proxy)
MANIM_GEN_MODEL=claude-sonnet-4-20250514       # Model to use
```

## Project Structure

```
src/manim_gen/
├── __main__.py     # CLI entry point & orchestration
├── cli.py          # Rich TUI — plan display & editing
├── planner.py      # LLM → structured AnimationPlan
├── codegen.py      # AnimationPlan → Manim Python code
├── renderer.py     # Write temp file, run manim, return .mp4
├── safety.py       # Input blocklist + output AST analysis
├── llm.py          # OpenAI-compatible httpx client
└── types.py        # Pydantic models
```

## Example Prompts

```bash
python -m manim_gen "Draw a circle and transform it into a square"
python -m manim_gen "Show the Pythagorean theorem with a right triangle and squares on each side"
python -m manim_gen "Explain the unit circle with sine and cosine projections"
python -m manim_gen "Derive the quadratic formula step by step"
python -m manim_gen "Visualize Euler's identity on the complex plane"
python -m manim_gen "Show how a 2x2 matrix transforms a grid of points"
```

## License

MIT

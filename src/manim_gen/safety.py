"""Safety checks for input prompts and generated code."""

from __future__ import annotations

import ast
import re
import time
from collections import deque

# --- Input safety ---

_MAX_PROMPT_LENGTH = 500

_CODE_BLOCKLIST = [
    "exec(", "eval(", "import ", "__import__", "os.", "subprocess",
    "system(", "open(", "rm ", "del /", "rmdir", "shutil",
    "compile(", "globals(", "locals(", "getattr(", "setattr(",
]

_TOPIC_BLOCKLIST_RE = re.compile(
    r"\b(kill|murder|weapon|bomb|explo[sd]|porn|nsfw|nude|sex|drug|hack)\b",
    re.IGNORECASE,
)

# Simple in-memory rate limiter: timestamps of recent calls
_rate_window: deque[float] = deque()
_RATE_LIMIT = 10
_RATE_PERIOD = 3600  # 1 hour


def check_input(prompt: str) -> str | None:
    """Validate user prompt. Returns an error message string, or None if safe."""
    if not prompt or not prompt.strip():
        return "Prompt is empty."

    if len(prompt) > _MAX_PROMPT_LENGTH:
        return f"Prompt too long ({len(prompt)} chars, max {_MAX_PROMPT_LENGTH})."

    lower = prompt.lower()
    for blocked in _CODE_BLOCKLIST:
        if blocked.lower() in lower:
            return f"Prompt contains blocked pattern: '{blocked.strip()}'"

    if _TOPIC_BLOCKLIST_RE.search(prompt):
        return "Prompt contains prohibited content."

    # Rate limit
    now = time.monotonic()
    while _rate_window and _rate_window[0] < now - _RATE_PERIOD:
        _rate_window.popleft()
    if len(_rate_window) >= _RATE_LIMIT:
        return f"Rate limit exceeded ({_RATE_LIMIT} requests per hour). Try again later."
    _rate_window.append(now)

    return None


# --- Output (code) safety ---

_MAX_CODE_LENGTH = 5000

_FORBIDDEN_CALLS = {
    "os", "sys", "subprocess", "open", "exec", "eval", "__import__",
    "compile", "globals", "locals", "getattr", "setattr", "delattr",
    "breakpoint", "exit", "quit",
}

_ALLOWED_DUNDERS = {"__init__", "__name__", "__class__", "__str__", "__repr__"}


def check_code(code: str) -> str | None:
    """Validate generated Manim code via AST. Returns error message or None if safe."""
    if len(code) > _MAX_CODE_LENGTH:
        return f"Generated code too long ({len(code)} chars, max {_MAX_CODE_LENGTH})."

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"Generated code has syntax error: {exc}"

    # Check imports — only allow `from manim import *`
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = ", ".join(alias.name for alias in node.names)
            return f"Forbidden import: 'import {names}'. Only 'from manim import *' is allowed."

        if isinstance(node, ast.ImportFrom):
            if node.module != "manim":
                return f"Forbidden import: 'from {node.module} import ...'. Only 'from manim import *' is allowed."

        # Check for forbidden function calls
        if isinstance(node, ast.Call):
            func = node.func
            name = _resolve_call_name(func)
            if name and name.split(".")[0] in _FORBIDDEN_CALLS:
                return f"Forbidden call: '{name}(...)'"

        # Check for dunder attribute access
        if isinstance(node, ast.Attribute):
            if (
                node.attr.startswith("__")
                and node.attr.endswith("__")
                and node.attr not in _ALLOWED_DUNDERS
            ):
                return f"Forbidden dunder access: '{node.attr}'"

        # Reject global/nonlocal
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            kind = "global" if isinstance(node, ast.Global) else "nonlocal"
            return f"Forbidden '{kind}' statement."

    return None


def _resolve_call_name(node: ast.expr) -> str | None:
    """Try to resolve a Call target to a dotted name string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _resolve_call_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
    return None

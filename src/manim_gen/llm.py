"""OpenAI-compatible LLM client targeting the local copilot-api proxy."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

_DEFAULT_BASE_URL = "http://localhost:4141/v1"
_DEFAULT_MODEL = "claude-sonnet-4-20250514"


def _base_url() -> str:
    return os.getenv("MANIM_GEN_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")


def _api_key() -> str:
    return os.getenv("MANIM_GEN_API_KEY", "")


def _model() -> str:
    return os.getenv("MANIM_GEN_MODEL", _DEFAULT_MODEL)


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    key = _api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


async def chat_completion(
    messages: list[dict[str, Any]],
    *,
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Send a chat completion request and return the assistant's text."""
    payload = _build_payload(
        messages, system=system, model=model,
        temperature=temperature, max_tokens=max_tokens, stream=False,
    )

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{_base_url()}/chat/completions",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"]


async def chat_completion_stream(
    messages: list[dict[str, Any]],
    *,
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncIterator[str]:
    """Stream chat completion tokens."""
    payload = _build_payload(
        messages, system=system, model=model,
        temperature=temperature, max_tokens=max_tokens, stream=True,
    )

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{_base_url()}/chat/completions",
            headers=_headers(),
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


def _build_payload(
    messages: list[dict[str, Any]],
    *,
    system: str | None,
    model: str | None,
    temperature: float,
    max_tokens: int,
    stream: bool,
) -> dict[str, Any]:
    """Build the request payload."""
    all_messages: list[dict[str, Any]] = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(messages)

    return {
        "model": model or _model(),
        "messages": all_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }

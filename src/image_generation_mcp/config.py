"""Environment-backed configuration."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from dotenv import find_dotenv, load_dotenv

DEFAULT_GEMINI_MODEL: Final[str] = "gemini-3.1-flash-image"
DEFAULT_OPENAI_MODEL: Final[str] = "gpt-image-2"
DEFAULT_VERCEL_MODEL: Final[str] = "bfl/flux-3-image-klein"
PROVIDERS: Final[tuple[str, ...]] = ("gemini", "openai", "vercel")


@dataclass(frozen=True)
class Config:
    """Resolved runtime settings."""

    gemini_api_key: str | None
    openai_api_key: str | None
    vercel_api_key: str | None
    provider: str | None
    gemini_model: str
    openai_model: str
    vercel_model: str
    out_dir: Path
    transport: str
    port: int


def _optional(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def _required_choice(name: str, choices: tuple[str, ...]) -> str | None:
    value = _optional(name)
    if value is not None and value not in choices:
        raise ValueError(f"{name} must be one of {', '.join(choices)}, got {value!r}")
    return value


def load_config() -> Config:
    """Read settings from the environment, falling back to a .env file if present."""
    # usecwd=True searches upward from the working directory instead of inspecting the
    # caller's stack frame, which is absent under `python -c` and stdin-fed scripts.
    load_dotenv(find_dotenv(usecwd=True), override=False)
    gemini_api_key = _optional("GEMINI_API_KEY")
    openai_api_key = _optional("OPENAI_API_KEY")
    vercel_api_key = _optional("AI_GATEWAY_API_KEY")
    if gemini_api_key is None and openai_api_key is None and vercel_api_key is None:
        raise RuntimeError(
            "No API key configured. Set GEMINI_API_KEY, OPENAI_API_KEY and/or "
            "AI_GATEWAY_API_KEY in the environment or in a .env file."
        )
    out_dir = _optional("OUT_DIR")
    port = _optional("MCP_PORT")
    if port is not None and not port.isdigit():
        raise ValueError(f"MCP_PORT must be a positive integer, got {port!r}")
    return Config(
        gemini_api_key=gemini_api_key,
        openai_api_key=openai_api_key,
        vercel_api_key=vercel_api_key,
        provider=_required_choice("IMAGE_PROVIDER", PROVIDERS),
        gemini_model=_optional("GEMINI_IMAGE_MODEL") or DEFAULT_GEMINI_MODEL,
        openai_model=_optional("OPENAI_IMAGE_MODEL") or DEFAULT_OPENAI_MODEL,
        vercel_model=_optional("VERCEL_IMAGE_MODEL") or DEFAULT_VERCEL_MODEL,
        out_dir=Path(out_dir).expanduser().resolve() if out_dir else Path.cwd() / "out",
        transport=_required_choice("MCP_TRANSPORT", ("stdio", "http")) or "stdio",
        port=int(port) if port else 8000,
    )

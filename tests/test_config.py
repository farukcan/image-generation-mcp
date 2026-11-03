"""Environment parsing."""

from pathlib import Path

import pytest

from image_generation_mcp.config import DEFAULT_GEMINI_MODEL, DEFAULT_VERCEL_MODEL, load_config

ENV_VARS = (
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "AI_GATEWAY_API_KEY",
    "IMAGE_PROVIDER",
    "GEMINI_IMAGE_MODEL",
    "OPENAI_IMAGE_MODEL",
    "VERCEL_IMAGE_MODEL",
    "OUT_DIR",
    "MCP_TRANSPORT",
    "MCP_PORT",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    # Keep a stray .env in the working tree from leaking into these assertions.
    monkeypatch.setattr("image_generation_mcp.config.load_dotenv", lambda path, override: None)


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    config = load_config()
    assert config.gemini_model == DEFAULT_GEMINI_MODEL
    assert config.out_dir == Path.cwd() / "out"
    assert config.transport == "stdio"
    assert config.port == 8000


def test_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("OUT_DIR", str(tmp_path))
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.setenv("MCP_PORT", "9001")
    config = load_config()
    assert config.out_dir == tmp_path.resolve()
    assert config.transport == "http"
    assert config.port == 9001


def test_vercel_key_alone_is_enough(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "k")
    monkeypatch.setenv("IMAGE_PROVIDER", "vercel")
    config = load_config()
    assert config.vercel_api_key == "k"
    assert config.provider == "vercel"
    assert config.vercel_model == DEFAULT_VERCEL_MODEL


def test_vercel_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "k")
    monkeypatch.setenv("VERCEL_IMAGE_MODEL", "spacexai/grok-imagine-image")
    assert load_config().vercel_model == "spacexai/grok-imagine-image"


def test_no_api_key_raises() -> None:
    with pytest.raises(RuntimeError, match="No API key configured"):
        load_config()


def test_unknown_provider_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("IMAGE_PROVIDER", "midjourney")
    with pytest.raises(ValueError, match="IMAGE_PROVIDER must be one of"):
        load_config()

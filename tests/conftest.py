"""Shared fixtures."""

import base64
from pathlib import Path

import pytest

from image_generation_mcp.config import Config

PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def pixel_png() -> bytes:
    return PIXEL_PNG


@pytest.fixture
def config(tmp_path: Path) -> Config:
    """A resolved config writing into a per-test directory, for stubbed-provider tests."""
    return Config(
        gemini_api_key="k",
        openai_api_key=None,
        vercel_api_key=None,
        provider=None,
        gemini_model="m",
        openai_model="m",
        vercel_model="m",
        out_dir=tmp_path / "out",
        transport="stdio",
        port=8000,
    )


@pytest.fixture
def pixel_file(tmp_path: Path) -> Path:
    path = tmp_path / "pixel.png"
    path.write_bytes(PIXEL_PNG)
    return path

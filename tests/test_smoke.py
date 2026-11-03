"""Real API calls. Run explicitly: `uv run pytest -m smoke`."""

import os
from pathlib import Path

import pytest
from dotenv import find_dotenv, load_dotenv

from image_generation_mcp.server import generate_image

pytestmark = pytest.mark.smoke

# The keys usually live in .env, so load it before deciding whether to skip.
load_dotenv(find_dotenv(usecwd=True), override=False)


@pytest.mark.skipif(
    not (os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")),
    reason="needs GEMINI_API_KEY or OPENAI_API_KEY",
)
async def test_generates_a_real_image() -> None:
    path = Path(await generate_image("a red bicycle on a white background", aspect_ratio="16:9"))
    assert path.is_file()
    assert path.stat().st_size > 1024
    print(f"\nwrote {path}")


@pytest.mark.skipif(
    not (os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")),
    reason="needs GEMINI_API_KEY or OPENAI_API_KEY",
)
async def test_edits_a_real_image() -> None:
    """Cover the reference-image path. Costs two generations, not one."""
    reference = await generate_image("a red bicycle on a white background", aspect_ratio="16:9")
    path = Path(
        await generate_image(
            "Change the bicycle's frame color from red to a vivid blue. "
            "Keep everything else identical.",
            images=[reference],
            aspect_ratio="16:9",
        )
    )
    assert path.is_file()
    assert path.stat().st_size > 1024
    print(f"\nedited {reference} -> {path}")


@pytest.mark.skipif(not os.environ.get("AI_GATEWAY_API_KEY"), reason="needs AI_GATEWAY_API_KEY")
async def test_vercel_generates_and_edits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the Vercel AI Gateway provider. Costs two generations on VERCEL_IMAGE_MODEL."""
    monkeypatch.setenv("IMAGE_PROVIDER", "vercel")
    reference = await generate_image("a red bicycle on a white background", aspect_ratio="16:9")
    path = Path(
        await generate_image(
            "Change the bicycle's frame color from red to a vivid blue. "
            "Keep everything else identical.",
            images=[reference],
            aspect_ratio="16:9",
        )
    )
    assert path.is_file()
    assert path.stat().st_size > 1024
    print(f"\nvercel: generated {reference} -> edited {path}")

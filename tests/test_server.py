"""End-to-end tool flow with a stubbed provider."""

from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from image_generation_mcp.config import Config
from image_generation_mcp.server import generate_image
from image_generation_mcp.types import GeneratedImage, ImagePart


class StubProvider:
    """Records what the tool passed down and returns fixed bytes."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self.calls: list[tuple[str, list[ImagePart], str]] = []

    @property
    def label(self) -> str:
        return "stub/model"

    async def generate(
        self, prompt: str, sources: list[ImagePart], aspect_ratio: str
    ) -> GeneratedImage:
        self.calls.append((prompt, sources, aspect_ratio))
        return GeneratedImage(data=self._data, mime_type="image/png")


@pytest.fixture
def stub(monkeypatch: pytest.MonkeyPatch, config: Config, pixel_png: bytes) -> StubProvider:
    provider = StubProvider(pixel_png)
    monkeypatch.setattr("image_generation_mcp.server.load_config", lambda: config)
    monkeypatch.setattr("image_generation_mcp.server.select_provider", lambda _: provider)
    return provider


async def test_returns_path_of_written_file(stub: StubProvider, pixel_png: bytes) -> None:
    result = Path(await generate_image("a cat"))
    assert result.read_bytes() == pixel_png
    assert stub.calls == [("a cat", [], "1:1")]


async def test_passes_reference_images(stub: StubProvider, pixel_file: Path) -> None:
    await generate_image("restyle", images=[str(pixel_file)], aspect_ratio="16:9")
    prompt, sources, ratio = stub.calls[0]
    assert (prompt, ratio) == ("restyle", "16:9")
    assert [part.mime_type for part in sources] == ["image/png"]


async def test_invalid_aspect_ratio_raises(stub: StubProvider) -> None:
    with pytest.raises(ToolError, match="ValueError: Unsupported aspect_ratio"):
        await generate_image("a cat", aspect_ratio="7:3")
    assert stub.calls == []

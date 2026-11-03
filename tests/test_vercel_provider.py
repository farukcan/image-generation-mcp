"""Vercel AI Gateway provider request shape and response handling."""

import base64
from typing import Any

import pytest

from image_generation_mcp.types import ImagePart
from image_generation_mcp.vercel_provider import BASE_URL, VercelProvider

JPEG_HEADER = b"\xff\xd8\xff\xe0" + b"\x00" * 16


class RecordingImages:
    """Stands in for client.images, capturing kwargs and returning a canned response."""

    def __init__(self, payload: str | None) -> None:
        self._payload = payload
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def generate(self, **kwargs: Any) -> Any:
        self.calls.append(("generate", kwargs))
        return self._response()

    async def edit(self, **kwargs: Any) -> Any:
        self.calls.append(("edit", kwargs))
        return self._response()

    def _response(self) -> Any:
        datum = type("Datum", (), {"b64_json": self._payload})()
        return type(
            "Response",
            (),
            {"data": [datum], "model_dump_json": lambda self: "{}"},
        )()


def make_provider(monkeypatch: pytest.MonkeyPatch, payload: bytes | None) -> VercelProvider:
    instance = VercelProvider("key", "bfl/flux-3-image-klein")
    encoded = base64.b64encode(payload).decode("ascii") if payload is not None else None
    images = RecordingImages(encoded)
    monkeypatch.setattr(instance, "_client", type("Client", (), {"images": images})())
    return instance


def calls(provider: VercelProvider) -> list[tuple[str, dict[str, Any]]]:
    return provider._client.images.calls  # type: ignore[attr-defined,no-any-return]


def test_client_points_at_gateway() -> None:
    provider = VercelProvider("key", "bfl/flux-3-image-klein")
    assert str(provider._client.base_url).rstrip("/") == BASE_URL
    assert provider.label == "vercel/bfl/flux-3-image-klein"


async def test_generate_without_sources(monkeypatch: pytest.MonkeyPatch, pixel_png: bytes) -> None:
    provider = make_provider(monkeypatch, pixel_png)
    result = await provider.generate("a cat", [], "16:9")
    assert result.data == pixel_png
    assert result.mime_type == "image/png"
    method, kwargs = calls(provider)[0]
    assert method == "generate"
    assert kwargs["model"] == "bfl/flux-3-image-klein"
    assert kwargs["size"] == "1536x1024"
    assert kwargs["response_format"] == "b64_json"
    assert "extra_body" not in kwargs


async def test_edit_with_sources(monkeypatch: pytest.MonkeyPatch, pixel_png: bytes) -> None:
    provider = make_provider(monkeypatch, pixel_png)
    await provider.generate("restyle", [ImagePart(pixel_png, "image/webp")], "9:16")
    method, kwargs = calls(provider)[0]
    assert method == "edit"
    assert kwargs["image"] == [("reference-0.webp", pixel_png, "image/webp")]
    assert kwargs["size"] == "1024x1536"


async def test_mime_type_follows_returned_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = make_provider(monkeypatch, JPEG_HEADER)
    result = await provider.generate("a cat", [], "1:1")
    assert result.mime_type == "image/jpeg"


async def test_unknown_output_format_names_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = make_provider(monkeypatch, b"<svg xmlns='http://www.w3.org/2000/svg'/>")
    with pytest.raises(ValueError, match="vercel/bfl/flux-3-image-klein returned an unsupported"):
        await provider.generate("a cat", [], "1:1")


async def test_missing_payload_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = make_provider(monkeypatch, None)
    with pytest.raises(RuntimeError, match="vercel/bfl/flux-3-image-klein returned no image"):
        await provider.generate("a cat", [], "1:1")

"""Failures reach the MCP client as tool errors carrying the exception type and message."""

import httpx
import httpx2
import openai
import pytest
from google.genai._gaos.lib import compat_errors as gemini_errors
from mcp.client import Client
from mcp.types import TextContent

from image_generation_mcp.config import Config
from image_generation_mcp.server import mcp
from image_generation_mcp.types import GeneratedImage, ImagePart

REQUEST = httpx.Request("POST", "https://upstream.test/v1/images")
RESPONSE = httpx.Response(429, request=REQUEST)
# The openai SDK runs on httpx2, so its errors carry httpx2 objects rather than httpx ones.
OPENAI_RESPONSE = httpx2.Response(429, request=httpx2.Request("POST", "https://upstream.test/"))


class FailingProvider:
    """Raises a given exception the way a provider SDK does when the upstream call fails."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    @property
    def label(self) -> str:
        return "failing/model"

    async def generate(
        self, prompt: str, sources: list[ImagePart], aspect_ratio: str
    ) -> GeneratedImage:
        raise self._error


@pytest.fixture(autouse=True)
def use_config(monkeypatch: pytest.MonkeyPatch, config: Config) -> None:
    monkeypatch.setattr("image_generation_mcp.server.load_config", lambda: config)


def fail_with(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    provider = FailingProvider(error)
    monkeypatch.setattr("image_generation_mcp.server.select_provider", lambda _: provider)


async def call_over_mcp(arguments: dict[str, str]) -> tuple[bool, str]:
    """Call the tool through an in-process MCP client and return (is_error, text)."""
    async with Client(mcp) as client:
        result = await client.call_tool("generate_image", arguments)
    content = result.content[0]
    assert isinstance(content, TextContent)
    return result.is_error, content.text


async def test_input_error_reaches_client() -> None:
    is_error, text = await call_over_mcp({"prompt": "a cat", "aspect_ratio": "7:3"})
    assert is_error
    assert "ValueError: Unsupported aspect_ratio '7:3'" in text


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(RuntimeError("gemini/m returned no image"), id="runtime"),
        pytest.param(
            openai.RateLimitError("quota", response=OPENAI_RESPONSE, body=None), id="openai"
        ),
        pytest.param(
            gemini_errors.RateLimitError("quota", response=RESPONSE, body=None), id="gemini"
        ),
        pytest.param(
            httpx.HTTPStatusError("429 Too Many Requests", request=REQUEST, response=RESPONSE),
            id="httpx",
        ),
    ],
)
async def test_provider_error_reaches_client(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    fail_with(monkeypatch, error)
    is_error, text = await call_over_mcp({"prompt": "a cat"})
    assert is_error
    assert text.endswith(f"{type(error).__name__}: {error}")


async def test_unexpected_error_stays_generic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Programming errors are crashes, not caller-actionable failures, so stay opaque."""
    fail_with(monkeypatch, TypeError("internal detail"))
    is_error, text = await call_over_mcp({"prompt": "a cat"})
    assert is_error
    assert "internal detail" not in text

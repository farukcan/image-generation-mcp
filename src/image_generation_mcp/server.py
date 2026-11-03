"""MCP server exposing a single image generation tool."""

import logging
import time
from typing import Final

import httpx
import openai

# The Interactions API raises its own hierarchy, which google-genai (>= 2.9.0) does not
# re-export publicly and which is unrelated to google.genai.errors.APIError.
from google.genai._gaos.lib.compat_errors import GeminiNextGenAPIClientError
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .aspect import validate_aspect_ratio
from .config import load_config
from .output import write_image
from .registry import select_provider
from .sources import resolve_sources

logger = logging.getLogger(__name__)

mcp = MCPServer(name="image-generation")

# Failures the caller can act on: bad input, missing config, provider and download errors.
# The SDK forwards only ToolError messages to the client; any other exception reaches it as
# a bare "Error executing tool", hiding the status code and body it needs to react.
EXPECTED_ERRORS: Final[tuple[type[Exception], ...]] = (
    ValueError,
    RuntimeError,
    OSError,
    httpx.HTTPError,
    openai.APIError,
    GeminiNextGenAPIClientError,
)


@mcp.tool()
async def generate_image(
    prompt: str,
    images: list[str] | None = None,
    aspect_ratio: str = "1:1",
) -> str:
    """Generate an image from a text prompt and optional reference images.

    Args:
        prompt: What the image should show.
        images: Up to 4 reference images, each a local file path, an http(s) URL,
            or base64-encoded image data.
        aspect_ratio: One of 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9.

    Returns:
        The absolute path of the generated image file.
    """
    try:
        return await _generate(prompt, images or [], aspect_ratio)
    except EXPECTED_ERRORS as error:
        # The SDK logs a ToolError without its traceback, so keep the cause visible here.
        logger.warning("generate_image failed error_type=%s", type(error).__name__, exc_info=error)
        raise ToolError(f"{type(error).__name__}: {error}") from error


async def _generate(prompt: str, images: list[str], aspect_ratio: str) -> str:
    ratio = validate_aspect_ratio(aspect_ratio)
    sources = await resolve_sources(images)
    config = load_config()
    provider = select_provider(config)
    started = time.monotonic()
    generated = await provider.generate(prompt, sources, ratio)
    path = write_image(config.out_dir, generated.data, generated.mime_type)
    logger.info(
        "generated image provider=%s aspect_ratio=%s sources=%d duration_ms=%d path=%s",
        provider.label,
        ratio,
        len(sources),
        round((time.monotonic() - started) * 1000),
        path,
    )
    return str(path)

"""Pick the image provider to use for a request."""

from functools import lru_cache

from .config import Config
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider
from .types import ImageProvider
from .vercel_provider import VercelProvider


@lru_cache(maxsize=4)
def select_provider(config: Config) -> ImageProvider:
    """Return the configured provider, or the first one whose API key is set.

    Cached per config so each provider's SDK client and connection pool is reused
    across tool calls instead of being rebuilt (and leaked) on every request.
    """
    if config.provider == "gemini":
        if config.gemini_api_key is None:
            raise RuntimeError("IMAGE_PROVIDER=gemini but GEMINI_API_KEY is not set")
        return GeminiProvider(config.gemini_api_key, config.gemini_model)
    if config.provider == "openai":
        if config.openai_api_key is None:
            raise RuntimeError("IMAGE_PROVIDER=openai but OPENAI_API_KEY is not set")
        return OpenAIProvider(config.openai_api_key, config.openai_model)
    if config.provider == "vercel":
        if config.vercel_api_key is None:
            raise RuntimeError("IMAGE_PROVIDER=vercel but AI_GATEWAY_API_KEY is not set")
        return VercelProvider(config.vercel_api_key, config.vercel_model)
    if config.gemini_api_key is not None:
        return GeminiProvider(config.gemini_api_key, config.gemini_model)
    if config.openai_api_key is not None:
        return OpenAIProvider(config.openai_api_key, config.openai_model)
    if config.vercel_api_key is not None:
        return VercelProvider(config.vercel_api_key, config.vercel_model)
    raise RuntimeError(
        "No API key configured; set GEMINI_API_KEY, OPENAI_API_KEY and/or AI_GATEWAY_API_KEY"
    )

"""Vercel AI Gateway image generation via its OpenAI-compatible Images API."""

from typing import Final

from openai import AsyncOpenAI

from .aspect import openai_size
from .openai_provider import decode_first_image
from .sources import detect_mime_type
from .types import GeneratedImage, ImagePart

BASE_URL: Final[str] = "https://ai-gateway.vercel.sh/v1"


def _reference_file(index: int, part: ImagePart) -> tuple[str, bytes, str]:
    # The gateway forwards references to many vendors, so no format allowlist is applied
    # here; an unsupported type surfaces as the gateway's own error.
    extension = part.mime_type.split("/", 1)[1]
    return (f"reference-{index}.{extension}", part.data, part.mime_type)


class VercelProvider:
    """Connector to the Vercel AI Gateway Images API (image-only models)."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=BASE_URL)
        self._model = model

    @property
    def label(self) -> str:
        return f"vercel/{self._model}"

    async def generate(
        self, prompt: str, sources: list[ImagePart], aspect_ratio: str
    ) -> GeneratedImage:
        """Generate one image, editing from reference images when they are supplied.

        The gateway's Images endpoint does not forward an `aspectRatio` field, so the ratio
        goes out as one of the three OpenAI sizes: OpenAI models reject any other size, and
        Flux honours these. Some models (e.g. Grok Imagine) ignore `size` and pick their own
        shape. Output formats differ per model, so the MIME type is read from the bytes.
        """
        size = openai_size(aspect_ratio)
        if sources:
            response = await self._client.images.edit(
                model=self._model,
                prompt=prompt,
                image=[_reference_file(index, part) for index, part in enumerate(sources)],
                size=size,
                response_format="b64_json",
                n=1,
            )
        else:
            response = await self._client.images.generate(
                model=self._model,
                prompt=prompt,
                size=size,
                response_format="b64_json",
                n=1,
            )
        data = decode_first_image(self.label, response)
        try:
            mime_type = detect_mime_type(data)
        except ValueError as error:
            raise ValueError(f"{self.label} returned an unsupported image: {error}") from error
        return GeneratedImage(data=data, mime_type=mime_type)

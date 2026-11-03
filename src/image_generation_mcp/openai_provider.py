"""OpenAI image generation via the Images API."""

import base64
from typing import Final, Literal

from openai import AsyncOpenAI
from openai.types import ImagesResponse

from .aspect import openai_size
from .types import GeneratedImage, ImagePart

OUTPUT_FORMAT: Final[Literal["png"]] = "png"

# Formats the Images API accepts as edit references; anything else is a 400.
REFERENCE_EXTENSIONS: Final[dict[str, str]] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}


def _reference_file(index: int, part: ImagePart) -> tuple[str, bytes, str]:
    extension = REFERENCE_EXTENSIONS.get(part.mime_type)
    if extension is None:
        raise ValueError(
            f"OpenAI reference images must be one of "
            f"{', '.join(REFERENCE_EXTENSIONS)}, got {part.mime_type}"
        )
    return (f"reference-{index}.{extension}", part.data, part.mime_type)


def decode_first_image(label: str, response: ImagesResponse) -> bytes:
    """Decode the first base64 image of an Images API response, or raise with the full body."""
    payload = response.data[0].b64_json if response.data else None
    if not payload:
        raise RuntimeError(f"{label} returned no image data: {response.model_dump_json()}")
    return base64.b64decode(payload)


class OpenAIProvider:
    """Connector to the OpenAI Images API."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    @property
    def label(self) -> str:
        return f"openai/{self._model}"

    async def generate(
        self, prompt: str, sources: list[ImagePart], aspect_ratio: str
    ) -> GeneratedImage:
        """Generate one PNG, editing from reference images when they are supplied."""
        size = openai_size(aspect_ratio)
        if sources:
            # input_fidelity is deliberately omitted: gpt-image-2 rejects it with a 400.
            response = await self._client.images.edit(
                model=self._model,
                prompt=prompt,
                image=[_reference_file(index, part) for index, part in enumerate(sources)],
                size=size,
                output_format=OUTPUT_FORMAT,
                n=1,
            )
        else:
            response = await self._client.images.generate(
                model=self._model,
                prompt=prompt,
                size=size,
                output_format=OUTPUT_FORMAT,
                n=1,
            )
        return GeneratedImage(data=decode_first_image(self.label, response), mime_type="image/png")

"""
openai_vision_ocr.py
-----------------------
Recommended OCR backend for Pydroid3. Sends each page image straight to an
OpenAI vision-capable model and asks it to transcribe the Persian text
exactly as it appears - no local OCR engine or language pack needed, just
the same API key you're already using for translation.

Trade-off vs Tesseract: costs API tokens per page and needs network access,
but requires zero extra installation, which is exactly what's needed on a
phone/Pydroid3 where installing native OCR binaries is unreliable.
"""

import base64
import io

from ocr.base import BaseOCRBackend
from config import SETTINGS, require_api_key

OCR_SYSTEM_PROMPT = (
    "You transcribe scanned pages of classical Persian (Farsi-script) text. "
    "Return ONLY the exact Persian text you see in the image, preserving line "
    "breaks between verses/couplets. Do not translate. Do not add commentary, "
    "page numbers, or headers unless they are literally printed on the page."
)


class OpenAIVisionOCRBackend(BaseOCRBackend):
    name = "openai"

    def __init__(self, model: str = None):
        self.model = model or SETTINGS.ocr_model
        self._client = None

    def is_available(self) -> bool:
        return bool(SETTINGS.api_key)

    @property
    def client(self):
        if self._client is None:
            require_api_key()
            from openai import OpenAI
            self._client = OpenAI(api_key=SETTINGS.api_key)
        return self._client

    @staticmethod
    def _image_to_data_url(image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    def recognize_text(self, image) -> str:
        data_url = self._image_to_data_url(image)
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            timeout=SETTINGS.request_timeout,
            messages=[
                {"role": "system", "content": OCR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Transcribe the Persian text in this page image."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
        )
        return response.choices[0].message.content.strip()

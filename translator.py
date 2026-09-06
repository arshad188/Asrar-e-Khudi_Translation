"""
translator.py
-------------
Wraps the OpenAI API. Kept separate from extraction and chunking so you
could, in principle, swap in a different translation provider later just
by writing a new class with the same `translate_chunk` method.
"""

import time
from dataclasses import dataclass
from typing import Dict

from config import SETTINGS, require_api_key


SYSTEM_PROMPT_TEMPLATE = """You are an expert literary translator specializing in classical \
Persian poetry, specifically the works of Allama Muhammad Iqbal. Translate the given \
Persian (Farsi-script) verse into {language_name}.

Guidelines:
- Preserve the couplet/line structure of the original as closely as possible.
- Aim for a translation that is faithful to the philosophical and literary meaning, \
not a mechanical word-for-word rendering.
- Where a Persian term carries specific philosophical weight in Iqbal's thought \
(e.g. khudi), you may keep the transliterated term with a brief inline gloss the \
first time it appears.
- Output ONLY the translated text, with no commentary, no source text repeated, \
and no extra headers."""


@dataclass
class TranslationResult:
    language: str
    text: str


class OpenAITranslator:
    def __init__(self, model: str = None, temperature: float = None):
        self.model = model or SETTINGS.model
        self.temperature = temperature if temperature is not None else SETTINGS.temperature
        self._client = None

    @property
    def client(self):
        if self._client is None:
            require_api_key()
            from openai import OpenAI
            self._client = OpenAI(api_key=SETTINGS.api_key)
        return self._client

    def translate_chunk(self, persian_text: str, target_lang_code: str) -> TranslationResult:
        language_name = SETTINGS.language_names.get(target_lang_code, target_lang_code)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(language_name=language_name)

        last_error = None
        for attempt in range(1, SETTINGS.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    timeout=SETTINGS.request_timeout,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": persian_text},
                    ],
                )
                text = response.choices[0].message.content.strip()
                return TranslationResult(language=target_lang_code, text=text)
            except Exception as exc:  # broad on purpose: network/API errors of many types
                last_error = exc
                wait = min(2 ** attempt, 20)
                print(f"  [retry {attempt}/{SETTINGS.max_retries}] "
                      f"{type(exc).__name__}: {exc} - waiting {wait}s")
                time.sleep(wait)

        raise RuntimeError(f"Translation failed after {SETTINGS.max_retries} attempts: {last_error}")

    def translate_chunk_all_languages(self, persian_text: str) -> Dict[str, TranslationResult]:
        return {
            lang: self.translate_chunk(persian_text, lang)
            for lang in SETTINGS.target_languages
        }

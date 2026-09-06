"""
config.py
---------
Central place for all settings. Reads the OpenAI API key from the
OPENAI_API_KEY environment variable by default, but you can also pass it
on the command line (see main.py --api-key) or drop it into a local
`.env`-style file called `secrets.txt` (one line: OPENAI_API_KEY=sk-...).

Keeping this in its own module means every other module just does
`from config import SETTINGS` instead of re-reading env vars everywhere.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_secrets_file(path: str = "secrets.txt") -> None:
    """Optionally load KEY=VALUE lines from a local file into os.environ.
    Silently does nothing if the file doesn't exist - this is just a
    convenience for phone/Pydroid3 use where exporting env vars is awkward.
    """
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_secrets_file()


@dataclass
class Settings:
    # --- OpenAI ---
    api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))
    model: str = os.environ.get("IQBAL_MODEL", "gpt-4o-mini")
    temperature: float = 0.3
    max_retries: int = 4
    request_timeout: int = 60

    # --- Translation ---
    # Target languages to translate INTO. Source is always Persian (Farsi/Dari
    # script as used in Iqbal's Persian works).
    target_languages: tuple = ("en", "ur")
    language_names = {"en": "English", "ur": "Urdu"}

    # --- Chunking ---
    # Roughly how many characters of Persian source text go into one
    # translation request. Keeping chunks small preserves poetic structure
    # (couplet-by-couplet) and keeps API calls cheap and reliable.
    max_chunk_chars: int = 700

    # --- Output ---
    output_dir: str = "translated_output"

    # --- OCR (only used when --ocr is passed, for scanned/image PDFs) ---
    # "openai" needs no local binary and works reliably in Pydroid3.
    # "tesseract" is fully offline but needs the tesseract binary + Persian
    # ("fas") language data installed, which isn't guaranteed on Android.
    ocr_backend: str = os.environ.get("IQBAL_OCR_BACKEND", "openai")
    ocr_model: str = os.environ.get("IQBAL_OCR_MODEL", "gpt-4o-mini")
    ocr_tesseract_lang: str = "fas"
    ocr_dpi: int = 200


SETTINGS = Settings()


def require_api_key() -> str:
    """Raise a clear, actionable error if no API key is configured."""
    if not SETTINGS.api_key:
        raise RuntimeError(
            "No OpenAI API key found.\n"
            "Set it one of these ways:\n"
            "  1) export OPENAI_API_KEY=sk-...   (before running)\n"
            "  2) python main.py --api-key sk-...\n"
            "  3) create a file 'secrets.txt' next to main.py containing:\n"
            "     OPENAI_API_KEY=sk-..."
        )
    return SETTINGS.api_key

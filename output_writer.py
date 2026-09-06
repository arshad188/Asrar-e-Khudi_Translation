"""
output_writer.py
------------------
Handles turning a list of (source chunk, translations) pairs into files on
disk. Kept modular so you can add e.g. a DocxWriter or JsonWriter later
without touching translator.py or main.py.
"""

import json
from pathlib import Path
from typing import Dict, List

from config import SETTINGS


class TextOutputWriter:
    """Writes one plain-text file per target language, plus a combined
    Persian/English/Urdu side-by-side file for easy proofreading."""

    def __init__(self, output_dir: str = None, base_name: str = "translation"):
        self.output_dir = Path(output_dir or SETTINGS.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_name = base_name

    def write(self, results: List[dict]) -> Dict[str, str]:
        """
        results: list of dicts like
          {"index": 0, "source": "...", "translations": {"en": "...", "ur": "..."}}
        Returns a dict of {label: written_file_path}.
        """
        written = {}

        # One file per language
        for lang in SETTINGS.target_languages:
            path = self.output_dir / f"{self.base_name}_{lang}.txt"
            with open(path, "w", encoding="utf-8") as f:
                for item in results:
                    f.write(item["translations"][lang].text)
                    f.write("\n\n")
            written[lang] = str(path)

        # Combined side-by-side file (useful for checking alignment)
        combined_path = self.output_dir / f"{self.base_name}_combined.txt"
        with open(combined_path, "w", encoding="utf-8") as f:
            for item in results:
                f.write(f"[{item['index']}] PERSIAN:\n{item['source']}\n\n")
                for lang in SETTINGS.target_languages:
                    name = SETTINGS.language_names.get(lang, lang)
                    f.write(f"{name.upper()}:\n{item['translations'][lang].text}\n\n")
                f.write("-" * 40 + "\n\n")
        written["combined"] = str(combined_path)

        # JSON dump too, so downstream tools (or a future docx export step)
        # can consume structured data instead of re-parsing text files.
        json_path = self.output_dir / f"{self.base_name}.json"
        json_data = [
            {
                "index": item["index"],
                "source": item["source"],
                "translations": {
                    lang: item["translations"][lang].text
                    for lang in SETTINGS.target_languages
                },
            }
            for item in results
        ]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        written["json"] = str(json_path)

        return written

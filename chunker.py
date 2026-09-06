"""
chunker.py
----------
Iqbal's Persian works (Asrar-i-Khudi, Payam-i-Mashriq, Zabur-i-Ajam,
Javid Nama, etc.) are written in verse - couplets and short stanzas. We
don't want to hand the model one giant blob of text; we want to break it
into small, coherent units (blank-line separated blocks, i.e. usually a
couplet or short stanza) so that:
  1. Poetic structure/line breaks are preserved in translation.
  2. Each API call stays small, fast, and cheap.
  3. If one chunk fails, you only need to retry that chunk.
"""

from dataclasses import dataclass
from typing import List
import re

from config import SETTINGS


@dataclass
class Chunk:
    index: int
    source_text: str


def _split_into_blocks(raw_text: str) -> List[str]:
    """Split on blank lines first (natural verse/paragraph boundaries)."""
    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", raw_text)
    return [b.strip() for b in blocks if b.strip()]


def _merge_small_blocks(blocks: List[str], max_chars: int) -> List[str]:
    """Greedily merge consecutive small blocks up to max_chars, so we don't
    make a wasteful API call for a single two-word line."""
    merged: List[str] = []
    current = ""
    for block in blocks:
        candidate = (current + "\n\n" + block).strip() if current else block
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                merged.append(current)
            # If a single block is itself bigger than max_chars, split it
            # further by lines so nothing gets silently dropped.
            if len(block) > max_chars:
                merged.extend(_split_long_block(block, max_chars))
                current = ""
            else:
                current = block
    if current:
        merged.append(current)
    return merged


def _split_long_block(block: str, max_chars: int) -> List[str]:
    lines = block.split("\n")
    parts, current = [], ""
    for line in lines:
        candidate = (current + "\n" + line).strip() if current else line
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                parts.append(current)
            current = line
    if current:
        parts.append(current)
    return parts


def build_chunks(raw_text: str, max_chars: int = None) -> List[Chunk]:
    max_chars = max_chars or SETTINGS.max_chunk_chars
    blocks = _split_into_blocks(raw_text)
    merged = _merge_small_blocks(blocks, max_chars)
    return [Chunk(index=i, source_text=text) for i, text in enumerate(merged)]

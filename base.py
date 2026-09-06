"""
base.py
-------
Every extractor backend (pypdf, pdfminer, pymupdf, plain .txt, ...) implements
this same tiny interface. That's the whole point of making this modular:
main.py and everything downstream never needs to know or care which library
actually pulled the text out of the file. If PyMuPDF ever becomes installable
in your Pydroid3 environment, you just add extractors/pymupdf_extractor.py
implementing this same interface and register it in factory.py - nothing
else in the program changes.
"""

from abc import ABC, abstractmethod


class BaseExtractor(ABC):
    #: short id used in logs / factory selection
    name = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the required third-party library is importable."""
        raise NotImplementedError

    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """Return the full extracted text of the document as one string."""
        raise NotImplementedError

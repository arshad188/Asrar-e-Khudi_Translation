"""
factory.py
----------
Tries extractor backends in priority order and returns the first one whose
dependency is actually importable. This is the piece that makes the
"pymupdf isn't installed" problem a non-issue: the program degrades
gracefully to pypdf (or pdfminer) without any code changes needed.

Priority: pymupdf (best quality, if available) > pypdf (reliable, pure
Python) > pdfminer (secondary fallback) > txt (for plain text files).
"""

from pathlib import Path

from extractors.pymupdf_extractor import PyMuPDFExtractor
from extractors.pypdf_extractor import PyPDFExtractor
from extractors.pdfminer_extractor import PDFMinerExtractor
from extractors.txt_extractor import TxtExtractor

PDF_BACKENDS_IN_PRIORITY_ORDER = [
    PyMuPDFExtractor(),
    PyPDFExtractor(),
    PDFMinerExtractor(),
]


def get_extractor_for(file_path: str):
    """Return an extractor instance suitable for file_path, or raise."""
    suffix = Path(file_path).suffix.lower()

    if suffix == ".txt":
        return TxtExtractor()

    if suffix == ".pdf":
        for backend in PDF_BACKENDS_IN_PRIORITY_ORDER:
            if backend.is_available():
                return backend
        raise RuntimeError(
            "No PDF extraction library is installed. Install one with:\n"
            "  pip install pypdf\n"
            "(pypdf is pure Python and is the one most likely to install "
            "successfully in Pydroid3.)"
        )

    raise ValueError(f"Unsupported file type: {suffix}. Use .pdf or .txt")


def list_available_backends() -> list:
    """Handy for a --check-setup diagnostic in main.py."""
    all_backends = PDF_BACKENDS_IN_PRIORITY_ORDER + [TxtExtractor()]
    return [(b.name, b.is_available()) for b in all_backends]

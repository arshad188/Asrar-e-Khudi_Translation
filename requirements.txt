# Required: OpenAI SDK (v1.x style client used in translator.py)
openai>=1.0.0

# Required for PDF input: pure-Python, installs reliably in Pydroid3.
pypdf>=4.0.0

# Optional fallback PDF backend (also pure Python-ish, sometimes handles
# tricky font encodings better). Install if pypdf ever mis-extracts text.
# pdfminer.six>=20221105

# Optional, NOT required right now: PyMuPDF. Skip this on Pydroid3 since it
# needs a compiled wheel that often isn't available for Android. The program
# will automatically use it if it's ever importable (see extractors/factory.py),
# but everything works fully without it.
# pymupdf>=1.24.0

# --- OCR (only needed if you use --ocr, for scanned/image PDFs) ---

# Needed to turn PDF pages into images for OCR. Worth trying on Pydroid3 -
# more likely to install than pymupdf, but not guaranteed. If it fails,
# convert pages to image files yourself and OCR those directly instead.
pypdfium2>=4.0.0

# Only needed if you want the offline "tesseract" OCR backend instead of
# the default "openai" one. Also requires the tesseract binary itself
# (with 'fas' Persian language data) to be present on the system - see
# README.md's OCR section for Pydroid3-specific notes.
# pytesseract>=0.3.10

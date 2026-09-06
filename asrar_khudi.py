# asrar_khudi_translator_v3.py
# Allama Iqbal - Asrar-e-Khudi Translator
# Features: Resume, Side-by-side PDFs, Verse-aware splitting
# For Pydroid 3 (Python 3.13)
# Updated: Uses pypdf instead of pymupdf (fitz)

from pypdf import PdfReader
import requests
import os
import time
import json
import re
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib import colors

# Optional shaping
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_BIDI = True
except ImportError:
    HAS_BIDI = False
    print("Warning: arabic-reshaper / python-bidi missing → Urdu may look wrong")

# ===================== CONFIG =====================
API_KEY   = "YOUR_STRONG_MD_LS_API_KEY_HERE"
BASE_URL  = "https://api.openai.com/v1"
MODEL     = "gpt-4o-mini"

PERSIAN_PDF        = "Asrar-e-Khudi.pdf"
OUTPUT_URDU        = "Asrar-e-Khudi_Urdu.pdf"
OUTPUT_ENGLISH     = "Asrar-e-Khudi_English.pdf"
OUTPUT_SIDE_URDU   = "Asrar-e-Khudi_SideBySide_Urdu.pdf"
OUTPUT_SIDE_ENG    = "Asrar-e-Khudi_SideBySide_English.pdf"

PROGRESS_FILE      = "translation_progress.json"   # resume support

URDU_FONT_FILE     = "NotoNastaliqUrdu-Regular.ttf"
URDU_FONT_NAME     = "NotoNastaliq"

MAX_CHARS_PER_REQUEST = 2600
SLEEP_BETWEEN_CALLS   = 1.2
# ==================================================

def register_fonts():
    if os.path.exists(URDU_FONT_FILE):
        try:
            pdfmetrics.registerFont(TTFont(URDU_FONT_NAME, URDU_FONT_FILE))
            print(f"✓ Font registered: {URDU_FONT_NAME}")
            return True
        except Exception as e:
            print(f"Font error: {e}")
    else:
        print(f"⚠ Font file not found: {URDU_FONT_FILE}")
    return False

def reshape(text):
    if not HAS_BIDI or not text.strip():
        return text
    try:
        return get_display(arabic_reshaper.reshape(text))
    except:
        return text

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"urdu": {}, "english": {}}

def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def extract_pages(pdf_path):
    """Extract text from PDF using pure-Python pypdf (works on Pydroid 3)"""
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            text = text.strip()
            if text:
                pages.append({"page": i + 1, "text": text})
    return pages

def split_into_verses(text):
    """
    Better verse-level splitting for Persian poetry.
    Tries to keep couplets / lines together.
    """
    # Normalize line breaks
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    # Group into small verse blocks (usually 1-4 lines)
    verses = []
    current = []
    for ln in lines:
        current.append(ln)
        # Heuristic: end of couplet / blank-ish
        if len(current) >= 2 and (len(ln) < 40 or ln.endswith(("۔", ".", "!", "؟", "?"))):
            verses.append("\n".join(current))
            current = []
    if current:
        verses.append("\n".join(current))
    return verses if verses else [text]

def create_smart_chunks(pages):
    """
    Create chunks that respect verse boundaries as much as possible.
    """
    chunks = []
    current_text = ""
    current_pages = []
    current_page_objs = []

    for p in pages:
        verses = split_into_verses(p["text"])
        for verse in verses:
            candidate = (current_text + "\n\n" + verse).strip() if current_text else verse

            if len(candidate) > MAX_CHARS_PER_REQUEST and current_text:
                chunks.append({
                    "page_nums": current_pages[:],
                    "text": current_text,
                    "pages": current_page_objs[:]
                })
                current_text = verse
                current_pages = [p["page"]]
                current_page_objs = [p]
            else:
                current_text = candidate
                if p["page"] not in current_pages:
                    current_pages.append(p["page"])
                    current_page_objs.append(p)

    if current_text:
        chunks.append({
            "page_nums": current_pages,
            "text": current_text,
            "pages": current_page_objs
        })
    return chunks

def translate_text(text, target_lang):
    system = (
        f"You are an expert literary translator of classical Persian poetry, "
        f"specializing in Allama Iqbal's Asrar-e-Khudi. "
        f"Translate the following Persian text into elegant, accurate {target_lang}. "
        f"Preserve philosophical depth, poetic feeling and line structure as much as possible. "
        f"Output ONLY the translation."
    )
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text}
        ],
        "temperature": 0.25,
        "max_tokens": 4096
    }
    url = f"{BASE_URL.rstrip('/')}/chat/completions"
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=180)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  API Error: {e}")
        return f"[Translation failed: {e}]"

def translate_with_resume(pages, target_lang, progress):
    key = "urdu" if target_lang.lower().startswith("u") else "english"
    already = progress.get(key, {})
    print(f"\n=== Translating to {target_lang} ===")
    print(f"Already done: {len(already)} pages")

    chunks = create_smart_chunks(pages)
    print(f"Total chunks to process: {len(chunks)}")

    page_results = {}

    for idx, chunk in enumerate(chunks, 1):
        # Check if all pages in this chunk are already done
        if all(str(p) in already for p in chunk["page_nums"]):
            print(f"  [{idx}/{len(chunks)}] Skipping pages {chunk['page_nums']} (already done)")
            for p in chunk["page_nums"]:
                page_results[p] = already[str(p)]
            continue

        print(f"  [{idx}/{len(chunks)}] Translating pages {chunk['page_nums']} ...")
        translated = translate_text(chunk["text"], target_lang)

        for pnum in chunk["page_nums"]:
            page_results[pnum] = translated
            already[str(pnum)] = translated

        # Save progress after every successful chunk
        progress[key] = already
        save_progress(progress)
        time.sleep(SLEEP_BETWEEN_CALLS)

    # Rebuild ordered list
    results = []
    for p in pages:
        results.append({
            "page": p["page"],
            "persian": p["text"],
            "text": page_results.get(p["page"], already.get(str(p["page"]), "[missing]"))
        })
    return results

def build_single_pdf(translations, output_path, lang="english", has_font=False):
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=15*mm, leftMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('T', parent=styles['Heading1'],
                                 fontSize=16, alignment=TA_CENTER, spaceAfter=10,
                                 fontName='Helvetica-Bold')

    if lang == "urdu" and has_font:
        body = ParagraphStyle('U', parent=styles['Normal'],
                              fontName=URDU_FONT_NAME, fontSize=12, leading=20,
                              alignment=TA_RIGHT, spaceAfter=8, wordWrap='RTL')
        hdr = ParagraphStyle('UH', parent=styles['Heading3'],
                             fontName=URDU_FONT_NAME, fontSize=10,
                             alignment=TA_RIGHT, spaceBefore=6, spaceAfter=3)
    else:
        body = ParagraphStyle('E', parent=styles['Normal'],
                              fontName='Helvetica', fontSize=10.5, leading=14,
                              alignment=TA_LEFT, spaceAfter=6)
        hdr = ParagraphStyle('EH', parent=styles['Heading3'],
                             fontSize=9, alignment=TA_LEFT,
                             spaceBefore=6, spaceAfter=3)

    story = []
    if lang == "urdu":
        story.append(Paragraph(reshape("اسرارِ خودی"), title_style))
        story.append(Paragraph(reshape("علامہ محمد اقبال"), styles['Heading2']))
    else:
        story.append(Paragraph("Asrar-e-Khudi (The Secrets of the Self)", title_style))
        story.append(Paragraph("Allama Muhammad Iqbal", styles['Heading2']))

    story.append(Spacer(1, 12))
    story.append(PageBreak())

    for item in translations:
        h = reshape(f"صفحہ {item['page']}") if lang == "urdu" else f"Page {item['page']}"
        story.append(Paragraph(h, hdr))
        txt = reshape(item["text"]) if lang == "urdu" else item["text"]
        txt = txt.replace("\n", "<br/>")
        story.append(Paragraph(txt, body))
        story.append(Spacer(1, 4))

    doc.build(story)
    print(f"✓ Single PDF → {output_path}")

def build_side_by_side(translations, output_path, lang="english", has_font=False):
    """Create landscape side-by-side: Persian | Translation"""
    doc = SimpleDocTemplate(output_path, pagesize=landscape(A4),
                            rightMargin=12*mm, leftMargin=12*mm,
                            topMargin=12*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()

    # Persian style
    pers_style = ParagraphStyle('Pers', parent=styles['Normal'],
                                fontName=URDU_FONT_NAME if has_font else 'Helvetica',
                                fontSize=10, leading=15,
                                alignment=TA_RIGHT, wordWrap='RTL')

    if lang == "urdu" and has_font:
        trans_style = ParagraphStyle('Trans', parent=styles['Normal'],
                                     fontName=URDU_FONT_NAME, fontSize=10, leading=15,
                                     alignment=TA_RIGHT, wordWrap='RTL')
    else:
        trans_style = ParagraphStyle('Trans', parent=styles['Normal'],
                                     fontName='Helvetica', fontSize=9.5, leading=13,
                                     alignment=TA_LEFT)

    header_style = ParagraphStyle('H', parent=styles['Heading3'],
                                  fontSize=9, alignment=TA_CENTER)

    story = []
    title = "اسرارِ خودی – فارسی + اردو" if lang == "urdu" else "Asrar-e-Khudi – Persian + English"
    story.append(Paragraph(reshape(title) if lang == "urdu" else title,
                           ParagraphStyle('T', parent=styles['Heading1'],
                                          fontSize=14, alignment=TA_CENTER)))
    story.append(Spacer(1, 8))

    for item in translations:
        # Header row
        left_h = Paragraph("<b>Persian (Original)</b>", header_style)
        right_h = Paragraph(f"<b>{'Urdu' if lang=='urdu' else 'English'} Translation</b> — Page {item['page']}", header_style)

        pers_txt = reshape(item["persian"]).replace("\n", "<br/>")
        trans_txt = (reshape(item["text"]) if lang == "urdu" else item["text"]).replace("\n", "<br/>")

        left_p = Paragraph(pers_txt, pers_style)
        right_p = Paragraph(trans_txt, trans_style)

        data = [[left_h, right_h], [left_p, right_p]]
        t = Table(data, colWidths=[130*mm, 130*mm])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.92, 0.92, 0.95)),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))

    doc.build(story)
    print(f"✓ Side-by-side PDF → {output_path}")

def main():
    if not os.path.exists(PERSIAN_PDF):
        print(f"ERROR: {PERSIAN_PDF} not found")
        return

    has_font = register_fonts()
    progress = load_progress()

    print("Extracting Persian text...")
    pages = extract_pages(PERSIAN_PDF)
    print(f"Found {len(pages)} pages with text.")

    # ----- Urdu -----
    urdu_results = translate_with_resume(pages, "Urdu", progress)
    build_single_pdf(urdu_results, OUTPUT_URDU, lang="urdu", has_font=has_font)
    build_side_by_side(urdu_results, OUTPUT_SIDE_URDU, lang="urdu", has_font=has_font)

    # ----- English -----
    eng_results = translate_with_resume(pages, "English", progress)
    build_single_pdf(eng_results, OUTPUT_ENGLISH, lang="english", has_font=False)
    build_side_by_side(eng_results, OUTPUT_SIDE_ENG, lang="english", has_font=has_font)

    print("\n========== ALL DONE ==========")
    print("Created files:")
    print(f"  • {OUTPUT_URDU}")
    print(f"  • {OUTPUT_ENGLISH}")
    print(f"  • {OUTPUT_SIDE_URDU}")
    print(f"  • {OUTPUT_SIDE_ENG}")
    print(f"Progress saved in: {PROGRESS_FILE}")
    print("You can re-run the script anytime — it will skip already translated pages.")

if __name__ == "__main__":
    main()
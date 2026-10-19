from __future__ import annotations

import io
import os
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Optional


def extract_text_from_pdf(path: Path, max_pages: int = 50) -> str:
    """Extract text from a PDF file using pypdfium2, PyPDF2, or pdfminer."""
    # Method 1: pypdfium2 (fastest, C++ based)
    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(str(path))
        pages_text = []
        for i in range(min(len(pdf), max_pages)):
            page = pdf[i]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            if text:
                pages_text.append(text)
        return "\n".join(pages_text)
    except Exception:
        pass

    # Method 2: PyPDF2 fallback
    try:
        import PyPDF2

        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            pages_text = []
            for i in range(min(len(reader.pages), max_pages)):
                page = reader.pages[i]
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            return "\n".join(pages_text)
    except Exception:
        pass

    return ""


def extract_text_from_docx(path: Path) -> str:
    """Extract text from a .docx file using standard library zipfile and XML parser."""
    try:
        with zipfile.ZipFile(path) as z:
            if "word/document.xml" not in z.namelist():
                return ""
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            # Namespace for WordprocessingML
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = []
            for p in tree.iterfind(".//w:p", ns):
                texts = [node.text for node in p.iterfind(".//w:t", ns) if node.text]
                if texts:
                    paragraphs.append("".join(texts))
            return "\n".join(paragraphs)
    except Exception:
        return ""


def extract_text_from_xlsx(path: Path) -> str:
    """Extract strings and cell values from .xlsx using standard library zipfile and XML."""
    try:
        with zipfile.ZipFile(path) as z:
            strings: list[str] = []
            if "xl/sharedStrings.xml" in z.namelist():
                xml_content = z.read("xl/sharedStrings.xml")
                tree = ET.fromstring(xml_content)
                ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                for t in tree.iterfind(".//s:t", ns):
                    if t.text:
                        strings.append(t.text)
            return " ".join(strings)
    except Exception:
        return ""


def extract_text_from_pptx(path: Path) -> str:
    """Extract text from .pptx slides using standard library zipfile and XML."""
    try:
        with zipfile.ZipFile(path) as z:
            texts: list[str] = []
            ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
            slide_files = sorted(
                [name for name in z.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
            )
            for s in slide_files:
                xml_content = z.read(s)
                tree = ET.fromstring(xml_content)
                for t in tree.iterfind(".//a:t", ns):
                    if t.text:
                        texts.append(t.text)
            return "\n".join(texts)
    except Exception:
        return ""


def extract_document_text(path: Path, max_size_bytes: int = 15_000_000) -> str:
    """Universal text extractor for code, plain text, PDF, Word, Excel, and PowerPoint."""
    if not path.is_file():
        return ""

    try:
        if path.stat().st_size > max_size_bytes:
            return ""
    except OSError:
        return ""

    ext = path.suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext == ".docx":
        return extract_text_from_docx(path)
    elif ext == ".xlsx":
        return extract_text_from_xlsx(path)
    elif ext == ".pptx":
        return extract_text_from_pptx(path)

    # For plain text and source code files
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(path, "r", encoding=enc, errors="replace") as f:
                return f.read(500_000)
        except (UnicodeDecodeError, OSError):
            continue

    return ""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from baizo.core.parsers import (
    extract_document_text,
    extract_text_from_docx,
    extract_text_from_xlsx,
)


def create_dummy_docx(path: Path, text: str) -> None:
    xml_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body>
            <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
        </w:body>
    </w:document>
    """
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", xml_content)


def create_dummy_xlsx(path: Path, text: str) -> None:
    xml_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
        <si><t>{text}</t></si>
    </sst>
    """
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/sharedStrings.xml", xml_content)


def test_extract_docx(tmp_path: Path) -> None:
    docx_file = tmp_path / "sample.docx"
    create_dummy_docx(docx_file, "Financial Quarterly Performance Review 2026")
    extracted = extract_text_from_docx(docx_file)
    assert "Financial Quarterly" in extracted
    assert "2026" in extracted

    universal = extract_document_text(docx_file)
    assert "Financial Quarterly" in universal


def test_extract_xlsx(tmp_path: Path) -> None:
    xlsx_file = tmp_path / "budget.xlsx"
    create_dummy_xlsx(xlsx_file, "Project Budget Forecast Q4")
    extracted = extract_text_from_xlsx(xlsx_file)
    assert "Project Budget" in extracted

    universal = extract_document_text(xlsx_file)
    assert "Project Budget" in universal

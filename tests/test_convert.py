from __future__ import annotations

import os
from email.message import EmailMessage
from pathlib import Path

from eml2pdf.convert import batch_convert, convert_eml_to_pdf


def _write_eml(path: Path, msg: EmailMessage) -> None:
    path.write_bytes(msg.as_bytes())


def _make_basic_eml(subject: str, text: str, html: str | None = None) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "sender@example.com"
    msg["To"] = "to@example.com"
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    return msg


def test_convert_text_eml(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("EML2PDF_FORCE_TEXT", "1")

    eml_path = tmp_path / "test.eml"
    pdf_path = tmp_path / "out.pdf"
    msg = _make_basic_eml("Hello", "This is a test.")
    _write_eml(eml_path, msg)

    convert_eml_to_pdf(eml_path, pdf_path, overwrite=True, extract_attachments=False)

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0


def test_convert_html_eml_with_attachment(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("EML2PDF_FORCE_TEXT", "1")

    eml_path = tmp_path / "test2.eml"
    pdf_path = tmp_path / "out2.pdf"
    msg = _make_basic_eml("HTML", "Fallback body", "<p><strong>HTML</strong> body</p>")
    msg.add_attachment(b"hello", maintype="text", subtype="plain", filename="note.txt")
    _write_eml(eml_path, msg)

    convert_eml_to_pdf(eml_path, pdf_path, overwrite=True, extract_attachments=True)

    attachments_dir = tmp_path / "attachments" / "test2"
    assert (attachments_dir / "note.txt").exists()
    assert pdf_path.exists()


def test_batch_convert(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("EML2PDF_FORCE_TEXT", "1")
    input_dir = tmp_path / "eml"
    output_dir = tmp_path / "pdf"
    input_dir.mkdir()

    for i in range(2):
        eml_path = input_dir / f"m{i}.eml"
        msg = _make_basic_eml(f"Subject {i}", f"Body {i}")
        _write_eml(eml_path, msg)

    count = batch_convert(input_dir, output_dir, recursive=False, overwrite=True)

    assert count == 2
    assert (output_dir / "m0.pdf").exists()
    assert (output_dir / "m1.pdf").exists()

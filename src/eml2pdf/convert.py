from __future__ import annotations

import email
import os
import re
from dataclasses import dataclass
from email import policy
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


@dataclass
class EmailContent:
    subject: str
    sender: str
    to: str
    date: str
    body: str


def _read_eml(path: Path) -> EmailMessage:
    with path.open("rb") as f:
        return email.message_from_binary_file(f, policy=policy.default)


def _extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    # Collapse excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _get_body(msg: EmailMessage) -> str:
    if msg.is_multipart():
        # Prefer plain text, fallback to html
        text_part = None
        html_part = None
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                continue
            ctype = part.get_content_type()
            if ctype == "text/plain" and text_part is None:
                text_part = part.get_content()
            elif ctype == "text/html" and html_part is None:
                html_part = part.get_content()
        if text_part:
            return str(text_part).strip()
        if html_part:
            return _extract_text_from_html(str(html_part))
        return ""

    ctype = msg.get_content_type()
    if ctype == "text/html":
        return _extract_text_from_html(str(msg.get_content()))
    return str(msg.get_content()).strip()


def _extract_content(msg: EmailMessage) -> EmailContent:
    subject = msg.get("subject", "")
    sender = msg.get("from", "")
    to = msg.get("to", "")
    date = msg.get("date", "")
    body = _get_body(msg)
    return EmailContent(subject=subject, sender=sender, to=to, date=date, body=body)


def _wrap_text(text: str, width: int) -> Iterable[str]:
    words = text.split()
    if not words:
        return []
    line = words[0]
    lines = []
    for w in words[1:]:
        if len(line) + 1 + len(w) <= width:
            line += " " + w
        else:
            lines.append(line)
            line = w
    lines.append(line)
    return lines


def _draw_paragraphs(c: canvas.Canvas, text: str, x: float, y: float, max_width: int, line_height: float) -> float:
    for para in text.split("\n"):
        if not para.strip():
            y -= line_height
            continue
        for line in _wrap_text(para, max_width):
            if y <= 1 * inch:
                c.showPage()
                y = 10.5 * inch
            c.drawString(x, y, line)
            y -= line_height
    return y


def convert_eml_to_pdf(eml_path: Path, pdf_path: Path, overwrite: bool = False) -> None:
    if pdf_path.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {pdf_path}")

    msg = _read_eml(eml_path)
    content = _extract_content(msg)

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(pdf_path), pagesize=letter)

    left = 1 * inch
    top = 10.5 * inch
    line_height = 14

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, top, f"Subject: {content.subject}")
    c.setFont("Helvetica", 11)
    y = top - line_height
    c.drawString(left, y, f"From: {content.sender}")
    y -= line_height
    c.drawString(left, y, f"To: {content.to}")
    y -= line_height
    c.drawString(left, y, f"Date: {content.date}")

    y -= line_height * 1.5
    c.setFont("Helvetica", 11)

    # Rough character width for wrapping (monospace-like estimate)
    max_chars = 90
    y = _draw_paragraphs(c, content.body, left, y, max_chars, line_height)

    c.save()


def _iter_eml_files(path: Path, recursive: bool) -> Iterable[Path]:
    if path.is_file():
        if path.suffix.lower() == ".eml":
            yield path
        return

    pattern = "**/*.eml" if recursive else "*.eml"
    for p in path.glob(pattern):
        if p.is_file():
            yield p


def batch_convert(input_path: Path, output_dir: Path, recursive: bool = False, overwrite: bool = False) -> int:
    count = 0
    for eml_path in _iter_eml_files(input_path, recursive):
        rel_name = eml_path.stem + ".pdf"
        pdf_path = output_dir / rel_name
        convert_eml_to_pdf(eml_path, pdf_path, overwrite=overwrite)
        count += 1
    return count

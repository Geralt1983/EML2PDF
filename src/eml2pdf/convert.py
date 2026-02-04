from __future__ import annotations

import email
import html
import mimetypes
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
    body_text: str
    body_html: str


@dataclass
class Attachment:
    filename: str
    content_type: str
    size: int
    saved_path: Path


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


def _get_body_parts(msg: EmailMessage) -> tuple[str, str]:
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
        return (
            str(text_part).strip() if text_part else "",
            str(html_part).strip() if html_part else "",
        )

    ctype = msg.get_content_type()
    if ctype == "text/html":
        return "", str(msg.get_content()).strip()
    return str(msg.get_content()).strip(), ""


def _extract_content(msg: EmailMessage) -> EmailContent:
    subject = msg.get("subject", "")
    sender = msg.get("from", "")
    to = msg.get("to", "")
    date = msg.get("date", "")
    body_text, body_html = _get_body_parts(msg)
    return EmailContent(
        subject=subject,
        sender=sender,
        to=to,
        date=date,
        body_text=body_text,
        body_html=body_html,
    )


def _sanitize_filename(name: str, default: str) -> str:
    name = name.strip().replace("\\", "_").replace("/", "_")
    if not name:
        return default
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def _save_attachments(msg: EmailMessage, attachments_dir: Path) -> list[Attachment]:
    attachments: list[Attachment] = []
    index = 1
    attachments_dir.mkdir(parents=True, exist_ok=True)

    for part in msg.walk():
        if part.is_multipart():
            continue
        disposition = part.get_content_disposition()
        if disposition not in ("attachment", "inline"):
            continue

        filename = part.get_filename() or ""
        content_type = part.get_content_type()
        ext = mimetypes.guess_extension(content_type) or ""
        safe_name = _sanitize_filename(filename, f"attachment-{index}{ext}")

        payload = part.get_payload(decode=True) or b""
        saved_path = attachments_dir / safe_name
        saved_path.write_bytes(payload)

        attachments.append(
            Attachment(
                filename=safe_name,
                content_type=content_type,
                size=len(payload),
                saved_path=saved_path,
            )
        )
        index += 1

    return attachments


def _build_email_html(content: EmailContent, attachments: list[Attachment]) -> str:
    body_html = content.body_html
    if not body_html and content.body_text:
        body_html = f"<pre>{html.escape(content.body_text)}</pre>"

    attachment_html = ""
    if attachments:
        items = "".join(
            f"<li><strong>{html.escape(a.filename)}</strong> ({html.escape(a.content_type)}, {a.size} bytes)</li>"
            for a in attachments
        )
        attachment_html = f"<h2>Attachments</h2><ul>{items}</ul>"

    return f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      body {{ font-family: Arial, sans-serif; font-size: 12px; color: #111; }}
      .meta {{ margin-bottom: 16px; }}
      .meta div {{ margin: 2px 0; }}
      .content {{ margin-top: 8px; }}
      pre {{ white-space: pre-wrap; font-family: Arial, sans-serif; }}
      h2 {{ margin-top: 24px; font-size: 14px; }}
    </style>
  </head>
  <body>
    <div class="meta">
      <div><strong>Subject:</strong> {html.escape(content.subject)}</div>
      <div><strong>From:</strong> {html.escape(content.sender)}</div>
      <div><strong>To:</strong> {html.escape(content.to)}</div>
      <div><strong>Date:</strong> {html.escape(content.date)}</div>
    </div>
    <div class="content">{body_html}</div>
    {attachment_html}
  </body>
</html>
"""


def _render_html_to_pdf(html_string: str, pdf_path: Path) -> bool:
    if os.environ.get("EML2PDF_FORCE_TEXT") == "1":
        return False
    try:
        from weasyprint import HTML
    except Exception:
        return False

    HTML(string=html_string).write_pdf(str(pdf_path))
    return True


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


def convert_eml_to_pdf(
    eml_path: Path,
    pdf_path: Path,
    overwrite: bool = False,
    extract_attachments: bool = True,
    attachments_dirname: str = "attachments",
) -> None:
    if pdf_path.exists() and not overwrite:
        raise FileExistsError(f"Output exists: {pdf_path}")

    msg = _read_eml(eml_path)
    content = _extract_content(msg)

    attachments: list[Attachment] = []
    if extract_attachments:
        attachments_dir = pdf_path.parent / attachments_dirname / eml_path.stem
        attachments = _save_attachments(msg, attachments_dir)

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    html_string = _build_email_html(content, attachments)
    if _render_html_to_pdf(html_string, pdf_path):
        return

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

    body_text = content.body_text
    if not body_text and content.body_html:
        body_text = _extract_text_from_html(content.body_html)

    max_chars = 90
    y = _draw_paragraphs(c, body_text, left, y, max_chars, line_height)

    if attachments:
        y -= line_height
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left, y, "Attachments:")
        c.setFont("Helvetica", 11)
        y -= line_height
        for att in attachments:
            line = f"- {att.filename} ({att.content_type}, {att.size} bytes)"
            for wrapped in _wrap_text(line, max_chars):
                if y <= 1 * inch:
                    c.showPage()
                    y = 10.5 * inch
                c.drawString(left, y, wrapped)
                y -= line_height

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


def batch_convert(
    input_path: Path,
    output_dir: Path,
    recursive: bool = False,
    overwrite: bool = False,
    extract_attachments: bool = True,
    attachments_dirname: str = "attachments",
) -> int:
    count = 0
    for eml_path in _iter_eml_files(input_path, recursive):
        rel_name = eml_path.stem + ".pdf"
        pdf_path = output_dir / rel_name
        convert_eml_to_pdf(
            eml_path,
            pdf_path,
            overwrite=overwrite,
            extract_attachments=extract_attachments,
            attachments_dirname=attachments_dirname,
        )
        count += 1
    return count

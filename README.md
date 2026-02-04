# EML2PDF

Batch convert `.eml` files to PDFs.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e .

# Optional: better HTML rendering
pip install -e .[html]

eml2pdf ./input-eml ./output-pdf
```

## Notes
- Each EML becomes one PDF.
- Attachments are saved to `attachments/<email-stem>/` by default.
- HTML is rendered to PDF when `weasyprint` is available (`pip install -e .[html]`). If not, it falls back to text.

## CLI

```bash
eml2pdf <input_path> <output_dir> [--recursive] [--overwrite] [--no-attachments] [--attachments-dir <dir>]
```

## Development

```bash
pip install -e .[dev]
python -m eml2pdf --help
```

## Standalone (No Python)

If you want a single-file executable:

```bash
pip install -e .
pip install pyinstaller
pyinstaller --onefile -n eml2pdf src/eml2pdf/cli.py
```

The binary will be in `dist/eml2pdf`.

# EML2PDF

Batch convert `.eml` files to PDFs.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e .

eml2pdf ./input-eml ./output-pdf
```

## Notes
- Each EML becomes one PDF.
- Attachments are ignored (for now).
- Plain text and HTML bodies are supported; HTML is converted to text.

## CLI

```bash
eml2pdf <input_path> <output_dir> [--recursive] [--overwrite]
```

## Development

```bash
pip install -e .[dev]
python -m eml2pdf --help
```

# Decisions & Learnings

## Rendering Strategy
- Use WeasyPrint when available for HTML fidelity.
- Always keep a text fallback path (ReportLab) and allow `EML2PDF_FORCE_TEXT=1` for deterministic tests.

## Attachment Handling
- Sanitize filenames and avoid collisions by appending counters.
- Save attachments to `attachments/<email-stem>/` to keep outputs organized.

## Inline Images
- Replace `cid:` references with local file URIs for HTML renderers.

## Windows Packaging
- Provide PowerShell scripts for tests and builds.
- Document WeasyPrint Windows prerequisites; fall back to text when unavailable.

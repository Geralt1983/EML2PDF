from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .convert import batch_convert


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Batch convert EML files to PDFs")
    p.add_argument("input_path", type=Path, help="EML file or directory")
    p.add_argument("output_dir", type=Path, help="Output directory for PDFs")
    p.add_argument("--recursive", action="store_true", help="Recurse into subdirectories")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing PDFs")
    p.add_argument("--no-attachments", action="store_true", help="Skip extracting attachments")
    p.add_argument(
        "--attachments-dir",
        default="attachments",
        help="Directory (within output) for saved attachments",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    try:
        count = batch_convert(
            args.input_path,
            args.output_dir,
            args.recursive,
            args.overwrite,
            extract_attachments=not args.no_attachments,
            attachments_dirname=args.attachments_dir,
        )
    except FileExistsError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"Converted {count} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

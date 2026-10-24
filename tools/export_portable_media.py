"""Explicitly copy an Edivora .edap/.edvp project into a new portable folder.

Examples:
    python tools/export_portable_media.py /path/session.edap /path/portable-copy
    python tools/export_portable_media.py "C:\\Media\\movie.edvp" "D:\\Travel\\movie"
The destination directory must not exist. No original source files are altered.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from local_ai_photo_editor.core.media_project import load_media_project
from local_ai_photo_editor.core.portable_media import create_portable_media_folder


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Existing saved .edap/.edvp project.")
    parser.add_argument("destination", type=Path, help="New, non-existing portable folder.")
    args = parser.parse_args(argv)
    try:
        source = load_media_project(args.project)
        output = create_portable_media_folder(source, args.destination)
    except (OSError, ValueError, InterruptedError) as exc:
        print(f"Portable export refused: {exc}", file=sys.stderr)
        return 1
    print(f"Portable project created: {output}")
    print("Inspect its contents before sharing; media may contain private metadata.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

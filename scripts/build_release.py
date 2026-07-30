#!/usr/bin/env python3
"""Build a reproducible release ZIP for the skill-only plugin."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


INCLUDE = (
    Path(".agents"),
    Path("plugins"),
    Path("README.md"),
    Path("README_EN.md"),
    Path("CONTRIBUTING.md"),
    Path("LICENSE"),
)
FIXED_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def iter_files(root: Path):
    for relative in INCLUDE:
        target = root / relative
        if target.is_file():
            yield target
        elif target.is_dir():
            yield from sorted(path for path in target.rglob("*") if path.is_file())
        else:
            raise FileNotFoundError(f"Required release input is missing: {target}")


def build(root: Path, output_dir: Path) -> Path:
    manifest = json.loads(
        (root / "plugins/scientific-figure-builder-reviewer/.codex-plugin/plugin.json").read_text(
            encoding="utf-8"
        )
    )
    name = manifest["name"]
    version = manifest["version"]
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{name}-{version}.zip"

    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as bundle:
        for source in iter_files(root):
            relative = source.relative_to(root).as_posix()
            info = zipfile.ZipInfo(relative, FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, source.read_bytes())

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"Built {archive}")
    print(f"SHA256 {digest}")
    return archive


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    build(args.root.resolve(), args.output_dir.resolve())


if __name__ == "__main__":
    main()

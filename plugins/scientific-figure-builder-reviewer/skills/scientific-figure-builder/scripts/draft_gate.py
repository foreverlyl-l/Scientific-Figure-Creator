#!/usr/bin/env python3
"""Create and verify a human-approved whole-figure draft lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 1


class GateError(ValueError):
    """Raised when a draft cannot pass the freeze gate."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_relative(root: Path, value: str, *, must_exist: bool) -> Path:
    relative = Path(value)
    if relative.is_absolute():
        raise GateError(f"Path must be relative to the task root: {value}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise GateError(f"Path escapes the task root: {value}") from exc
    if must_exist and not resolved.is_file():
        raise GateError(f"Required file does not exist: {value}")
    return resolved


def relative_posix(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temporary_name = handle.name
        os.replace(temporary_name, path)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def create_lock(args: argparse.Namespace) -> int:
    if not args.confirmed:
        raise GateError("Explicit user confirmation is required; pass --confirmed only after it occurs")
    if args.approved_by != "user" or args.approval_source != "chat":
        raise GateError("The whole-first freeze gate requires approved_by=user and approval_source=chat")

    root = args.root.resolve()
    if not root.is_dir():
        raise GateError(f"Task root does not exist: {root}")
    draft = resolve_relative(root, args.draft, must_exist=True)
    spec = resolve_relative(root, args.spec, must_exist=True)
    output = resolve_relative(root, args.output, must_exist=False)

    palette = [item.strip() for item in args.palette.split(",") if item.strip()]
    lock = {
        "schema_version": SCHEMA_VERSION,
        "status": "approved",
        "approved_by": args.approved_by,
        "approval_source": args.approval_source,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "approval_note": args.approval_note,
        "draft": {
            "path": relative_posix(root, draft),
            "sha256": sha256_file(draft),
        },
        "figure_spec": {
            "path": relative_posix(root, spec),
            "sha256": sha256_file(spec),
        },
        "visual_lock": {
            "background_colors": args.background_color,
            "palette": palette,
            "style_note": args.style_note,
        },
    }
    write_json_atomic(output, lock)
    print(f"Created approved draft lock: {relative_posix(root, output)}")
    return 0


def verify_lock(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    if not root.is_dir():
        raise GateError(f"Task root does not exist: {root}")
    lock_path = resolve_relative(root, args.lock, must_exist=True)
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateError(f"Invalid lock JSON: {exc}") from exc

    if lock.get("schema_version") != SCHEMA_VERSION:
        raise GateError("Unsupported draft lock schema")
    if lock.get("status") != "approved":
        raise GateError("Draft lock status is not approved")
    if lock.get("approved_by") != "user" or lock.get("approval_source") != "chat":
        raise GateError("Draft lock does not record explicit user approval in chat")

    for key in ("draft", "figure_spec"):
        record = lock.get(key)
        if not isinstance(record, dict):
            raise GateError(f"Missing {key} lock record")
        stored_path = record.get("path")
        stored_hash = record.get("sha256")
        if not isinstance(stored_path, str) or not isinstance(stored_hash, str):
            raise GateError(f"Invalid {key} lock record")
        source = resolve_relative(root, stored_path, must_exist=True)
        actual_hash = sha256_file(source)
        if actual_hash != stored_hash:
            raise GateError(f"{key} hash changed after user approval")

    print(f"Draft lock verified: {relative_posix(root, lock_path)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a lock after explicit user approval")
    create.add_argument("--root", type=Path, required=True)
    create.add_argument("--draft", required=True, help="Draft image path relative to --root")
    create.add_argument("--spec", required=True, help="figure_spec.json path relative to --root")
    create.add_argument("--output", default="draft_lock.json")
    create.add_argument("--confirmed", action="store_true")
    create.add_argument("--approved-by", default="user")
    create.add_argument("--approval-source", default="chat")
    create.add_argument("--approval-note", default="")
    create.add_argument("--background-color", action="append", default=[])
    create.add_argument("--palette", default="")
    create.add_argument("--style-note", default="")
    create.set_defaults(handler=create_lock)

    verify = subparsers.add_parser("verify", help="Verify approval metadata and locked hashes")
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--lock", default="draft_lock.json")
    verify.set_defaults(handler=verify_lock)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.handler(args)
    except (GateError, OSError) as exc:
        print(f"Draft gate failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

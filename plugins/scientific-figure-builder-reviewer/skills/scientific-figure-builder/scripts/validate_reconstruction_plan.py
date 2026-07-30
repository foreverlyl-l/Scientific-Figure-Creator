#!/usr/bin/env python3
"""Validate the native-object and raster boundary for a reconstruction plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ACTION_BY_CLASS = {
    "native-simple-shape": {"native-shape", "native-connector"},
    "native-text": {"native-text"},
    "native-formula": {"native-formula"},
    "external-crop": {"raster-image"},
    "deferred-complex": set(),
}
OUTPUT_KEYS = ("pptx", "render_png", "layout_json")


class PlanError(ValueError):
    """Raised when the reconstruction plan violates the build contract."""


def resolve_relative(root: Path, value: str, *, must_exist: bool) -> Path:
    relative = Path(value)
    if relative.is_absolute():
        raise PlanError(f"Path must be relative to --root: {value}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PlanError(f"Path escapes --root: {value}") from exc
    if must_exist and not resolved.is_file():
        raise PlanError(f"Required file does not exist: {value}")
    return resolved


def number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise PlanError(f"{label} must be numeric")
    return float(value)


def validate_position(
    position: object,
    slide_width: float,
    slide_height: float,
    object_id: str,
) -> None:
    if not isinstance(position, dict):
        raise PlanError(f"{object_id} is missing position")
    left = number(position.get("left"), f"{object_id}.position.left")
    top = number(position.get("top"), f"{object_id}.position.top")
    width = number(position.get("width"), f"{object_id}.position.width")
    height = number(position.get("height"), f"{object_id}.position.height")
    if left < 0 or top < 0 or width <= 0 or height <= 0:
        raise PlanError(f"{object_id} has an invalid position")
    if left + width > slide_width or top + height > slide_height:
        raise PlanError(f"{object_id} extends outside the slide")


def validate(root: Path, plan_path: Path) -> None:
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PlanError(f"Invalid reconstruction plan JSON: {exc}") from exc
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        raise PlanError("Unsupported reconstruction plan schema")

    slide_size = plan.get("slide_size")
    if not isinstance(slide_size, dict):
        raise PlanError("Missing slide_size")
    slide_width = number(slide_size.get("width"), "slide_size.width")
    slide_height = number(slide_size.get("height"), "slide_size.height")
    if slide_width <= 0 or slide_height <= 0:
        raise PlanError("Slide size must be positive")

    objects = plan.get("objects")
    if not isinstance(objects, list) or not objects:
        raise PlanError("objects must be a non-empty array")
    ids: set[str] = set()
    records: dict[str, dict] = {}
    for index, item in enumerate(objects):
        if not isinstance(item, dict):
            raise PlanError(f"Object {index + 1} must be a JSON object")
        object_id = item.get("object_id")
        if not isinstance(object_id, str) or not object_id.strip() or object_id in ids:
            raise PlanError(f"Object {index + 1} has a missing or duplicate object_id")
        ids.add(object_id)
        records[object_id] = item

        source_class = item.get("source_class")
        action = item.get("action")
        if source_class not in ACTION_BY_CLASS:
            raise PlanError(f"{object_id} has an unknown source_class")
        if action not in ACTION_BY_CLASS[source_class]:
            raise PlanError(
                f"{object_id}: action {action!r} is forbidden for source_class {source_class!r}"
            )
        validate_position(item.get("position"), slide_width, slide_height, object_id)
        if action == "raster-image":
            source_path = item.get("source_path")
            if not isinstance(source_path, str):
                raise PlanError(f"{object_id} raster-image is missing source_path")
            resolve_relative(root, source_path, must_exist=True)
            if item.get("fit") not in ("contain", "cover"):
                raise PlanError(f"{object_id} raster-image must declare fit")

    for object_id, item in records.items():
        if item.get("action") != "native-connector":
            continue
        from_id = item.get("from_id")
        to_id = item.get("to_id")
        if from_id not in records or to_id not in records:
            raise PlanError(f"{object_id} references a missing connector endpoint")
        if records[from_id].get("action") == "native-connector" or records[to_id].get(
            "action"
        ) == "native-connector":
            raise PlanError(f"{object_id} cannot connect to another connector")

    outputs = plan.get("outputs")
    if not isinstance(outputs, dict):
        raise PlanError("Missing outputs")
    for key in OUTPUT_KEYS:
        value = outputs.get(key)
        if not isinstance(value, str) or not value:
            raise PlanError(f"Missing outputs.{key}")
        resolve_relative(root, value, must_exist=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--plan", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        root = args.root.resolve()
        if not root.is_dir():
            raise PlanError(f"Task root does not exist: {root}")
        plan_path = resolve_relative(root, args.plan, must_exist=True)
        validate(root, plan_path)
        print(f"Reconstruction plan validated: {plan_path.relative_to(root).as_posix()}")
        return 0
    except (OSError, PlanError) as exc:
        print(f"Reconstruction plan failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

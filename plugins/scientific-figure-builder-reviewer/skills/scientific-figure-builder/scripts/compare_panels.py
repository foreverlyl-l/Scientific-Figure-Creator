#!/usr/bin/env python3
"""Redetect, align, and compare source and rendered scientific-figure panels."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from segment_assets import (
    add_padding,
    build_foreground_mask,
    clamp_box,
    clearance_failure_reason,
    estimate_background,
    foreground_count,
    trim_to_foreground,
)


class ComparisonError(ValueError):
    """Raised when panel comparison inputs are unsafe or incomplete."""


def resolve_relative(root: Path, value: str, *, must_exist: bool) -> Path:
    relative = Path(value)
    if relative.is_absolute():
        raise ComparisonError(f"Path must be relative to --root: {value}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ComparisonError(f"Path escapes --root: {value}") from exc
    if must_exist and not resolved.is_file():
        raise ComparisonError(f"Required file does not exist: {value}")
    return resolved


def relative_posix(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def atomic_json(path: Path, value: object) -> None:
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
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temporary_name = handle.name
        os.replace(temporary_name, path)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def read_panel_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    panels = [
        row
        for row in rows
        if row.get("boundary_status") == "accepted"
        and (
            row.get("semantic_role", "").strip().lower() == "panel"
            or row.get("asset_id") == row.get("parent_panel")
        )
    ]
    if not panels:
        raise ComparisonError("Manifest contains no accepted panel rows")
    return panels


def manifest_box(row: dict[str, str]) -> tuple[int, int, int, int]:
    try:
        box = tuple(int(row[key]) for key in ("left", "top", "right", "bottom"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ComparisonError(f"Invalid bounds for {row.get('asset_id', '<unknown>')}") from exc
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ComparisonError(f"Empty bounds for {row.get('asset_id', '<unknown>')}")
    return box


def scale_box(
    box: tuple[int, int, int, int],
    source_size: tuple[int, int],
    target_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    scale_x = target_size[0] / source_size[0]
    scale_y = target_size[1] / source_size[1]
    return clamp_box(
        (
            round(box[0] * scale_x),
            round(box[1] * scale_y),
            round(box[2] * scale_x),
            round(box[3] * scale_y),
        ),
        *target_size,
    )


def detect_in_window(
    image: Image.Image,
    mask: Image.Image,
    window: tuple[int, int, int, int],
    padding: int,
    safety_margin: int,
) -> tuple[tuple[int, int, int, int] | None, str]:
    detected = trim_to_foreground(mask, window)
    if detected is None:
        return None, "no foreground detected"
    bounds = add_padding(detected, padding, *image.size)
    failure = clearance_failure_reason(mask, bounds, safety_margin, image.size)
    if foreground_count(mask, detected) == 0:
        failure = "empty foreground"
    return bounds, failure


def fit_image(image: Image.Image, width: int, height: int, background: str) -> Image.Image:
    copy = image.convert("RGB")
    copy.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), background)
    left = (width - copy.width) // 2
    top = (height - copy.height) // 2
    canvas.paste(copy, (left, top))
    return canvas


def comparison_image(
    panel_id: str,
    source_crop: Image.Image,
    render_crop: Image.Image,
    width: int,
    height: int,
) -> Image.Image:
    label_height = 36
    gap = 16
    canvas = Image.new("RGB", (width * 2 + gap, height + label_height), "#ECECEC")
    source_fit = fit_image(source_crop, width, height, "#FFFFFF")
    render_fit = fit_image(render_crop, width, height, "#FFFFFF")
    canvas.paste(source_fit, (0, label_height))
    canvas.paste(render_fit, (width + gap, label_height))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 10), f"{panel_id} | frozen source", fill="#202020")
    draw.text((width + gap + 8, 10), "PowerPoint render", fill="#202020")
    draw.line((width + gap // 2, 0, width + gap // 2, canvas.height), fill="#777777", width=2)
    return canvas


def make_contact_sheet(images: list[Image.Image], columns: int = 2) -> Image.Image:
    if not images:
        return Image.new("RGB", (800, 160), "white")
    cell_width = max(image.width for image in images)
    cell_height = max(image.height for image in images)
    rows = math.ceil(len(images) / columns)
    sheet = Image.new("RGB", (cell_width * columns, cell_height * rows), "#D8D8D8")
    for index, image in enumerate(images):
        left = (index % columns) * cell_width
        top = (index // columns) * cell_height
        sheet.paste(image, (left, top))
    return sheet


def read_decisions(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ComparisonError(f"Invalid review decisions JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ComparisonError("Review decisions must be a JSON object keyed by panel ID")
    result: dict[str, dict[str, str]] = {}
    for panel_id, decision in value.items():
        if not isinstance(decision, dict) or decision.get("status") not in (
            "approved",
            "rejected",
        ):
            raise ComparisonError(
                f"Decision for {panel_id} must have status approved or rejected"
            )
        result[str(panel_id)] = {
            "status": str(decision["status"]),
            "note": str(decision.get("note", "")),
        }
    return result


def run(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    if not root.is_dir():
        raise ComparisonError(f"Task root does not exist: {root}")
    source_path = resolve_relative(root, args.source, must_exist=True)
    render_path = resolve_relative(root, args.render, must_exist=True)
    manifest_path = resolve_relative(root, args.manifest, must_exist=True)
    output_dir = resolve_relative(root, args.output_dir, must_exist=False)
    decisions_path = (
        resolve_relative(root, args.review_decisions, must_exist=True)
        if args.review_decisions
        else None
    )

    source = Image.open(source_path).convert("RGBA")
    render = Image.open(render_path).convert("RGBA")
    source_background, source_dispersion = estimate_background(source)
    render_background, render_dispersion = estimate_background(render)
    source_threshold = max(args.threshold, source_dispersion * 3.0 + 4.0)
    render_threshold = max(args.threshold, render_dispersion * 3.0 + 4.0)
    source_mask = build_foreground_mask(source, source_background, source_threshold)
    render_mask = build_foreground_mask(render, render_background, render_threshold)
    panels = read_panel_rows(manifest_path)
    decisions = read_decisions(decisions_path)

    comparisons_dir = output_dir / "comparisons"
    comparisons_dir.mkdir(parents=True, exist_ok=True)
    panel_reports: list[dict] = []
    comparison_images: list[Image.Image] = []
    for row in panels:
        panel_id = row["asset_id"]
        source_seed = clamp_box(manifest_box(row), *source.size)
        render_seed = scale_box(source_seed, source.size, render.size)
        source_bounds, source_failure = detect_in_window(
            source, source_mask, source_seed, args.padding, args.safety_margin
        )
        render_bounds, render_failure = detect_in_window(
            render, render_mask, render_seed, args.padding, args.safety_margin
        )
        failures = [reason for reason in (source_failure, render_failure) if reason]

        source_crop = source.crop(source_bounds or source_seed)
        render_crop = render.crop(render_bounds or render_seed)
        aspect_delta = abs(
            (source_crop.width / source_crop.height)
            - (render_crop.width / render_crop.height)
        ) / max(0.0001, source_crop.width / source_crop.height)
        if aspect_delta > args.max_aspect_delta:
            failures.append(f"panel aspect-ratio delta exceeds limit: {aspect_delta:.4f}")

        decision = decisions.get(panel_id)
        if failures or (decision and decision["status"] == "rejected"):
            status = "fail"
            if decision and decision["status"] == "rejected":
                failures.append("Agent visual review rejected this panel")
        elif decision and decision["status"] == "approved":
            status = "pass"
        else:
            status = "needs-review"

        comparison = comparison_image(
            panel_id,
            source_crop,
            render_crop,
            args.panel_width,
            args.panel_height,
        )
        comparison_path = comparisons_dir / f"{panel_id}-side-by-side.png"
        comparison.save(comparison_path)
        comparison_images.append(comparison)
        panel_reports.append(
            {
                "panel_id": panel_id,
                "status": status,
                "source_seed": list(source_seed),
                "render_seed": list(render_seed),
                "source_detected_bounds": list(source_bounds) if source_bounds else None,
                "render_detected_bounds": list(render_bounds) if render_bounds else None,
                "source_threshold": source_threshold,
                "render_threshold": render_threshold,
                "aspect_ratio_delta": aspect_delta,
                "visual_review": decision or {"status": "pending", "note": ""},
                "failures": failures,
                "comparison_path": relative_posix(root, comparison_path),
            }
        )

    if args.expected_count is not None and len(panel_reports) != args.expected_count:
        reason = (
            f"expected {args.expected_count} panel comparisons but found {len(panel_reports)}"
        )
        for report in panel_reports:
            report["status"] = "fail"
            report["failures"].append(reason)

    contact_sheet = make_contact_sheet(comparison_images)
    contact_path = comparisons_dir / "contact-sheet.png"
    contact_sheet.save(contact_path)
    statuses = [report["status"] for report in panel_reports]
    overall = (
        "fail"
        if "fail" in statuses
        else "needs-review"
        if "needs-review" in statuses
        else "pass"
    )
    report_path = output_dir / "comparison_report.json"
    atomic_json(
        report_path,
        {
            "schema_version": 1,
            "status": overall,
            "source_path": relative_posix(root, source_path),
            "render_path": relative_posix(root, render_path),
            "manifest_path": relative_posix(root, manifest_path),
            "contact_sheet_path": relative_posix(root, contact_path),
            "panel_count": len(panel_reports),
            "panels": panel_reports,
        },
    )
    print(f"Panel comparison {overall}: {len(panel_reports)} panels")
    print(f"Report: {relative_posix(root, report_path)}")
    return 0 if overall == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--render", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--review-decisions")
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--threshold", type=float, default=24.0)
    parser.add_argument("--padding", type=int, default=4)
    parser.add_argument("--safety-margin", type=int, default=2)
    parser.add_argument("--max-aspect-delta", type=float, default=0.20)
    parser.add_argument("--panel-width", type=int, default=480)
    parser.add_argument("--panel-height", type=int, default=320)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.expected_count is not None and args.expected_count <= 0:
            raise ComparisonError("--expected-count must be positive")
        return run(args)
    except (ComparisonError, OSError) as exc:
        print(f"Panel comparison failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

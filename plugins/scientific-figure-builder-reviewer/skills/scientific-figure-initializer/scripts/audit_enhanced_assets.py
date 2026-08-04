#!/usr/bin/env python3
"""Audit an initializer-managed raster asset before PowerPoint replacement."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import tempfile
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from PIL import Image, ImageChops, ImageColor, ImageStat


class AuditError(ValueError):
    """Raised when an enhancement audit cannot be completed safely."""


def resolve_relative(root: Path, value: str, *, must_exist: bool) -> Path:
    relative = Path(value)
    if relative.is_absolute():
        raise AuditError(f"Path must be relative to --root: {value}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AuditError(f"Path escapes --root: {value}") from exc
    if must_exist and not resolved.is_file():
        raise AuditError(f"Required file does not exist: {value}")
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


def estimate_background(image: Image.Image) -> tuple[int, int, int]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    step_x = max(1, width // 48)
    step_y = max(1, height // 48)
    samples: list[tuple[int, int, int]] = []
    for x in range(0, width, step_x):
        samples.extend((rgb.getpixel((x, 0)), rgb.getpixel((x, height - 1))))
    for y in range(0, height, step_y):
        samples.extend((rgb.getpixel((0, y)), rgb.getpixel((width - 1, y))))
    return tuple(int(median(channel)) for channel in zip(*samples))


def color_distance(first: tuple[int, int, int], second: tuple[int, int, int]) -> float:
    return math.sqrt(sum((first[index] - second[index]) ** 2 for index in range(3)))


def foreground_mask(
    image: Image.Image, background: tuple[int, int, int], threshold: float
) -> Image.Image:
    rgba = image.convert("RGBA")
    threshold_squared = threshold * threshold
    values = []
    for red, green, blue, alpha in rgba.getdata():
        distance_squared = (
            (red - background[0]) ** 2
            + (green - background[1]) ** 2
            + (blue - background[2]) ** 2
        )
        values.append(255 if alpha > 16 and distance_squared > threshold_squared else 0)
    mask = Image.new("L", rgba.size)
    mask.putdata(values)
    return mask


def normalized_mask(mask: Image.Image, size: int = 256) -> Image.Image:
    return mask.resize((size, size), Image.Resampling.NEAREST).point(
        lambda value: 255 if value >= 128 else 0
    )


def count_white(mask: Image.Image) -> int:
    histogram = mask.histogram()
    return histogram[255]


def silhouette_iou(first: Image.Image, second: Image.Image) -> float:
    first_normalized = normalized_mask(first)
    second_normalized = normalized_mask(second)
    intersection = count_white(ImageChops.multiply(first_normalized, second_normalized))
    union = count_white(ImageChops.lighter(first_normalized, second_normalized))
    return 1.0 if union == 0 else intersection / union


def foreground_coverage(mask: Image.Image) -> float:
    return count_white(mask) / max(1, mask.width * mask.height)


def foreground_mean(image: Image.Image, mask: Image.Image) -> tuple[float, float, float]:
    stats = ImageStat.Stat(image.convert("RGB"), mask=mask)
    return tuple(float(value) for value in stats.mean[:3])


def connected_component_count(mask: Image.Image, size: int = 128) -> int:
    normalized = normalized_mask(mask, size=size)
    pixels = bytearray(normalized.tobytes())
    visited = bytearray(len(pixels))
    components = 0
    for index, value in enumerate(pixels):
        if not value or visited[index]:
            continue
        queue: deque[int] = deque([index])
        visited[index] = 1
        area = 0
        while queue:
            current = queue.popleft()
            area += 1
            x = current % size
            y = current // size
            for next_x, next_y in (
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1),
            ):
                if not (0 <= next_x < size and 0 <= next_y < size):
                    continue
                neighbor = next_y * size + next_x
                if pixels[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    queue.append(neighbor)
        if area >= 3:
            components += 1
    return components


def parse_locked_background(value: str | None) -> tuple[int, int, int] | None:
    if value is None:
        return None
    try:
        return ImageColor.getrgb(value)[:3]
    except ValueError as exc:
        raise AuditError(f"Invalid locked background color: {value}") from exc


def run(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    if not root.is_dir():
        raise AuditError(f"Task root does not exist: {root}")
    original_path = resolve_relative(root, args.original, must_exist=True)
    enhanced_path = resolve_relative(root, args.enhanced, must_exist=True)
    output_dir = resolve_relative(root, args.output_dir, must_exist=False)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        original = Image.open(original_path).convert("RGBA")
        enhanced = Image.open(enhanced_path).convert("RGBA")
        original.load()
        enhanced.load()
    except (OSError, ValueError) as exc:
        raise AuditError(f"Unreadable image input: {exc}") from exc

    original_background = estimate_background(original)
    enhanced_background = estimate_background(enhanced)
    locked_background = parse_locked_background(args.locked_background)
    original_mask = foreground_mask(original, original_background, args.mask_threshold)
    enhanced_mask = foreground_mask(enhanced, enhanced_background, args.mask_threshold)

    original_aspect = original.width / original.height
    enhanced_aspect = enhanced.width / enhanced.height
    aspect_delta = abs(original_aspect - enhanced_aspect) / original_aspect
    iou = silhouette_iou(original_mask, enhanced_mask)
    original_coverage = foreground_coverage(original_mask)
    enhanced_coverage = foreground_coverage(enhanced_mask)
    coverage_delta = abs(original_coverage - enhanced_coverage)
    background_delta = color_distance(original_background, enhanced_background)
    locked_background_delta = (
        color_distance(enhanced_background, locked_background)
        if locked_background is not None
        else None
    )
    original_mean = foreground_mean(original, original_mask)
    enhanced_mean = foreground_mean(enhanced, enhanced_mask)
    palette_delta = math.sqrt(
        sum((original_mean[index] - enhanced_mean[index]) ** 2 for index in range(3))
    ) / math.sqrt(3 * 255**2)
    original_components = connected_component_count(original_mask)
    enhanced_components = connected_component_count(enhanced_mask)
    component_delta = abs(original_components - enhanced_components)

    failures: list[str] = []
    warnings: list[str] = []
    if args.asset_kind == "scientific-evidence" and args.method != "deterministic":
        failures.append("generative enhancement is forbidden for scientific evidence")
    if enhanced.width < original.width or enhanced.height < original.height:
        failures.append("enhanced image has lower pixel dimensions than the original")
    if aspect_delta > args.max_aspect_delta:
        failures.append(f"aspect-ratio delta exceeds limit: {aspect_delta:.4f}")
    if iou < args.min_silhouette_iou:
        failures.append(f"silhouette IoU below limit: {iou:.4f}")
    elif iou < args.warn_silhouette_iou:
        warnings.append(f"silhouette IoU needs review: {iou:.4f}")
    if coverage_delta > args.max_coverage_delta:
        failures.append(f"foreground coverage delta exceeds limit: {coverage_delta:.4f}")
    if background_delta > args.max_background_delta:
        failures.append(f"background color delta exceeds limit: {background_delta:.2f}")
    elif background_delta > args.warn_background_delta:
        warnings.append(f"background color delta needs review: {background_delta:.2f}")
    if (
        locked_background_delta is not None
        and locked_background_delta > args.max_background_delta
    ):
        failures.append(
            f"enhanced background differs from locked color: {locked_background_delta:.2f}"
        )
    if palette_delta > args.max_palette_delta:
        failures.append(f"foreground palette delta exceeds limit: {palette_delta:.4f}")
    elif palette_delta > args.warn_palette_delta:
        warnings.append(f"foreground palette delta needs review: {palette_delta:.4f}")
    allowed_component_delta = max(1, math.ceil(original_components * 0.5))
    if component_delta > allowed_component_delta:
        failures.append(
            f"connected-component count changed from {original_components} "
            f"to {enhanced_components}"
        )

    if failures or args.visual_review == "rejected":
        status = "fail"
        if args.visual_review == "rejected":
            failures.append("Agent visual review rejected the enhanced asset")
    elif warnings or args.visual_review == "pending":
        status = "needs-review"
    else:
        status = "pass"

    approved_path: Path | None = None
    if status == "pass":
        approved_dir = output_dir / "approved_assets"
        approved_dir.mkdir(parents=True, exist_ok=True)
        approved_path = approved_dir / f"{args.asset_id}.png"
        shutil.copy2(enhanced_path, approved_path)

    report = {
        "schema_version": 1,
        "asset_id": args.asset_id,
        "status": status,
        "asset_kind": args.asset_kind,
        "enhancement_method": args.method,
        "visual_review": args.visual_review,
        "visual_review_note": args.visual_review_note,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "original_path": relative_posix(root, original_path),
        "enhanced_candidate_path": relative_posix(root, enhanced_path),
        "approved_replacement_path": (
            relative_posix(root, approved_path) if approved_path is not None else ""
        ),
        "replacement_policy": {
            "preserve_original": True,
            "preserve_frame": True,
            "preserve_crop": True,
            "preserve_fit": True,
            "auto_reinsert_allowed": status == "pass",
        },
        "metrics": {
            "original_size": list(original.size),
            "enhanced_size": list(enhanced.size),
            "aspect_ratio_delta": aspect_delta,
            "silhouette_iou": iou,
            "foreground_coverage_original": original_coverage,
            "foreground_coverage_enhanced": enhanced_coverage,
            "foreground_coverage_delta": coverage_delta,
            "background_original_rgb": list(original_background),
            "background_enhanced_rgb": list(enhanced_background),
            "background_delta": background_delta,
            "locked_background_rgb": (
                list(locked_background) if locked_background is not None else None
            ),
            "locked_background_delta": locked_background_delta,
            "foreground_palette_delta": palette_delta,
            "connected_components_original": original_components,
            "connected_components_enhanced": enhanced_components,
        },
        "warnings": warnings,
        "failures": failures,
    }
    atomic_json(output_dir / "enhancement_report.json", report)
    atomic_json(
        output_dir / "replacement_manifest.json",
        {
            "schema_version": 1,
            "asset_id": args.asset_id,
            "status": status,
            "original_path": relative_posix(root, original_path),
            "replacement_path": (
                relative_posix(root, approved_path) if approved_path is not None else ""
            ),
            "preserve_frame": True,
            "preserve_crop": True,
            "preserve_fit": True,
        },
    )
    print(f"Enhancement audit {status}: {args.asset_id}")
    print(f"Report: {relative_posix(root, output_dir / 'enhancement_report.json')}")
    return 0 if status == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--original", required=True)
    parser.add_argument("--enhanced", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--asset-kind",
        choices=("explanatory-illustration", "scientific-evidence"),
        required=True,
    )
    parser.add_argument(
        "--method", choices=("deterministic", "generative"), required=True
    )
    parser.add_argument(
        "--visual-review",
        choices=("pending", "approved", "rejected"),
        default="pending",
    )
    parser.add_argument("--visual-review-note", default="")
    parser.add_argument("--locked-background")
    parser.add_argument("--mask-threshold", type=float, default=24.0)
    parser.add_argument("--max-aspect-delta", type=float, default=0.01)
    parser.add_argument("--min-silhouette-iou", type=float, default=0.72)
    parser.add_argument("--warn-silhouette-iou", type=float, default=0.85)
    parser.add_argument("--max-coverage-delta", type=float, default=0.12)
    parser.add_argument("--max-background-delta", type=float, default=18.0)
    parser.add_argument("--warn-background-delta", type=float, default=8.0)
    parser.add_argument("--max-palette-delta", type=float, default=0.35)
    parser.add_argument("--warn-palette-delta", type=float, default=0.18)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return run(args)
    except (AuditError, OSError) as exc:
        print(f"Enhancement audit failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Detect initializer-managed content boundaries, crop assets, and write manifests."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Iterable

from PIL import Image, ImageColor, ImageDraw


MANIFEST_FIELDS = (
    "asset_id",
    "parent_panel",
    "semantic_role",
    "asset_class",
    "left",
    "top",
    "right",
    "bottom",
    "width",
    "height",
    "source_path",
    "output_path",
    "canonical_id",
    "boundary_method",
    "boundary_confidence",
    "boundary_status",
    "notes",
)
REPORT_FIELDS = (
    "asset_id",
    "search_window",
    "detected_content_bounds",
    "final_bounds",
    "foreground_pixels",
    "background_rgb",
    "effective_threshold",
    "confidence",
    "status",
    "failure_reason",
)
ALLOWED_CLASSES = {
    "native-simple-shape",
    "native-text",
    "native-formula",
    "external-crop",
    "deferred-complex",
}


class SegmentationError(ValueError):
    """Raised when input configuration cannot be processed safely."""


@dataclass
class Seed:
    asset_id: str
    parent_panel: str
    semantic_role: str
    asset_class: str
    search_window: tuple[int, int, int, int]
    canonical_id: str
    notes: str


@dataclass
class Detection:
    asset_id: str
    search_window: tuple[int, int, int, int]
    detected_content_bounds: tuple[int, int, int, int] | None
    final_bounds: tuple[int, int, int, int] | None
    foreground_pixels: int
    background_rgb: tuple[int, int, int]
    effective_threshold: float
    confidence: float
    status: str
    failure_reason: str


def resolve_relative(root: Path, value: str, *, must_exist: bool) -> Path:
    relative = Path(value)
    if relative.is_absolute():
        raise SegmentationError(f"Path must be relative to --root: {value}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SegmentationError(f"Path escapes --root: {value}") from exc
    if must_exist and not resolved.is_file():
        raise SegmentationError(f"Required file does not exist: {value}")
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


def atomic_csv(path: Path, fields: Iterable[str], rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fields))
            writer.writeheader()
            writer.writerows(rows)
            temporary_name = handle.name
        os.replace(temporary_name, path)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def parse_color(value: str | None) -> tuple[int, int, int] | None:
    if value is None:
        return None
    try:
        color = ImageColor.getrgb(value)
    except ValueError as exc:
        raise SegmentationError(f"Invalid background color: {value}") from exc
    return color[:3]


def border_samples(image: Image.Image) -> list[tuple[int, int, int]]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    step_x = max(1, width // 64)
    step_y = max(1, height // 64)
    samples: list[tuple[int, int, int]] = []
    for x in range(0, width, step_x):
        samples.append(rgb.getpixel((x, 0)))
        samples.append(rgb.getpixel((x, height - 1)))
    for y in range(0, height, step_y):
        samples.append(rgb.getpixel((0, y)))
        samples.append(rgb.getpixel((width - 1, y)))
    return samples


def estimate_background(image: Image.Image) -> tuple[tuple[int, int, int], float]:
    samples = border_samples(image)
    background = tuple(int(median(channel)) for channel in zip(*samples))
    distances = [
        math.sqrt(sum((sample[index] - background[index]) ** 2 for index in range(3)))
        for sample in samples
    ]
    dispersion = float(median(distances))
    return background, dispersion


def build_foreground_mask(
    image: Image.Image,
    background: tuple[int, int, int],
    threshold: float,
) -> Image.Image:
    rgba = image.convert("RGBA")
    mask_data = []
    threshold_squared = threshold * threshold
    for red, green, blue, alpha in rgba.getdata():
        distance_squared = (
            (red - background[0]) ** 2
            + (green - background[1]) ** 2
            + (blue - background[2]) ** 2
        )
        foreground = alpha > 16 and distance_squared > threshold_squared
        mask_data.append(255 if foreground else 0)
    mask = Image.new("L", rgba.size)
    mask.putdata(mask_data)
    return mask


def clamp_box(
    box: tuple[int, int, int, int], width: int, height: int
) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    return (
        max(0, min(width, left)),
        max(0, min(height, top)),
        max(0, min(width, right)),
        max(0, min(height, bottom)),
    )


def valid_box(box: tuple[int, int, int, int]) -> bool:
    return box[2] > box[0] and box[3] > box[1]


def foreground_count(mask: Image.Image, box: tuple[int, int, int, int]) -> int:
    return sum(1 for value in mask.crop(box).getdata() if value)


def trim_to_foreground(
    mask: Image.Image, search_window: tuple[int, int, int, int]
) -> tuple[int, int, int, int] | None:
    local = mask.crop(search_window)
    local_box = local.getbbox()
    if local_box is None:
        return None
    return (
        search_window[0] + local_box[0],
        search_window[1] + local_box[1],
        search_window[0] + local_box[2],
        search_window[1] + local_box[3],
    )


def add_padding(
    box: tuple[int, int, int, int],
    padding: int,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    return clamp_box(
        (box[0] - padding, box[1] - padding, box[2] + padding, box[3] + padding),
        width,
        height,
    )


def margin_has_foreground(
    mask: Image.Image, box: tuple[int, int, int, int], margin: int
) -> bool:
    if margin <= 0:
        return False
    left, top, right, bottom = box
    bands = (
        (left, top, right, min(bottom, top + margin)),
        (left, max(top, bottom - margin), right, bottom),
        (left, top, min(right, left + margin), bottom),
        (max(left, right - margin), top, right, bottom),
    )
    return any(valid_box(band) and mask.crop(band).getbbox() is not None for band in bands)


def clearance_failure_reason(
    mask: Image.Image,
    box: tuple[int, int, int, int],
    safety_margin: int,
    image_size: tuple[int, int],
) -> str:
    if not margin_has_foreground(mask, box, safety_margin):
        return ""
    width, height = image_size
    edges = []
    if box[0] == 0:
        edges.append("left")
    if box[1] == 0:
        edges.append("top")
    if box[2] == width:
        edges.append("right")
    if box[3] == height:
        edges.append("bottom")
    if edges:
        return f"foreground touches image edge without clearance: {','.join(edges)}"
    return "foreground touches crop safety margin"


def projection(mask: Image.Image, box: tuple[int, int, int, int], axis: str) -> list[int]:
    cropped = mask.crop(box)
    width, height = cropped.size
    pixels = cropped.load()
    if axis == "x":
        return [sum(1 for y in range(height) if pixels[x, y]) for x in range(width)]
    return [sum(1 for x in range(width) if pixels[x, y]) for y in range(height)]


def gutter_runs(values: list[int], maximum: int, minimum_length: int) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(values + [maximum + 1]):
        if value <= maximum and start is None:
            start = index
        elif value > maximum and start is not None:
            if index - start >= minimum_length:
                runs.append((start, index))
            start = None
    return runs


def best_gutter_split(
    mask: Image.Image,
    box: tuple[int, int, int, int],
    min_gutter: int,
    min_region: int,
) -> tuple[str, int, float] | None:
    width = box[2] - box[0]
    height = box[3] - box[1]
    candidates: list[tuple[str, int, float]] = []
    for axis, length, orthogonal in (("x", width, height), ("y", height, width)):
        values = projection(mask, box, axis)
        maximum = max(0, int(orthogonal * 0.002))
        for start, end in gutter_runs(values, maximum, min_gutter):
            if start < min_region or length - end < min_region:
                continue
            center = (start + end) // 2
            score = (end - start) / max(1, length)
            candidates.append((axis, center, score))
    return max(candidates, key=lambda item: item[2]) if candidates else None


def split_by_gutters(
    mask: Image.Image,
    box: tuple[int, int, int, int],
    min_gutter: int,
    min_region: int,
    depth: int = 0,
) -> list[tuple[int, int, int, int]]:
    if depth >= 8:
        return [box]
    split = best_gutter_split(mask, box, min_gutter, min_region)
    if split is None:
        return [box]
    axis, offset, _score = split
    if axis == "x":
        children = (
            (box[0], box[1], box[0] + offset, box[3]),
            (box[0] + offset, box[1], box[2], box[3]),
        )
    else:
        children = (
            (box[0], box[1], box[2], box[1] + offset),
            (box[0], box[1] + offset, box[2], box[3]),
        )
    result: list[tuple[int, int, int, int]] = []
    for child in children:
        trimmed = trim_to_foreground(mask, child)
        if trimmed is not None:
            result.extend(split_by_gutters(mask, trimmed, min_gutter, min_region, depth + 1))
    return result or [box]


def parse_window(value: object, image_size: tuple[int, int]) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4 or not all(
        isinstance(item, int) for item in value
    ):
        raise SegmentationError("Each search_window must contain four integer coordinates")
    box = clamp_box(tuple(value), *image_size)
    if not valid_box(box):
        raise SegmentationError(f"Invalid search_window: {value}")
    return box


def load_seeds(
    root: Path,
    seed_path: Path | None,
    image_size: tuple[int, int],
    auto_boxes: list[tuple[int, int, int, int]],
) -> list[Seed]:
    if seed_path is None:
        sorted_boxes = sorted(auto_boxes, key=lambda box: (box[1], box[0]))
        return [
            Seed(
                asset_id=f"panel-{index}",
                parent_panel=f"panel-{index}",
                semantic_role="panel",
                asset_class="external-crop",
                search_window=box,
                canonical_id=f"panel-{index}",
                notes="Automatically proposed panel; final bounds redetected from foreground",
            )
            for index, box in enumerate(sorted_boxes, start=1)
        ]

    try:
        raw = json.loads(seed_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SegmentationError(f"Invalid seed JSON: {exc}") from exc
    if not isinstance(raw, list) or not raw:
        raise SegmentationError("Seed manifest must be a non-empty JSON array")

    seeds: list[Seed] = []
    seen: set[str] = set()
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise SegmentationError(f"Seed {index} must be an object")
        asset_id = str(item.get("asset_id", "")).strip()
        if not asset_id or asset_id in seen:
            raise SegmentationError(f"Seed {index} has a missing or duplicate asset_id")
        seen.add(asset_id)
        asset_class = str(item.get("asset_class", "external-crop"))
        if asset_class not in ALLOWED_CLASSES:
            raise SegmentationError(f"Seed {asset_id} has invalid asset_class")
        seeds.append(
            Seed(
                asset_id=asset_id,
                parent_panel=str(item.get("parent_panel", asset_id)),
                semantic_role=str(item.get("semantic_role", "")),
                asset_class=asset_class,
                search_window=parse_window(item.get("search_window"), image_size),
                canonical_id=str(item.get("canonical_id", asset_id)),
                notes=str(item.get("notes", "")),
            )
        )
    return seeds


def boxes_overlap(
    first: tuple[int, int, int, int], second: tuple[int, int, int, int]
) -> bool:
    return (
        min(first[2], second[2]) > max(first[0], second[0])
        and min(first[3], second[3]) > max(first[1], second[1])
    )


def report_row(detection: Detection) -> dict:
    data = asdict(detection)
    for key in ("search_window", "detected_content_bounds", "final_bounds", "background_rgb"):
        value = data[key]
        data[key] = "" if value is None else ",".join(str(item) for item in value)
    data["confidence"] = f"{detection.confidence:.4f}"
    data["effective_threshold"] = f"{detection.effective_threshold:.2f}"
    return data


def run(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    if not root.is_dir():
        raise SegmentationError(f"Task root does not exist: {root}")
    image_path = resolve_relative(root, args.image, must_exist=True)
    output_dir = resolve_relative(root, args.output_dir, must_exist=False)
    seed_path = (
        resolve_relative(root, args.seeds, must_exist=True) if args.seeds is not None else None
    )

    image = Image.open(image_path).convert("RGBA")
    width, height = image.size
    supplied_background = parse_color(args.background)
    estimated_background, dispersion = estimate_background(image)
    background = supplied_background or estimated_background
    effective_threshold = max(args.threshold, dispersion * 3.0 + 4.0)
    mask = build_foreground_mask(image, background, effective_threshold)
    full_content = mask.getbbox()
    auto_boxes = (
        split_by_gutters(mask, full_content, args.min_gutter, args.min_region)
        if full_content is not None
        else []
    )
    seeds = load_seeds(root, seed_path, image.size, auto_boxes)

    detections: list[Detection] = []
    for seed in seeds:
        detected = trim_to_foreground(mask, seed.search_window)
        if detected is None:
            detections.append(
                Detection(
                    seed.asset_id,
                    seed.search_window,
                    None,
                    None,
                    0,
                    background,
                    effective_threshold,
                    0.0,
                    "failed",
                    "no foreground detected",
                )
            )
            continue
        count = foreground_count(mask, detected)
        final_bounds = add_padding(detected, args.padding, width, height)
        failure = ""
        if count < args.min_foreground:
            failure = f"foreground pixel count below minimum: {count}"
        if not failure:
            failure = clearance_failure_reason(
                mask, final_bounds, args.safety_margin, image.size
            )
        density = count / max(1, (detected[2] - detected[0]) * (detected[3] - detected[1]))
        confidence = min(
            1.0,
            0.55
            + 0.20 * min(1.0, count / max(1, args.min_foreground * 8))
            + 0.15 * min(1.0, density / 0.20)
            + (0.10 if not failure else 0.0),
        )
        if not failure and confidence < args.min_confidence:
            failure = f"confidence below threshold: {confidence:.4f}"
        detections.append(
            Detection(
                seed.asset_id,
                seed.search_window,
                detected,
                final_bounds,
                count,
                background,
                effective_threshold,
                confidence,
                "failed" if failure else "accepted",
                failure,
            )
        )

    accepted = [item for item in detections if item.status == "accepted"]
    for index, first in enumerate(accepted):
        for second in accepted[index + 1 :]:
            if first.final_bounds and second.final_bounds and boxes_overlap(
                first.final_bounds, second.final_bounds
            ):
                reason = f"unresolved overlap with {second.asset_id}"
                first.status = "failed"
                first.failure_reason = reason
                second.status = "failed"
                second.failure_reason = f"unresolved overlap with {first.asset_id}"

    if args.expected_count is not None and len(seeds) != args.expected_count:
        mismatch = f"expected {args.expected_count} regions but detected/configured {len(seeds)}"
        for item in detections:
            item.status = "failed"
            item.failure_reason = mismatch

    output_dir.mkdir(parents=True, exist_ok=True)
    crops_dir = output_dir / "cropped_assets"
    crops_dir.mkdir(parents=True, exist_ok=True)
    seed_by_id = {seed.asset_id: seed for seed in seeds}
    manifest_rows: list[dict] = []
    for detection in detections:
        seed = seed_by_id[detection.asset_id]
        output_path = crops_dir / f"{seed.canonical_id}.png"
        if detection.status == "accepted" and detection.final_bounds is not None:
            image.crop(detection.final_bounds).save(output_path)
            stored_output = relative_posix(root, output_path)
        else:
            stored_output = ""
        bounds = detection.final_bounds or (0, 0, 0, 0)
        manifest_rows.append(
            {
                "asset_id": seed.asset_id,
                "parent_panel": seed.parent_panel,
                "semantic_role": seed.semantic_role,
                "asset_class": seed.asset_class,
                "left": bounds[0],
                "top": bounds[1],
                "right": bounds[2],
                "bottom": bounds[3],
                "width": bounds[2] - bounds[0],
                "height": bounds[3] - bounds[1],
                "source_path": relative_posix(root, image_path),
                "output_path": stored_output,
                "canonical_id": seed.canonical_id,
                "boundary_method": (
                    "pillow-background-mask+seed-snap"
                    if seed_path is not None
                    else "pillow-background-mask+projection-gutters"
                ),
                "boundary_confidence": f"{detection.confidence:.4f}",
                "boundary_status": detection.status,
                "notes": (
                    seed.notes
                    if not detection.failure_reason
                    else f"{seed.notes}; {detection.failure_reason}".strip("; ")
                ),
            }
        )

    atomic_csv(output_dir / "asset_manifest.csv", MANIFEST_FIELDS, manifest_rows)
    atomic_json(
        output_dir / "boundary_report.json",
        {
            "schema_version": 1,
            "source_path": relative_posix(root, image_path),
            "background_rgb": list(background),
            "background_dispersion": dispersion,
            "effective_threshold": effective_threshold,
            "expected_count": args.expected_count,
            "detections": [asdict(item) for item in detections],
        },
    )
    atomic_csv(
        output_dir / "boundary_report.csv",
        REPORT_FIELDS,
        [report_row(item) for item in detections],
    )

    overlay = image.convert("RGB")
    draw = ImageDraw.Draw(overlay)
    for index, detection in enumerate(detections, start=1):
        box = detection.final_bounds or detection.search_window
        color = "#1B9E77" if detection.status == "accepted" else "#D62728"
        draw.rectangle(box, outline=color, width=3)
        draw.text((box[0] + 4, box[1] + 4), f"{index}:{detection.asset_id}", fill=color)
    overlay.save(output_dir / "boundary_overlay.png")

    failed = [item for item in detections if item.status != "accepted"]
    print(
        f"Boundary detection complete: {len(detections) - len(failed)} accepted, "
        f"{len(failed)} failed"
    )
    print(f"Evidence directory: {relative_posix(root, output_dir)}")
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--image", required=True, help="Source image relative to --root")
    parser.add_argument("--output-dir", required=True, help="Output directory relative to --root")
    parser.add_argument("--seeds", help="Optional JSON seed manifest relative to --root")
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--background", help="Known background color")
    parser.add_argument("--threshold", type=float, default=24.0)
    parser.add_argument("--padding", type=int, default=8)
    parser.add_argument("--safety-margin", type=int, default=3)
    parser.add_argument("--min-foreground", type=int, default=24)
    parser.add_argument("--min-confidence", type=float, default=0.60)
    parser.add_argument("--min-gutter", type=int, default=12)
    parser.add_argument("--min-region", type=int, default=32)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.expected_count is not None and args.expected_count <= 0:
            raise SegmentationError("--expected-count must be positive")
        for name in ("padding", "safety_margin", "min_foreground", "min_gutter", "min_region"):
            if getattr(args, name) < 0:
                raise SegmentationError(f"--{name.replace('_', '-')} must be non-negative")
        return run(args)
    except (SegmentationError, OSError) as exc:
        print(f"Segmentation failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

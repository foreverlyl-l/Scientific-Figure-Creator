from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = (
    ROOT
    / "plugins"
    / "scientific-figure-builder-reviewer"
    / "skills"
    / "scientific-figure-builder"
    / "scripts"
)
DRAFT_GATE = SCRIPT_DIR / "draft_gate.py"
SEGMENT_ASSETS = SCRIPT_DIR / "segment_assets.py"


def run_script(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


class DraftGateTests(unittest.TestCase):
    def test_requires_confirmation_and_detects_hash_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            Image.new("RGB", (80, 40), "white").save(root / "draft.png")
            (root / "figure_spec.json").write_text(
                json.dumps({"schema_version": 1, "figure_id": "test"}),
                encoding="utf-8",
            )

            denied = run_script(
                DRAFT_GATE,
                "create",
                "--root",
                str(root),
                "--draft",
                "draft.png",
                "--spec",
                "figure_spec.json",
            )
            self.assertNotEqual(denied.returncode, 0)
            self.assertIn("Explicit user confirmation is required", denied.stdout)

            created = run_script(
                DRAFT_GATE,
                "create",
                "--root",
                str(root),
                "--draft",
                "draft.png",
                "--spec",
                "figure_spec.json",
                "--confirmed",
                "--background-color",
                "#FFFFFF",
            )
            self.assertEqual(created.returncode, 0, created.stdout + created.stderr)

            verified = run_script(
                DRAFT_GATE,
                "verify",
                "--root",
                str(root),
                "--lock",
                "draft_lock.json",
            )
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)

            (root / "figure_spec.json").write_text(
                json.dumps({"schema_version": 1, "figure_id": "changed"}),
                encoding="utf-8",
            )
            changed = run_script(
                DRAFT_GATE,
                "verify",
                "--root",
                str(root),
                "--lock",
                "draft_lock.json",
            )
            self.assertNotEqual(changed.returncode, 0)
            self.assertIn("hash changed", changed.stdout)


class SegmentAssetsTests(unittest.TestCase):
    @staticmethod
    def make_four_panel_image(path: Path, background: tuple[int, int, int]) -> None:
        image = Image.new("RGB", (800, 600), background)
        draw = ImageDraw.Draw(image)
        panels = (
            (40, 40, 360, 260, "#235789"),
            (440, 40, 760, 260, "#F1D302"),
            (40, 340, 360, 560, "#C1292E"),
            (440, 340, 760, 560, "#3A7D44"),
        )
        for left, top, right, bottom, color in panels:
            draw.rectangle((left, top, right, bottom), fill=color)
        image.save(path)

    def test_auto_detects_four_panels_and_writes_required_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_four_panel_image(root / "figure.png", (246, 246, 242))
            result = run_script(
                SEGMENT_ASSETS,
                "--root",
                str(root),
                "--image",
                "figure.png",
                "--output-dir",
                "segmentation",
                "--expected-count",
                "4",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            output = root / "segmentation"
            self.assertTrue((output / "boundary_overlay.png").is_file())
            self.assertTrue((output / "boundary_report.json").is_file())
            self.assertTrue((output / "boundary_report.csv").is_file())
            with (output / "asset_manifest.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(row["boundary_status"] == "accepted" for row in rows))
            self.assertTrue(all(not Path(row["source_path"]).is_absolute() for row in rows))
            self.assertTrue(all(not Path(row["output_path"]).is_absolute() for row in rows))

    def test_seed_window_is_snapped_to_foreground(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = Image.new("RGB", (300, 200), "#FAFAF8")
            ImageDraw.Draw(image).rectangle((90, 60, 180, 130), fill="#245B78")
            image.save(root / "figure.png")
            (root / "seeds.json").write_text(
                json.dumps(
                    [
                        {
                            "asset_id": "panel-1-device",
                            "parent_panel": "panel-1",
                            "semantic_role": "device",
                            "asset_class": "external-crop",
                            "search_window": [40, 20, 230, 170],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            result = run_script(
                SEGMENT_ASSETS,
                "--root",
                str(root),
                "--image",
                "figure.png",
                "--output-dir",
                "segmentation",
                "--seeds",
                "seeds.json",
                "--expected-count",
                "1",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with (root / "segmentation" / "asset_manifest.csv").open(
                encoding="utf-8", newline=""
            ) as handle:
                row = next(csv.DictReader(handle))
            self.assertGreater(int(row["left"]), 40)
            self.assertGreater(int(row["top"]), 20)
            self.assertLess(int(row["right"]), 230)
            self.assertLess(int(row["bottom"]), 170)

    def test_count_mismatch_and_edge_contact_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_four_panel_image(root / "figure.png", (255, 255, 255))
            mismatch = run_script(
                SEGMENT_ASSETS,
                "--root",
                str(root),
                "--image",
                "figure.png",
                "--output-dir",
                "mismatch",
                "--expected-count",
                "3",
            )
            self.assertNotEqual(mismatch.returncode, 0)

            edge = Image.new("RGB", (200, 120), "white")
            ImageDraw.Draw(edge).rectangle((0, 20, 80, 100), fill="black")
            edge.save(root / "edge.png")
            edge_result = run_script(
                SEGMENT_ASSETS,
                "--root",
                str(root),
                "--image",
                "edge.png",
                "--output-dir",
                "edge-output",
                "--expected-count",
                "1",
            )
            self.assertNotEqual(edge_result.returncode, 0)
            report = json.loads(
                (root / "edge-output" / "boundary_report.json").read_text(encoding="utf-8")
            )
            self.assertIn("image edge", report["detections"][0]["failure_reason"])


if __name__ == "__main__":
    unittest.main()

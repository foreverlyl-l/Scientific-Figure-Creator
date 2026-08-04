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
    / "scientific-figure-initializer"
    / "scripts"
)
DRAFT_GATE = SCRIPT_DIR / "draft_gate.py"
SEGMENT_ASSETS = SCRIPT_DIR / "segment_assets.py"
VALIDATE_RECONSTRUCTION = SCRIPT_DIR / "validate_reconstruction_plan.py"
AUDIT_ENHANCED = SCRIPT_DIR / "audit_enhanced_assets.py"
COMPARE_PANELS = SCRIPT_DIR / "compare_panels.py"
SKILLS_DIR = ROOT / "plugins" / "scientific-figure-builder-reviewer" / "skills"


def run_script(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


class SkillRoleTests(unittest.TestCase):
    def test_three_role_names_and_invocations_are_distinct(self) -> None:
        expected = {
            "scientific-figure-initializer",
            "scientific-figure-builder",
            "scientific-figure-reviewer",
        }
        found = {path.name for path in SKILLS_DIR.iterdir() if path.is_dir()}
        self.assertEqual(found, expected)

        for name in expected:
            skill_text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
            agent_text = (SKILLS_DIR / name / "agents" / "openai.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn(f"name: {name}", skill_text)
            self.assertIn(f"${name}", agent_text)

        initializer = SKILLS_DIR / "scientific-figure-initializer"
        self.assertTrue((initializer / "scripts" / "draft_gate.py").is_file())
        self.assertTrue((initializer / "references" / "whole-first-workflow.md").is_file())

        builder_text = (SKILLS_DIR / "scientific-figure-builder" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("staged reconstruction", builder_text)
        self.assertNotIn("name: ppt-shape-recreate-review", builder_text)

        reviewer_agent = (
            SKILLS_DIR / "scientific-figure-reviewer" / "agents" / "openai.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", reviewer_agent)


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

    def test_auto_detects_three_and_six_panels_on_textured_background(self) -> None:
        for count in (3, 6):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                width = count * 150 + 20
                image = Image.new("RGB", (width, 160), "#F8F8F6")
                pixels = image.load()
                for y in range(image.height):
                    for x in range(image.width):
                        delta = (x + y) % 3
                        pixels[x, y] = (248 + delta, 248 + delta, 246 + delta)
                draw = ImageDraw.Draw(image)
                for index in range(count):
                    left = 20 + index * 150
                    draw.rectangle(
                        (left, 30, left + 110, 130),
                        fill=(35 + index * 8, 90, 120),
                    )
                image.save(root / "figure.png")
                result = run_script(
                    SEGMENT_ASSETS,
                    "--root",
                    str(root),
                    "--image",
                    "figure.png",
                    "--output-dir",
                    "segmentation",
                    "--expected-count",
                    str(count),
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                with (root / "segmentation" / "asset_manifest.csv").open(
                    encoding="utf-8", newline=""
                ) as handle:
                    self.assertEqual(len(list(csv.DictReader(handle))), count)


class ReconstructionPlanTests(unittest.TestCase):
    def test_native_raster_boundary_and_connector_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            Image.new("RGB", (40, 40), "#245B78").save(assets / "device.png")
            plan = {
                "schema_version": 1,
                "slide_size": {"width": 800, "height": 450},
                "objects": [
                    {
                        "object_id": "node-1",
                        "semantic_role": "source",
                        "source_class": "native-simple-shape",
                        "action": "native-shape",
                        "position": {"left": 20, "top": 40, "width": 120, "height": 60},
                    },
                    {
                        "object_id": "node-2",
                        "semantic_role": "target",
                        "source_class": "external-crop",
                        "action": "raster-image",
                        "source_path": "assets/device.png",
                        "fit": "contain",
                        "position": {"left": 260, "top": 40, "width": 120, "height": 60},
                    },
                    {
                        "object_id": "edge-1",
                        "semantic_role": "flow",
                        "source_class": "native-simple-shape",
                        "action": "native-connector",
                        "from_id": "node-1",
                        "to_id": "node-2",
                        "position": {"left": 140, "top": 69, "width": 120, "height": 1},
                    },
                ],
                "outputs": {
                    "pptx": "deliverables/figure.pptx",
                    "render_png": "render/figure.png",
                    "layout_json": "render/figure.layout.json",
                },
            }
            (root / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            valid = run_script(
                VALIDATE_RECONSTRUCTION,
                "--root",
                str(root),
                "--plan",
                "plan.json",
            )
            self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)

            plan["objects"][0]["action"] = "raster-image"
            plan["objects"][0]["source_path"] = "assets/device.png"
            plan["objects"][0]["fit"] = "contain"
            (root / "invalid.json").write_text(json.dumps(plan), encoding="utf-8")
            invalid = run_script(
                VALIDATE_RECONSTRUCTION,
                "--root",
                str(root),
                "--plan",
                "invalid.json",
            )
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("forbidden", invalid.stdout)


class EnhancedAssetAuditTests(unittest.TestCase):
    @staticmethod
    def make_original(path: Path) -> Image.Image:
        image = Image.new("RGB", (100, 100), "white")
        ImageDraw.Draw(image).rounded_rectangle(
            (25, 20, 75, 80), radius=8, fill="#245B78"
        )
        image.save(path)
        return image

    def test_pass_requires_agent_visual_approval_and_preserves_original(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = self.make_original(root / "original.png")
            original.resize((200, 200), Image.Resampling.NEAREST).save(
                root / "enhanced.png"
            )

            pending = run_script(
                AUDIT_ENHANCED,
                "--root",
                str(root),
                "--asset-id",
                "device-1",
                "--original",
                "original.png",
                "--enhanced",
                "enhanced.png",
                "--output-dir",
                "pending",
                "--asset-kind",
                "explanatory-illustration",
                "--method",
                "deterministic",
            )
            self.assertNotEqual(pending.returncode, 0)
            pending_report = json.loads(
                (root / "pending" / "enhancement_report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(pending_report["status"], "needs-review")
            self.assertFalse(pending_report["replacement_policy"]["auto_reinsert_allowed"])

            approved = run_script(
                AUDIT_ENHANCED,
                "--root",
                str(root),
                "--asset-id",
                "device-1",
                "--original",
                "original.png",
                "--enhanced",
                "enhanced.png",
                "--output-dir",
                "approved",
                "--asset-kind",
                "explanatory-illustration",
                "--method",
                "deterministic",
                "--visual-review",
                "approved",
                "--locked-background",
                "#FFFFFF",
            )
            self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
            report = json.loads(
                (root / "approved" / "enhancement_report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["status"], "pass")
            self.assertTrue(report["replacement_policy"]["auto_reinsert_allowed"])
            self.assertTrue(
                (root / report["approved_replacement_path"]).is_file()
            )
            self.assertTrue((root / "original.png").is_file())

    def test_rejects_shape_background_aspect_and_evidence_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_original(root / "original.png")
            changed = Image.new("RGB", (260, 180), "#D0D0D0")
            draw = ImageDraw.Draw(changed)
            draw.ellipse((20, 20, 130, 150), fill="#D62728")
            draw.rectangle((180, 30, 230, 80), fill="#111111")
            changed.save(root / "changed.png")

            result = run_script(
                AUDIT_ENHANCED,
                "--root",
                str(root),
                "--asset-id",
                "evidence-1",
                "--original",
                "original.png",
                "--enhanced",
                "changed.png",
                "--output-dir",
                "failed",
                "--asset-kind",
                "scientific-evidence",
                "--method",
                "generative",
                "--visual-review",
                "approved",
                "--locked-background",
                "#FFFFFF",
            )
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(
                (root / "failed" / "enhancement_report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["status"], "fail")
            joined = " ".join(report["failures"])
            self.assertIn("scientific evidence", joined)
            self.assertIn("aspect-ratio", joined)
            self.assertEqual(report["approved_replacement_path"], "")


class PanelComparisonTests(unittest.TestCase):
    def test_four_panel_end_to_end_requires_visual_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            SegmentAssetsTests.make_four_panel_image(
                root / "source.png", (246, 246, 242)
            )
            source = Image.open(root / "source.png").convert("RGB")
            render = source.resize((1200, 900), Image.Resampling.NEAREST)
            render.save(root / "render.png")

            segmented = run_script(
                SEGMENT_ASSETS,
                "--root",
                str(root),
                "--image",
                "source.png",
                "--output-dir",
                "segmentation",
                "--expected-count",
                "4",
            )
            self.assertEqual(segmented.returncode, 0, segmented.stdout + segmented.stderr)

            pending = run_script(
                COMPARE_PANELS,
                "--root",
                str(root),
                "--source",
                "source.png",
                "--render",
                "render.png",
                "--manifest",
                "segmentation/asset_manifest.csv",
                "--output-dir",
                "comparison-pending",
                "--expected-count",
                "4",
            )
            self.assertNotEqual(pending.returncode, 0)
            pending_report = json.loads(
                (root / "comparison-pending" / "comparison_report.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(pending_report["status"], "needs-review")
            self.assertEqual(pending_report["panel_count"], 4)
            self.assertTrue(
                (root / "comparison-pending" / "comparisons" / "contact-sheet.png").is_file()
            )
            self.assertTrue(
                all(
                    (root / panel["comparison_path"]).is_file()
                    for panel in pending_report["panels"]
                )
            )

            decisions = {
                f"panel-{index}": {
                    "status": "approved",
                    "note": "Panel meaning and layout match the frozen source.",
                }
                for index in range(1, 5)
            }
            (root / "decisions.json").write_text(
                json.dumps(decisions), encoding="utf-8"
            )
            approved = run_script(
                COMPARE_PANELS,
                "--root",
                str(root),
                "--source",
                "source.png",
                "--render",
                "render.png",
                "--manifest",
                "segmentation/asset_manifest.csv",
                "--output-dir",
                "comparison-approved",
                "--review-decisions",
                "decisions.json",
                "--expected-count",
                "4",
            )
            self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
            approved_report = json.loads(
                (root / "comparison-approved" / "comparison_report.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(approved_report["status"], "pass")
            self.assertTrue(
                all(panel["status"] == "pass" for panel in approved_report["panels"])
            )


if __name__ == "__main__":
    unittest.main()

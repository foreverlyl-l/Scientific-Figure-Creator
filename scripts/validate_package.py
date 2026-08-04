#!/usr/bin/env python3
"""Validate the open-source skill-only plugin package."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml


SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FORBIDDEN_TEXT = (
    "BEGIN " + "RSA PRIVATE KEY",
    "BEGIN " + "OPENSSH PRIVATE KEY",
    "BEGIN " + "EC PRIVATE KEY",
    "\ufffd",
    "\u9225",
)
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:\\")


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Invalid JSON at {path}: {exc}")


def load_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        fail(f"Invalid YAML at {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"Expected a YAML mapping at {path}")
    return data


def parse_frontmatter(skill_md: Path) -> tuple[dict, str]:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(f"{skill_md} must start with YAML frontmatter")
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        fail(f"{skill_md} has malformed YAML frontmatter")
    metadata = yaml.safe_load(parts[1])
    if not isinstance(metadata, dict):
        fail(f"{skill_md} frontmatter must be a mapping")
    if set(metadata) != {"name", "description"}:
        fail(f"{skill_md} frontmatter must contain only name and description")
    return metadata, parts[2]


def validate_skill(skill_dir: Path) -> str:
    skill_md = skill_dir / "SKILL.md"
    agents_yaml = skill_dir / "agents" / "openai.yaml"
    if not skill_md.is_file():
        fail(f"Missing {skill_md}")
    if not agents_yaml.is_file():
        fail(f"Missing {agents_yaml}")

    metadata, body = parse_frontmatter(skill_md)
    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(name, str) or not SKILL_NAME.fullmatch(name):
        fail(f"Invalid skill name in {skill_md}: {name!r}")
    if name != skill_dir.name:
        fail(f"Skill folder {skill_dir.name!r} does not match name {name!r}")
    if not isinstance(description, str) or not description.strip():
        fail(f"Missing skill description in {skill_md}")
    if not body.strip():
        fail(f"Missing skill instructions in {skill_md}")

    agents = load_yaml(agents_yaml)
    interface = agents.get("interface")
    if not isinstance(interface, dict):
        fail(f"Missing interface mapping in {agents_yaml}")
    for key in ("display_name", "short_description", "default_prompt"):
        if not isinstance(interface.get(key), str) or not interface[key].strip():
            fail(f"Missing interface.{key} in {agents_yaml}")
    if f"${name}" not in interface["default_prompt"]:
        fail(f"default_prompt in {agents_yaml} must reference ${name}")

    if name == "scientific-figure-reviewer":
        policy = agents.get("policy")
        if not isinstance(policy, dict) or policy.get("allow_implicit_invocation") is not False:
            fail("The final-review skill must keep allow_implicit_invocation: false")

    for relative_ref in re.findall(r"`(references/[^`]+)`", body):
        target = skill_dir / relative_ref
        if not target.is_file():
            fail(f"Missing referenced file: {target}")

    return name


def scan_text_files(root: Path) -> None:
    excluded_parts = {".git", "dist", "__pycache__"}
    extensions = {".md", ".yaml", ".yml", ".json", ".py", ".gitignore"}
    for path in root.rglob("*"):
        if not path.is_file() or excluded_parts.intersection(path.parts):
            continue
        if path.suffix.lower() not in extensions and path.name != ".gitignore":
            continue
        text = path.read_text(encoding="utf-8")
        if WINDOWS_ABSOLUTE_PATH.search(text):
            fail(f"Machine-specific Windows path found in {path}")
        for marker in FORBIDDEN_TEXT:
            if marker in text:
                fail(f"Forbidden local or corrupted marker {marker!r} in {path}")


def validate(root: Path, expected_version: str | None) -> None:
    plugin_dir = root / "plugins" / "scientific-figure-builder-reviewer"
    plugin_json = plugin_dir / ".codex-plugin" / "plugin.json"
    marketplace_json = root / ".agents" / "plugins" / "marketplace.json"
    plugin = load_json(plugin_json)
    marketplace = load_json(marketplace_json)

    if plugin.get("name") != plugin_dir.name:
        fail("Plugin manifest name does not match its directory")
    version = plugin.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        fail(f"Invalid plugin version: {version!r}")
    if expected_version and version != expected_version:
        fail(f"Tag version {expected_version!r} does not match plugin version {version!r}")
    if plugin.get("skills") != "./skills/":
        fail("Plugin manifest must expose ./skills/")
    if plugin.get("license") != "MIT":
        fail("Plugin manifest and repository license must remain MIT")
    if not (root / "LICENSE").is_file():
        fail("Missing repository LICENSE")

    readme_zh = root / "README.md"
    readme_en = root / "README_EN.md"
    if not readme_zh.is_file() or not readme_en.is_file():
        fail("Both README.md and README_EN.md are required")
    if 'href="./README_EN.md"' not in readme_zh.read_text(encoding="utf-8"):
        fail("README.md must link to README_EN.md")
    if 'href="./README.md"' not in readme_en.read_text(encoding="utf-8"):
        fail("README_EN.md must link to README.md")

    entries = marketplace.get("plugins")
    if not isinstance(entries, list) or len(entries) != 1:
        fail("Marketplace must contain exactly one plugin entry")
    entry = entries[0]
    source = entry.get("source")
    if entry.get("name") != plugin["name"] or not isinstance(source, dict):
        fail("Marketplace plugin entry does not match plugin manifest")
    source_path = source.get("path")
    if source.get("source") != "local" or not isinstance(source_path, str):
        fail("Marketplace source must be a local relative path")
    if (root / source_path).resolve() != plugin_dir.resolve():
        fail("Marketplace source path does not resolve to the packaged plugin")

    skills_dir = plugin_dir / "skills"
    found = sorted(validate_skill(path) for path in skills_dir.iterdir() if path.is_dir())
    expected = [
        "scientific-figure-builder",
        "scientific-figure-initializer",
        "scientific-figure-reviewer",
    ]
    if found != expected:
        fail(f"Expected skills {expected}, found {found}")

    scan_text_files(root)
    print(f"Package validation passed: {plugin['name']} {version}")
    print(f"Skills: {', '.join(found)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expected-version")
    args = parser.parse_args()
    try:
        validate(args.root.resolve(), args.expected_version)
    except (OSError, ValueError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

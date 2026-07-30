# Contributing

Contributions are welcome.

## Principles

- Preserve user edits and keep reconstruction output maximally editable.
- Do not weaken the strict simple-shape whitelist or fail-closed acceptance gates without documented evidence.
- Do not automatically invoke or suggest `scientific-figure-reviewer`; it must remain explicit-only and read-only by default.
- Keep reference images, PPTX outputs, generated renders, credentials, and machine-specific paths out of the repository.
- Prefer concise skill instructions and move detailed checklists into `references/`.

## Validation

Before opening a change, validate both skills and the plugin:

```powershell
python -m pip install PyYAML==6.0.2
python scripts/validate_package.py
```

The GitHub workflow runs the same repository-level validation automatically.

Also confirm that:

- every relative reference in a `SKILL.md` resolves;
- `agents/openai.yaml` prompts use the correct `$skill-name`;
- no absolute local paths or private data are present;
- Markdown and YAML render without encoding corruption;
- the final-review skill still has `allow_implicit_invocation: false`.

## Releases

Use semantic versioning in `.codex-plugin/plugin.json`. Update documentation when behavior or invocation boundaries change.

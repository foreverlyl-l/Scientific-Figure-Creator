# Whole-First Scientific Figure Workflow

## Contents

1. Route and required gates
2. Semantic specification
3. Whole-image draft and human freeze
4. Automatic boundary detection
5. PowerPoint reconstruction
6. Controlled raster enhancement
7. Source/render comparison
8. Failure rules and deliverables

## 1. Route and Required Gates

Use this route when a task needs a new first draft, automatic cropping, enhanced complex illustrations, or matched source/render evidence.

Execute the stages in this order:

1. Write `figure_spec.json`.
2. Generate one complete draft image.
3. Review every semantic block.
4. Review the whole-figure meaning and reading order.
5. Show the accepted draft and review summary to the user.
6. Wait for an explicit user confirmation in chat.
7. Create and verify `draft_lock.json`.
8. Detect boundaries and crop assets.
9. Rebuild the figure in PowerPoint.
10. Enhance only eligible complex raster assets.
11. Audit and reinsert passing enhanced assets.
12. Render the deck and compare matching panels.
13. Repeat block and whole-figure review.

Do not combine or reorder gates 3–7. A passing model review is not human approval.

## 2. Semantic Specification

Treat `figure_spec.json` as the semantic source of truth. Use relative paths and stable IDs.

Minimum shape:

```json
{
  "schema_version": 1,
  "figure_id": "figure-1",
  "canvas": {
    "width": 1600,
    "height": 900,
    "background": "#F7F7F5"
  },
  "panels": [
    {
      "id": "panel-1",
      "role": "input-and-preprocessing",
      "reading_order": 1,
      "nodes": [],
      "text": [],
      "formulas": [],
      "edges": [],
      "semantic_constraints": []
    }
  ],
  "global_edges": [],
  "style": {
    "palette": [],
    "line_style": "",
    "illustration_style": "",
    "generation_backend": "<user-selected backend>"
  }
}
```

Record every required label, formula, node, input, output, directed edge, legend, and reading-order constraint. Do not encode decorative details as semantic requirements unless they carry meaning.

## 3. Whole-Image Draft and Human Freeze

Before any draft generation or generative enhancement, show the user the image-generation routes that are actually available in the current runtime and ask them to select one. State the relevant provider, cost/privacy implications when known, reference-image support, and batch behavior. Do not set a default choice and do not interpret silence as consent. Record whether the user's selection covers only the draft, only enhancement, or the entire run; ask again when the recorded scope does not cover the next generation step.

Use native `imagegen` only after the user selects it. Use `baoyu-image-gen` only when the user explicitly names that skill or explicitly selects it after the provider and batch implications are presented. It is not a generic fallback. If the selected backend fails, report the failure and ask before switching to another backend.

Generate the entire figure in one image. The generation prompt must include the semantic specification, full canvas ratio, background, shared palette, shared line treatment, shared illustration style, and the intended empty space for PowerPoint-native labels.

Review in two levels:

- `block review`: verify each panel's nodes, labels, formulas, edge directions, inputs, outputs, and local ordering.
- `whole review`: verify panel order, cross-panel edges, global reading direction, legend meaning, color semantics, and narrative continuity.

If a local semantic error can be isolated, edit the whole draft with a mask and rerun both reviews. If the overall flow or composition is wrong, regenerate the whole draft and rerun both reviews.

After both reviews pass, request an explicit user confirmation. Do not infer confirmation from silence or from an earlier general request to continue.

After confirmation, create the lock:

```text
python scripts/draft_gate.py create \
  --root <task-output-root> \
  --draft <relative-draft-path> \
  --spec figure_spec.json \
  --output draft_lock.json \
  --confirmed \
  --background-color "#F7F7F5" \
  --palette "#245B78,#63A69F,#F2C14E" \
  --style-note "flat scientific editorial illustration"
```

Run `verify` immediately before segmentation and again before final comparison:

```text
python scripts/draft_gate.py verify \
  --root <task-output-root> \
  --lock draft_lock.json
```

The lock is invalid if the draft or specification hash changes.

## 4. Automatic Boundary Detection

Use `scripts/segment_assets.py`. Human or agent observation may provide:

- semantic IDs and labels;
- rough search windows;
- an optional expected panel count;
- an optional known panel background.

It may not provide final authoritative crop bounds.

The detector must:

1. Estimate the local background from border and corner samples unless supplied.
2. Create a foreground mask from alpha and RGB color distance.
3. Locate content with projection profiles and connected components.
4. Merge nearby components and snap each rough seed to detected content.
5. add configurable padding;
6. expand until foreground no longer touches the safety margin;
7. clamp bounds to the image;
8. calculate confidence and emit evidence.

Required outputs:

- cropped PNG files;
- `asset_manifest.csv`;
- `boundary_report.json`;
- `boundary_report.csv`;
- `boundary_overlay.png`.

Fail closed on empty foreground, invalid bounds, unresolved overlaps, an explicit count mismatch, low confidence, or foreground touching an image edge without clearance. Adjust seeds or thresholds and rerun; never bypass detection.

## 5. PowerPoint Reconstruction

Use the installed Presentations skill and read its Artifact Tool documentation before coding.

Create a task-local JavaScript ES module and use `@oai/artifact-tool`:

- add text, formulas, borders, color fields, and standard shapes as editable native objects;
- use native connectors for arrows and relationships;
- create connectors before nodes when practical so edges remain behind entities;
- add only approved `external-crop` and complex assets as byte-backed PNG images;
- preserve manifest positions, fit mode, crop, and z-order;
- export the PPTX and a full-slide PNG render;
- run overflow, overlap, clipping, wrapping, connector, and unresolved-placeholder checks.

Never use Python to draw or modify the presentation. Never use an absolute machine-specific path in committed skill resources.

## 6. Controlled Raster Enhancement

Enhance only `external-crop` or approved complex raster assets. Never generatively alter experimental evidence, measured plots, microscopy, radiology, or other scientific evidence. Those assets may receive only deterministic, non-generative resampling unless the user supplies an explicit scientifically valid method.

For an eligible explanatory illustration, provide:

- the original crop;
- a context crop containing its surrounding background;
- the frozen whole draft as the style reference;
- the original bounds and edge mask;
- the locked background sample and palette.

Lock object count, silhouette, pose, perspective, composition, palette, outline, lighting, shadow, and background. Prohibit new labels, symbols, decoration, objects, or changed scientific meaning.

Prefer deterministic resizing first. Use reference-guided generation only when resizing is insufficient, the asset is not scientific evidence, and the user has explicitly selected the generation backend for that enhancement run.

Run `scripts/audit_enhanced_assets.py`. Reinsert only a `pass` result. Preserve the original on `needs-review` or `fail`; ask the user only when the workflow cannot resolve the failure safely.

First run the audit with `--visual-review pending`. Inspect the original and enhanced assets at full size, then rerun with `--visual-review approved` or `--visual-review rejected` and a short note. The script creates an approved copy and permits automatic reinsertion only when the metrics have no failures or warnings and the Agent review is approved.

```text
python scripts/audit_enhanced_assets.py \
  --root <task-output-root> \
  --asset-id <stable-asset-id> \
  --original <relative-original-path> \
  --enhanced <relative-enhanced-path> \
  --output-dir <relative-audit-directory> \
  --asset-kind explanatory-illustration \
  --method deterministic \
  --visual-review approved \
  --visual-review-note "<what was inspected>" \
  --locked-background "#F7F7F5"
```

Use `--asset-kind scientific-evidence` for measured or experimental imagery. The script rejects a generative method for that class.

For flat backgrounds, normalize the enhanced border to the exact locked RGB or make the background transparent before insertion.

## 7. Source/Render Comparison

Render the final slide, then run `scripts/compare_panels.py` with:

- the frozen draft or accepted reference;
- the final slide render;
- the panel segmentation manifest.

The comparison script must redetect the corresponding panel bounds, align panel sizes without distortion, and write:

- one `comparisons/<panel-id>-side-by-side.png` per panel;
- `comparisons/contact-sheet.png`;
- `comparison_report.json`.

Inspect every comparison at full size. A contact sheet is for overview only. Resolve `needs-review` panels before reporting completion.

## 8. Failure Rules and Deliverables

Stop the workflow when:

- explicit user confirmation is absent;
- a lock hash changes;
- boundary detection fails;
- an enhanced asset fails its audit;
- the PowerPoint render has unintended overlap, clipping, broken connectors, or unresolved placeholders;
- a panel comparison remains unresolved.

Deliver, as applicable:

- editable PPTX;
- frozen draft and semantic specification;
- lock record;
- canonical cropped assets;
- asset and boundary manifests;
- enhancement audit;
- rendered slide;
- panel comparison images and report;
- construction review report.

Do not invoke the separate `scientific-figure-reviewer` unless the user explicitly requests that independent final audit.

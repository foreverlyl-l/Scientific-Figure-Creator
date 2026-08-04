# Scientific Figure Initializer: Artifact Tool Reconstruction Contract

## Purpose

Use this contract after semantic segmentation and draft-lock verification. It keeps PowerPoint construction task-specific while making the native-object/raster boundary machine-checkable.

Do not bundle one universal figure generator. Create a task-local ES module because scientific figures have different objects, formulas, connector routes, and z-order requirements.

## Required Inputs

Create `reconstruction_plan.json` under the task output root. Use relative paths only.

```json
{
  "schema_version": 1,
  "slide_size": {"width": 1600, "height": 900},
  "objects": [
    {
      "object_id": "panel-1-frame",
      "semantic_role": "panel boundary",
      "source_class": "native-simple-shape",
      "action": "native-shape",
      "position": {"left": 40, "top": 80, "width": 340, "height": 700}
    },
    {
      "object_id": "panel-1-title",
      "semantic_role": "panel heading",
      "source_class": "native-text",
      "action": "native-text",
      "text": "Input",
      "position": {"left": 60, "top": 96, "width": 180, "height": 40}
    },
    {
      "object_id": "panel-1-device",
      "semantic_role": "explanatory device illustration",
      "source_class": "external-crop",
      "action": "raster-image",
      "source_path": "segmentation/cropped_assets/panel-1-device.png",
      "fit": "contain",
      "crop": {"left": 0, "top": 0, "right": 0, "bottom": 0},
      "position": {"left": 90, "top": 190, "width": 210, "height": 180}
    },
    {
      "object_id": "flow-1",
      "semantic_role": "directed process flow",
      "source_class": "native-simple-shape",
      "action": "native-connector",
      "from_id": "panel-1-frame",
      "to_id": "panel-2-frame",
      "position": {"left": 380, "top": 400, "width": 80, "height": 1}
    }
  ],
  "outputs": {
    "pptx": "deliverables/figure.pptx",
    "render_png": "render/figure.png",
    "layout_json": "render/figure.layout.json"
  }
}
```

Run:

```text
python scripts/validate_reconstruction_plan.py \
  --root <task-output-root> \
  --plan reconstruction_plan.json
```

The validator enforces unique IDs, in-slide frames, existing connector endpoints, relative paths, existing raster inputs, and the following mapping:

| Source class | Allowed action |
|---|---|
| `native-simple-shape` | `native-shape`, `native-connector` |
| `native-text` | `native-text` |
| `native-formula` | `native-formula` |
| `external-crop` | `raster-image` |
| `deferred-complex` | no insertion until explicitly approved as an external crop |

## Environment

Read the installed Presentations skill and its current Artifact Tool documentation. Locate its workspace setup helper at runtime; do not commit a machine-specific path.

Create a writable task work directory and initialize it:

```text
node "<presentations-skill-dir>/container_tools/setup_artifact_tool_workspace.mjs" \
  --workspace "<task-work-dir>"
```

Write `rebuild_figure.mjs` in that task work directory. Use JavaScript ES modules without TypeScript-only syntax.

## Construction Order

1. Verify `draft_lock.json`.
2. Validate `reconstruction_plan.json`.
3. Create the `Presentation` with the specified slide size.
4. Add background fields, panel frames, and connector routes.
5. Add entity shapes above connectors.
6. Add native text and formulas.
7. Add approved byte-backed PNG assets.
8. Apply exact z-order, fit, crop, and frame values.
9. Export the slide render and layout JSON.
10. Export the PPTX.
11. Run the Presentations skill's overflow test and inspect the render at full size.

## Artifact Tool Calls

Use current documented APIs:

```js
import fs from "node:fs/promises";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const presentation = Presentation.create({
  slideSize: { width: plan.slide_size.width, height: plan.slide_size.height },
});
const slide = presentation.slides.add();

const node = slide.shapes.add({
  geometry: "roundRect",
  name: "encoder-node",
  position: { left: 120, top: 180, width: 220, height: 90 },
  fill: "#E8F1F5",
  line: { style: "solid", fill: "#245B78", width: 2 },
});
node.text = "Encoder";

slide.shapes.connect(node, targetNode, {
  kind: "elbow",
  fromSide: "right",
  toSide: "left",
  line: { style: "solid", fill: "#245B78", width: 2 },
  head: { type: "arrow", width: "med", length: "med" },
});

const bytes = await fs.readFile(assetPath);
slide.images.add({
  blob: bytes,
  contentType: "image/png",
  alt: "Traceable complex scientific illustration",
  fit: "contain",
  crop: { left: 0, top: 0, right: 0, bottom: 0 },
  position: { left: 420, top: 180, width: 260, height: 210 },
});

const render = await presentation.export({ slide, format: "png", scale: 1 });
await fs.writeFile(renderPath, new Uint8Array(await render.arrayBuffer()));
const layout = await slide.export({ format: "layout" });
await fs.writeFile(layoutPath, await layout.text());
const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(pptxPath);
```

Use `slide.shapes.connect`, not a line plus triangle. Embed raster assets from bytes with a declared content type and alt text.

## Render Gate

Do not deliver on successful export alone.

- Render every final slide.
- Inspect each slide at full size.
- Run the Presentations skill's slide overflow checker.
- Resolve unintended overlaps, clipping, wrapping, broken connectors, unresolved placeholders, raster seams, and mismatched crop/fit.
- Verify that each `reconstruction_plan.json` object has one corresponding native object or approved raster placement.
- Write the final object IDs, classes, actions, and render evidence to the construction report.

If a required native object was flattened into a raster or a complex object was inserted without approval, fail the reconstruction gate.

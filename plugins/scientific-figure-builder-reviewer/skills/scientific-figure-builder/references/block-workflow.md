# Scientific Figure Builder: Block Workflow Reference

## Segmentation Table

Use a table like this while working:

| Block ID | Reference role | Slide location | Status | Notes |
| --- | --- | --- | --- | --- |
| panel-1 | synchronized window inputs | left panel | framed / filling / review | process, alarms, pressure, acoustic |
| panel-3-film | modality encoding and FiLM conditioning | middle panel | framed / filling / review | dashed conditioning arrows and encoders |

Statuses: `unstarted`, `framed`, `classified`, `filling`, `needs-review`, `accepted`, `deferred`.

Use these statuses as a fail-closed gate:

- `accepted` means every visible object in the block has an object-inventory entry, passed a rendered visual review, and is either an allowed native object or an explicitly approved external crop.
- `needs-review` means any object is unclassified, visually unverified, or potentially approximated.
- `deferred` means one or more complex objects are intentionally not completed; a deferred block must not be reported as fully completed.
- A title/text check, a surrounding frame, or a generic placeholder is never sufficient for `accepted`.

## Atomic Asset Segmentation and Deduplication

Segment hierarchically: first identify blocks, then decompose each block into the smallest meaningful reusable assets before cropping or drawing.

Use an asset manifest like this:

| Atomic Asset ID | Parent Block | Role | Source Bounds | Canonical ID | Placement | Grouping Reason |
| --- | --- | --- | --- | --- | --- | --- |
| panel-2-icon-visual | panel-2 | visual-measurement icon | x1,y1,x2,y2 | asset-visual-icon | instance-1 | split from adjacent label and arrow |
| panel-2-label-visual | panel-2 | label | x1,y1,x2,y2 | asset-label-visual | instance-1 | independent text |
| panel-4-arrow-input-1 | panel-4 | input relation | x1,y1,x2,y2 | asset-input-arrow | instance-1 | independent connector |

Rules:

- Split a composite material whenever its children have independent bounds, roles, or reuse value.
- Split `arrow + text + image` composites into separate arrow, text, and image assets when the parts can be separated cleanly.
- Split two or more side-by-side icons when each icon is independently meaningful.
- Keep a composite together only when separation destroys identity, removes essential context, or cuts through inseparable pixels; record that reason in the manifest.
- Give each atomic asset a stable child ID and record its parent block, bounds, semantic role, relationships, and intended placement.
- Deduplicate only after atomic segmentation. Use visual similarity plus semantic equivalence; visual similarity alone is not enough.
- Keep one canonical crop for exact or near-duplicate assets with the same meaning. Map all aliases and source instances to that canonical ID.
- Preserve intentional repetition as separate placement records that reuse one canonical asset. Do not create duplicate crop files for repeated instances.
- Before inserting an asset, check whether the same or a near-identical asset already occupies that target position. Never stack duplicates or near-duplicates in one placement.
- Do not collapse similar-looking assets that have different meanings, labels, directions, states, or source roles.

## Object Classification Table

| Object | Class | Native PPT approach | Defer reason |
| --- | --- | --- | --- |
| rectangles, rounded rectangles, straight lines, arrows, circles, dots, small bars, tables, dashed boxes, simple axes, simple colored cells | simple-shape | direct composition from the listed standard PPT shapes only | any custom geometry, two or more curves, or non-trivial multi-color tile/block assembly |
| mini axis plot | complex-icon unless it is only a simple axis and explicitly allowed cells/lines | use an external crop or defer; do not draw dense curves or signal/noise as a substitute | dense signal/noise, two or more curves, or unclear fidelity |
| equipment rendering | complex-icon | external crop or defer; never use a generic placeholder as the finished object | detailed or realistic rendering is not safely shape-composable |
| h-prime labels | formula | native equation or copied equation object | if no good equation source |

Unknown or borderline objects default to `complex-icon` and `deferred`; do not promote them to `simple-shape` without explicit evidence that they fit the whitelist.

## Semantic Review Checklist

Check these before discussing visual polish:

- Panel order and titles match the reference.
- Number badges and section labels identify the same stages.
- Inputs, outputs, and cross-panel arrows point in the same direction.
- Dashed lines, solid lines, and colored flows preserve their distinct meanings.
- Legends and color encodings still explain the same quantities.
- Expert/module labels are distinct when the reference distinguishes them.
- Formula symbols, primes, subscripts, superscripts, Greek letters, and loss/logit labels are correct.
- Shape-composed icons do not imply a different operation than the reference.
- Intentionally blank/unfinished complex icons are not mistaken for finished drawings.
- Every visible reference object has an object-inventory action: native, external crop, or deferred with a reason.
- Every separable composite material has atomic child entries, or a recorded reason for remaining grouped.
- Every exact or near-duplicate asset resolves to one canonical asset with alias and placement records.
- Intentional repeated instances preserve the reference count and positions without duplicate crop files or stacked placements.
- No forbidden approximation is present: no sparkline for a dense plot, generic box for equipment, custom cube/geometry outside the whitelist, or generic symbols replacing distinct source icons.
- The rendered block was checked against the corresponding reference crop; text presence alone does not pass review.

## Deletion Rule

If an attempted native drawing is misleading, remove it and document it as deferred. Do not keep a bad icon simply because it took time to draw.

If an object cannot be classified confidently or the visual review cannot verify it, fail closed: leave it deferred and keep the block at `needs-review` or `deferred` rather than accepting an approximation.

## Stage Report Template

```text
Checkpoint: <commit hash or no new changes>

Semantic Gaps:
1. <block>: <issue and why it changes meaning>

Acceptance Gate:
- <block>: accepted / needs-review / deferred; include the rendered-review evidence and object-inventory status

Completed Native Blocks:
- <block>: <simple shapes/text/formulas completed>

Deferred Items:
- <block>: <complex icon/formula description>

External Crops:
- <block>: <asset path under the final PPT's sibling cropped_assets/ folder, or none>

Asset Decomposition:
- <block>: <atomic child IDs and any justified composite assets>

Deduplication:
- Canonical asset: <ID and file>; aliases: <IDs>; intentional placements: <locations>; removed duplicates: <count>
- Stacked or excess similar assets found: none / <details>

Ignored Differences:
- Minor stroke width, spacing, exact plot noise, and non-semantic color variance were ignored.
```

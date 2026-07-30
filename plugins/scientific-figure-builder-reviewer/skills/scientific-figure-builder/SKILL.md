---
name: scientific-figure-builder
description: Build or recreate scientific figures as editable PowerPoint objects from a written brief, rough sketch, generated whole-figure draft, or reference image. Use when Codex needs to generate one visually continuous first draft, review block and whole-figure semantics, obtain explicit human approval before freezing the draft, automatically detect and crop complex assets, reconstruct text/shapes/formulas/connectors with PowerPoint-native objects, enhance selected raster illustrations under shape/style/background locks, deduplicate repeated assets, and validate matching source/rendered regions.
---

# Scientific Figure Builder

## Route Selection

- If the task needs a new visual draft, use the whole-first route. Read `references/whole-first-workflow.md` before generating anything.
- Generate the first draft as one complete image. Never generate independent panel drafts and assemble them as the first draft.
- Before draft generation or generative asset enhancement, ask the user which available image-generation backend to use. Do not select a provider by default and do not silently switch providers after a failure.
- Review block semantics and then whole-figure semantics. Obtain an explicit user confirmation in chat before freezing the draft or starting segmentation.
- If the user supplies an accepted reference image, keep it as the visual source and use the existing reconstruction route below. Use the whole-first reference whenever the task also requests automatic boundary detection, draft freezing, asset enhancement, or source/render panel comparisons.
- Use `scripts/draft_gate.py` to create and verify the machine-readable freeze record. Never write an approval record before the user confirms.

## Core Rule

Treat the task as a staged reconstruction, not a one-shot drawing. Preserve user edits first, segment hierarchically before drawing, split separable composite materials into atomic assets, deduplicate the asset library before placement, classify before filling, and review by semantic equivalence rather than pixel-perfect similarity unless the user explicitly asks for pixel-level matching. Use two review levels: trigger a block-level review before each region is marked complete, then run a final whole-figure review after all regions are complete.

When editing an existing user-touched deck, create a Git checkpoint before any overwrite or automated modification. Prefer PowerPoint-native operations for `.pptx` edits when prior XML/zip rewrites have caused corruption.

## Separate Final Audit

The block-level and whole-figure reviews in this workflow are mandatory and self-contained. `$scientific-figure-reviewer` is a separate read-only audit that may run only when the user explicitly invokes it or explicitly requests that distinct audit. Never chain or suggest it automatically from this workflow.

## Fail-Closed Completion Gate

- Never mark a block complete merely because its frame, title, or expected text exists.
- Maintain an object inventory for every reference block. Every visible object or semantic unit must be assigned exactly one action: `native-simple-shape`, `native-text`, `native-formula`, `external-crop`, or `deferred-complex`.
- If any object is unclassified, approximated, represented by a generic placeholder, or missing an action and reason, the block status must remain `needs-review` or `deferred`, never `accepted`.
- A placeholder is a review marker only. It is not a completed object and must not be used as a semantic substitute for a complex icon, dense plot, equipment rendering, or custom diagram.
- When classification or fidelity is uncertain, default to `deferred-complex`; do not guess or fill the gap.
- `accepted` is allowed only after the block-level visual review confirms that every reference object is either correctly completed with an allowed native object or covered by an explicitly approved external crop, with no forbidden approximation.

## Workflow

1. Segment the reference image semantically.
   - When the whole-first route is active, verify `draft_lock.json` before this step. Stop if confirmation is absent or either locked hash has changed.
   - Run `scripts/segment_assets.py` for every crop. Human observations may supply labels and rough search windows, but never final crop bounds.
   - Identify top-level regions: panels, subpanels, headers, legends, pipelines, feedback paths, grouped icons, formulas, and cross-panel arrows.
   - Assign stable block IDs such as `panel-1`, `panel-2-top-chart`, `panel-4-moe`, `panel-5-rule-mask`.
   - Record each block's role in the figure, not just its coordinates.
   - After top-level segmentation, inspect every block for separable sub-assets and split it again to the smallest meaningful reusable parts. Do not keep a composite crop when its parts have independent bounds or roles.
   - Split combinations such as `arrow + text + image` into separate arrow, text, and image assets when they can be separated without destroying meaning. Split two or more side-by-side icons into individual icon assets when each icon is visually and semantically independent.
   - Keep parts grouped only when separating them would destroy the object's identity, remove essential context, or cut through inseparable pixels. Record the reason whenever a composite asset is intentionally kept together.
   - Assign every atomic asset a stable child ID derived from its parent block, such as `panel-2-icon-visual`, `panel-2-label-visual`, or `panel-4-arrow-input-1`, and record its bounds, role, parent block, and relationship to neighboring assets.
   - Deduplicate the atomic asset set before placement. Collapse exact or near-duplicate assets with the same meaning into one canonical asset and map all repeated source instances to that canonical ID.
   - Preserve intentional repetition in the reference as separate placements that reuse the canonical asset. Do not create duplicate crop files for each instance, and never stack or overlap multiple identical or near-identical assets in one target position.
   - Do not merge visually similar assets when their semantic roles differ. When uncertain, keep distinct placement records, select one canonical source file only when semantic equivalence is confirmed, and flag the ambiguity for review.
   - Write every canonical cropped or segmented asset to a sibling folder named `cropped_assets/` in the same directory as the final PPT output. Do not put derived assets back into the source-image directory, and do not overwrite the original source files.
   - Include the stable atomic asset ID in each canonical filename, and maintain alias/placement records so every repeated instance remains traceable to its source region.

2. Segment the PowerPoint slide to match the reference.
   - Map each reference block to a slide block.
   - Map each atomic asset and every intentional repeated placement inside the block; do not treat a coarse parent crop as sufficient when finer separable assets exist.
   - Do not fill blocks until the surrounding frame, header, and inter-block connectors are placed.
   - Work block-by-block and keep unfinished blocks visibly empty or intentionally placeholder-like.
   - Before marking the current block complete, trigger its block-level semantic review and resolve or explicitly defer any issue found there.

3. Classify objects inside the current block before drawing.
   - `simple-shape`: only an object that can be composed directly from standard PPT rectangles, rounded rectangles, straight lines, arrows, circles, dots, small bars, tables, dashed boxes, simple axes, and simple colored cells. This is a strict whitelist; the object must not require two or more curves, non-trivial multi-color tile/block assembly, or other custom geometry.
   - `complex-icon`: realistic equipment, detailed 3D/texture icons, dense plots better supplied as image assets, icons whose fidelity would take disproportionate manual drawing, any object containing two or more curves, any object requiring non-trivial multi-color tile/block assembly beyond simple colored cells, and any other custom geometry outside the `simple-shape` whitelist. Do not attempt to approximate these objects with PPT shapes; leave them as image assets, visibly unfinished, or explicitly deferred.
   - `formula`: mathematical labels or symbols that should be native equation objects or copied from a known-good formula instance.
   - `text`: ordinary labels/headings. Confirm font family, weight, size, and italic/math treatment before finalizing.

4. Fill simple-shape and text content with native PPT tools.
   - Use JavaScript ES modules and `@oai/artifact-tool` for PowerPoint construction. Python may analyze and crop images but must not draw or modify the deck.
   - Only objects that satisfy the exact `simple-shape` whitelist above may be drawn directly with PPT-native operations. If an object has two or more curves, requires non-trivial multi-color tile/block assembly, or falls outside that whitelist, stop and classify it as `complex-icon` instead of filling it.
   - Use PPT-native connectors/arrows for arrows; do not fake arrows from a line plus triangle unless the user explicitly accepts it.
   - Decide whether each connection is straight, elbow, curved, dashed, or feedback-like before drawing.
   - Use native shapes for simple icons and mini-diagrams; keep them editable.
   - Pull formulas out of this pass and handle them separately.
   - Confirm typography early: default to the user's requested font and use formula styling only for math.

5. Review each block before marking it complete, then review the full figure after all blocks are complete.
   - The block-level review is mandatory at the end of every block; do not defer all review until the entire figure is finished.
   - Build or update the block's object inventory and compare the rendered block against the corresponding reference crop; a text-presence check alone is not a visual review and cannot produce `accepted`.
   - Verify that every separable composite material was decomposed into atomic inventory entries, or has a recorded reason for remaining grouped.
   - Verify that exact and near-duplicate assets resolve to one canonical asset, that intentional repeated instances preserve the reference count and positions, and that no duplicate or near-duplicate assets are stacked in the same placement.
   - Verify the actual PPT shape types and asset paths against the classification table and the `simple-shape` whitelist.
   - Compare only drawn content, but record every intentionally blank complex icon, external crop, and known excluded asset explicitly in the inventory.
   - Check semantic correctness first: direction of arrows, labels, formula identities, panel roles, grouping, ordering, legends, inputs/outputs, and whether a block conveys the same operation.
   - If a drawn icon is semantically wrong or visually misleading, delete it and reclassify it as `complex-icon` instead of polishing a bad approximation.
   - Reject skeleton substitutes such as a sparkline for a dense plot, a generic box for an equipment rendering, a cube/custom geometry outside the whitelist, or a generic symbol set replacing distinct source icons. Leave the item as `deferred-complex` or use the traceable external crop instead.
   - Do not flag harmless differences such as tiny line width changes, slight spacing differences, or non-semantic color variation unless they obscure meaning.
   - Set the block to `accepted` only when the inventory is complete and the rendered visual review passes; otherwise keep `needs-review` or `deferred`.
   - After every block has passed its local review, run one final whole-figure review to check cross-block relationships, global ordering, connectors, legends, inputs/outputs, and overall semantic equivalence.
   - When enhanced complex assets are used, run `scripts/audit_enhanced_assets.py` before insertion. Reinsert only `pass` assets at their original frames, then render again and repeat local and whole-figure review.
   - Run `scripts/compare_panels.py` when the task requires matched source/render evidence. Treat `needs-review` comparisons as unresolved.

6. Produce a stage report after the first pass.
   - List blocks as `accepted`, `needs-review`, or `deferred`; do not call a block completed when it contains unapproved approximations or unresolved complex items.
   - List completed native objects and the corresponding object-inventory evidence.
   - List canonical cropped assets, their aliases, repeated placements, and any composite assets intentionally kept together with reasons.
   - List duplicate assets removed and confirm that no similar assets were stacked or inserted more times than the reference requires.
   - List unfinished `complex-icon` items with short descriptions and locations.
   - List external crops with their paths under the final PPT's sibling `cropped_assets/` folder.
   - List unfinished formulas and whether a reference/native equation source exists.
   - List semantic risks that still need user confirmation.

## Review Output

When asked to review progress, return a concise report with these headings:

- `Checkpoint`: latest Git commit created before review, or say no new change existed.
- `Acceptance Gate`: whether each block passed visual review with a complete object inventory; list any block that remains `needs-review` or `deferred`.
- `Semantic Gaps`: only issues that change meaning or could mislead a reader.
- `Deferred Items`: complex icons/formulas intentionally not completed.
- `Ignored Differences`: brief note that minor stroke, spacing, and fidelity differences were ignored.

## Detailed Guide

For checklist tables and reporting templates, read `references/block-workflow.md` when planning or reviewing a concrete figure reconstruction.

For whole-image draft generation, human approval, freeze records, mandatory automatic boundary detection, Artifact Tool reconstruction, controlled raster enhancement, and source/render panel comparisons, read `references/whole-first-workflow.md`.

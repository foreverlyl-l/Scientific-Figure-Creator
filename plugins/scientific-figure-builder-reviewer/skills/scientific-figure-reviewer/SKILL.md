---
name: scientific-figure-reviewer
description: Perform a fail-closed final audit of recreated PowerPoint scientific figures against their reference images, using ordered block-level review followed by a whole-figure review. Use only when the user explicitly invokes $scientific-figure-reviewer or explicitly requests a separate final audit of a recreated PPTX, paper figure, flowchart, process diagram, or block diagram for semantic mismatches, source-reference errors, arrow and connector direction/style problems, illogical text, abnormal or discordant shapes, visual-detail differences, typography, layout, and aesthetics. Do not invoke automatically from reconstruction, generation, rendering, or ordinary PPT workflows.
---

# Scientific Figure Reviewer

Audit a completed recreation without editing it. Review every mapped region in order, then review the whole slide or figure. Treat visual rendering and reference comparison as mandatory evidence.

## Invocation Boundary

- Run this skill only when the user explicitly names `$scientific-figure-reviewer` or clearly asks for a separate final audit of an already recreated artifact.
- Do not call, chain, or suggest this skill automatically from `scientific-figure-builder`, PPT generation, image rendering, reconstruction, export, or ordinary review workflows.
- Do not treat words such as "review", "check", "finish", or "final" by themselves as authorization to invoke this skill.
- If another skill or workflow reaches a review stage without explicit user authorization for this final-audit skill, finish that workflow's own review and stop; do not hand off here.
- Once explicitly invoked, remain read-only unless the user separately authorizes fixes.

## Required Inputs

- Require the original reference image or figure and the final recreated PPTX.
- Use the upstream segmentation map, object inventory, and cropped assets when available.
- Render the final PPTX to images before judging it. Do not issue a pass from slide text, XML, shape counts, or object metadata alone.
- If the reference, final render, or block mapping is missing, report the review as incomplete; do not infer a pass.
- Read `references/final-review-checklist.md` before starting a concrete final review.

## Review Order

1. Confirm that the reference, PPTX, render, segmentation map, and output version belong to the same artifact set.
2. If no reliable block map exists, explicitly divide the reference and rendered slide into matching blocks before reviewing.
3. Review each block in the recorded source order. Finish and record the current block before moving to the next.
4. Review the complete figure after all block reviews. Check cross-block arrows, reading order, legends, color meaning, global consistency, and overall logic.
5. Consolidate duplicate findings, assign exactly one level to each issue, and issue the final verdict.

## Mandatory Checks

### Arrows and lines

- Check the actual source node, target node, direction, arrowhead side, endpoint attachment, connector route, crossings, and feedback direction.
- Check whether straight, elbow, curved, dashed, solid, colored, thick, and thin lines preserve the reference meaning.
- Treat a wrong target, direction, endpoint, arrowhead, or meaning-bearing line style as a Level 1 semantic issue.
- Treat a purely cosmetic stroke, spacing, or line-weight difference as Level 2.

### Shapes and visual coherence

- Flag distorted, malformed, clipped, colliding, protruding, unexpectedly rotated/flipped, asymmetrical, or visibly discordant shapes.
- Check that repeated objects remain consistent and that grouped shapes still look like one intended object.
- Treat a shape that represents the wrong object, operation, state, or relationship as Level 1.
- Treat an unattractive but semantically correct shape as Level 2.

### Text and logic

- Check labels, titles, descriptions, units, formulas, legends, terminology, causal statements, inputs/outputs, and cross-panel logic.
- Flag contradictions, impossible statements, reversed relationships, missing qualifiers, wrong units, wrong formula symbols, or text that does not logically fit the diagram.
- Treat meaning or logic errors as Level 1.
- Treat font family, weight, size, wrapping, spacing, alignment, and ordinary typography problems as Level 2 unless they make the meaning ambiguous or unreadable; then use Level 1.

### Reference errors

- Report logical or semantic errors already present in the original reference as Level 1 and label them `source-error`.
- Do not silently correct the source or blame the recreation for faithfully reproducing a source error.
- If the recreation changes a source error, report both the source error and whether the unapproved change creates a reference mismatch.

## Two-Level Classification

- `Level 1 — Semantic`: any mismatch that changes meaning or logic, including missing/extra objects, wrong text meaning, incorrect formulas/units, wrong arrow direction or target, incorrect meaning-bearing line styles, incorrect grouping/order, misleading shapes, and errors in the original reference. Level 1 is blocking.
- `Level 2 — Visual/Detail`: image-detail differences that preserve meaning, unattractive or discordant geometry, minor shape inaccuracies, cosmetic line-style differences, spacing/alignment problems, font and text-layout issues, color-fidelity differences, and other polish problems. Level 2 is non-blocking unless it makes content unreadable or ambiguous.

When an issue could fit both levels, assign Level 1 if it can change a reader's interpretation; otherwise assign Level 2. Do not invent additional severity levels.

## Fail-Closed Verdict

- `FAIL`: one or more Level 1 issues exist, or required evidence is missing.
- `PASS WITH LEVEL 2 FIXES`: no Level 1 issues exist, but one or more Level 2 issues remain.
- `PASS`: no meaningful Level 1 or Level 2 issues remain.

Do not use shape count, text presence, visual similarity at a glance, or the recreation agent's own acceptance report as sufficient evidence for a pass.

## Output

Return findings in this order:

1. `Final Verdict`
2. `Evidence Reviewed`
3. `Block Review Summary`
4. `Level 1 — Semantic Issues`
5. `Level 2 — Visual/Detail Issues`
6. `Whole-Figure Review`
7. `Required Fix Order`

For every issue, include: issue ID, level, block/location, reference evidence, recreated evidence, why it matters, and the recommended correction. Keep source errors clearly distinguished from recreation errors.

Do not modify the PPTX during final review unless the user explicitly requests fixes after receiving the report.

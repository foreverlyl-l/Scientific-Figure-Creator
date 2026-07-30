# Scientific Figure Reviewer: Final Review Checklist

Use this checklist after the upstream reconstruction is complete. Review the rendered result, not only the PPT object model.

## Evidence Set

Record these paths or identifiers before reviewing:

- original reference image or page
- final PPTX
- final rendered slide image
- segmentation or block map
- object inventory, if available
- cropped asset folder, if available
- recreation stage report, used only as context and never as proof of correctness

If the final PPTX and rendered image do not match, stop and regenerate the render from the actual final PPTX.

## Per-Block Checklist

Review blocks in source order and record the result before moving on.

### Structure and content

- Same block role, title, and reading position as the reference.
- Same required objects; no unexplained missing, added, duplicated, or substituted objects.
- Same grouping, sequence, input/output roles, legend meaning, and color encoding.
- Formulas, units, symbols, subscripts, superscripts, names, and labels preserve meaning.

### Arrows and connectors

- Arrow begins at the intended source and terminates at the intended target.
- Arrowhead appears on the correct end.
- Endpoint visually attaches to the correct object, not empty space or a neighboring object.
- Straight/elbow/curved route matches the intended relation.
- Solid/dashed, color, weight, and feedback-loop styling preserve meaning.
- No stray, broken, hidden, reversed, or misleading connectors.

### Shape sanity

- No malformed, stretched, clipped, overlapping, protruding, or accidental shapes.
- No abnormal rotation, mirror, perspective, aspect ratio, or inconsistent repeated geometry.
- No generic substitute that implies a different object or operation.
- No visibly discordant object that breaks the local visual system.

### Text and layout

- Text meaning and logic are correct in context.
- No contradictions, impossible process claims, wrong causal direction, or mismatched labels.
- Text is readable and not clipped, crowded, orphaned, or badly wrapped.
- Font family, size, weight, italics, alignment, spacing, and hierarchy are coherent.

### Block verdict

- `FAIL`: any Level 1 issue exists or evidence is insufficient.
- `PASS WITH LEVEL 2 FIXES`: no Level 1 issue, but Level 2 issues remain.
- `PASS`: no meaningful issue remains.

## Whole-Figure Checklist

- Cross-block arrows connect the correct panels and point in the correct direction.
- Global reading order and causal flow remain logical.
- Repeated colors, line styles, symbols, legends, and labels retain one meaning throughout.
- No block contradicts another block or the figure's title/conclusion.
- Panel spacing, alignment, scale, typography, and visual density are coherent.
- No block looks accidentally unfinished, distorted, or stylistically detached from the whole.
- Source errors are listed separately from recreation mismatches.

## Level Assignment Rules

| Observation | Level |
| --- | --- |
| Wrong arrow direction, target, endpoint, or feedback relation | Level 1 |
| Dashed/solid/color difference that changes relationship meaning | Level 1 |
| Cosmetic stroke width or line-spacing difference | Level 2 |
| Wrong, missing, extra, or substituted object that changes meaning | Level 1 |
| Malformed or unattractive shape with preserved meaning | Level 2 |
| Wrong text, formula, unit, label, legend, or logical statement | Level 1 |
| Font, wrapping, spacing, alignment, or hierarchy problem | Level 2 |
| Typography problem that makes meaning ambiguous or unreadable | Level 1 |
| Semantic/logical error already present in the source | Level 1, tagged `source-error` |

## Report Template

```text
Final Verdict: FAIL / PASS WITH LEVEL 2 FIXES / PASS

Evidence Reviewed:
- Reference: <path>
- Final PPTX: <path>
- Render: <path>
- Block map: <path or generated map>

Block Review Summary:
| Block | Level 1 count | Level 2 count | Verdict | Notes |

Level 1 — Semantic Issues:
- L1-01 | <block/location> | <reference evidence> | <recreated evidence> | <impact> | <correction>

Level 2 — Visual/Detail Issues:
- L2-01 | <block/location> | <reference evidence> | <recreated evidence> | <visual impact> | <correction>

Whole-Figure Review:
- <cross-block and global findings>

Required Fix Order:
1. Resolve all Level 1 issues.
2. Re-render and repeat block plus whole-figure review.
3. Resolve Level 2 issues.
4. Re-render and issue the final verdict.
```

<div align="center">

# Scientific Figure Builder & Reviewer

From scientific-figure drafts to editable, reviewable PowerPoint deliverables

<p>
  <strong>English</strong> |
  <a href="./README.md">中文</a>
</p>

</div>

Scientific Figure Builder & Reviewer is a pair of open-source Codex skills for turning a written brief, rough sketch, whole-image draft, or reference figure into a structured, editable, and reviewable PowerPoint scientific figure.

The repository contains two complementary skills:

- `scientific-figure-builder` handles drafts, reconstruction, asset processing, and construction-time review;
- `scientific-figure-reviewer` performs an explicit, read-only, independent final audit.

## What it can do

- **Generate a whole-image first draft:** Build a semantic specification for panels, nodes, text, formulas, inputs, outputs, directed connections, and reading order, then generate one complete draft through an image backend selected by the user. The skill does not choose a provider by default or silently switch backends after a failure.
- **Freeze only after human confirmation:** Review block semantics first and whole-figure logic second. A SHA-256 lock record is created only after the user explicitly confirms the draft in chat; changing the draft or semantic specification invalidates the approval.
- **Detect and crop boundaries automatically:** Python and Pillow snap human-provided rough regions to detected content using background distance, projection gaps, and foreground regions. The workflow emits cropped PNGs, `asset_manifest.csv`, boundary reports, and a numbered overlay, and fails closed on empty regions, edge contact, overlap, low confidence, or an explicit panel-count mismatch.
- **Reconstruct an editable PowerPoint figure:** JavaScript `@oai/artifact-tool` builds the deck. Text, formulas, borders, color fields, simple shapes, arrows, and connectors remain native objects; equipment renders, smoke, and complex curves may remain traceable PNG assets.
- **Enhance complex explanatory illustrations under controls:** Deterministic enlargement or user-selected generative enhancement can be checked for aspect ratio, silhouette, foreground coverage, background, palette, and added objects. A replacement copy is produced only after both automated metrics and Agent visual review pass, while the original remains untouched.
- **Validate matching panels:** Redetect corresponding regions in the frozen draft and PowerPoint render, then produce panel-by-panel comparisons, a contact sheet, and a machine-readable report. Every panel still requires visual and semantic approval.
- **Run an independent final audit:** `scientific-figure-reviewer` runs only when the user explicitly invokes it. The Builder never triggers it automatically, and the reviewer does not modify the deck.

## Deliverables

- An editable PPTX;
- the frozen draft, `figure_spec.json`, and `draft_lock.json`;
- atomic crops, an asset manifest, and boundary-detection evidence;
- enhancement audit and safe replacement records;
- slide renders, panel comparison images, and a construction report;
- an independent final-review report when explicitly requested.

## Main limitations

- Draft generation and generative enhancement depend on a backend that is actually available in the current Codex environment and explicitly selected by the user. Generated results still require semantic review and human confirmation.
- Scientific evidence such as microscopy, measured plots, and medical imagery must not be generatively rewritten; only an explicit non-generative method may be used.
- The current workflow focuses on PowerPoint, does not promise pixel-perfect reproduction, and does not yet deliver editable `.drawio` files.

## Where it works well

- Deep-learning and non-visual-domain model figures, data flows, system architectures, mechanisms, and method diagrams;
- figures whose scientific meaning is carried mainly by text, modules, formulas, and connections, with illustrations serving as explanatory support;
- projects that need a consistent background and illustration style while preserving editable text, geometry, and connectors;
- workflows that allow strong-model and human judgment during semantic review, draft approval, and final acceptance.

Future work will continue improving first-draft and controlled-enhancement stability and add editable draw.io reconstruction and delivery.

## License scope

The repository license applies to the plugin, skills, scripts, and documentation.  
It does not grant rights to third-party reference figures or automatically determine the license of user-generated PPTX files and assets.

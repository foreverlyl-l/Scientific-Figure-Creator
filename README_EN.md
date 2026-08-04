<div align="center">

# Scientific Figure Initializer, Builder & Reviewer

Scientific-figure initialization, PowerPoint reconstruction, and independent review

<p>
  <strong>English</strong> |
  <a href="./README.md">中文</a>
</p>

</div>

Scientific Figure Initializer, Builder & Reviewer is a set of open-source Codex skills for initializing scientific-figure workflows, reconstructing references as editable PowerPoint figures, and running an independent final audit.

The repository contains three consistently named skills:

- `scientific-figure-initializer` retains the previous repository Builder workflow for whole-image drafts, human freezing, asset processing, reconstruction coordination, and construction-time acceptance;
- `scientific-figure-builder`, renamed from `ppt-shape-recreate-review`, focuses on block-by-block reconstruction with editable PowerPoint-native objects;
- `scientific-figure-reviewer` performs an explicit, read-only, independent final audit.

## What it can do

- **Initializer — whole-image draft and freeze:** Build a semantic specification for panels, nodes, text, formulas, inputs, outputs, directed connections, and reading order, then generate one complete draft through a backend explicitly selected by the user. Create a SHA-256 lock only after block, whole-figure, and human approval.
- **Initializer — complete workflow coordination:** Retain the previous Builder's automatic boundary detection, crop manifests, Artifact Tool reconstruction contract, controlled illustration enhancement, and panel-by-panel comparison capabilities without splitting or removing them.
- **Builder — PowerPoint shape reconstruction:** Segment the reference semantically and into atomic assets, maintain an object inventory, strictly separate simple native shapes from complex illustrations, and require block and whole-figure review before acceptance.
- **Builder — editable objects first:** Keep text, formulas, borders, color fields, simple geometry, arrows, and connectors as native PowerPoint objects. Use traceable crops for complex equipment, texture, and dense curves rather than misleading generic approximations.
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

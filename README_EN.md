<div align="center">

# Scientific Figure Builder & Reviewer

PowerPoint-based scientific figure reconstruction and independent review skills

<p>
  <strong>English</strong> |
  <a href="./README.md">中文</a>
</p>

</div>

Scientific Figure Builder & Reviewer is a pair of Codex skills for turning an existing scientific figure draft or reference image into a structured, editable, and reviewable PowerPoint figure.

The repository contains two complementary skills:

- `scientific-figure-builder` for reconstruction and construction-time review;
- `scientific-figure-reviewer` for an explicit, read-only final audit.

## What it can do

- **Understand an existing draft:** Identify panels, headings, labels, formulas, legends, inputs, outputs, arrows, feedback paths, repeated objects, and reading order as parts of a scientific communication artifact.
- **Build a traceable structure:** Divide the reference into semantic blocks with stable IDs and parent-child relationships, then maintain an object inventory so missing, duplicated, substituted, and unfinished content remains visible.
- **Reconstruct in PowerPoint:** Rebuild text, formulas, rectangles, circles, tables, arrows, connectors, simple axes, and colored cells as editable native PowerPoint objects.
- **Handle complex content honestly:** Keep complex plots, scientific imagery, equipment renderings, textured icons, and custom geometry as traceable atomic crops or explicitly defer them instead of using misleading generic approximations.
- **Manage and reuse assets:** Record stable IDs, source regions, parent blocks, semantic roles, aliases, and placements. Semantically equivalent repeated objects can reuse one canonical asset.
- **Review during construction:** Compare every block with the matching reference region before acceptance, checking object completeness, arrow direction, relationships, text, formulas, grouping, ordering, and legends.
- **Perform an independent final audit:** When explicitly invoked, `scientific-figure-reviewer` reviews every block and then the complete figure, separating Level 1 semantic issues from Level 2 visual-detail issues.
- **Distinguish source errors:** Logical or semantic errors already present in the reference are reported as `source-error` rather than being attributed to the reconstruction.

The workflow can produce an editable PPTX, an atomic asset directory, a semantic block map, an object inventory, an asset manifest, a construction report, and an independent final-review report.

## What it cannot do

- It does not include its own PowerPoint drawing backend. Construction and rendering depend on the PowerPoint capabilities available in the Codex runtime.
- It currently starts from an existing draft or reference image. Automatic first-draft illustration and automatic image upscaling are not yet included.
- It does not guarantee pixel-perfect reproduction. Low-resolution references and highly complex visual objects may remain traceable image assets or be explicitly deferred. Editable `.drawio` output is not currently supported.

## Where it works well

- Paper figures, model diagrams, workflows, process diagrams, architecture figures, and block diagrams;
- projects with a reasonably clear visual draft, panels, labels, arrows, formulas, and reading order;
- figures combining editable geometric structures with a limited number of complex image elements;
- tasks requiring an editable PowerPoint deliverable rather than a single flattened image;
- projects where semantic correctness, traceable assets, intermediate review, and human or strong-model judgment matter.

## Roadmap

- Automated high-resolution image processing with source preservation and special protection for scientific evidence images;
- first-draft scientific illustration from a written brief, structured specification, or rough sketch;
- editable draw.io reconstruction and delivery.

## License scope

The repository license applies to the plugin, skills, scripts, and documentation.  
It does not grant rights to third-party reference figures or automatically determine the license of user-generated PPTX files and assets.

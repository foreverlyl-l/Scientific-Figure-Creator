# Scientific Figure Builder & Reviewer

## English

Scientific Figure Builder & Reviewer is a pair of Codex skills for turning an existing scientific figure draft or reference image into a structured, editable, and reviewable PowerPoint figure.

The workflow covers the path from an initial visual draft to a final deliverable: understanding the figure, separating it into semantic regions, reconstructing suitable content as native PowerPoint objects, managing complex image assets, reviewing each region, and performing an optional independent final audit.

The repository contains:

- `scientific-figure-builder` for reconstruction and construction-time review;
- `scientific-figure-reviewer` for an explicit, read-only final audit.

### What it can do

#### Understand and organize an existing draft

The builder analyzes the supplied draft or reference as a scientific communication artifact rather than treating it as a flat image. It identifies panels, subpanels, headings, labels, formulas, legends, inputs, outputs, arrows, feedback paths, repeated objects, and the intended reading order.

The figure is divided into stable semantic blocks with parent-child relationships and matching PowerPoint regions. Every visible object is recorded in an inventory so that missing, duplicated, substituted, or unfinished content remains visible during review.

#### Reconstruct the figure in PowerPoint

Simple and reliable structures—such as rectangles, rounded rectangles, circles, tables, text, arrows, connectors, axes, and simple colored cells—can be rebuilt as editable PowerPoint objects. Text and formulas are handled separately so that typography, symbols, subscripts, superscripts, and mathematical meaning can be checked.

Complex plots, scientific imagery, equipment renderings, textured icons, and custom geometry are not replaced with misleading generic shapes. They are decomposed into traceable atomic crops when appropriate, or explicitly marked as deferred. Repeated assets can share one canonical source while preserving every intentional placement in the figure.

The resulting workflow can produce:

- an editable PowerPoint figure;
- a `cropped_assets/` directory for canonical image assets when needed;
- a semantic block map and object inventory;
- an asset manifest containing stable IDs, source regions, aliases, and placements;
- construction-stage and final-review reports.

#### Review the figure during construction

Each semantic block is reviewed against the corresponding region of the reference before it can be accepted. The review checks object completeness, arrow direction, connector meaning, labels, formulas, grouping, ordering, legends, and whether the reconstructed region communicates the same scientific operation.

The workflow fails closed: an unclassified, misleading, visually unverified, or placeholder object cannot be reported as complete.

#### Perform an independent final review

When explicitly requested, `scientific-figure-reviewer` performs a separate read-only audit of the final PowerPoint figure. It reviews the figure block by block and then as a whole.

Findings are divided into:

- Level 1 semantic issues that can change a reader's interpretation;
- Level 2 visual or detail issues that preserve meaning but reduce clarity or polish.

Errors already present in the source figure are reported separately as `source-error` rather than being silently attributed to the reconstruction.

### What it cannot do

- It does not include its own PowerPoint drawing backend. Construction and rendering depend on the PowerPoint capabilities available in the Codex runtime.
- It currently starts from an existing draft or reference image. Automatic first-draft illustration and automatic image upscaling are not yet included.
- It does not guarantee pixel-perfect reproduction. Low-resolution references and highly complex visual objects may remain traceable image assets or be explicitly deferred. Editable `.drawio` output is not currently supported.

### Where it works well

The workflow is particularly suitable for:

- paper figures, model diagrams, workflows, process diagrams, architecture figures, and block diagrams;
- projects that already have a visual draft with reasonably clear panels, labels, arrows, formulas, and reading order;
- figures combining editable geometric structures with a limited number of complex image elements;
- work that requires an editable PowerPoint deliverable rather than a single flattened image;
- projects where semantic correctness, traceable assets, intermediate review, and human or strong-model judgment are important.

### Roadmap

- Automated high-resolution image processing with source preservation and special protection for scientific evidence images.
- First-draft scientific illustration from a written brief, structured specification, or rough sketch.
- Editable draw.io reconstruction and delivery.

### License scope

The repository license applies to the plugin, skills, scripts, and documentation.  
It does not grant rights to third-party reference figures or automatically determine the license of user-generated PPTX files and assets.

---

## 中文

Scientific Figure Builder & Reviewer 是一组面向 Codex 的科研图技能，用于把一张已有的科研图初稿或参考图，逐步重建为结构清晰、可编辑、可审核的 PowerPoint 科研图。

它覆盖从视觉初稿到最终交付的主要过程：理解原图、进行语义分块、把适合的内容重建为 PowerPoint 原生对象、管理复杂图片素材、逐块审核，并在用户明确要求时执行独立终审。

仓库包含两个配套 skill：

- `scientific-figure-builder`：负责科研图重建和施工期审核；
- `scientific-figure-reviewer`：负责仅显式调用、只读的独立终审。

### 现在能做什么

#### 理解并组织已有初稿

Builder 不会把参考图简单视为一张平面图片，而是从科研表达的角度识别面板、子面板、标题、标签、公式、图例、输入、输出、箭头、反馈路径、重复对象和整体阅读顺序。

原图会被拆分成带有稳定 ID 和父子关系的语义 block，并映射到对应的 PowerPoint 区域。每个可见对象都会进入 object inventory，使缺失、重复、替换错误和未完成内容在审核过程中保持可见。

#### 在 PowerPoint 中完成科研图重建

矩形、圆角矩形、圆形、表格、文字、箭头、连接线、简单坐标轴和简单色块等可靠结构，可以重建为可编辑的 PowerPoint 原生对象。文字与公式会被单独处理，以便检查字体、符号、上下标和数学含义。

复杂曲线图、科研图像、设备渲染、纹理图标和自定义几何不会被低质量的通用形状替代。适合保留为图片的对象会被拆分为可追踪的原子裁剪素材；暂时无法可靠完成的对象会被明确标记为 deferred。重复素材可以共享同一份规范源文件，同时保留原图中每一次有意的重复放置。

当前流程可以形成：

- 可编辑的 PowerPoint 科研图；
- 必要时与 PPTX 配套的 `cropped_assets/` 原子素材目录；
- 语义 block map 和 object inventory；
- 记录稳定 ID、原图区域、别名和放置位置的 asset manifest；
- 施工阶段报告和最终审核报告。

#### 在施工过程中逐块审核

每个语义 block 在被接受前，都需要与参考图对应区域进行对照。审核会检查对象是否完整、箭头方向、连接关系、文字、公式、分组、顺序、图例，以及重建区域是否表达了相同的科研操作。

流程采用失效关闭原则：未分类、具有误导性、未经视觉确认或仍是占位符的对象，不能被报告为已经完成。

#### 执行独立终审

用户明确调用 `scientific-figure-reviewer` 后，它会对最终 PowerPoint 科研图执行独立、只读的审核：先逐块检查，再检查整图关系。

问题分为：

- Level 1：可能改变读者理解的语义问题；
- Level 2：不改变含义，但影响清晰度或完成度的视觉与细节问题。

如果错误本身已经存在于参考图中，会被单独标记为 `source-error`，而不会被错误地归因于重建过程。

### 现在不能做什么

- 项目不自带 PowerPoint 绘图后端，实际施工和渲染依赖 Codex 运行环境中已有的 PowerPoint 能力。
- 当前需要从一张已有初稿或参考图开始，尚未包含自动初稿原图绘制和自动图片高清化。
- 不保证像素级完全复现。低分辨率参考图和高度复杂的视觉对象可能继续作为可追踪图片素材存在，或被明确延期；目前也不支持可编辑 `.drawio` 交付。

### 什么场景下表现较好

当前流程尤其适合：

- 论文配图、模型示意图、工作流、过程图、架构图和框图；
- 已有较清晰视觉初稿，并且面板、标签、箭头、公式和阅读顺序相对明确的项目；
- 同时包含可编辑几何结构和少量复杂图片元素的科研图；
- 需要交付可编辑 PowerPoint，而不是单张扁平图片的任务；
- 重视语义正确、素材可追踪、中间审核以及强模型或人工判断的项目。

### 后续计划

- 自动化图片高清化，同时保留原始素材，并对科研证据图实施专门保护。
- 根据文字需求、结构化规范或粗略草图自动绘制科研图初稿。
- 支持可编辑的 draw.io 重建与交付。

### 许可证范围

仓库许可证适用于插件、skills、脚本和文档。  
它不授予第三方参考图的使用权，也不会自动判定用户生成的 PPTX 文件和素材采用何种许可证。

# Scientific Figure Builder & Reviewer

[English](#english) · [中文](#中文)

## English

### Overview

Scientific Figure Builder & Reviewer is an open-source, skill-only Codex plugin for reference-guided scientific figure reconstruction and independent acceptance review.

It is designed as a strong-model/human-in-the-loop framework:

- Codex or another capable agent makes semantic decisions about segmentation, object classification, complex assets, formulas, and acceptance.
- The user can inspect intermediate artifacts, approve uncertain choices, and authorize corrections.
- Low-risk execution can be automated, while semantic judgment and final approval remain visible.

This repository packages two complementary skills:

- `scientific-figure-builder`: reconstructs a supplied paper figure, flowchart, process diagram, or block diagram through staged semantic blocks.
- `scientific-figure-reviewer`: performs a separate, read-only, fail-closed final audit when explicitly invoked by the user.

This is not a self-contained drawing engine. It provides reconstruction and review protocols, while Codex selects an available PowerPoint-capable execution layer. The plugin currently bundles no PowerPoint, draw.io, image-generation, or image-upscaling backend of its own.

### What it can do today

| Capability | Status | Current behavior |
| --- | --- | --- |
| Reference segmentation | Available | Assigns stable block IDs, parent-child relationships, semantic roles, and matching slide regions. |
| Object inventory | Available | Requires every visible reference object to receive exactly one action and an acceptance state. |
| Native PowerPoint reconstruction | Available, runtime-dependent | Routes shape, text, connector, and formula work to PowerPoint capabilities available to Codex. |
| Simple-shape boundary | Available | Uses a strict native-shape whitelist and rejects unsupported custom geometry as a finished approximation. |
| Complex-object handling | Available | Uses traceable `external-crop` assets or marks the object `deferred-complex`. |
| Atomic asset workflow | Available | Records stable IDs, parent blocks, semantic roles, source bounds, aliases, and repeated placements. |
| Asset deduplication | Available | Reuses one canonical asset for semantically equivalent repetitions and prevents accidental stacking. |
| Formula handling | Available | Classifies formulas separately and reviews their symbols, primes, subscripts, superscripts, and meaning. |
| Construction-time review | Available | Requires rendered, block-level semantic review before a block can be accepted. |
| Independent final review | Available | Provides an explicit-only, read-only audit with fail-closed verdicts. |
| Source-error reporting | Available | Separates errors already present in the reference from recreation errors using `source-error`. |
| Issue classification | Available | Uses blocking Level 1 semantic issues and non-blocking Level 2 visual/detail issues. |
| User-file protection | Available | Requires a Git checkpoint before modifying an existing user-edited deck when Git is applicable. |
| Automated image enhancement | Planned | Candidate generation/upscaling with provenance and strong-model or human approval. |
| First-draft source illustration | Planned | Brief- or sketch-to-first-draft scientific illustration before editable reconstruction. |
| draw.io delivery | Planned | A shared specification and inventory routed to an available official draw.io skill or MCP backend. |

### Where it works well

The current workflow is best suited to:

- paper figures, workflows, architecture diagrams, process diagrams, and block diagrams;
- references with clear panels, labels, arrows, legends, formulas, and reading order;
- figures that mix editable simple geometry with a limited number of detailed raster assets;
- projects where semantic correctness, traceability, and review evidence matter more than fully automatic one-click output;
- PowerPoint delivery environments where Codex can create, edit, render, and inspect a PPTX;
- work that can tolerate strong-model or human decisions for ambiguous objects.

### Known limitations

- The plugin has no bundled drawing backend. PPTX construction and rendering depend on the capabilities available in the Codex runtime, so the workflow is not currently a one-command, fully autonomous service.
- Pixel-perfect similarity is not guaranteed. Low-resolution references and complex plots, scientific imagery, textured icons, or custom geometry may remain traceable raster crops or be explicitly deferred.
- Automated image enhancement, first-draft source illustration, and `.drawio` delivery are planned rather than current capabilities. Experimental evidence images must not receive generative detail, and corrections after the read-only final review require separate user authorization.

### Deliverables

Depending on the task and available runtime, the current workflow can deliver:

1. An editable `.pptx` recreation.
2. A sibling `cropped_assets/` directory containing canonical atomic image assets when external crops are used.
3. A semantic block map with stable IDs and reference-to-slide region mapping.
4. An object inventory covering native shapes, text, formulas, external crops, and deferred complex objects.
5. An asset manifest containing canonical IDs, aliases, source bounds, grouping reasons, and repeated placements.
6. A reconstruction stage report with accepted, needs-review, and deferred blocks.
7. Rendered comparison evidence when the runtime supports PowerPoint rendering.
8. A separate final audit report containing evidence reviewed, block findings, Level 1 issues, Level 2 issues, whole-figure findings, and required fix order.

The repository itself ships instructions and metadata only. It does not include reference images, generated PPTX files, model credentials, telemetry, third-party binary assets, or a drawing service.

### Roadmap

The planned direction is to retain the strong-model/human approval boundary while automating more low-risk work:

- **Automated high-resolution assets:** generate or upscale candidates through APIs, preserve the original, record provenance, and require strong-model or human approval before replacement.
- **Scientific evidence protection:** allow only non-generative enlargement for experimental evidence images unless a user explicitly provides an approved scientific processing method; never hallucinate measurements or structures.
- **First-draft source illustration:** create an initial scientific figure from a brief, structured specification, or rough sketch before converting it into editable objects.
- **draw.io delivery:** route a shared reconstruction specification, inventory, and review evidence to an available official draw.io skill or MCP backend.
- **Cross-backend specification:** keep block IDs, object classifications, asset manifests, and render evidence consistent across PowerPoint and draw.io.
- **Additional previews and exports:** add reproducible preview generation and export guidance after the underlying editable artifact is verified.

Roadmap items are intentions, not current guarantees.

### Workflow

1. Segment the reference into stable semantic blocks.
2. Decompose each block into the smallest meaningful and reusable assets.
3. Deduplicate semantically equivalent assets and preserve intentional repeated placements.
4. Classify every visible object as a native simple shape, native text, native formula, external crop, or deferred complex object.
5. Construct and render one block at a time.
6. Fail closed when an object is missing, misleading, unclassified, or visually unverified.
7. Review cross-block relationships and the complete figure.
8. When explicitly requested, run the separate read-only final audit.

### Installation

#### Install as a plugin

Add this repository root as a local Codex marketplace, then install `scientific-figure-builder-reviewer` from the Codex plugin interface or the corresponding plugin command available in your installation.

- Marketplace manifest: `.agents/plugins/marketplace.json`
- Plugin manifest: `plugins/scientific-figure-builder-reviewer/.codex-plugin/plugin.json`

#### Install as standalone skills

Copy either or both skill folders into your Codex skills directory:

```text
$CODEX_HOME/skills/scientific-figure-builder/
$CODEX_HOME/skills/scientific-figure-reviewer/
```

The source folders are located under:

```text
plugins/scientific-figure-builder-reviewer/skills/
```

Restart or reload Codex after installation.

### GitHub validation and releases

The repository includes `.github/workflows/release.yml`.

- Pull requests and pushes to `main` run package validation.
- A manual `workflow_dispatch` run validates the repository and uploads a release archive as a temporary Actions artifact.
- Pushing a `v*` tag validates that the tag matches the version in `.codex-plugin/plugin.json`, builds a reproducible ZIP, uploads it as an Actions artifact, and creates a GitHub Release.

For example, after setting `plugin.json` to version `0.1.0`:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The repository does not need to store generated ZIP files. Release archives are built by GitHub Actions and `dist/` remains ignored.

### Usage

Recreate a reference figure:

```text
Use $scientific-figure-builder to recreate this reference figure as an editable PPTX.
```

Run the separate final audit:

```text
Use $scientific-figure-reviewer to audit this completed PPTX against the reference.
```

The reconstruction skill performs its own mandatory block and whole-figure reviews. It never automatically invokes or suggests the separate final-review skill.

### Repository layout

```text
Scientific-Figure-Creator/
├── .github/workflows/release.yml
├── .agents/plugins/marketplace.json
├── plugins/
│   └── scientific-figure-builder-reviewer/
│       ├── .codex-plugin/plugin.json
│       └── skills/
│           ├── scientific-figure-builder/
│           └── scientific-figure-reviewer/
├── scripts/
│   ├── build_release.py
│   └── validate_package.py
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

### Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md). Preserve the fail-closed acceptance rules, the strict complex-object boundary, and the explicit invocation boundary of the final-review skill.

Licensed under the [MIT License](LICENSE).

The repository license applies to the plugin, skills, scripts, and documentation.  
It does not grant rights to third-party reference figures or automatically determine the license of user-generated PPTX files and assets.

---

## 中文

### 项目简介

Scientific Figure Builder & Reviewer 是一个面向 Codex 的开源 skill-only 插件，用于依据参考图重建科研图，并对完成的结果进行独立验收。

它采用“强模型/人工在环”的工作方式：

- 由 Codex 或其他能力足够的 agent 对语义分块、对象分类、复杂素材、公式和验收结果作出判断；
- 用户可以检查中间产物、批准不确定项，并单独授权修改；
- 低风险执行可以自动化，但语义判断与最终批准始终保持可见。

仓库包含两个配套 skill：

- `scientific-figure-builder`：把已有论文图、流程图、过程图或框图按语义区域分阶段重建；
- `scientific-figure-reviewer`：仅在用户明确调用时，对最终 PPTX 进行只读、失效关闭的独立终审。

本项目不是自带绘图引擎的一体化软件。它提供重建与验收规范，由 Codex 根据当前环境选择可用的 PowerPoint 执行能力。插件目前不自带 PowerPoint、draw.io、图片生成或图片高清化后端。

### 当前能做什么

| 能力 | 状态 | 当前行为 |
| --- | --- | --- |
| 参考图分块 | 已有 | 建立稳定 block ID、父子关系、语义角色以及参考图到幻灯片的区域映射。 |
| 对象清单 | 已有 | 要求参考图中的每个可见对象只能对应一种处理动作和一个验收状态。 |
| PowerPoint 原生重建 | 已有，但依赖运行环境 | 将形状、文字、连接线和公式的施工路由到 Codex 当前可用的 PowerPoint 能力。 |
| 简单图形边界 | 已有 | 使用严格原生形状白名单，不把不支持的自定义几何伪装成完成品。 |
| 复杂对象处理 | 已有 | 使用可追踪的 `external-crop`，或标记为 `deferred-complex`。 |
| 原子素材流程 | 已有 | 记录稳定 ID、父级 block、语义角色、原图边界、别名和重复放置。 |
| 素材去重 | 已有 | 语义等价的重复对象复用一份规范素材，并防止意外堆叠。 |
| 公式处理 | 已有 | 单独分类公式，并检查符号、撇号、上下标和语义。 |
| 施工期审核 | 已有 | block 只有通过渲染后的逐块语义审核才能被接受。 |
| 独立终审 | 已有 | 提供仅显式调用、只读、失效关闭的最终审核。 |
| 原图错误报告 | 已有 | 用 `source-error` 区分参考图自身错误和复刻错误。 |
| 问题分级 | 已有 | Level 1 为阻断性的语义问题；Level 2 为非阻断性的视觉或细节问题。 |
| 用户文件保护 | 已有 | 在适用 Git 的情况下，修改用户已有 deck 前先建立 checkpoint。 |
| 自动化图片高清化 | 规划中 | 通过 API 生成或放大候选，保留来源，并由强模型或人工批准。 |
| 初稿原图绘制 | 规划中 | 根据文字需求或草图先生成科研图初稿，再进入可编辑重建。 |
| draw.io 交付 | 规划中 | 将统一规范和对象清单路由到可用的官方 draw.io skill 或 MCP 后端。 |

### 适合的场景

当前流程比较适合：

- 论文配图、工作流、架构图、过程图和框图；
- 面板、标题、标签、箭头、图例、公式和阅读顺序比较清楚的参考图；
- 同时包含简单可编辑几何和少量复杂栅格素材的图；
- 比起一键全自动，更重视语义正确、素材可追踪和验收证据的任务；
- Codex 可以创建、编辑、渲染并检查 PPTX 的 PowerPoint 交付环境；
- 可以接受强模型或人工处理歧义对象的项目。

### 已知局限

- 插件不自带绘图后端，PPTX 的施工和渲染依赖 Codex 运行环境中的可用能力，因此当前不是一条命令即可完全自治运行的服务。
- 不保证像素级完全一致。低分辨率参考图以及复杂曲线图、科研图像、纹理图标和自定义几何可能保留为可追踪栅格素材，或被明确延期。
- 自动图片高清化、初稿原图绘制和 `.drawio` 交付仍在规划中；实验性证据图不得生成不存在的细节，只读终审后的修改也需要用户另行授权。

### 当前可交付内容

根据任务和运行环境，当前流程可以交付：

1. 可编辑的 `.pptx` 重建文件；
2. 使用外部裁剪素材时，与 PPTX 同级的 `cropped_assets/` 目录；
3. 带稳定 ID 的语义 block map，以及参考图到幻灯片的区域映射；
4. 覆盖原生形状、文字、公式、外部裁剪和延期复杂对象的 object inventory；
5. 包含规范素材 ID、别名、原图边界、组合原因和重复放置记录的 asset manifest；
6. 标记 `accepted`、`needs-review` 和 `deferred` block 的施工阶段报告；
7. 在运行环境支持 PowerPoint 渲染时生成的对照证据图；
8. 一份独立终审报告，其中包括已检查证据、逐块结果、Level 1 问题、Level 2 问题、整图结论和修复顺序。

仓库本身只提供说明和元数据，不包含参考图、生成的 PPTX、模型密钥、遥测、第三方二进制素材或绘图服务。

### 路线图

未来会继续保持“强模型/人工批准”的边界，同时自动化更多低风险步骤：

- **自动化高清素材：** 通过 API 生成或放大候选，保留原始素材和来源记录，替换前必须经过强模型或人工批准；
- **科研证据保护：** 对实验性证据图原则上只允许非生成式放大；除非用户明确提供已批准的科研处理方法，否则绝不生成不存在的测量或结构细节；
- **初稿原图绘制：** 根据文字需求、结构化规范或粗略草图生成科研图初稿，再转换为可编辑对象；
- **draw.io 交付：** 把统一 reconstruction spec、对象清单和审核证据路由到可用的官方 draw.io skill 或 MCP 后端；
- **跨后端一致性：** 让 PowerPoint 和 draw.io 使用一致的 block ID、对象分类、素材清单和渲染证据；
- **预览与导出：** 在可编辑源文件通过验证后，增加可复现的预览生成与导出指导。

路线图表示计划方向，不代表当前已经提供或保证交付。

### 工作流程

1. 将参考图拆分为稳定的语义 block；
2. 把每个 block 继续拆成最小、可复用的有意义素材；
3. 对语义等价素材去重，同时保留参考图中的重复放置；
4. 把每个可见对象唯一分类为原生简单形状、原生文字、原生公式、外部裁剪或延期复杂对象；
5. 按 block 逐块施工、渲染和验收；
6. 对缺失、误导、未分类或未经视觉验证的对象执行失效关闭；
7. 检查跨 block 关系和整图表现；
8. 用户明确要求时，再运行独立只读终审。

### 安装

#### 作为插件安装

把本仓库根目录添加为 Codex 本地 marketplace，然后在 Codex 插件界面或当前安装支持的插件命令中安装 `scientific-figure-builder-reviewer`。

- Marketplace 清单：`.agents/plugins/marketplace.json`
- Plugin 清单：`plugins/scientific-figure-builder-reviewer/.codex-plugin/plugin.json`

#### 作为独立 skill 安装

把一个或两个 skill 目录复制到 Codex skills 目录：

```text
$CODEX_HOME/skills/scientific-figure-builder/
$CODEX_HOME/skills/scientific-figure-reviewer/
```

源目录位于：

```text
plugins/scientific-figure-builder-reviewer/skills/
```

安装后重新启动或加载 Codex。

### GitHub 校验与发布

仓库包含 `.github/workflows/release.yml`：

- Pull Request 和推送到 `main` 时自动校验包结构；
- 手动运行 `workflow_dispatch` 时，完成校验并把发布包上传为临时 Actions artifact；
- 推送 `v*` 标签时，检查标签版本是否与 `.codex-plugin/plugin.json` 一致，构建可复现 ZIP，上传 Actions artifact，并自动创建 GitHub Release。

例如，`plugin.json` 中版本为 `0.1.0` 时：

```bash
git tag v0.1.0
git push origin v0.1.0
```

仓库不需要保存生成的 ZIP。发布包由 GitHub Actions 构建，`dist/` 保持在忽略列表中。

### 使用方法

复刻已有参考图：

```text
Use $scientific-figure-builder to recreate this reference figure as an editable PPTX.
```

运行独立终审：

```text
Use $scientific-figure-reviewer to audit this completed PPTX against the reference.
```

重建 skill 自带强制的逐块和整图审核，并且不会自动调用或推荐独立终审 skill。

### 仓库结构

```text
Scientific-Figure-Creator/
├── .github/workflows/release.yml
├── .agents/plugins/marketplace.json
├── plugins/
│   └── scientific-figure-builder-reviewer/
│       ├── .codex-plugin/plugin.json
│       └── skills/
│           ├── scientific-figure-builder/
│           └── scientific-figure-reviewer/
├── scripts/
│   ├── build_release.py
│   └── validate_package.py
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

### 贡献与许可证

请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。贡献内容需要保留失效关闭验收规则、复杂对象边界，以及终审 skill 仅显式调用的约束。

项目采用 [MIT License](LICENSE)。

仓库许可证适用于插件、skills、脚本和文档。  
它不授予第三方参考图的使用权，也不会自动判定用户生成的 PPTX 文件和素材采用何种许可证。

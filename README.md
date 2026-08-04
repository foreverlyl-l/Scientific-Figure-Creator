<div align="center">

# Scientific Figure Initializer, Builder & Reviewer

科研图初始化、PowerPoint 重建与独立审核技能

<p>
  <a href="./README_EN.md">English</a> |
  <strong>中文</strong>
</p>

</div>

Scientific Figure Initializer, Builder & Reviewer 是一组面向 Codex 的开源 skill，用于初始化科研图工作流、把参考图重建为可编辑 PowerPoint，并执行独立终审。

仓库包含三个并列且命名一致的 skill：

- `scientific-figure-initializer`：原仓库 Builder 的完整工作流，负责整图初稿、人工冻结、素材处理、重建协调和施工期验收；
- `scientific-figure-builder`：由 `ppt-shape-recreate-review` 更名而来，专门把参考图分块重建为可编辑 PowerPoint 原生对象；
- `scientific-figure-reviewer`：负责用户显式调用、只读且独立的最终审核。

## 现在能做什么

- **Initializer — 整图初稿与冻结：** 建立面板、节点、文字、公式、输入输出、连线方向和阅读顺序的语义规格，再通过用户明确选择的图像后端生成完整初稿。完成分块及整图语义检查后，只有用户明确确认才生成带 SHA-256 的冻结记录。
- **Initializer — 完整工作流协调：** 保留原 Builder 的自动边界检测、裁剪清单、Artifact Tool 重建协议、受控图例高清化和逐面板并排验收能力，不对原功能进行拆分或删减。
- **Builder — PowerPoint 形状重建：** 对参考图进行语义分块和原子素材拆分，建立 object inventory，严格区分简单原生图形与复杂图例，并以分块审核和整图审核作为完成门禁。
- **Builder — 可编辑对象优先：** 文字、公式、边框、色块、简单图形、箭头和连接线使用 PowerPoint 原生对象；复杂设备、纹理和密集曲线可以使用可追踪裁剪，禁止用低质量通用形状冒充。
- **独立最终审核：** 只有用户明确调用 `scientific-figure-reviewer` 时才执行只读终审。它不会由 Builder 自动触发，也不会自动修改 PPT。

## 可交付内容

- 可编辑 PPTX；
- 冻结初稿、`figure_spec.json` 和 `draft_lock.json`；
- 原子裁剪素材、资产清单和边界检测证据；
- 高清化审核与安全回填清单；
- PPT 渲染图、逐面板并排图和施工审核报告；
- 用户显式请求时生成的独立最终审核报告。

## 主要局限

- 初稿和生成式高清化依赖当前 Codex 环境中实际可用、并由用户明确选择的图像后端；模型生成结果仍需要语义审核和人工确认。
- 显微图、实验曲线、医学影像等科研证据图禁止生成式改写，只允许采用明确、非生成式的方法处理。
- 当前重点是 PowerPoint，不能保证像素级复刻，也尚未交付可编辑 `.drawio` 文件。

## 适合的场景

- 深度学习、非视觉领域模型、数据流程、系统架构、机制和方法框架图；
- 科学性主要由文字、模块、公式与连接关系表达，图例用于辅助理解的科研图；
- 需要统一底色和画风，同时希望保留可编辑文字、图形和连接线的项目；
- 允许强模型与人工参与语义判断、初稿确认和最终验收的工作流。

后续将继续提高初稿生成和受控高清化的稳定性，并增加可编辑 draw.io 重建与交付。

## 许可范围

仓库许可证适用于插件、skills、脚本和文档。  
它不授予第三方参考图的使用权，也不会自动判定用户生成的 PPTX 文件和素材采用何种许可证。

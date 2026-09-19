# 图示设计工坊 · diagram-studio

一个用于 Codex 的本地图示 Skill：根据内容选择图型，生成架构图、流程图、结构图、甘特图和数据图表，并交付 SVG、可编辑的 draw.io 源文件及检查记录。

它先建立对象、关系和数据模型，再选择排版与视觉表达。普通流程、树和分层架构支持自适应文字、节点尺寸及连线路由；复杂内容可另生成总览、局部关系页和阅读详页。专门图型使用相应脚本，支持范围请看 [SKILL.md](SKILL.md) 与各项参考文档。

## 安装到 Codex

在终端运行：

```bash
git clone https://github.com/leolemon777/diagram-studio.git ~/.codex/skills/diagram-studio
```

然后在 Codex 中使用 `$diagram-studio`，例如：“用 `$diagram-studio` 画一个带异常回流的客户服务流程图，给我 SVG 和可编辑源”。也可以把整个仓库放到你的 Codex Skills 目录，并阅读 [SKILL.md](SKILL.md)。

## 直接试用生成器

基础生成器使用 Python 3.9+ 标准库，不需要 API 密钥或远程服务。部分专业图表另需 Matplotlib；自适应排版可选 Pillow 获取更准确的字体度量。

```bash
python3 scripts/render.py assets/examples/01-system-architecture.json --out /tmp/diagram-architecture --theme light
python3 scripts/render.py assets/examples/02-workflow.json --out /tmp/diagram-workflow --theme light
python3 scripts/expression_lab.py --out /tmp/diagram-expression-lab
```

前两条生成架构与流程的 SVG、draw.io、阅读页和检查文件。第三条生成四组共八种表达的离线对照页；[演示文件](demos/expression-lab/index.html)也保存在仓库中。演示数据为模拟数据，四组分别展示营销转化、教育前后对照、项目时间与依赖、客户服务分支与回流。

## 使用边界

- 目录条目不等于独立渲染器，也不代表每种图型都完成了视觉验收。复杂图生成后要查看实际输出，核对数据、方向、文字和连线。
- SVG 与 draw.io 是可继续编辑的源；目标编辑器的实际拖动、保存与重开情况需要对具体文件验证。
- 工程、医疗、科研等专业图只能按已实现的输入与校验范围使用，不能替代专业审查。
- 研究参考包括公开的图示产品与设计资料；此项目为独立实现，不包含商业模板、图片或字体文件，也不隶属于万兴图示。

本仓库目前用于公开试用与反馈，尚未附开源许可证。

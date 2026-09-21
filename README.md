# 图示设计工坊 · diagram-studio

**中文** · [English](README.en.md)

这是一个供 Codex 使用的本地图示 Skill。你用自然语言说明内容与用途，它会选择合适的图型、组织信息、绘图并检查结果；也可以直接运行仓库中的 Python 生成器。适合需要架构图、流程图、关系与结构图、计划图和数据图表的人。

## 它可以画什么

| 任务 | 常见表达 | 支持方式 |
| --- | --- | --- |
| 架构与系统 | 业务/系统分层、C4、应用与云架构、网络和数据关系 | 普通分层架构支持自适应排版；专门模型按对应输入规则生成。见 [架构方法](references/architecture.md)。 |
| 流程与协作 | 流程、分支、异常回流、泳道、基础时序、BPMN 子集 | 普通关系流程支持自适应节点和连线；正式记法需对应后端与校验。见 [流程方法](references/process.md)。 |
| 组织与关系 | 组织树、任务分解、脑图、人物关系、责任矩阵 | 按树、网络或矩阵语义分别表达。 |
| 计划与运营 | 甘特、任务依赖、看板、PERT、里程碑、运营分析 | 日期、依赖、进度与计算由专门规则处理；[甘特等输入边界](references/rendering.md)需单独查看。 |
| 数据与科研 | 对比、趋势、分布、统计图、部分科学图 | 按真实数据和单位选择图形；专门统计图需相应 Python 依赖及验证。见 [数据图](references/charts.md)。 |
| 工程与行业示意 | 设施、能源、控制、软件基础设施及跨行业常见图 | 各专门脚本只覆盖文档说明的模型子集；需要领域复核。 |

它还支持针对**同一份数据**比较不同表达方式，改变阅读顺序与构图，同时保留数值、关系、单位和方向。[四个行业场景的八种表达](demos/expression-lab/index.html)是可重绘的实验示例。目录中的类型名称是检索入口，不代表每个类型都有独立渲染器；详细状态见 [验证记录](references/verification-status.md)。

首次试用可以直接走[双语六行业试用包](references/trial-guide.md)，按场景做一次内容修改，再检查 SVG、HTML、draw.io 和 JSON 的边界；本版的范围、证据和限制见[发布说明](references/release-notes-v74.md)。

不同后端的交付格式范围见[交付格式矩阵](references/delivery-matrix.md)；PNG/PDF 等专门格式不会被普通后端默认承诺。

关系网络的双语跨行业案例见[网络演示](demos/network/index.html)：对象、方向、返回关系和三页详读均保留，适合先看结构再按群组拆图。分层职责与横向关注点见[架构演示](demos/architecture/index.html)；普通步骤、判断和异常回流见[预约流程演示](demos/flow/index.html)；同一份排期的汇报、执行和打印版见[甘特图演示](demos/gantt/index.html)；同一社区服务场景的 SWOT 双语矩阵见[SWOT 演示](demos/swot/index.html)；消息先后可看[交互时序演示](demos/sequence/index.html)，返回消息以虚线和方向保留；并行工作与汇合约束见[任务依赖演示](demos/dependency/index.html)；角色交接与异常回流见[责任泳道演示](demos/swimlane/index.html)。

## 怎么用

如果不知道该选哪种图，克隆仓库后在浏览器打开本地的[中英双语选图向导](demos/chooser/index.html)：按“想让读者看懂什么 → 图型 → 风格”选择，填入自己的内容后复制生成的 `$diagram-studio` 指令。向导按能力登记提供 30 项已登记能力的选型提示，新增精益画布和用户路径故事板；它本身不渲染任意输入，完整成图仍由 Codex 使用 Skill 完成。向导的后端、格式和证据状态来自[能力登记](references/capability-registry.md)，不会只根据旧页面文案宣称支持。风格卡会复用当前选中图型的真实缩略结构，同时仍是方向示意；实际支持范围见[风格家族](references/style-families.md)。

### 1. 安装给 Codex

在 macOS 或 Linux 的终端运行：

```bash
git clone https://github.com/leolemon777/diagram-studio.git ~/.codex/skills/diagram-studio
```

如果这个目录已经是 Git 克隆，可以在其中运行 `git pull` 更新；如果是手动复制的目录，先备份再替换。Windows 用户可以把仓库放到 `%USERPROFILE%\.codex\skills\diagram-studio`。之后在 Codex 任务里写 `$diagram-studio`，再描述你需要的图。Skill 的完整工作规则在 [SKILL.md](SKILL.md)。

下面三种请求都可以直接复制后改内容：

```text
用 $diagram-studio 画一张订单履约流程图：下单→库存检查→付款→发货→签收；库存不足回到补货，付款失败结束。标出判断条件，交付 SVG 和 draw.io 源。

用 $diagram-studio 做一个软件系统架构图：面向产品评审，展示前端、API、订单服务、库存服务和数据库；只画我明确给出的调用关系，另给适合汇报的总览与详细页。

用 $diagram-studio 比较四个课程的前后成绩：给我两种看变化的表达，保持同一份数值和 0–100 分口径，并说明各自适合回答什么问题。
```

告诉它**给谁看、想回答什么问题、必须出现的内容和关系、数据单位、输出格式与尺寸**，结果会更可靠。缺少关键事实时可以让它标明假设；不要让示例数据冒充你的真实数据。中文和英文请求都可以使用同一个 Skill。

### 2. 不经 Codex，直接运行示例

基础生成器需要 Python 3.9+，不需要 API 密钥或远程生成服务。请在仓库根目录运行：

```bash
python3 scripts/render.py assets/examples/01-system-architecture.json --out /tmp/diagram-architecture --theme light
python3 scripts/render.py assets/examples/02-workflow.json --out /tmp/diagram-workflow --theme light
python3 scripts/render.py assets/examples-en/architecture.json --out /tmp/diagram-architecture-en --theme light
python3 scripts/render.py assets/examples-en/workflow.json --out /tmp/diagram-workflow-en --theme light
python3 scripts/expression_lab.py --out /tmp/diagram-expression-lab
```

前四条分别生成中英架构图、流程图。`render.py` 的普通输出包含 SVG、draw.io、原始 brief、场景和检查记录；自适应模式还会生成阅读 HTML 与多页源。最后一条生成四组、八种表达的离线对照页；演示数据均为模拟数据。更多输入字段见 [生成格式](references/rendering.md)。部分专业图表需要 Matplotlib，自适应字宽度量可选 Pillow；缺少依赖时按对应后端文档安装。若要在隔离环境运行跨行业、数据艺术或科学后端，可执行 `python3 -m pip install matplotlib pillow`；没有这些可选依赖时，普通 SVG/draw.io 生成仍可运行。

## 多元白板方法与 UI/UX

结合 Boardmix 公开研究及登录后四种模板的实看，选图向导新增“洞察与共创”：亲和图、旅程、服务蓝图、复盘行动板、用户故事地图和用户路径故事板。按目的解释选择，并显示实际支持范围与示例；切换保留输入和键盘焦点。旅程图和服务蓝图现在分别有专用中英后端，保留证据链、服务分界线和显式交接；[输入规则](references/experience-maps.md)。故事地图现有专用自适应生成器，用户路径故事板补齐前置条件、状态、下一步、分支和异常；[故事板输入规则](references/user-path-storyboard.md)。战略与执行新增精益画布，和商业模式画布保持不同问题与布局；[精益画布输入规则](references/lean-canvas.md)。选图向导按类型限制实际可用格式并记住各分类的图型选择；实时协作和投票服务未实现。后续累计实看 12 种模板，并由 Grok CLI 调研 8 条 X 候选；[证据与后续重点](references/boardmix-deep-study.md) 明确区分画布观察和仅正文线索。见 [方法与来源](references/boardmix-study.md) 和 [实际示例](demos/workshop-study/index.html)。

## 五类精修与验收

普通流程、分层架构、执行甘特、单系列对比和趋势新增精修模式：按长文字扩展、区分主线和回流、保留正负值与缺测，提供不同表达。运行 `python3 scripts/refinement_suite.py --out /tmp/diagram-refinement`，再用本地 HTTP 服务打开该目录，可查看中英切换的 11 份原版、修改与对照样例。输入方式与范围见 [五类精修规则](references/refinement.md)。

截至 v74，源仓库与安装目录均有 130 项回归通过（此前基线为 128 项，新增六行业试用包的 receipt 哈希、scene/QA 解析、实际变更文字可见性和行业语义回归）。23 个演示页已在 390×844、768×1024、1280×720、1600×900 四种实际浏览器视窗测量，页面级横向溢出为 0/92；另对流程、架构、泳道、甘特、网络、数据叙事、故事地图、用户路径和精益画布 9 个热门页的嵌入内容做了 390×844 与 768×1024 实测，页面溢出为 0/18，窄屏默认进入可读原尺寸并把宽图留在明确的内部滚动区；嵌入文字实际显示最小字号为 14px，甘特紧凑打印版为 12px。15 个代表性 draw.io 文件已在 diagrams.net 中修改、保存并重开，覆盖架构、泳道、时序、条形图、中英精益画布、用户路径故事板、教育体验地图和树状思维导图等热门结构。六个跨行业试用案例现在各有修改后的 JSON、SVG、draw.io、scene、QA 和 delivery receipt，并由回归测试验证输入哈希、receipt 清单、QA 状态和变更文字真的出现在预览中。检查不代表所有图型的原生编辑或 JEV 审核已完成，详见 [验证记录](references/verification-status.md)。

## 流程与交付改进

普通自适应流程现在会分别处理前进分支与回流，保留所有连线标签。阅读页支持中英界面与“总览 / 清晰阅读”，并显示实际字号；字太小会提示复核。`render.py` 先在临时目录完成整套图和详页检查，再替换成品；生成失败会保留上一版，成功附 `delivery.json` 输入与输出校验记录。公共协议还可检查稳定 ID、关系端点、显示文本和独立版本快照，见[交付协议](references/delivery-contract.md)。具体范围与限制见[自适应布局](references/adaptive-layout.md)。这些改进吸收了 [Archify](https://github.com/tt-a1i/archify) 的公开设计思路，代码独立实现。

## 交付与边界

Skill 会选择图形表达并保留可修改的源文件；脚本不会自行理解自然语言，需求理解和最终视觉判断由运行它的助手完成。生成后要实际查看文字、箭头、分支、单位和数据；自动边界检查通过不等于读者一定看懂。

SVG 与 draw.io 可以继续编辑。目标编辑器能否逐对象拖动并保存重开，需要针对具体文件验证。工程、医疗、科研等专业图只适用于已实现的输入与校验范围，不能替代专业审查。

项目参考公开的图示设计资料，代码、布局和示例独立实现；不包含商业模板、图片或字体文件，也不隶属于万兴图示。本仓库目前用于公开试用与反馈，尚未附开源许可证。

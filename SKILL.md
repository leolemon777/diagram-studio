---
name: diagram-studio
description: 根据自然语言创建架构图、流程图、结构图与数据图表，按内容排版并交付 SVG 和可编辑源。Create architecture diagrams, workflows, structural diagrams, and charts from briefs with adaptive layout and editable outputs. Does not replace professional engineering validation.
---

# 图示设计工坊

English users can read the [English usage guide](README.en.md); the same input model, semantic checks, output formats, and quality rules apply to requests in either language.

核心目标是让用户给出的内容自动获得清楚、合适且精致的表达。先理解信息主次和关系，再选择布局；根据实际成图反复修正，交付可继续修改的成果。图型数量、脚本执行成功或零越界均不能代替视觉完成度。

用户要创新图形、多角度探索或摆脱常规模板时，读取 [图形表达创新](references/expression-design.md)。围绕读者要回答的问题，比较结构与阅读顺序不同、事实一致的表达；覆盖各行业高频任务。创新保持数值、关系、单位和方向准确，不以奇特外形增加理解负担；也不把同一套卡片构图套到所有图型上。

用户要头脑风暴、调研归纳、旅程、复盘、故事地图、灵感板或白板交互时，读取 [Boardmix 方法与多元 UX](references/boardmix-study.md)。按目的组合步骤工作区、主题簇、带直白标签的视觉隐喻或二维层次；长画布使用有名称的导航及清晰尺寸。保留观察来源、分歧和行动去向；新颖结构可以独立设计，但区分方法配方、已实现后端和实测功能，不把模板入口当生成能力。

万兴图示是研究参考，交付使用独立编写的规则和代码。观察范围见 [研究依据](references/research.md)，不要声称已复制全部模板、符号、私有提示词或算法。

## 内容自适应与视觉修正

高质量的普通流程、分层架构、执行甘特、单系列对比和趋势，先读 [五类精修规则](references/refinement.md)，优先使用 `layout.profile: "refined"`。按已有真实关系设置主线，保留正负值、实际日期间隔与缺测；用同内容修改样例复查排版。固定坐标、其他甘特版本与专业后端按其原有规则处理，不强套此模式。

普通流程、关系、组织/任务分解和分层架构先读 [自适应布局](references/adaptive-layout.md)。给出完整内容、稳定 ID 和真实关系，让生成器决定框尺寸、方向与路由；树图和分层架构默认启用，普通 graph 未给固定坐标时默认启用。不要先手写所有坐标再声称自动排版。

长内容先分清名称、说明与关系标签，不擅自删事实。复杂图使用总览、局部关系图、对象详解和完整关系索引；可将冗长说明放入详页，但必须保留可追溯的原文。大图总览缩到窗口只能用来观察结构，不能当作正文可读的证明。

生成后打开真正的 SVG/阅读页：查长中文、标题、菱形内部文字、分支标签与反馈线，再判断主次、拥挤和阅读顺序。阅读页会运行浏览器实际文字边界检查；若有问题，修正模型角色、布局方向、分组或排版代码并重绘，再查看同一份输出。几何失败不能作为最终成品提交，视觉不清楚也要继续调整。检查状态只记录实际完成的范围。

专门的数据图、甘特、时序、BPMN、工程和科学图仍走各自后端；按其语义自适应排版和实际查看。当前自适应引擎没有自动覆盖全部专用后端，不能把它们改成普通节点图来冒充支持。用户指定风格、原生格式或固定布局时保留这些约束。

流程含回流时，明确哪些是前进、哪些是返回；已知返回边可标 `role: "return"`，不要为了排版而更改真实方向。交付检查分开报告几何、窗口字号、浏览器文字边界与人工查看。`render.py` 会先生成并检查完整临时输出，再替换成品，附 `delivery.json` 校验记录；生成失败时保留上一版。具体边界见 [自适应布局](references/adaptive-layout.md)。

## 工作方式

1. 提取图的目的、读者、必须出现的对象、关系/数据、输出尺寸和格式。能由需求推断的直接采用；缺少会改变语义的关键事实才提问。将推断写入 `assumptions`，不能把示例数值或候选技术写成用户事实。
2. 先用 [结构选择规则](references/structure-selection.md) 判断关系，再查 [全部类型](references/all-types.md)；完整规则库含 326 条入口（中文目录 208 条＋补充细分 118 条），另有 [国际目录 185 条逐项映射](references/international-crosswalk.md)。条目含主题/同义分类，不等于 326 个独立渲染器。蒸馏范围按各行各业的高频需求、可复用性和专业价值确定，不以工业场景为主轴；过时、重复、季节过窄或高度专业入口保留检索但不计入热门范围，口径见 [蒸馏范围](references/distillation-scope.md)。目录的“有示例”和实际生成、渲染检查、人工查看是不同证据等级，先读 [验证状态](references/verification-status.md)，不能把目录覆盖率说成质量验收。按需搜索 `python3 <skill-dir>/scripts/knowledge.py <关键词>`，读取 `--card <ID>`。用户要“全部类型”时用 `--list` 或完整索引，不能用默认前 12 条冒充全部。
3. 阅读命中卡片的最小输入、语义、变体与择优规则，并结合 [方法对比](references/selection-playbook.md)、[来源证据](references/source-comparison.md) 和 [符号语法](references/symbols-and-grammar.md) 选择实现。需求同时含结构和流程时，优先两张互相引用的图。结构范例现有 60 个，另有 5 个专业后端示例及 24 个深化科研范例，以及 12 套能源分析配方；按卡片的 `example_paths` / `advanced_example_paths` / `scientific_example_paths` / `energy_example_paths` 读取，通用范例也可用 `scripts/catalog.py <关键词>` 搜索，见 [范例索引](references/library-index.md)。新增结构/数据图的输入语法见 [扩展布局](references/extended-layouts.md)。

   按领域进一步读取：
   - 系统/企业/云/网络/数据架构：[architecture.md](references/architecture.md)
   - 流程/泳道/BPMN/状态/时序：[process.md](references/process.md)
   - 组织/脑图/关系/分解结构：[structure.md](references/structure.md)
   - 数据图表/看板：[charts.md](references/charts.md)；科研统计、模型评估与三线/消融表按需读取 [科研图表方法与输入](references/scientific-atlas.md)
   - 甘特/路线图/战略/分析画布/信息图：[planning.md](references/planning.md)
   - 水电耗、能源、同比/环比、负荷、单耗、目标与前后对照：[能源与运行分析](references/energy-atlas.md)，12 套配方用 `scripts/energy_plot.py`。
   - OEE、工位平衡、控制图、价值流、SIPOC、销售、库存和综合能耗：[运营与精益配方](references/operations-atlas.md)，9 套用 `scripts/operations_plot.py`。从 `assets/operations-examples/` 读取命中的一份输入，`knowledge.py` 卡片的 `operations_example_paths` 给出路径。
   - 子组均值/极差、不合格比例、不合格件数、缺陷与单位缺陷：[控制图方法](references/spc.md)，X̄–R/X̄–S/p/np/c/u/EWMA/CUSUM 用 `scripts/spc.py`；输入见卡片 `spc_example_paths`。I–MR仍用原运营后端。
   - 故障树/错误树：读取 [静态故障树](references/fault-tree.md)，AND/OR、重复事件最小割集及明确独立基本事件概率用 `scripts/fault_tree.py`，示例见 `fault_tree_example_paths`。相关性、动态及其余变体仍待补。
   - 质量屋/需求到技术优先级：读取 [质量屋方法](references/house-quality.md)，用 `scripts/house_quality.py`；示例路径见 `house_quality_example_paths`。单阶段质量屋不等于完整多阶段QFD。
   - 多阶段QFD/需求逐层展开：读取 [多阶段QFD](references/qfd-deployment.md)，用 `scripts/qfd_deployment.py`；`qfd_example_paths` 返回完整承接与显式筛选输入，输出含原需求贡献和多页draw.io。
   - 事件树/防护响应路径：读取 [事件树方法](references/event-tree.md)，用 `scripts/event_tree.py`；`event_tree_example_paths` 包含定性、条件概率和频度模式。保留路径条件及终止理由，不擅自假设独立。
   - PERT/CPM与任务网络：读取 [PERT计算与AON图](references/pert.md)，`scripts/pert.py`计算精确时间，`scripts/pert_render.py`成图；输入由卡片`pert_example_paths`返回。当前限零时滞FS，不宣称资源计划或完成概率。
   - PLC梯形逻辑/串并联触点：读取 [布尔梯形图](references/ladder.md)，用 `scripts/ladder.py`；`ladder_example_paths` 返回九套教学输入。定时、计数与边沿另读 [时间功能块](references/ladder-timed.md)。明确扫描顺序、多写入策略和初始状态；不等于厂商程序编译或物理接线图。
   - 泳道看板：读取 [工作流、WIP与显式策略](references/kanban-swimlane.md)，用scripts/kanban_render.py；kanban_example_paths返回设备维修教学输入。当前限单板、逐列与逐泳道WIP、阻塞和四类服务；历史轨迹、CFD及实时系统同步未实现。
   - 人物关系、人力资源、RACI、团队画布、影响/亲和、矩阵组织与因果回路：读取 [组织与关系模型](references/organization-relations.md)，用 `scripts/organization_relations.py`；`organization_relation_example_paths` 返回八份模拟输入。关联和影响必须分开，责任/分组/双重汇报/回路极性均由输入校验。
   - 企业应用、AWS/Azure/Google Cloud、企业分层、ArchiMate、Kubernetes、C4组件与动态图：读取 [架构模型](references/architecture-models.md)，用 `scripts/architecture_models.py`；`architecture_model_paths` 返回九份模拟输入。先固定抽象层次与身份/资源/网络边界，再校验有向流、追踪、选择器或静态关系引用；云示例保留官方服务名但不捆绑厂商图标包。
   - Chen ER、园区/详细网络、机架、Active Directory、网络位置、网站/iPhone/Android线框：读取 [软件与基础设施模型](references/software-infrastructure.md)，用 `scripts/software_infrastructure.py`；`software_infrastructure_model_paths` 返回九份模拟输入。先校验键/基数、逐端口链路、U位、目录包含、地点来源或交互状态，再排版；厂商名称只作语义说明，图中使用中性矢量元素。
   - 办公室布局、电气与通信规划、座位、门禁、消防疏散、暖通、端子接线、电气单线与给排水：读取 [设施与工程平面模型](references/facilities-engineering.md)，用 `scripts/facilities_engineering.py`；`facilities_engineering_model_paths` 返回九份模拟输入。先校验尺寸、路线、端点、系统平衡、径向关系或排水坡度，再排版；所有专业结论保留属地审查和工程复核边界。
   - 电路与逻辑、系统图、线路/地理地图、数学/力学/光学/化学/实验装置、演示与出版物、品管/TQM、SysML v1 四图、国产云架构和故事分镜：读取 [最终常用类型](references/final-common-types.md)，用 `scripts/remaining_types.py`；`remaining_type_model_paths` 返回三十三份模拟输入。先按图型校验真值表、守恒、约束、拓扑、内容角色、阅读顺序、可用区或镜头时长，再排版。
   - 办公财务、招聘、教育、医疗、建筑家装、软件产品、行业信息图、旅游交通、新闻传播和营销卡片：读取 [跨行业热门类型](references/cross-industry-popular.md)，用 `scripts/cross_industry.py`；`cross_industry_model_paths` 返回四十六份模拟输入。先校验关系、算术、空间边界、页面跳转、来源字段、内容角色或学习完成标准，再排版；科学类仅生成概念关系示意，不能作为解剖、分子或诊断图。
   - UML部署图：读取 [运行节点、制品与逻辑定义分离](references/deployment-diagram.md)，用scripts/deployment_render.py；deployment_example_paths返回教学输入。当前限单行设备实例、单层执行环境、嵌套制品、一对一显化和设备通信路径。
   - UML活动图：读取 [令牌流、责任分区与两类终点](references/activity-diagram.md)，用scripts/activity_render.py；activity_example_paths返回教学输入。当前限三泳道、自上而下活动、显式对象流、基本并发与返工回路。
   - UML组件图：读取 [组件、端口与接口协作](references/component-diagram.md)，用scripts/component_render.py；component_example_paths返回教学输入。当前限黑盒逻辑组件与简单装配连接，部署与内部实现另图表达。
   - UML用例图：读取 [主体、参与者、include与extend](references/use-case.md)，用scripts/usecase_render.py；usecase_example_paths返回教学输入。当前限单主体，详细行为步骤另用文字、活动或交互规格。
   - UML对象快照：读取 [对象实例、槽位和链接](references/object-snapshot.md)，用scripts/object_render.py；object_example_paths返回教学输入。类模型约束、多重性及复杂变体尚未覆盖。
   - N-S结构化程序图：读取 [结构化程序输入与布局](references/structured-program.md)，用scripts/structured_render.py；structured_example_paths给出两套输入。表达式仅文本，CASE源已有保存重开验证；循环源及完整变体仍待验证。
   - CTUD双向计数与混合梯形扫描：读取 [CTUD输入、双输出与时序](references/ctud.md)，四套输入在`assets/ctud-models/`；独立序列用ctud_render.py，梯形接线用ladder.py，按输入结构选择，不混用两种schema。
   - 其余电气/P&ID/平面/科学示意：[specialist.md](references/specialist.md)
4. 读取 [视觉规范](references/style.md)；用户定义视觉风格。当前明确方向为科研感、Claude 风格、克制配色；用户已明确喜欢并提供底色色块 #F1EFEB，以 `light` 暖灰科研实现。具体样图的其余细节尚待用户评价。读取用户新提供的视觉要求后覆盖主题，不能把本次参数当作永久偏好。提到“更高级”时优先改善阅读层次、对齐、线条和信息组织，不默认添加装饰。
5. 每条规则含专用提示词：`python3 <skill-dir>/scripts/knowledge.py --card <ID> --prompt '真实需求'`。可搭配 [通用任务块](references/prompts.md)。先建立节点/边/数据模型，再排版。图型规范不能被风格覆盖。
   用户要鱼骨参考配色、纸感科研或多配色比较时，按需读取 [七套主题与排版规则](references/editorial-style.md)。这些是可选风格，不能当作全部已获用户认可。通用矢量生成器支持 `editorial-warm` 等主题；运营后端支持 `warm` 等七个简写。
   用户提到 Lieflat、归藏、Kami，或要更多独特风格、跨图型适配时，按需读取 [六套风格家族](references/style-families.md)。它们将构图、字体、旁注和图形语言与颜色分开；使用 `scripts/style_family.py` 和 `assets/style-family-examples/` 可重绘六家族 × 四种图版。其它图型按迁移规则另行排版，不宣称全目录已适配。
   用户要纯白背景、白底报告或白底上的精致科研/商业图版时，读取 [纯白精研的字体、线条与数据规则](references/white-precision.md)。`assets/white-precision.json` 定义纯白视觉角色，`scripts/white_plate.py` 对现有 12 种分享图版逐项精修；保留原配色。其他图型与比例按后端重新布局验证。
   用户要分享图册的更多配色或同内容颜色对照时，读取 [六套新色与角色对比度](references/share-palettes.md)。`assets/share-palettes.json` 保留原三色并新增六色，`scripts/recolor_plate.py` 可重绘已有 Plate 场景；当前仅以 12 张固定图版验证，不等于全后端与全比例适配。
   神经网络图需要细线、节点明暗、局部聚焦或逐层阅读时，读取 [细线交互网络](references/network-ui.md)。`scripts/network_explorer.py` 提供三主题、横竖重排的8→14→10→3 MLP示例，激活实际计算，支持SVG/PNG及模型JSON；不等于所有神经网络家族已覆盖。
   要充分落实 Lieflat 的精致数据图、逐条观测、刻度/点阵/细线表达时，读取 [数据图形细读配方](references/data-art.md)，优先按数据含义选择 `scripts/data_art.py` 的12类配方。它们提供细读/快读、原七色、离线交互 HTML 与矢量源；配方、示例和对比不等于原参考项目的全量复刻。
6. 常见图型使用本地生成器，参照 [生成格式](references/rendering.md) 和 `assets/examples/`：
   用户要求横屏、竖屏、自定义比例或分辨率时，读取 [画布尺寸与排版](references/canvas-sizing.md)。现有四类风格图版与12类精致数据图可用 `--ratio/--long-edge` 或 `--width/--height` 自适应重排；DPI独立设置。其他后端需按各自布局规则处理并验证，不把预览缩放称为导出分辨率改变。
   ```bash
   python3 <skill-dir>/scripts/render.py brief.json --out <output-dir> --theme light
   ```
   生成 `.svg`、`.drawio`、`.scene.json` 和 `.qa.json`。自适应模式还生成离线阅读 HTML、阅读详页、关系索引和多页 draw.io。原始 brief 也随交付保存。该脚本是排版与导出器，自然语言理解与视觉判断由当前助手完成；没有隐藏的远程 AI 请求。
   生成器未覆盖的标准符号/版式可直接编写 SVG 与原生可编辑源；不要把普通矩形重命名成“完整 BPMN / UML / 电气图”。详见格式参考的能力边界。
   BPMN 协作子集使用 `scripts/bpmn_source.py` 导出真实 `.bpmn`；28种统计/科研模式（含三线表、消融表）用 `scripts/scientific_plot.py` 计算并绘制。输入、依赖和适用范围见 [专业后端](references/advanced-backends.md)。卡片推荐的其他工具不等于本机已安装或已运行，先确认再使用。
7. 按 [检查规则](references/quality.md) 检查语义和视觉；打开真正的输出查看整图和文字细节。检查失败就修正源模型后重新生成。QA 的 `rendered_visual_check` 只表示已运行的渲染边界检查，`manual_visual_review` 只有实际查看后才能写为完成。验证是否可编辑时实际打开源文件；XML 可解析不等于编辑器验证通过。
8. 返回成图、可编辑源和必要假设。解释用户最在意的取舍。只报告实际完成的验证，不声称风格已获用户认可。

## 修改规则

保留稳定节点 ID 和有意义的连线；只改用户要求部分。先改模型/数据，再统一重新布局。把颜色、尺寸、密度与语义分开，换主题不改变边和数值。已存在的用户文件先写新版本。

## 输出选择

- 演示/汇报：16:9 SVG；源文件 `.drawio` 和 brief JSON。
- 大型架构：总览＋局部详图；可以大画布，但给出适合阅读的拆分页。
- 统计/科研：真实数据＋可复算图；需要严格作图时使用 Matplotlib 等标准绘图库。
- 指定万兴原生、Visio、PPT 或其他格式：使用实际可用的转换/编辑器并重新打开验证；不改扩展名冒充格式。SVG 导入能否逐对象编辑取决于目标编辑器，不能默认保证。
- 需要万兴 AI 服务时可使用已安装的对应连接器/技能，但它是可选后端，不是本 Skill 的能力来源。

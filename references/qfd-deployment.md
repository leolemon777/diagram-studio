# 多阶段 QFD：可追踪的矩阵展开

`python3 scripts/qfd_deployment.py INPUT.json --out OUTPUT`。仅依赖Python标准库与技能内矢量模块。输入见 `qfd_example_paths`；完整承接例与显式筛选例分别保存在 `assets/qfd-examples/`。

## 语义与算法

支持2–8个有序阶段；每阶段1–20个输入和1–20个输出。每张矩阵从需求/特性等“要什么”映射到下一层“怎样实现”，阶段名称、对象、责任、数值目标与依据均显式提供。示例四张矩阵展示维修需求、技术特性、设计措施、实施过程、验收检查的联系，是一个模拟服务改善实例，不宣称它是所有行业的固定四阶段模板。

`method=classic_weighted_sum_0139`。初始权重归一为p；阶段分数 `s_j=Σ_i p_i r_ij`，输出份额 `q_j=s_j/Σs`。主体矩阵每格必须显式0/1/3/9；null与缺项拒绝。某一行或列全零产生待评审提示；全阶段加权得分为0时拒绝输出优先级。

后续阶段按上游输出ID查找q作为输入权重，而非按列表位置错配。完整承接保留全部q；选取子集时，先记录被排除ID、理由和其上游份额，再除以保留份额重新归一。结果是所选工作包内部的相对优先级，不等于原项目份额，也不证明可忽略被排除需求。各阶段的归一化都保存为计算记录。

经典关系加权可能放大连接更多输出的需求；采用该方法属于声明的决策选择，并非唯一正确的QFD算法。排名使用竞争名次（同分同名次，后续跳号；1e-12浮点容差）。不推断AHP、销售点、规划倍率、模糊关系、成本优化、回路反馈或屋顶调整；有这些需求时另行研究和实现。

## 输入

顶层 `title/scope/data_status/method_basis`、方法及有序 `stages` 必填。每阶段唯一ASCII `id`、`title/input_kind/output_kind/relationship_basis`、`outputs/relationships` 必填。阶段ID不能占用导出文件名 `overview/deployment/priorities/origin-trace`。

首次阶段提供 `weight_basis` 和 `inputs`：每项唯一 `id/label/source` 与非负有限 `weight`，至少一个正值。用按最大权重缩放的归一化避免超大权重求和溢出。

后续阶段不得再提供 `inputs/weight_basis` 来覆盖继承结果，必须提供 `input_ids` 与 `carry_mode`：

- `full`：完整、唯一地列出上一阶段全部输出，允许改变顺序，矩阵行顺序随之匹配。
- `subset_renormalize`：选定输入，并用 `excluded=[{id,reason}]` 覆盖其余上游输出。选取与排除不重叠、不能遗漏、不能重复，且保留总份额必须为正。

输出 `outputs` 每项必填：全局唯一 `id`、`label/source/owner`、`direction=min|max|target`、数值 `target`、`unit`。数值目标是输入的工程评审结果，算法不从优先级推断物理指标。后续阶段自动继承原输出标签和目标信息。

`relationships` 行顺序对应本阶段inputs/input_ids，列顺序对应outputs。未知值必须补评，零值必须是确认的无关联。

## 追踪与产物

保存原始需求×本阶段输出的贡献矩阵。首次以每项原需求的加权关系贡献初始化；后续沿矩阵关系传递并经过相同的筛选及归一化。每列原始需求贡献之和等于该输出优先级。这个分解是计算来源，不是因果概率；筛选与关系密度会改变原需求的最终份额。

输出包括总览和逐阶段 SVG/原生draw.io、带总览和全部阶段页的 `deployment.drawio`、完整输入/分析JSON、逐阶段场景/QA JSON、`priorities.csv`、`origin-trace.csv`。所有浮点计算以JSON/CSV为准；图中百分比经过舍入。

原生编辑器可修改文字和布局，但业务值修改后应重新运行JSON输入，编辑器中不自动复算。当前示例为模拟数据；不把验收目标当作现场达标证据。每份最终图应实际查看，合并draw.io需在编辑器核对页面与可编辑性。

## 来源与范围

- [ASQ QFD](https://asq.org/quality-resources/qfd-quality-function-deployment)：需求优先级向责任职能展开，质量屋和后续矩阵关系；2026-09-17读取方法段落。
- [van de Poel 2007, §2](https://link.springer.com/article/10.1007/s00163-007-0029-7)：经典加权关系矩阵、后续展开及方法限制；2026-09-17读取相关段落。
- [QFD Institute FAQ](https://www.qfdi.org/faq)：质量屋不等于完整QFD，沿用本项目已读的范围记录。

此实现是上述公开方法的独立软件表达，不宣称ISO 16355全文符合性或穷尽所有现代QFD方法。动态反馈、多对多阶段图、全部画布比例、其它专业原生格式与全主题视觉检查仍待补。

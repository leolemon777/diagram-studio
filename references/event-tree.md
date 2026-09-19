# 事件树 ETA：路径条件与结果归并

使用 `scripts/event_tree.py INPUT.json --out OUTPUT`。标准库与技能内矢量模块，无远程计算。`event_tree_example_paths` 返回定性、频度及三状态条件概率示例。

## 范围与输入

从一个已发生的初始事件出发，依次经过声明的防护阶段，直到明确的终点。支持1–8个顺序阶段、每次2–5分支、最多255个节点与64条终点路径。允许同一结果由多条不同路径到达，允许有理由的提前终止；不把树合并成有共享子节点的有向图。

顶层 `title/scope/data_status`、`mode`、`initiator`、`stages/outcomes/nodes/root` 必填。所有概率和性能若为假设应在data_status和来源中注明，不把示意图当现场风险评估。

- `mode=qualitative`：只列路径，拒绝夹带分支概率或初始频度，不生成数值风险。
- `mode=conditional_probability`：只算初始事件已发生条件下的路径概率，不能解释为全年发生概率。
- `mode=frequency`：在条件概率基础上乘以初始事件平均频度。`initiator.frequency` 必须给 `value/unit/source`，例如2次/年；频度可以大于1，不等于概率。输出保留原时间单位，不做单位转换或推导某时段内至少发生一次的概率。

`initiator` 包含 `id/label/source`。不支持直接输入初始事件概率，不能把它悄悄当频度。

`stages` 是唯一ID和名称的有序数组。`outcomes` 每项为 `id/label/description`，保存终点含义；所有声明结果必须至少有一条路径。

`nodes` 两种：

- decision：`id/kind/stage/context/partition_basis/branches`。context说明此前路径条件；partition_basis明确为什么分支互斥且完备。每个branch含局部唯一 `id/label/to`。定量模式还需 `probability/source`。
- terminal：`id/kind/outcome/termination_reason`。不得含stage/branches。即使已到最后阶段，也需说明终点判定；提前终止会记录后续未经过阶段。

根必须从第一个声明阶段开始，decision子节点必须是紧接的下一阶段。拒绝跳层、环、重复节点、悬空目标、不可达定义和共享子节点；共同结果通过不同terminal引用同一个outcome归并。状态可为成功/失效，也可为三个以上互斥状态。

## 条件概率与计算

每次分叉的概率都是以“初始事件＋此前全部路径”为条件。因而同一屏障在不同分支上的数值可不同。路径概率是这些条件概率的乘积（链式法则），无需擅自假设屏障无条件独立。

每个分叉显式给出全部概率，不自动补 `1-p`，也不归一化错误输入。单格必须是[0,1]有限数，不接受bool/null；分支和容差1e-12，记录残差。用80位十进制上下文计算，并在JSON/CSV输出十进制字符串，防止极小路径被二进制浮点下溢变成零。终点总和用1e-10容差复核。局部互斥完备性是模型输入前提，数值和为1不能证明真实工况已全覆盖。

同一结果的不同路径互斥时才可相加。零概率路径保留，不能借此删除未验证的场景。频度=初始频度×路径条件概率；结果频度同样按路径相加。算法不提供后果严重度、期望损失、置信区间、共因失效拟合或参数估计。

## 交付与审阅

输出 SVG、原生draw.io、输入/分析/场景/几何检查JSON与路径CSV。图中防护阶段按列，分支标签沿连线，终点列显示条件概率和频度，底部按结果归并；context、概率来源、提前终止理由和跳过阶段完整保留于JSON/CSV。

原生draw.io支持改文字、形状与连线；不自动重算业务数据。更新概率请修改输入重绘。大树、长分支标签、全主题、横竖比例与其它格式仍需逐份验图；几何检查不能取代现场语义审核。

## 研究依据

- [NRC事件树定义](https://www.nrc.gov/education-regulatory-research/glossary/event-tree)：从初始事件按照系统成功/失效展开路径；2026-09-17已读取正文。
- [NRC PRA背景](https://www.nrc.gov/regulations-legislation/fact-sheets-brochures/backgrounder-on-probabilistic-risk-assessment)：官方检索摘要说明路径归并及初始事件频度相乘；本次直接打开该URL受工具限制，未声称通读全文。
- [NRC PRA概览](https://www.nrc.gov/regulations-legislation/how-we-regulate/risk-assessment/probabilistic-risk-assessment-pra)：2026-09-17已读取Level 1段落，说明事件树与故障树的分工、路径频度按结果归并。

仅借鉴公开风险建模语义，示例使用一般设备教学情景；不是核设施模型、标准认证或安全许可依据。动态时间事件树、合并图、多初始事件联合模型、与故障树自动耦合、蒙特卡洛不确定性及完整专业导出仍待补。

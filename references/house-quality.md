# 质量屋：需求到可测技术特性

## 使用与方法边界

使用 `scripts/house_quality.py INPUT.json --out OUTPUT`。标准库依赖；输出原生 SVG、draw.io、输入/计算/场景/检查 JSON 与技术优先级 CSV。卡片 `cn-1180` 的 `house_quality_example_paths` 返回示例。

本后端是明确权重的经典单阶段质量屋。需求、测量特性、关系与目标须由使用者或评审给出；图形不能证明客户满意度、因果关系、实际质量或工程可行性。提供重要度权重本身，不自动添加销售点、改善倍率或竞争得分系数。

QFD不等于一张质量屋。经典有序多阶段需求追踪已另由 `scripts/qfd_deployment.py` 实现，见 [多阶段QFD](qfd-deployment.md)。AHP获取权重、模糊QFD、成本约束优化、技术对标曲线、行归一关系方法与屋顶调整方法尚未实现；不要混称本后端已经完成这些方法。

## 输入契约

必须提供 `title/scope/data_status/weight_basis/relationship_basis/roof_basis`，声明目的、数据是否模拟、权重、主体及屋顶关系依据。`method` 固定为 `classic_weighted_sum_0139`，禁止不声明算法就给出分数。

- `requirements`：1–20行；每行唯一ASCII `id`、`label`、非负有限 `weight`、`source`。总权重须大于0。
- `technical`：2–12列；唯一ASCII `id/label/source`、`direction=min|max|target`、数值 `target` 与 `unit`。目标由输入提供，绝不从分数反推物理目标。
- `relationships`：严格对应输入顺序的完整二维矩阵；每格显式0/1/3/9（无/弱/中/强）。`null`、漏格与布尔值拒绝，避免未调查被当作无关系。
- `roof`：每一对不同技术ID恰好一次。`a/b/value`，值为−2/−1/0/+1/+2或null；0表示已评估无关联，null表示未评估。正负是沿已注明期望改进方向的协同/冲突，绝非实测Pearson相关系数。每个菱形连接相应两列；JSON保存配对ID。
- 可选 `benchmark`：需求满意度对标，含 `scale=[最小,最大]`、`direction=higher_is_better`、`basis`、1–4个 `alternatives`。每方案 `label/scores` 与需求行一一对应；null显示问号。不同物理单位的技术测量值不能填进这里。

计算：先令 `p_i = weight_i / Σweight`，再令 `s_j = Σ_i(p_i × relationship_ij)`；技术占比 `s_j / Σs`。输出逐格贡献和竞争排名（同分同名次，随后跳号；1e-12浮点容差）。显示百分比可能有舍入差，CSV/JSON保留浮点结果。屋顶、技术目标和需求对标不改变得分。

全零加权关系拒绝生成优先级。未映射需求或技术、未评估屋顶对会在计算记录和图中提示。经典加权矩阵可能使关联较多的需求贡献更大；算法是明确的决策规则，并非唯一正确的权重传递办法。

## 视觉与编辑

屋顶仅显示配对评分，主体显示数值及强关系底色，单色仍可识别；需求权重与技术占比分开。列头同时显示改善方向；底部显示单位、目标、得分和排序。文字按容量自动换行，长标签需核对实际成图。横竖画布切换、多页拆分、超容量输入及全部主题尚未逐份验图。

draw.io是原生图元和文字，可修改排版；不在编辑器内重算。业务数据变化应修改JSON并重绘。v12技能包包含本增补；下载版本与验证范围见delivery-v12.md。

## 研究依据（2026-09-17读取）

- ASQ，质量屋的需求与技术关系、目标和两种对标区别： https://asq.org/quality-resources/house-of-quality
- ASQ，QFD部署流程与质量屋的位置： https://asq.org/quality-resources/qfd-quality-function-deployment
- van de Poel (2007), *Methodological problems in QFD and directions for future development*, §2：经典关系分值、权重传递、屋顶关系与归一化方法的差别；本文也讨论方法限制。 https://link.springer.com/article/10.1007/s00163-007-0029-7
- QFD Institute FAQ：质量屋是工具之一，单独建图不构成完整QFD。 https://www.qfdi.org/faq

以上是公开方法研究后独立编写的实现；未复制模板、付费课程或宣称ISO 16355全文符合性。

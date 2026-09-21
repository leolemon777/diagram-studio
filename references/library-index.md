# 结构范例索引

60 个范例按九个用途分组。名称是结构入口，具体语法以 JSON 的 type 和 references/extended-layouts.md 为准。

## 系统与软件

| 范例 | 输入与可复用语义 |
|---|---|
| [01 分层系统架构](../assets/examples/01-system-architecture.json) | 从用户入口到服务能力与数据底座；横向能力贯穿每层 |
| [12 逻辑数据模型](../assets/examples/12-data-model.json) | 三个实体与两条关系；基数直接标注，字段仅展示关键标识 |
| [13 系统上下文](../assets/examples/13-c4-context.json) | 只画目标系统、使用者和外部依赖；连线标明交互内容 |
| [14 部署拓扑](../assets/examples/14-deployment.json) | 逻辑服务、运行实例与网络边界分开；图中实例数量仅为演示 |
| [15 网络拓扑](../assets/examples/15-network-topology.json) | 连线表示链路，中心是接入交换节点；不暗示冗余与安全隔离 |
| [16 数据流图](../assets/examples/16-data-flow.json) | 处理过程使用动词；外部实体、数据存储和命名数据流分开 |
| [18 类结构](../assets/examples/18-class-diagram.json) | 三个分区分别是类名、属性和操作；连线为关联，基数直接标注 |
| [19 用例关系](../assets/examples/19-use-case.json) | 系统边界包围用例；角色在边界外；线表示参与关系 |

## 过程与时序

| 范例 | 输入与可复用语义 |
|---|---|
| [02 责任泳道](../assets/examples/02-workflow.json) | 三条责任泳道；信息不完整回到申请人，交付后由协调团队验收 |
| [05 交互时序](../assets/examples/05-sequence.json) | 纵向表示先后；虚线表示返回，图中不暗示实际耗时 |
| [17 状态机](../assets/examples/17-state-machine.json) | 边标注触发事件；退回与取消为明确转移 |
| [24 循环结构](../assets/examples/24-cycle.json) | 箭头沿同一方向闭环；每个阶段有明确产出 |
| [32 决策树](../assets/examples/32-decision-tree.json) | 每个问题都有明确分支，叶子是行动结果 |

## 关系与结构

| 范例 | 输入与可复用语义 |
|---|---|
| [03 组织结构](../assets/examples/03-organization.json) | 服务运营团队的职责结构；岗位职责独立于姓名 |
| [04 思维导图](../assets/examples/04-mindmap.json) | 把观察、机会、试验和复盘分开；分支是主题拆解，不是因果证明 |
| [22 概念图](../assets/examples/22-concept-map.json) | 概念之间用可读命题连接，允许交叉关系 |
| [23 辐射结构](../assets/examples/23-hub-spoke.json) | 辐射线表示主题关联，没有先后顺序 |
| [26 金字塔结构](../assets/examples/26-pyramid.json) | 形状表达层级，面积不代表数值比例 |
| [27 韦恩结构](../assets/examples/27-venn.json) | 交叠表示共同成员；圆面积不编码集合大小 |
| [28 同心层次](../assets/examples/28-concentric.json) | 由外到内表示包含关系，不表示数量大小 |

## 计划与协作

| 范例 | 输入与可复用语义 |
|---|---|
| [06 甘特排期](../assets/examples/06-gantt.json) | 按阶段、责任人和实际日期跟踪一场跨团队活动；深色条表示完成进度 |
| [21 工作分解结构](../assets/examples/21-wbs.json) | 父节点范围由子交付物分解；不把分解线当作时间依赖 |
| [29 时间线](../assets/examples/29-timeline.json) | 日期按自然日距离定位；上下错开说明，避免均匀排期造成误读 |
| [30 路线图](../assets/examples/30-roadmap.json) | 每行是一条工作流；每列是阶段，单元格给出交付重点 |
| [31 任务依赖网络](../assets/examples/31-dependency-network.json) | 箭头表示前置依赖；未进行工期计算，因此不标注关键路径 |
| [37 RACI 矩阵](../assets/examples/37-raci.json) | 每行一个 A；R 执行、A 负责、C 咨询、I 知会 |

## 商业与管理

| 范例 | 输入与可复用语义 |
|---|---|
| [07 SWOT 分析](../assets/examples/07-swot.json) | 社区服务平台四类因素；每条都是待验证假说，需要证据与负责人 |
| [33 商业模式画布](../assets/examples/33-business-model-canvas.json) | 保留九格的含义与位置；条目为待验证假说 |
| [34 PEST 分析](../assets/examples/34-pest.json) | 四个维度均需来源与时间范围；本图只提供研究问题 |
| [35 五力分析](../assets/examples/35-five-forces.json) | 中心为现有竞争，四周呈现外部力量；关系强弱需要证据 |
| [36 四象限](../assets/examples/36-quadrant.json) | 服务改进的影响与实施难度；坐标为演示评分，依据需要公开 |
| [38 用户旅程](../assets/examples/38-customer-journey.json) | 按使用者的经历组织阶段，区分行为与改进假说 |
| [39 服务蓝图](../assets/examples/39-service-blueprint.json) | 阶段为列，用户、前台、后台和支撑为行；表中边界需按组织调整 |
| [40 风险矩阵](../assets/examples/40-risk-matrix.json) | 示例等级 = 可能性等级 × 影响等级；序数评分不是概率 |
| [41 对比矩阵](../assets/examples/41-comparison.json) | 相同维度逐项对照；不使用未经提供的评分 |
| [42 价值链](../assets/examples/42-value-chain.json) | 箭头表示价值活动的阅读顺序，不自动代表系统调用 |

## 数据图表

| 范例 | 输入与可复用语义 |
|---|---|
| [08 横条比较](../assets/examples/08-bar-chart.json) | 同一活动周期、同一统计口径；条形从零基线开始 |
| [09 折线趋势](../assets/examples/09-line-chart.json) | 按周等距记录；保留原始数值，不使用平滑曲线 |
| [10 环图构成](../assets/examples/10-donut-chart.json) | 各类别互斥且属于同一总体；面积按人数比例计算 |
| [44 分组柱状图](../assets/examples/44-grouped-bar.json) | 各系列共享零基线和相同量纲 |
| [45 堆叠柱状图](../assets/examples/45-stacked-bar.json) | 每根柱的组成必须互斥且量纲一致 |
| [46 散点图](../assets/examples/46-scatter.json) | 每一点是一组配对值；位置不自动证明因果 |
| [47 气泡图](../assets/examples/47-bubble.json) | 气泡面积与第三个量成比例，半径不是线性编码 |
| [48 热力矩阵](../assets/examples/48-heatmap.json) | 同一色阶映射同一量纲，数值直接保留 |
| [49 雷达结构](../assets/examples/49-radar.json) | 各轴共享 0–100 量程；维度与评分均为演示 |
| [50 直方图](../assets/examples/50-histogram.json) | 分箱等宽且相邻；柱面积与频数成比例 |
| [51 瀑布图](../assets/examples/51-waterfall.json) | 增减从前一累计值起算；总量柱从零起算 |
| [52 面积图](../assets/examples/52-area.json) | 底部从零开始；横轴为等间隔类别，面积不额外表示独立指标 |
| [53 饼图](../assets/examples/53-pie.json) | 类别互斥且穷尽；扇形角度按真实比例计算 |
| [54 矩形树图](../assets/examples/54-treemap.json) | 每块面积与数值成比例；当前为单层构成 |
| [55 桑基结构](../assets/examples/55-sankey.json) | 带宽与流量成比例；由连接值计算两端总量，保持守恒 |
| [56 目标条图](../assets/examples/56-bullet.json) | 条长表示实绩，竖线表示目标；所有行共享量程 |

## 科研与分析

| 范例 | 输入与可复用语义 |
|---|---|
| [11 鱼骨原因分析](../assets/examples/11-fishbone.json) | 服务请求反复未完成的六类原因假说；连线不等于因果证据 |
| [20 科研技术路线](../assets/examples/20-research-route.json) | 研究问题、并行方法和验证环节分别呈现；全部为拟研究方案 |
| [43 验证 V 模型](../assets/examples/43-v-model.json) | 左右对应的是同层验证关系；底部实现连接设计与验证 |

## 信息表达

| 范例 | 输入与可复用语义 |
|---|---|
| [25 漏斗结构](../assets/examples/25-funnel.json) | 每层顶边宽度表示阶段数量；连续阶段数量不得递增 |
| [60 编号信息结构](../assets/examples/60-numbered-information.json) | 每个观点配一条解释；编号用于阅读顺序，不代表量值 |

## 工程与空间

| 范例 | 输入与可复用语义 |
|---|---|
| [57 空间布置](../assets/examples/57-floorplan.json) | 平面区划按输入尺寸同比缩放；不含建筑、消防或施工校核 |
| [58 基本电路](../assets/examples/58-circuit.json) | 电源、开关与负载以导线连接；仅作拓扑教学，不给出额定参数 |
| [59 工艺流程](../assets/examples/59-process-flow.json) | 容器、输送与处理单元按物料方向连接；这是概念 PFD |

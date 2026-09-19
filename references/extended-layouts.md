# 扩展结构语法

从 `assets/examples/` 选择完整输入，改成用户事实后使用同一个 `scripts/render.py`。所有引擎均生成 SVG、drawio 和 JSON。这里说明会改变结构选择或正确性的差别；复杂任务可以在现有语法外编写新布局，不把范例数量当作能力上限。

## 关系、层次与循环

- `radial`：`center`、可选 `detail`、`items:[{id?,label,detail?}]`，3–8 分支；`arrows` 默认 false。用于中心关联或星形拓扑，不能表示多级父子关系。
- `cycle`：`center`、3–6 个 `items`，每项 `label/detail`；最后阶段连接第一阶段。用于真正反馈循环；一次性过程不要强制闭环。
- `tapered`：`mode:pyramid|funnel`、2–6 个 `items`。pyramid 为定性层级；funnel 项含正数 `value`，要求顺序非递增，每层顶边宽度与值成比例。若阶段可以增加或有零值，改用条图或扩展零值处理，不能改数据凑形状。
- `venn`：当前是两个 `items` 和 `intersection`。交集表示共有成员；面积不编码数量。三个以上集合或精确集合规模需要扩展几何。
- `concentric`：2–5 层 `items` 按外到内排列，`center` 为核心。包含关系适用；无包含关系时用径向关联。
- `chevrons`：2–6 阶段 `items`，用于价值链、顺序阶段；不从外观推导真实依赖。
- `record`：`classes:[{id,label,x?,y?,w?,fields:[],methods:[]}]` 和关联 `edges`。保留三个分区；当前只有普通关联，不宣称支持继承、聚合、组合、接口和所有 UML 标记。

## 时间、矩阵与画布

- `timeline`：2–7 个 `items:[{date:YYYY-MM-DD,label,detail}]`；日期递增且唯一，横向距离按日数计算。不是等间距事件卡片。
- `table`：`columns` 为含第一列标题的列名；`rows` 为同长度二维数组，`row_height` 默认 110。适用于路线图、RACI、旅程、服务蓝图、方案比较。生成前分别检查它们的语义：RACI 每活动通常一个最终负责者 A；旅程以用户阶段为列；服务蓝图区分用户、前台、后台和支撑；比较表维度保持一致。
- `bmc`：九个 `items` 固定顺序为关键伙伴、关键活动、关键资源、价值主张、客户关系、渠道通路、客户细分、成本结构、收入来源。每项 label/detail；保留布局对应关系。输入缺事实时保留问题/假说，不填未经提供的商业数据。
- `quadrant`：`x_label`、`y_label`、`quadrants`（左上、右上、左下、右下），`items:[{label,x,y}]`，坐标范围 0–100。真实指标先说明归一化方式；定性评分必须标注其来源。
- `infographic`：2–6 个 `items`，每项 label/detail，形成编号信息块。编号仅是顺序。

## 数量与流向

- `treemap`：2–10 个 `items:[{label,value}]`，value 为正数。当前为单层切片矩形树；各块面积按比例计算，meta 保留 area。多层树和微小类别需另行布局，不能无限缩字。
- `sankey`：`sources/targets:[{id,label}]`、`links:[{from,to,value}]`。两端 ID 在各自集合内唯一，连接值正数；通过流量累加计算源与目标高度，同一缩放常数计算带宽。当前仅两列，最多各 6 个节点、24 条连接；不支持环路或多阶段流。多阶段需求可分图或扩展布局。

## 扩展数据图 `type:plot`

| mode | 主要输入 | 关键语义 |
|---|---|---|
| grouped | categories、series:[{label,values}] | 每组并列、共享零基线，系列长度等于类别数 |
| stacked | 同上 | 非负、同单位、互斥组成，柱高为合计 |
| scatter | data:[{x,y,label?}]，可选 x_range/y_range、x_label/y_label | 成对观测，支持有符号坐标；不画未经提供的回归或因果箭头 |
| bubble | scatter 输入加 size | size 正数，半径按平方根缩放，使面积与 size 成比例 |
| heatmap | row_labels、column_labels、values 二维数组，minimum/maximum、unit | 同一固定数值范围映射同一连续明度，直接显示数值 |
| radar | data:[{label,value}]、maximum | 各维共享 0–maximum，不能直接混合单位 |
| histogram | values 原始观测、bin_edges | 等宽严格递增分箱；左闭右开，末箱包含右端点；越界报错 |
| waterfall | data:[{label,value,total?}] | 增减累计；首个 total 为起点，后续 total 必须等于累计结果 |
| area | data:[{label,value}] | 非负、零基线、类别等距；不等距日期不能套用 |
| pie | data:[{label,value}] | 同总体，非负且总和大于零；最多 5 类 |
| bullet | maximum、data:[{label,value,target}] | 实绩条与目标线共享量程；不使用仪表装饰替代比较 |

这些是可编辑的数量示意引擎。严格科研出版的置信区间、统计检验、分布估计、对数/多轴、缺失数据和不等距时间序列仍使用标准科学绘图库；不能把样式范例当作已经完成统计分析。单位、样本量、来源、时间和研究结论都来自用户真实资料。

## 工程与空间的明确范围

- `floorplan`：`room_size:[宽m,高m]`，`zones:[{label,detail?,rect:[x,y,w,h]}]`。同比例区划示意；检查超界和重叠。不是墙体/门窗库，不包含疏散、荷载或机电校核。
- `circuit`：当前只有直流源—电阻—断开开关的教学拓扑，source/load/switch 控制标签。其他元件与网表需要新增相应符号和连接模型，禁止只换标题冒充另一种电路。
- `processplant`：3–5 个 units，每项 id/label/tag/detail/kind(tank/pump/process)，按输入顺序连接物料流。表达概念 PFD；不含 P&ID 的仪表逻辑、阀门规格和设计参数。

工程、软件、业务和科研任务可以共享图形语法，但不能共享未经确认的事实或专业标准声明。

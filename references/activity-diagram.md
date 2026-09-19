# UML活动图：令牌流、责任分区与两类终点

依据 OMG UML 2.5.1 第15章，活动图表达令牌在 ActivityNode 之间沿 ActivityEdge 的流动。ControlFlow 传递控制令牌，ObjectFlow 传递对象令牌。ActivityPartition 常用泳道表示责任或其他共同特征，但分区本身不改变令牌流。

当前 `activity_model.py` 输入包含 `title`、`scope`、非空 `assumptions`、`partitions`、`nodes` 和 `edges`。分区顺序必须连续；节点必须位于唯一的分区/行位置；所有节点必须从唯一 InitialNode 可达，并能到达 FlowFinalNode 或 ActivityFinalNode。

当前节点与关系规则：

- `initial` 使用实心圆，没有入边，只发出 ControlFlow。
- `activity_final` 使用靶心符号，终止整个活动；`flow_final` 使用圆内 X，只销毁到达该节点的流。
- `decision` 一入多出，每条出边必须有唯一守卫；`merge` 多入一出，不做同步。二者都使用菱形。
- `fork` 一入多出并发复制令牌；`join` 多入一出同步令牌。二者都使用粗条。
- `object` 使用矩形并为名称加下划线。当前子集要求每条 ObjectFlow 至少接触一个显式 ObjectNode，避免数据语义被隐藏。
- 泳道、节点和终点在 draw.io 中保持原生可编辑；语义节点归属各自分区，ActivityFinal 内圆归属外圆。

教学输入 `assets/activity-models/maintenance-workflow.json` 展示三个责任分区、九个动作、两个对象节点、一个初始节点、两类终点、两个判断、一个合并、一个分叉和一个汇合，共17条控制流与4条对象流。当前覆盖自上而下的黑盒活动；pins、参数节点、中断区、扩展区、信号/时间事件、结构化节点、多维分区及完整 UML 元模型仍需逐项验证。

该教学输入已在 diagrams.net 完成一次真实文字编辑、保存和重开；保存前后的54个单元ID、21条边绑定、泳道父子关系、样式、几何和路径点保持一致。此结果只证明当前三泳道源的可编辑性。

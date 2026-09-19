# UML部署图：运行节点、制品与逻辑定义分离

依据 OMG UML 2.5.1 第19章，部署图描述系统的执行架构以及软件制品到系统元素的分配。`Device` 是具有处理能力的物理计算资源；`ExecutionEnvironment` 是应用运行时依赖的软件执行系统。二者都是具体的部署目标，执行环境通常嵌套在设备中。

当前 `deployment_model.py` 输入包含 `title`、`scope`、非空 `assumptions`、`devices`、`environments`、`artifacts`、`components`、`manifestations` 和 `communication_paths`。设备采用运行实例 `instance : type`；环境归属设备；制品归属具体部署目标；逻辑组件保持在节点之外，通过显化关系与制品关联。

当前符号与关系：

- 设备使用带 `«device»` 的透视节点框；执行环境使用带 `«executionEnvironment»` 的节点框并嵌套于设备。
- 制品使用 `«artifact»` 分类器矩形，并嵌套于其部署目标。嵌套已经表达部署，因而不重复画 `«deploy»` 箭头。
- 逻辑组件使用 `«component»` 矩形，位于独立的逻辑定义区。制品以虚线开放箭头指向所显化的组件，并标 `«manifest»`。
- 设备间通信路径使用无箭头实线，表示可交换信号或消息的 Association；协议文字是当前教学假设，不等于网络工程校核。
- 当前输入要求设备通信图连通、每个设备恰有一个执行环境、每个部署目标最多四个制品，且每个制品与逻辑组件一一显化。这些是当前渲染子集限制，不是 UML 对完整模型的限制。

教学输入 `assets/deployment-models/maintenance-deployment.json` 展示四个设备实例、四个执行环境、五个制品、五个逻辑组件、五条显化关系和三条通信路径。当前覆盖单行物理拓扑与单层执行环境；通用 Node、外置 `«deploy»`、DeploymentSpecification、多层嵌套、多实例/多制品映射、多区域、冗余、故障域、通信多重性及完整 UML 元模型仍需逐项验证。

当前教学源已在 diagrams.net 完成一次真实文字编辑、保存和重开。结构比对确认 48 个单元 ID、8 条边的端点绑定、样式、父子关系、几何和路径点保持；该证据仅覆盖当前单行四设备源。

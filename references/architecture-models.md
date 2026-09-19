# 应用、云、企业、Kubernetes 与 C4 架构模型

## 当前覆盖

`scripts/architecture_models.py` 接受七种模式，九份教学输入位于 `assets/architecture-models/`：

- `application-landscape`：业务能力、应用组合、生命周期、集成模式和数据主责。
- `cloud-architecture`：AWS、Azure、Google Cloud 的资源/身份/网络边界、服务和有向流。
- `enterprise-layered`：战略、业务、应用、数据、技术五层的可追踪企业架构。
- `archimate-layered`：ArchiMate 3.2 的业务、应用、技术分层视图精选子集。
- `kubernetes-architecture`：控制平面、工作节点、namespace、工作负载、Service、Ingress、配置与持久卷。
- `c4-component`：一个容器内部的组件、职责、技术与直接依赖。
- `c4-dynamic`：一个运行场景中按序发生、并引用静态关系的交互。

每份输入输出 SVG、PNG、输入 JSON、计算摘要和 QA。JSON 是可编辑源；修改后应由同一后端重绘和重新计算，不能直接改图片文字。

## 语义边界

企业应用图必须把能力覆盖、应用所有者与生命周期、同步/事件/批处理集成、数据主责分开；“有一条线”不等于说明了集成契约。

云架构图把账号/订阅/项目等身份或资源范围与 VPC/VNet/子网等网络隔离分开。Azure 资源组不得标成网络边界；Google Cloud 项目在当前输入中显式声明为身份和资源范围。每条流包含方向、负载、协议、数据等级和安全控制。当前示例保存官方服务名称，但只绘制中性服务徽标，不重新分发厂商图标包；若交付需要品牌图标，应从厂商当前官方图标包引入并按许可使用。

企业分层图要求每个元素可从战略或业务入口沿显式关系到达；这只是追踪检查，不自动证明业务目标能实现。

ArchiMate 当前实现是 3.2 分层视图精选子集，不是完整元模型验证器。元素分别记录层、方面和元素类型；当前对 assignment、access、triggering 做方面约束，对 serving、realization 等保存显式类型与证据。需要交换文件或完整一致性检查时应使用正式 ArchiMate 工具。

Kubernetes 图按官方概念分开控制平面与节点，并把 Deployment/StatefulSet 的期望副本、Pod 标签、Service 选择器、Ingress 路由、ConfigMap/Secret 引用和 PVC 消费者作为结构化输入。Service 选择器必须实际匹配同 namespace 的工作负载；Secret 只能记录对象与引用，示例值必须脱敏。本图不把 Deployment 固定到某一节点，也不声称表示实时集群状态。

C4 组件图的范围必须是一个容器，组件写职责与技术，外围只放直接相连的人员、容器和软件系统。C4 动态图用于一个值得解释的运行场景，交互序号从 1 连续排列，并引用静态模型中的稳定关系 ID；动态图不能替代静态结构图。

## 公开依据

- C4 组件图说明：https://c4model.com/diagrams/component
- C4 动态图说明：https://c4model.com/diagrams/dynamic
- Kubernetes 组件：https://kubernetes.io/docs/concepts/overview/components/
- Kubernetes 对象：https://kubernetes.io/docs/concepts/overview/working-with-objects/
- Kubernetes ConfigMap：https://kubernetes.io/docs/concepts/configuration/configmap/
- Kubernetes Secret：https://kubernetes.io/docs/concepts/configuration/secret/
- Azure 架构图规范：https://learn.microsoft.com/en-us/azure/well-architected/architect-role/design-diagrams
- Azure 官方图标说明：https://learn.microsoft.com/en-us/azure/architecture/icons/
- AWS 架构图与图标入口：https://aws.amazon.com/architecture/icons/
- Google Cloud 架构图标入口：https://cloud.google.com/architecture/icons
- ArchiMate 入口：https://www.opengroup.org/archimate-forum/archimate-overview

上述页面用于约束公开语义和图示做法。当前代码、输入、版式和中文说明均为本地原创实现；没有复制厂商模板或私有图标资产。

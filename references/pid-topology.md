# P&ID 拓扑：输入约定与实施缺口

本轮实现 `scripts/pid_model.py`，校验明确声明的连接；另有pid_render.py绘制独立教学符号。八套教学输入位于 `assets/pid-models/`，覆盖通用供水测压、非连通交叉、旁路，以及过程、公用发电、环境、辅机和配送五个常用专业分支。完整标准符号和工程变体仍待补。不支持DEXPI导入导出、工程计算或标准符合性认证。

## 来源边界

2026-09-17核对 [ISA5.1委员会](https://www.isa.org/standards-and-publications/isa-standards/isa-standards-committees/isa5-1) 与 [DEXPI规范入口](https://dexpi.org/specifications/)。ISA页面确认现行2024版的仪表与控制符号/标识范围，未取得标准全文，不能据此声称完整符号验证。

DEXPI 2.0整合plant/process模型并采用DEXPI XML；旧1.4的Proteus序列化不能直接当作2.0交换格式。[1.4管网段](https://dexpi.org/static/pid_specification_1.4/reference/Piping/PipingNetworkSegment.html)用于识别连接、节点、流向和介质等概念。以下JSON是独立教学合同，不是DEXPI类的完整映射。

## 已实现合同

顶层严格包含schema=pid-topology-1、title、非空assumptions、items、connections。最多200对象、500连接。每对象有唯一id、唯一非空tag、kind、label、ports；kind暂含tank/pump/valve/instrument/junction/boundary，不区分全部设备子类。

端口id全局唯一，domain为process或signal，direction为in/out/bidirectional。连接有唯一id、from/to端口、domain、label、flow。端点必须存在并匹配domain；forward按from到to检查方向；bidirectional和unknown要求双向端口。测压连接不能因画了有向边就推断物料流量，示例将其flow明确设为unknown。

每端口最多一条外部连接，分支使用至少三个process端口的junction。连接自身对象暂不支持。未连接端口输出警告，不能静默称为完整回路。未知字段拒绝，避免未经实现的压力、管径或联锁设定被悄悄忽略。几何交叉不参与连接推断，后续渲染器必须从此拓扑生成连接点。

用法：`python3 scripts/pid_model.py assets/pid-models/water-pressure.json --out topology.json`。输出对象/端口/连接计数、按对象归并的连接边、未连接警告和验证边界。

## 后续必须补齐

| 工作项 | 需要形成的证据 |
|---|---|
| 设备、阀门子类与仪表位置/功能 | 逐符号来源、端口定义、渲染和原生编辑 |
| 管路与测量、气动、电气、数据连接 | 分域线型、完整图例；交叉与连接点不混淆 |
| 回路与联锁 | 独立回路模型、控制目标、正常/故障状态与未知项 |
| 管线编号、介质、管径、等级 | 明确单位及缺失语义，跨图保持一致 |
| 旁路、并联泵、回流、跨页 | 拓扑验证、避障、长中文与多页源重开 |
| DEXPI 2.0交换 | 官方模式校验、真实往返与目标工具导入 |
| 正式图纸与格式 | SVG/draw.io及指定CAD/Visio格式的实际查看与重开 |

过程、公用发电、环境、辅机和配送五个入口已有独立教学输入与成图证据；这些示例只覆盖各一条小型拓扑，不代表相应专业的全部设备、回路、图纸层级或正式验收。

## 教学图形后端

`python3 scripts/pid_render.py assets/pid-models/water-pressure.json --layout assets/pid-models/water-pressure.layout.json --out output`

layout显式提供positions（对象中心）、ports（端口到符号方位的绑定）、routes（连接中间拐点）；不自动猜测布局。槽体端口可绑定左、右、上、下四个方位，其余符号按各自支持的方位校验。输出SVG、draw.io、输入、布局、scene、QA与连接CSV。要求完整绑定、无端口方位重用、有限坐标及正交外部连接。几何范围为1600宽固定版面内的绘图区；已检测外部线路交叉、接触、重叠、自交和穿过符号保守包围框；发现时报告并拒绝渲染。跨线桥、自动绕障、符号分组/拖动自动重连仍未实现。draw.io各图元和文字可编辑，但端点为显式坐标，不宣称智能工程元件或编辑后自动拓扑更新。

槽体为开口容器示意，泵为圆与三角形，阀为通用隔离示意，仪表用功能字母圆形；这些是自定义教学图例，尚未逐个对照标准全文。没有执行机构、安装位置、故障状态等完整语义。八套示例已实际查看SVG；环境P&ID另完成draw.io文字编辑、保存、结构比对和编辑版重开。

几何检测由pid_geometry.py执行，使用精确正交线段计算；相邻线段正常拐角放行，回折重叠拒绝。符号包围框为保守矩形，可能拒绝靠近圆角而实际不碰符号的路线；这类路线需明确重排，不声称已实现任意复杂管网。坐标碰巧相同不会产生新的拓扑连接。

## 显式非连通交叉

layout现在可选crossings数组，例如`{"over":"H","under":"V","at":[800,490],"gap":18}`。每条声明必须对应唯一实际的两连接内部交叉；全部交叉必须声明，重复/无效/漏声明拒绝。端点接触、自交、重叠和穿设备仍不允许用声明消除。

under连接在显示层分成多段，断口宽度为8..40图面单位，不得触及弯点/端点或与其他断口重叠；仅最后显示段保留原方向箭头。原connections、端口端点与CSV不拆分，断口不表示物理断开。scene同时保存完整路线与显示分段，可追溯比较。此为明确图例的教学绘图规则，不宣称标准符号兼容。

crossing.json与crossing.layout.json示例包含独立过程连接和信号连接。SVG已实际查看；交叉示例draw.io已独立打开，检查断口并编辑信号去向标签后撤销。尚未完成保存后重开往返验收。跨线圆弧、自动避障和复杂密集管网仍待补。

## 旁路结构示例

bypass.json与bypass.layout.json增加主路/旁路、两个三端口分支节点。两条路径只表示静态连接；阀门标签明确状态未给。独立图遍历核对两条路径和分支移除后的可达性，未做流量计算。SVG已查看，旁路draw.io已实际打开，旁路阀标签编辑后撤销；保存后重开仍待验收。

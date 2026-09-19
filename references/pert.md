# PERT / CPM：活动节点计算合同

入口scripts/pert.py。计算与AON图形后端已实现；三点估计源已编辑核验，确定工期源及保存后重开尚待补。两个输入位于assets/pert-models：parallel-maintenance.json、three-point.json。

2026-09-17读取PMI的[进度风险分析](https://www.pmi.org/learning/library/project-schedule-risk-analysis-simulation-4620)及[估算标准说明](https://www.pmi.org/learning/library/leveraging-new-practice-standard-project-estimating-6222)。经典三点加权均值为(a+4m+b)/6，活动方差近似为((b-a)/6)^2。多条路径汇合存在风险偏差，不能将平均工期网络的最长路径直接称为真实项目期望完成时间，也不能由此承诺某日期的完成概率。本实现不输出项目方差或概率。

## 输入与范围

顶层title、unit、mode、assumptions、tasks严格必填。mode为deterministic或pert，统一时间单位。任务id唯一、label非空、predecessors列出前置活动。deterministic任务用duration；pert任务用optimistic、likely、pessimistic，要求0≤a≤m≤b。数值为非负整数或十进制字符串，不接受浮点数、布尔值、分数字符串和未知字段。零工期支持里程碑。

最多200活动。依赖仅零时滞完成到开始（FS），多源从共同零时刻开始，多终点以全部完成为统一终点。先验证引用与有向无环，再前向计算ES/EF，后向计算LS/LF。总浮动=LS−ES，自由浮动=最早后继开始−EF，终点自由浮动相对统一完成时间。用Fraction精确计算，输出有理数字符串，不能先舍入再判关键。

关键活动为总浮动零；关键依赖还要求前活动EF等于后活动ES。使用动态计数返回全部并列关键路径数量，避免只给一条路径或枚举指数数量路径。浮动不是可同时消耗的独立缓冲。

## 待补

AON图面、每节点时间格、所有关键边标识、数据表与原生源；AOA与虚活动；SS/FF/SF和时滞；日历/资源约束/强制日期；相关工期和汇合风险模拟。不存在已完成PERT全类型的声明。

## AON绘图

`python3 scripts/pert_render.py assets/pert-models/parallel-maintenance.json --out output`。输出SVG、draw.io、输入、analysis、scene、QA和CSV。节点包含工期、ES/EF/LS/LF/TF/FF，关键依赖以粗线标识；PERT模式额外列出a/m/b。按依赖层级排布，不按时间比例。多终点共用计算终点，但图中未添加虚拟终点。两套图已查看；三点估计draw.io已编辑任务标题后撤销，确定工期源原生检查、保存后重开和大型复杂布局仍待补。


## 跨层连线避障增补

`skip-dependencies.json` 保留六个任务、九条依赖（含三条跨层冗余依赖），工期10天。跨层依赖沿列间空隙进入卡片下方的独立水平通道，依赖关系与精确时间不变。对全部卡片单独检查线段相交，避免通用检查跳过背景矩形而漏报。SVG和draw.io已实际查看，F标题编辑与撤销已验证；未保存后重开。

`test_pert_routing.py` 另以8/20/60/200任务各两组网络及42任务宽层网络核验边数、正交性和全卡片矩形避障。该证据只证明这些输入的几何性质，不证明任意大图的可读性。连线之间仍可交叉或共享部分路径，交叉不表示新增任务或依赖；独立端口、连线辨识、长标签、自动拆页及大图视觉验收尚待补齐。


## 保存后重开证据

跨层依赖示例已在draw.io将F标题改为“F · 保存重开核验”，通过下载保存为`pert-skip-roundtrip.drawio`，再以该文件的原始XML在新编辑器页重开并查看整图。54个对象ID、全部样式/几何及9条连线的绑定与路径点保留，唯一内容变更为标题。核验脚本为工作区`verify_pert_roundtrip.py`，证据为`research/pert-roundtrip-validation.json`。只证明此示例的文字编辑保存往返；不外推其他示例、节点拖动、自动重算或其他格式。

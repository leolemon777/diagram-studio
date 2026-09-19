# 专业生成后端

规则覆盖与实现覆盖分开。完整目录的326条规则负责选图与语义；本页只说明已实际实现的两个新增后端。

## BPMN 协作子集

输入见 `assets/advanced-examples/procurement-bpmn.json`，Python标准库即可：

```bash
python3 <skill-dir>/scripts/bpmn_source.py procurement-bpmn.json --out output/procurement.bpmn
```

模型有 pools、nodes、flows、messages。节点支持 startEvent、endEvent、task、userTask、serviceTask、sendTask、receiveTask、exclusiveGateway、parallelGateway。每个节点具有稳定ID、所属池、位置和名称。顺序流仅在同一池内，消息流跨池；两者的 `from/to` 均引用存在的节点。可指定折线 `points` 与标签框 `label_box`。默认尺寸只是起点，真实内容须重新检查标签和连线。

校验重复ID、未知端点、跨池顺序流、错误事件流、网关消息端点、缺失条件标签、非有限几何、超出池边界、从开始不可达或无法到达结束的节点。生成包含 BPMN DI 的非执行模型 `isExecutable=false`。已用 bpmn-moddle 解析且 bpmn-js 实际显示采购示例，均零导入警告；这不等于全BPMN规范认证或执行引擎验证。

未实现子流程、边界事件、定时器、事件网关、数据对象、泳道等完整语义，也不把条件名称当成执行表达式。需求包含这些元素时用完整建模器或扩展模型后独立验证。界面预览的外部中文标签增加16px测量余量；这是本地预览排版修正，不改变模型语义。可编辑源是 `.bpmn`，而非只保存一张图片。

## 科研统计

需要 Matplotlib 与 NumPy；在任务自己的虚拟环境安装，避免修改全局依赖：

```bash
python3 -m venv .venv
.venv/bin/pip install matplotlib
.venv/bin/python <skill-dir>/scripts/scientific_plot.py <skill-dir>/assets/advanced-examples/research-boxplot.json --out output
```

本次环境的实际版本记录于交付的 `.calculation.json`。原有四种 mode 如下；另新增24种已实现模式，输入和方法详见 [科研图表图谱](scientific-atlas.md)。

| mode | 输入 | 计算与边界 |
|---|---|---|
| boxplot | groups 中 label 和 values | 线性插值分位数，1.5×IQR须；叠加原始点；不自动删除离群观测 |
| ecdf | groups 中原始 values | 排序并计算累计比例；不分箱、不估计密度；完整样本端点为1 |
| errorbar | data 中 estimate、low、high；uncertainty_kind | 必须声明SD、SE、CI或provided interval；区间须包含点估计；不代替区间推断与研究设计校核 |
| pareto | data 中 label、value | 非负观测量、正总量；降序排列与累计百分比；频次不能代替风险严重性 |

输出 SVG、PNG、输入 `.data.json`、计算 `.calculation.json`。SVG保留文本；字体可用性影响跨机器外观。本次采用macOS黑体，其他系统需配置覆盖中文的字体并重看输出。示例均为原创演示数据，不是用户实验结果。

## 其他推荐路线

PlantUML、Graphviz、ELK、KiCad、RDKit、QGIS、Vega-Lite 等是按任务推荐的候选工具，未在此技能中捆绑、完整实现或逐一运行。不得仅凭推荐条目宣称相应工程设计、统计结论或原生格式已验证。

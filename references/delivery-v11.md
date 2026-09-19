# v11 增量交付范围

本包包含截至2026-09-17的本地技能源码、规则、输入范例和模板。生成后的图册、测试日志与核验截图保留在Apat工作区，不在技能ZIP内。它不是全目录完成声明。

新增控制图入口：`scripts/spc.py`，支持Xbar-R、Xbar-S、p、np、c、u、EWMA、CUSUM，以及均值图可选WECO四规则。输入位于`assets/spc-examples/`；方法、参数口径和未覆盖范围见`references/spc.md`。

新增故障树入口：`scripts/fault_tree.py`，支持静态AND/OR、重复事件最小割集和明确独立基本事件的概率计算。输入位于`assets/fault-tree-examples/`；限制见`references/fault-tree.md`。

故障树后端只依赖Python标准库。控制图绘制需要Matplotlib和现有风格模块，适当的中文字体影响实际显示；当前验图环境为macOS。计算模块无需网络，数据不上传。包的解压重绘验证与源码清单另见Apat的`research/release-v11-validation.json`和`research/skill-manifest-v11.json`。

全目录仍为326入口，121项有关联示例，205项未关联示例；目录入口和示例数不代表全部变体完成。新后端未全部适配横竖画布、跨页和所有目标编辑器。原生draw.io是图形源，修改业务数据后须用输入JSON重新计算绘制。

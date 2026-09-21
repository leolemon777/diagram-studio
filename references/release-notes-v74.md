# v74 发布说明

日期：2026-09-21

v74 把高频、跨行业和发布可信度放在同一个可复查闭环里。它不是“所有复杂内容都自动完美排版”的承诺；实际范围以输入规则、证据文件和下面的边界为准。

## 本版交付

- 8 个分组、30 项能力登记，提供中英双语选图向导和连续选型证据。
- 流程、架构、泳道、甘特、网络、数据叙事、故事地图、用户路径和精益画布 9 个热门页，在 390×844 和 768×1024 视窗完成嵌入内容闭环；宽图留在明确的内部滚动区。
- 软件、电商、教育、营销、人事行政、文旅/门店六个跨行业试用案例各完成一次有意义的修改，并保留输入、SVG 预览、draw.io 源、scene、QA 与 delivery receipt。
- 新鲜临时目录复现普通流程和一个合法的跨行业模型；生成产物完整、QA 无错误，输出中没有开发机绝对路径、临时服务地址或私有目录依赖。
- 15 个代表性 draw.io 文件在 diagrams.net 中完成修改、保存、重开往返；这项证据不外推到所有类型或所有编辑器。

## 可追溯文件

- [双语试用指南](trial-guide.md)
- [热门视窗证据](../assets/v74-popular-viewport-evidence.json)
- [选图连续性证据](../assets/v74-chooser-continuity-evidence.json)
- [六行业试用证据](../assets/v74-trials/evidence.json)
- [干净目录证据](../assets/v74-clean-install-evidence.json)
- [完整发布证据](../assets/v74-release-evidence.json)
- [验证状态与边界](verification-status.md)

## 验证结果

源仓库与安装目录各通过 128 项回归；quick validation、JSON 解析、链接审计、差异检查和目录 parity 均需在发布前再次运行并记录。基础 renderer 只依赖 Python 3.9+；跨行业等专门后端可能需要 Matplotlib/Pillow。

## 边界

模拟案例不等于行业事实，专业领域仍需人工复核；热门窄屏证据不外推到任意高密度输入。万兴图示对本机临时 `.drawio` 副本仍显示“打开文件失败”，因此只记录 diagrams.net 代表性往返通过。JEV 没有真实 Skill 名称、路径或可调用入口，暂不写成已接入或已通过。

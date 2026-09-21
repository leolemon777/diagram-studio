# 交付格式矩阵

能力登记是格式范围的唯一当前来源；不同后端不强求相同格式。以下是 v71 实际存在且可检查的代表文件，字节与页面检查只覆盖列出的产物。

| 后端/形式 | 已登记格式 | 代表性实际检查 | 可继续修改的源 |
| --- | --- | --- | --- |
| `scripts/render.py` · 架构/流程/网络/计划等 | SVG、draw.io、scene JSON、QA JSON、HTML | 网络英文 SVG 1800×792；draw.io 为可解析 XML；HTML 含离线阅读页和 viewport | JSON brief、draw.io；数据变化应从 JSON 重绘 |
| `scripts/data_art.py` · dumbbell/waterfall | SVG、draw.io、PNG、PDF、HTML、input JSON、scene JSON、analysis JSON、QA JSON、CSV | 英文 dumbbell PNG 1600×1000、PDF 1 页、CSV 可读；英文 waterfall 同样输出全套 | input JSON、draw.io；数值变化应从 JSON 重绘 |
| `scripts/kanban_render.py` · 看板 | SVG、draw.io、input JSON、model JSON、QA JSON | 输入、模型和 XML 源存在；不把静态快照当实时协作 | input JSON、draw.io |
| `scripts/organization_relations.py` · 亲和图 | SVG、PNG、input JSON、calculation JSON、QA JSON | 中英文示例输出存在；计算记录与输入分离 | input JSON |
| `scripts/render.py` · storymap | SVG、draw.io、scene JSON、brief JSON、QA JSON、HTML | 英文故事地图 SVG、draw.io 和阅读页存在；活动/切片/故事 ID 可追查 | JSON brief、draw.io |

所有输出都应先检查字节非空、格式可解析、关键文字存在、QA 错误为空，再做浏览器或原生编辑器检查。SVG/HTML 可打开不代表专业事实或审美已验收；PNG/PDF 仅在对应专门后端登记，不由普通后端自动承诺。生成失败时沿用上一版交付由[交付协议](delivery-contract.md)测试覆盖。

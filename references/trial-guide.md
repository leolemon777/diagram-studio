# 双语试用包 · Diagram Studio

这份试用包让第一次使用者从六个高频行业问题开始。每个案例都用模拟数据；先打开演示看阅读顺序，再替换 JSON 或把双语请求交给 Codex。输入变化后要重新生成并检查文字、关系、数值、单位和输出文件。

## 六个起步场景

| 行业问题 | 推荐读法 | 入口与可修改源 | 有意义的修改 |
| --- | --- | --- | --- |
| 软件产品：模块边界和服务连接 | 分层总览 → 关系详读 | [架构演示](../demos/architecture/index.html)、[网络演示](../demos/network/index.html) | 加一个明确的用户反馈模块，并补一条声明过的回流关系 |
| 电商零售：订单履约异常 | 流程主线 → 异常回流 | [流程演示](../demos/flow/index.html)、[看板演示](../demos/strategy-execution/index.html) | 把“库存不足”分支改成“门店确认失败”，重新检查终点和条件标签 |
| 教育培训：课程上线和学习路径 | 时间顺序 → 任务依赖 | [甘特演示](../demos/gantt/index.html)、[路线与脑图](../demos/route-mindmap/index.html) | 调整一个活动日期并增加一个前置关系，确认日期、进度和依赖同时更新 |
| 营销：活动结果和变化 | 零基线比较 → 趋势变化 | [数据叙事演示](../demos/data-story/index.html)、[瀑布演示](../demos/waterfall/index.html) | 修改一个渠道值，确认单位、总量和图例不显示旧值 |
| 人事与行政：责任交接和优先级 | 责任泳道 → SWOT/看板 | [泳道演示](../demos/swimlane/index.html)、[分析表单](../demos/analysis-forms/index.html) | 增加一条责任交接，确认角色、方向和异常回路完整 |
| 文旅与门店：到店体验和后台履约 | 旅程证据链 → 服务蓝图 | [体验图演示](../demos/experience-maps/index.html)、[故事地图](../demos/storymap/index.html) | 把一个触点改为“改期请求”，确认证据、机会和行动仍能追溯 |

新增两种高频试用入口：[精益画布](../demos/lean-canvas/index.html)适合把问题、方案、指标和证据放在同一张验证板上；[用户路径故事板](../demos/user-path-storyboard/index.html)适合审查前置条件、可见状态、下一步、分支和异常。两者都提供中英文 JSON、SVG、draw.io 和 QA，且不把拟议内容自动当成事实。

## 最小流程

1. 打开入口，先读“它回答什么问题”和边界说明。
2. 打开同页的 JSON 或 draw.io 源，做一项上表中的修改。
3. 从仓库根目录运行，例如：

   ```bash
   python3 scripts/render.py assets/examples/02-workflow.json --out /tmp/diagram-trial-flow --theme light
   python3 scripts/render.py assets/examples/61-gantt-delivery.json --out /tmp/diagram-trial-gantt --theme light
   python3 scripts/render.py assets/examples/09-line-chart-en.json --out /tmp/diagram-trial-trend --theme light
   ```

4. 打开生成的 SVG、HTML 和 draw.io，记录哪些内容可直接编辑、哪些数据必须回到 JSON 重绘。
5. 用中英选图向导生成同一问题的另一种表达，比较阅读顺序；风格卡是所选图型的真实缩略结构，最终成图仍需实际检查。

## 反馈记录

```text
场景 / 输入语言：
读者和问题：
选图是否容易：是 / 否，卡在哪里：
关键文字和关系是否读得懂：是 / 否，哪一处：
风格是否帮助阅读：是 / 否，哪一处：
SVG / draw.io / JSON 是否能继续修改：
导出或打开失败信息：
建议新增的高频形式：
```

这份反馈模板不等同真实用户研究。专业事实、数据来源、统计显著性和原生编辑器行为仍需相应领域或工具复核；实时协作、投票和完整白板功能不在本试用包范围内。

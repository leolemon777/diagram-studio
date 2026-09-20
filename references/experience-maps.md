# 旅程图与服务蓝图

这两种图型共用 `scripts/render.py` 的 SVG、draw.io、scene、QA 和交付收据，但语义不同：旅程图追踪一个人的阶段体验，服务蓝图追踪同一服务中可见动作与后台协作。

## 用户旅程图

输入使用 `type: "journey"`：

- `persona`、`goal` 和 2–8 个 `stages` 是必需的。
- 每个阶段包含稳定 `id`、`label`、`behavior`、`touchpoint`。
- `evidence` 保存原文与 `source`；`opportunities` 必须引用证据；`actions` 必须引用机会，并提供 `owner` 与可检查的 `check`。
- `emotion` 只能写带 `basis` 的定性描述，不会把主观感受编成分数。

生成示例：

```bash
python3 scripts/render.py assets/experience-models/education-journey.json --out /tmp/education-journey
```

图中的阅读顺序是阶段从左到右、证据到机会再到行动从上到下。没有证据的空位会明确写出，不会被解释成“没有问题”。

## 服务蓝图

输入使用 `type: "service-blueprint"`：

- `customer`、`goal`、2–8 个服务阶段和 3–6 条 `lanes` 是必需的。
- 泳道必须声明 `kind`：`customer`、`frontstage`、`backstage`、`support` 或 `system`。
- 每个动作格有稳定 `id`、所属 `stage` 和 `text`，可选 `owner`。
- `boundaries` 只在相邻泳道之间画分界线；`handoffs` 必须指向实际存在的动作格。排版不会从相邻位置猜测协作关系。

示例：`assets/experience-models/retail-service-blueprint.json` 及其英文版。它把线上下单、门店备货、到店取货和售后放在同一条服务链中，分开显示前台、后台、支撑和系统记录。

两种输入都能由 `python3 scripts/capability_registry.py --check` 检查引用，并由公共交付协议检查稳定 ID、显示文字和生成收据。它们表达的是可审阅的服务模型，不提供实时协作、投票、工单执行或领域事实验证。

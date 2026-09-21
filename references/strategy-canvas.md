# 漏斗与商业模式画布

这两类形式属于高频战略与执行表达，但回答的问题不同：漏斗图展示一个过程按阶段收窄，商业模式画布整理九个固定要素中的待验证假说。

## 漏斗图

使用 `type: "tapered"`、`mode: "funnel"`。`items` 为 2–6 个有序阶段，每项需要 `label` 和正数 `value`；数量必须从前到后保持或递减。`unit` 和 `ratio_label` 会显示在阶段说明中，适合人数、订单或申请数等同一口径的计数。

```bash
python3 scripts/render.py assets/examples/25-funnel-cn.json --out output/funnel-cn
python3 scripts/render.py assets/examples/25-funnel-en.json --out output/funnel-en
```

漏斗宽度只编码声明的数量比例。它不解释下降原因，不计算统计显著性，也不把一张模拟图当作真实转化率。

## 商业模式画布

使用 `type: "bmc"`，`items` 必须按固定顺序提供九项：关键伙伴、关键活动、关键资源、价值主张、客户关系、渠道通路、客户细分、成本结构、收入来源。每项有 `label` 和 `detail`；短条目更适合单张画布，长研究材料应拆成验证页。

```bash
python3 scripts/render.py assets/examples/33-business-model-canvas-cn.json --out output/bmc-cn
python3 scripts/render.py assets/examples/33-business-model-canvas-en.json --out output/bmc-en
```

画布整理的是待验证假说，不计算市场规模、定价、收入预测或战略优先级。请在条目中标明证据状态、来源和负责人，再把真实资料交给领域评审。

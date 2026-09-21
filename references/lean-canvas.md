# 精益画布：九个验证问题

精益画布用于早期产品假说，和商业模式画布回答的问题不同。它把问题、客户、价值主张、方案、渠道、收入、成本、指标和难以复制的优势放在一张不等区块的工作板上。每条内容必须有稳定 ID、证据和状态；没有证据时明确写成 `unknown` 或 `hypothesis`。

## 输入

使用 `type: "lean-canvas"`，`items` 必须正好包含以下九个 ID：

`problem`、`customer-segments`、`unique-value-proposition`、`solution`、`channels`、`revenue-streams`、`cost-structure`、`key-metrics`、`unfair-advantage`。

每个区块包含 1–6 个 `entries`。每条 entry 需要 `id`、`text`、`evidence` 和 `status`，状态可用 `observed`、`validated`、`hypothesis`、`proposed` 或 `unknown`。稳定 ID 会进入 SVG、draw.io 和 scene JSON，证据状态会作为可编辑文字保留。

```bash
python3 scripts/render.py assets/examples/38-lean-canvas-cn.json --out output/lean-canvas-cn
python3 scripts/render.py assets/examples/38-lean-canvas-en.json --out output/lean-canvas-en
```

布局采用外侧问题/客户、中间价值主张、下方成本/收入横向区。长内容会增加区块高度；过密材料应拆验证页。画布整理待验证假说，不计算市场规模、收入预测、优先级权重或产品市场匹配。

## 与商业模式画布的区别

商业模式画布固定讨论伙伴、活动、资源、价值、客户关系、渠道、客户细分、成本和收入；精益画布首先追问问题和客户，再把方案与可验证指标放在中心。两种形式不能通过换标题互相替代。

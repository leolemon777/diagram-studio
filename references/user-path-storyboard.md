# 用户路径故事板：把路径审查做完整

用户路径故事板用于界面、服务和流程审查。它回答“用户在什么前置条件下，经过哪些可见状态和步骤，下一步是什么，哪里会分支或出错”，与用户故事地图的活动/交付切片不同。

## 输入

使用 `type: "user-path-storyboard"`，至少提供：

- `preconditions`：1–6 个带稳定 `id` 的前置条件；
- `states`：2–8 个带稳定 `id`、`label` 和 `detail` 的可见状态；
- `steps`：4–12 个连续编号的步骤，每步有 `id`、`state`、`actor`、`action`、`result` 和 `next`；最后一步的 `next` 必须为空；
- `branches` 和 `exceptions`：可选，但每条都要有稳定 ID、`from`、`to`、`label`、`condition` 和 `proposal`。异常还要写 `recovery`。

非最终步骤必须声明下一步、分支或异常。`proposal: true` 只表示待验证方案，生成器会用虚线和拟议标记表达，不把它当事实。所有源 ID 会进入 SVG、draw.io 和 scene JSON，方便逐项编辑和复核。

```bash
python3 scripts/render.py assets/examples/37-user-path-storyboard-cn.json --out output/user-path-cn
python3 scripts/render.py assets/examples/37-user-path-storyboard-en.json --out output/user-path-en
```

主路径横向展开，回流、分支和异常在独立路径轨中连接回具体步骤。长内容会增加卡片高度；路径过长时拆成总览和局部异常页。它是低保真审查和方案讨论工具，不是可执行流程引擎、真实服务承诺或领域审批。

# 本地生成与源格式

`python3 scripts/render.py <brief.json> --out <目录> --theme light|dark|mono`

`light` 为暖灰科研默认；`dark` 为深色阅读变体；`mono` 为黑白论文变体。风格由用户指定，参考 style.md。

基础生成使用 Python 3.9+ 标准库，无 API 密钥、无远程请求、无付费生成调用。v38 自适应布局可选 Pillow 获取真实字体度量，缺少时记录为保守估算，见 [自适应布局](adaptive-layout.md)。读 brief，建立对象坐标和关系，再导出 SVG / drawio / scene JSON / brief 副本 / QA JSON；自适应模式还导出阅读 HTML 与多页源。输出目录已存在时会覆盖同名生成文件，修改用户图时使用新目录或新名称。

## 用户定义配色

在 brief 增加 `"style":{"bg":"#F1EFEB","accent":"#AC6046"}` 可以覆盖本次主题。支持 style.md 中的所有颜色 token，只接受六位十六进制；未提供的 token 继承基础主题。不修改全局风格，不改变节点和边；最终 palette 保存在 scene JSON。字体、密度、线型等更细的用户要求由助手调整布局/矢量样式并重新检查。

## 通用字段

```json
{
  "type": "architecture",
  "title": "设备平台系统架构",
  "subtitle": "范围与阅读提示",
  "eyebrow": "SYSTEM ARCHITECTURE",
  "footer": "来源、版本、口径或必要假设",
  "assumptions": ["哪些是示例或建议"],
  "width": 1600,
  "height": 900
}
```

画布会按内容向下扩展；若必须 16:9，应缩减内容/拆成多图，而不是宣传扩展后的页面仍为 16:9。普通图优先使用 1600 宽；树会按分支数量扩展。

## 八类排版引擎

| type | 输入结构 | 实例 |
|---|---|---|
| architecture | `layers: [{label,description,tone,items:[{id,label,detail}]}]`；可选 `crosscut` | 01-system-architecture.json |
| graph | `groups:[{id,x,y,w,h,label}]`，`nodes:[{id,label,detail,x,y,w,h,kind,tone}]`，`edges` | 02-workflow.json、12-data-model.json |
| tree | `root:{id,label,detail,children:[...]}`；`direction:right|down` | 03-organization.json、04-mindmap.json |
| sequence | `actors:[{id,label}]`，`messages:[{from,to,label,return}]` | 05-sequence.json |
| gantt | `tasks:[{id,label,owner,start,end,progress,depends,milestone}]` | 06-gantt.json |
| matrix | `columns`，`cell_height`，`cells:[{label,tone,items:[]}]` | 07-swot.json |
| chart | `mode:bar|line|donut`，`data:[{label,value}]`，`unit` | 08/09/10 开头的实例 |
| fishbone | `effect`，`effect_detail`，`categories:[{label,causes:[]}]` | 11-fishbone.json |

实例都在 `assets/examples/`，包含可运行的完整输入。优先复用结构，不保留与用户无关的示例内容。

### Graph 节点和边

节点形状 `rect` / `diamond` / `pill` / `cylinder` / `ellipse`。背景分区通过 groups 定义。ID 为字符串且唯一，不使用 `0`、`1` 或 `_edge_` 前缀。

边字段：`from`, `to`, `label`, `tone`, `dashed`, `arrow`, `source_port`, `target_port`；端口可选 `left/right/top/bottom`。固定坐标模式可用 `points:[[x,y],...]` 提供完整折线路由，用 `label_at:[x,y]` 避开拥挤；其自动折线只解决简单连接。v38 自适应模式会重算路由、寻找避障通道并比较候选布局，复杂图仍需实际查看。

`tone` 可用 `accent,teal,amber,red,muted,ink,line` 等主题色角色。显式坐标从 x=64、y=190 后开始，留出标题区。节点文字一般 22，说明 16。较长文字拆分，别用很小字号藏问题。

### Architecture

固定布局每层最多 6 个并列模块；v38 默认自适应会在同一语义层内换行。`flow` 可为层间加方向说明，`flow_direction` 为 `up|down`；只有真实需求有逐层流动时才用。`crosscut` 只表示横向支撑，没有默认虚构数据流。

### Gantt

日期必须 ISO `YYYY-MM-DD`，包含结束日；依赖采用 finish-to-start，后继开始必须晚于前驱结束。同日里程碑要求 start=end。进度百分比 0–100。

`gantt_variant` 可选：

- `executive`：按 `phase` 分组，突出阶段、关键事项和里程碑；每个任务必须有 `phase`。
- `delivery`：保留责任人、日期、进度和依赖，适合日常执行跟踪。
- `print`：黑白表格与时间轴，适合打印、会议纪要或归档。

同一项目需要比较风格时，三份输入必须共享完全相同的 `tasks`、日期、依赖和进度，只能改变标题与 `gantt_variant`。当前按自然日含结束日计算；未实现工作日历、资源平衡、时区、关键路径计算，元数据会明确写 `critical_path: not-calculated`。这些需求应使用专门排期模型或扩展脚本后验证。

### Charts

横条仅支持非负值，明确零基线；折线的类别等距；环图最多 5 类，非负且合计大于零。负值、真实不等距时间轴、置信区间、分布统计、地图等转标准绘图库。需要严格学术出版图时，不强行使用这个演示图形排版器。

## 能力边界

- 基础时序尚无 alt/loop 框、精确激活周期语义；图中不能声称存在这些能力。
- ER 示例通过文字显示基数，未实现 Crow's Foot 端点库。
- 正式 BPMN/UML/电气/P&ID、CAD 比例图需要专用符号/格式和领域验证。
- 生成器不是对自然语言自行理解的模型，也不是万兴桌面所有功能的替代品。
- `.drawio` 使用 mxGraph 原生节点和连接，可在兼容编辑器中继续编辑；实际兼容情况必须用输出文件重开确认。

## 扩展结构库

新增布局的数据格式见 [extended-layouts.md](extended-layouts.md)。现有 60 个结构范例共使用 26 个布局入口；同一布局可以表达不同语义任务，不能把两者数量混称为标准图型数量。

先搜索再读范例，避免每次把整个库加载进上下文：

```bash
python3 <skill-dir>/scripts/catalog.py 桑基
python3 <skill-dir>/scripts/catalog.py --family 关系与结构 --limit 20
```

命中项给出中文名称、适用语义、生成 type 和可直接读取的完整 brief 路径。完整分组索引见 [结构范例索引](library-index.md)。

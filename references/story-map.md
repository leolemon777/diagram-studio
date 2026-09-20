# 用户故事地图：从体验到交付

English: [User story maps](story-map.en.md)。用于产品、教育、零售、服务等场景的活动顺序与交付范围讨论。已有专用生成器，不再只是方法配方；切片是否构成可用体验仍须由团队确认。

## 结构与输入

横向是用户活动顺序，纵向是明确的交付切片。每条故事唯一归属一个活动与一个切片；空位表示未安排，不能解释为零、遗漏或自动补齐。此图不表达日期比例、依赖排期或关键路径。

使用 `scripts/render.py`，设置 `type: "storymap"`。最小输入：

```json
{
  "type": "storymap",
  "title": "完成首次学习",
  "persona": "首次报名的学习者",
  "goal": "选到合适课程并开始学习",
  "activities": [{"id": "learn", "label": "开始学习"}],
  "releases": [{"id": "R1", "label": "首次可用", "goal": "能够进入并完成首课"}],
  "stories": [{"id": "S01", "activity": "learn", "release": "R1", "label": "找到首课入口", "detail": "在报名确认中提供入口和准备说明。", "source": "模拟访谈 E01"}]
}
```

- `persona`、`goal`、三组非空数组必填。每组内 ID 唯一：ASCII 字母开头，可含数字、下划线、短横线，最多 64 字符；显示文字支持中英文。
- 活动和切片按数组顺序排列，同一单元格中的故事保持输入顺序。每个切片必须有非空 `goal`，但生成器不自动证明其业务完整性。
- 故事必填 `id/activity/release/label`；`detail/source` 可选，提供时必须是非空文本。来源字段不等于来源真实性已核验。
- `language: "en"` 使用英文结构标签；用户正文需自行提供英文，生成器不自动翻译。`width` 是最小宽度，列多时会扩大；不能把固定 16:9、有限空间与任意全文同时保证。
- 顶层 `edges/dependencies/votes/dates` 和故事的 `depends/depends_on/votes/start/end` 会报不支持，避免静默丢掉这些含义。其他未列出的自定义字段没有显示或处理承诺。

## 自动排版与使用

先按字体度量换行，再计算卡片高度、每个切片的最大堆叠高度和后续行位置。保留正文字号；长文向下扩展，多活动向横向扩展。稳定 ID 保存在场景与 draw.io 对象中，故事归属同时记录在 `scene.json` 的 `meta.story_map`。

```bash
python3 scripts/render.py assets/storymap-examples/education-storymap.json --out output/storymap
python3 scripts/render.py assets/storymap-examples/education-storymap-en.json --out output/storymap
```

交付完整 SVG、draw.io、原始 brief JSON、场景、几何 QA、交付校验记录与独立阅读 HTML。[中英文演示](../demos/storymap/index.html) 可切换真实图中文字，明确下载包含 R1/R2、3 项活动和全部 6 条故事；下载不受当前滚动位置影响。

清晰阅读保持原生字号并允许画布内部滚动。总览仅观察结构；文字小于当前 12px 复核阈值时，提示切回清晰阅读。文字边界通过、字号达到阈值和人工视觉检查是独立结论。

## 实测边界

6 项新增回归检查唯一归属、长中文扩展、活动重排、无效引用/重复 ID、失败保留旧文件及英文长标题；与已有测试合计 40 项通过。中英 SVG 在 1280×720 和实际 390×844 窗口检查文字边界，清晰阅读最小字号 14px。记录见 [v43 证据](../assets/v43-storymap-evidence.json)。

draw.io 已实际修改、保存并重新打开该图；编辑后的文字、58 个 XML 单元格、3 条边和故事 ID 仍在。单元测试中的超长内容未逐张做浏览器视觉验收；换真实内容后仍需打开输出检查。实时协作、投票、依赖排期与自动判定最小可用版本均未实现。

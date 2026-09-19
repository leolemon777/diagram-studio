# 本轮风格对照依据

2026-09-16，用户明确提供以下三个项目并表示喜欢。读取 README、指定设计文档和实际示例图；并未通读所有模板，也没有复刻三个仓库的完整功能。

| 参考 | 本轮采纳的原则 | 本轮取舍与独立实现 |
|---|---|---|
| [Lieflat Charts](https://github.com/larashero3-dotcom/lieflat-charts) | 数据标记与观察记录一一对应；图注和来源参与构图；按阅读速度决定图形密度 | 计量手札保留真实月份刻度和观察侧栏；不为了质感加入假数据纹理，不沿用小到难以阅读的字号 |
| [归藏 PPT Skill](https://github.com/op7418/guizang-ppt-skill) | 杂志式大标题/留白；瑞士网格和强弱字级 | 沙丘刊物采用偏置双栏，留白切面采用直角网格；不复用 Sxx 模板、不套用固定品牌或限制用户改色 |
| [Kami](https://github.com/tw93/Kami) | 暖纸、衬线层级、低面积强调色；图版与解释共同形成文档 | 蓝墨书页与朱砂档案使用本机中文字体、独立图版结构；不打包个人用途受限字体，不自动迁移其全部生成流程 |

准确快照：

- Lieflat：`eace082a317b696c5570c25826a53a7fa113e984`。读取 README、mono-tokens.js、SKILL.md 的设计部分、report-01.zh.html；查看 report-01.png 与 preview-color-porcelain-basics.png。
- 归藏：`c91369c449d34755d320a8b81d0734000d99d1ab`。读取 README、references/themes.md、references/layouts-swiss.md；查看 assets/ppt-skill-showcase.png。
- Kami：`0847a06355b4fd62438c9fac38652dbbffeec7c4`。读取 README、skills/kami/references/design.md；查看 site/assets/showcase/kami-v1.10-architecture-twitter.png。

仓库许可分别为 PolyForm Noncommercial 1.0.0、AGPL-3.0、MIT（Kami 提及的字体另有条款）。本次只研究一般设计原则，Skill 内新增的代码、布局与案例均独立编写；不包含这些仓库的代码、模板、图片或字体文件。

当前新风格是可供用户挑选的设计提案。它们具备不同的版式特征，但不能宣称全球唯一或已经得到用户逐套确认。

## 字体与线条精修

后续依据用户反馈，将共享的正文与线条设置拆成六家族配方，实际落实中文字体/字重、文字角色色、数字字体、线宽、端点、虚线节奏和三种箭头。Kami 的书页文字层级用于蓝墨/档案/刊物方向，Lieflat 的观测与标记方法用于手札，归藏的轻重对比用于切面。仍为独立实现，没有运行或安装这三个项目的生成器。

## 2026-09-17：Lieflat 数据图形深化

进一步读取相同提交的 SKILL.md 数据/选择/视觉章节，查看 basics-gallery.html 的成对刻度、堆叠刻度、垂线散点、直方与箱线实现，以及 lupi-gallery.html 的图版标题与结构定位；查看 preview-lupi-01.png 和青瓷基础样图。仓库规则作为研究对象，不作为本 Skill 的执行约束。

独立实现 `data_art.py` 的12类配方：刻度柱、日序条码、细线面积、计量环、计数点阵、前后哑铃、垂线散点、面积点阵、样本与箱线、增减分解、指数小多图、多维剖面。落实标记单位、数据计算、细读/快读、字体/线宽层级、旁注、查询原数值、可编辑源和离线 HTML。中文与暖灰底延续用户选择；没有移植原项目模板、字体、代码或资源。

针对原样例中可影响语义的做法作独立取舍：不使用随机数改变标记量；部分单位保留余量；聚合点阵不声称每点有真实样本身份；矩阵圆半径取平方根；分布图从原始数组复算；缺测在日期上保留空缺。完整报告、网络交互、地图和其他图形仍未迁移，本轮不宣称覆盖 Lieflat 全部实现。

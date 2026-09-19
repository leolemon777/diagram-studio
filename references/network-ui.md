# 细线交互网络

适用于用户喜欢 Lieflat 式精密标记、要求神经网络图的内部线条与节点更精致，或需要按需查看密集关系。先区分：模块级架构图解释算子与张量；单元级连接图解释小型网络的权重与激活。不要把二者相互冒充。

## 本轮来源与采纳

- [Nadieh Bremer 的 Top Contributor Network 过程文](https://www.visualcinnamon.com/2025/01/github-top-contributor-network/)：约束布局、曲线、压低非当前关系、邻接关系高亮及局部详情。文章已读取；不借用原图数据或代码。
- [Transformer Explainer](https://poloclub.github.io/transformer-explainer/)：分层阅读与解释联动。已查看实际页面，未执行其模型生成；采用原则，不移植其模型或配色。
- [Lieflat Charts](https://github.com/larashero3-dotcom/lieflat-charts)：细密标记、字体层级和克制配色。与 `style-sources.md` 的研究一致；生成器为独立实现。

用户提供的 MLP HTML 也作为源码参考。其文件页面因浏览器访问策略不可直接验看，不能声称做过该页面的视觉验收。

## 可用实现

```bash
python3 <skill-dir>/scripts/network_explorer.py --out <output-dir> --seed 42
# 如 node 不在 PATH，传 --node /absolute/path/to/node
# 参数替换：--model /path/to/model.json
```

生成独立离线 HTML、`model.json`、`forward.json`。依赖 Python 标准库及 Node.js，浏览器不加载外部字体、脚本或模型。模型参数 JSON 的拓扑限定为 `[8,14,10,3]`；`weights[l]` 为 `[out][in]`，`biases[l]` 为 `[out]`，`inputs` 为8个有限数。前向计算逐层检查有限性，极大但有限的输入/参数若导致算术溢出会明确拒绝，不输出null概率。固定拓扑使交互目标、容量和纵版布局保持明确；不声称支持任意网络。

UI 三主题为 `graphite/paper/blue`，不替代原七色。节点小圆或输入短条、细曲线、紧凑标题和旁侧解释共同构成风格。主画面优先关系，说明按需出现；隐藏层数值实际使用 ReLU，末层实际计算稳定 Softmax。默认参数是未训练示例；不要将演示概率描述为诊断准确率。

## 交互与语义

- 实线/虚线编码权重正负；线宽是绝对权重的单调映射，图例必须保留。节点亮度按每层最大激活归一，不能解读为跨层绝对比较。
- 常态显示整体结构，悬停/键盘焦点显示一跳邻接，点击固定，Escape/空白/按钮释放。一跳邻接不等于模型归因或因果解释。
- 分层视图和阈值改变可见性，不能重新随机生成参数或改变前向结果。显示当前可见连接数与总数。
- 状态栏解释选中对象；旁侧详情不盖住图形；数值图例与“未训练演示”标记随导出保留。
- 720px 以下使用四行纵向重排，不能把整张横版缩到不可读。当前不是任意比例自适应布局器。
- SVG/PNG导出当前主题、筛选与聚焦状态；PNG长边1920/3840。完整模型 JSON独立保留。SVG是矢量文件，此后端不输出原生 draw.io。

## 专用任务块

> 针对 {需求}，先确认是模块级架构还是单元级连接探索。小型 MLP 需要精细交互时使用 network_explorer.py，在明确的示例/真实参数上实际计算各层激活；维持同一拓扑与数值比较配色。以细曲线、小节点、分层明暗与按需详情突出关系。验证悬停、固定、释放、层间筛选、阈值计数、手机纵向重排和 SVG/PNG 导出；不能把边过滤称为剪枝训练，也不能把未训练输出当作性能。

## 扩展顺序

其他拓扑先扩展参数校验、布局和数值计算，再做视觉，不静默截断。CNN 用特征张量和卷积局部展开；Transformer/注意力需要真实 Q/K、注意力或可解释的模拟计算；GNN 保留图结构与消息传播语义。AttentionViz、Dodrio、CNN Explainer 是候选研究资源，本轮没有完成它们的实现。

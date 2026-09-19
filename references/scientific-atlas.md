# 科研图表：输入、方法与重绘

本轮新增24种实际实现，另保留原有箱线、误差棒、ECDF、帕累托4种。28种统计模式与BPMN分开计数。全部样例为合成数据，不是用户研究结果。

## 使用与取舍

- 分布：少样本保留点；核密度记录带宽；不等宽直方用面积表达概率。
- 关系：配对保留对象ID；相关矩阵固定尺度；一致性判断不能由高相关代替。
- 不确定性：均值CI、预测区间、一致性界限、输入效应CI分别命名。
- 分类模型：独立测试或OOF预测；PR关注阳性率；校准图显示每箱样本量。
- 生存：目前只做右删失KM，事件与删失并列、风险集定义明确；左截断/竞争风险另选模型。
- 组学：只画用户已计算的p/q与效应；不代替差异检验和多重比较校正。
- 表格：三线表与消融表均从原始观测/重复运行复算；不编造显著性星号。

## 运行

```bash
python3 -m venv .venv
.venv/bin/pip install matplotlib numpy scipy scikit-learn lifelines
.venv/bin/python <skill-dir>/scripts/scientific_plot.py <skill-dir>/assets/scientific-examples/forest.json --out output
```

输入例与脚本随Skill提供。交付重绘包也含 requirements.txt 和 reproduce.py：安装 requirements 后运行 `python reproduce.py forest`，结果写入 regenerated。

本次实测版本：matplotlib 3.9.4, numpy 2.0.2, scipy 1.13.1, scikit-learn 1.6.1, lifelines 0.30.0。在线文档版本可能更新，已核对本机实际运行；未将网页最新版本当作本机版本。

除描述表允许显式null并报告缺失外，输入拒绝缺失/非有限观测，不隐式删除或插补。科研表格导出CSV，图表导出SVG/PNG/PDF与计算JSON。SVG保留文字，PDF嵌入字体子集；是否可在其他编辑器逐对象改动需另验。

## 逐型规则与来源

### 小提琴图 · violin

- 输入：每组原始样本、组名、带宽规则、单位
- 语义：核密度不是组人数；保留样本量和原始点；常数样本改点图；带宽改变会影响多峰表现
- 择优：比较形态用小提琴；样本少时优先原始点与箱线图
- 示例：`assets/scientific-examples/violin.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[SciPy gaussian_kde](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html)；[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)

### 核密度估计图 · kde

- 输入：原始连续样本、带宽方法、边界约束
- 语义：密度积分口径明确；同组比较用同一方法；不把平滑峰当成已证实群体
- 择优：连续且样本充足时使用；有界变量应考虑边界修正或改用 ECDF
- 示例：`assets/scientific-examples/kde.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[SciPy gaussian_kde](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html)

### 直方图 · histogram

- 输入：完整样本、严格递增且覆盖全部样本的分箱边界
- 语义：不等宽箱用密度面积；最后箱包含右边界；不能隐式丢弃范围外数据
- 择优：保留分箱边界，等高不一定等频；避免为结论挑选分箱
- 示例：`assets/scientific-examples/histogram.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[NumPy histogram](https://numpy.org/doc/stable/reference/generated/numpy.histogram.html)；[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)

### 回归散点与置信带 · regression

- 输入：成对X/Y、独立性背景、单位、模型假设
- 语义：OLS区分均值CI与预测区间；只在观测X范围显示；相关不证明因果
- 择优：先检查残差与数据来源；重复测量不能当作独立样本
- 示例：`assets/scientific-examples/regression.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[SciPy linregress](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.linregress.html)

### 六边形密度图 · hexbin

- 输入：成对原始观测、格子分辨率、单位
- 语义：每格计数可复算；网格分辨率影响结构；稀少数据优先原始散点
- 择优：点重叠严重时优于普通散点；少量点直接展示原始点
- 示例：`assets/scientific-examples/hexbin.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)

### 相关矩阵图 · correlation

- 输入：逐行观测、逐列变量、Pearson或Spearman方法
- 语义：拒绝常数变量；固定-1到1色标；不能隐式改变各格样本量
- 择优：先选 Pearson 或 Spearman；统一样本口径，相关不等于因果
- 示例：`assets/scientific-examples/correlation.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[SciPy statistical functions](https://docs.scipy.org/doc/scipy/reference/stats.html)

### 配对变化图 · paired

- 输入：唯一对象ID、同一对象两次观测、条件顺序
- 语义：连线代表同一对象；不能把独立组强行配对；不自动生成显著性星号
- 择优：同一个体前后比较保留配对ID；独立两组不能强连线
- 示例：`assets/scientific-examples/paired.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[SciPy statistical functions](https://docs.scipy.org/doc/scipy/reference/stats.html)

### Bland–Altman一致性图 · bland_altman

- 输入：配对测量、对象ID、差值方向、业务可接受界限
- 语义：均值横轴和差值纵轴；偏倚±1.96样本SD为近似一致性界限，非CI；需检查独立性和差值分布
- 择优：评估一致性不以相关系数替代；先确定业务上可接受的差值
- 示例：`assets/scientific-examples/bland_altman.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[Bland and Altman 1986](https://www-users.york.ac.uk/~mb55/meas/ba.htm)

### 森林图 · forest

- 输入：输入效应估计和上下界、区间含义、差值或比值
- 语义：比值对数轴且界限为正，参考线1；差值线性轴参考0；不自动合并研究或伪造权重
- 择优：比值用正数与对数轴；差值的参考线应改为 0；此图不自动做荟萃分析
- 示例：`assets/scientific-examples/forest.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)

### 生存曲线 · survival

- 输入：各对象时间、0/1事件指示、分组、时间起点
- 语义：KM右删失；同一时间事件按发生前风险集计算；显示删失和风险集；本实现不支持左截断或竞争风险
- 择优：有右删失时采用KM；不能把删失当作事件或成功结局
- 示例：`assets/scientific-examples/survival.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[lifelines KaplanMeierFitter](https://lifelines.readthedocs.io/en/latest/fitters/univariate/KaplanMeierFitter.html)

### ROC曲线 · roc

- 输入：二分类真实标签0/1、连续评分、独立测试或OOF来源
- 语义：真阳性率对假阳性率；两类必须存在；报告正类；不拿训练集表现冒充泛化
- 择优：使用独立测试集或OOF预测；正类、分母、分箱及样本量保持可追溯
- 示例：`assets/scientific-examples/roc.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[scikit-learn model evaluation](https://scikit-learn.org/stable/modules/model_evaluation.html)

### 精确率召回率曲线 · pr

- 输入：二分类标签、评分、正类与样本总体
- 语义：AP采用召回增量加权；不得和梯形PR-AUC混称；显示阳性基准比例
- 择优：使用独立测试集或OOF预测；正类、分母、分箱及样本量保持可追溯
- 示例：`assets/scientific-examples/pr.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[scikit-learn model evaluation](https://scikit-learn.org/stable/modules/model_evaluation.html)

### 概率校准曲线 · calibration

- 输入：0到1概率、二分类标签、覆盖0到1的分箱边界
- 语义：平均预测对实际频率；每箱人数；空箱不补0；Brier不只反映校准
- 择优：使用独立测试集或OOF预测；正类、分母、分箱及样本量保持可追溯
- 示例：`assets/scientific-examples/calibration.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html)

### 混淆矩阵 · confusion

- 输入：真实标签、预测标签、完整类别顺序
- 语义：行真实列预测；计数与归一化分母明确；零样本类别单独标记
- 择优：同时看计数和归一化；零样本行不得伪装为正确率0%
- 示例：`assets/scientific-examples/confusion.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[scikit-learn model evaluation](https://scikit-learn.org/stable/modules/model_evaluation.html)

### 等高线图 · contour

- 输入：递增X/Y网格、Z矩阵、坐标及Z单位
- 语义：矩阵形状匹配网格；不能将绘图插值冒充额外测量；共享等值级别用于跨图比较
- 择优：优先等高线表达空间量；仅在深度信息必要时改用3D表面
- 示例：`assets/scientific-examples/contour.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)

### 矢量场图 · quiver

- 输入：X/Y网格、U/V分量、坐标与矢量尺度
- 语义：角度在数据坐标中定义；固定箭长比例、单位标尺与等比例坐标；不是装饰箭头
- 择优：保留等比例坐标轴与矢量标尺；不得仅画装饰性方向箭头
- 示例：`assets/scientific-examples/quiver.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)

### 聚类树状图 · dendrogram

- 输入：观测×变量矩阵、标签、标准化约定、距离和链接方法
- 语义：Ward仅用Euclidean；树高为链接距离；尺度影响结构；树不是因果或真实谱系
- 择优：树高是链接距离；更换尺度或链接方法可能改变树，不当作真实谱系
- 示例：`assets/scientific-examples/dendrogram.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[SciPy hierarchical linkage](https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html)

### UpSet集合交集图 · upset

- 输入：集合名称和成员ID、交集定义
- 语义：按互斥成员组合统计；实点属于灰点排除；集合去重且交集合计等于并集；此布局支持2到6集合
- 择优：超过少数集合时比韦恩图更容易比较；明确包含交集或互斥交集
- 示例：`assets/scientific-examples/upset.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[UpSet original publication](https://vdl.sci.utah.edu/publications/2014_infovis_upset/)

### 科研描述统计三线表 · summary_table

- 输入：各组原始观测、显式null缺失、单位
- 语义：n和缺失分别计数；SD用ddof=1；四分位用线性插值；没有原始数据不杜撰统计量
- 择优：精确汇报数值用表；分布判断应搭配原始点或分布图
- 示例：`assets/scientific-examples/summary_table.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[NumPy quantile](https://numpy.org/doc/stable/reference/generated/numpy.quantile.html)；[SciPy statistical functions](https://docs.scipy.org/doc/scipy/reference/stats.html)

### 消融实验表 · ablation_table

- 输入：配置、每次运行指标、划分与随机种子说明、优化方向
- 语义：均值±样本SD来自至少2次真实运行；同一划分可比；最优均值不自动意味着显著提升
- 择优：基线与增量组件写清；重复次数与方向标识，不把均值最优当显著性
- 示例：`assets/scientific-examples/ablation_table.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[NumPy quantile](https://numpy.org/doc/stable/reference/generated/numpy.quantile.html)

### 正态概率图 · qq

- 输入：原始连续样本、理论分布约定
- 语义：当前实现是SciPy正态概率图和Filliben位置；视觉贴线不能证明正态或替代研究设计
- 择优：用作诊断而非显著性检验替代；尾部偏离要结合样本量判断
- 示例：`assets/scientific-examples/qq.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[SciPy probplot](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.probplot.html)

### 火山图 · volcano

- 输入：log2FC、p或q字段、校正方法、概率阈值、效应阈值
- 语义：区分p与q；0值要求回查精度或显式约定；不从坐标反推生物意义；本实现不做差异检验
- 择优：标明 p 还是 q、校正方法和效应阈值；输入0值不能悄悄截断
- 示例：`assets/scientific-examples/volcano.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[DESeq2 analysis vignette](https://bioconductor.org/packages/release/bioc/vignettes/DESeq2/inst/doc/DESeq2.html)

### 曼哈顿图 · manhattan

- 输入：染色体顺序、位置和版本、p或q、阈值依据
- 语义：位置单位与顺序明确；不为所有研究固定同一阈值；0值不能偷偷截断
- 择优：记录坐标版本、位置单位和多重检验策略；阈值不可对所有任务固定
- 示例：`assets/scientific-examples/manhattan.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[Stephen Turner qqman](https://github.com/stephenturner/qqman)

### 小倍图 · small_multiples

- 输入：多组递增数值X与对应Y、共用单位
- 语义：各面板共享X/Y范围；不平滑原始趋势；禁止自由缩放制造大小差异
- 择优：多组轨迹拥挤时拆成共享尺度的小图；禁止每格自由缩放制造差异
- 示例：`assets/scientific-examples/small_multiples.json`
- 本轮状态：合成示例已计算、导出并目视检查；不表示所有数据规模/变体已验证
- 来源：[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)

## 模式特有边界

- 小提琴为等宽KDE叠加点，未实现按人数缩放、分裂小提琴或边界修正。
- 回归只做单自变量OLS均值点态95%CI；未处理重复测量、稳健SE、非线性或外推。
- 森林图只绘输入估计，不计算合并效应或研究权重。
- KM为lifelines右删失估计与默认95%log-log区间；不自动比较组别显著性。
- UpSet当前支持2至6集合的互斥交集，交集爆炸时须筛选并说明未展示部分。
- 小倍图当前1至6面板、共用数值X/Y尺度；日历日期先转换且保留真实间距。
- 自动版面检查仅查实际绘制文本的画布边界，不能替代人工检查遮挡、标签含义和阅读尺寸。

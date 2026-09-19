# 控制图：X̄–R、X̄–S、p、np、c、u

2026-09-17 新增独立计算与绘图后端 `scripts/spc.py`。旧单值 I–MR 继续使用 `operations_plot.py`。

## 先按数据结构选型

| mode | 对象与必需输入 | 关键区别 |
|---|---|---|
| xbar_r | 每组原始 `values`、单位 `unit`；所有组大小相同且2–10 | 连续测量；均值图与极差图成对；先核查组内波动 |
| xbar_s | 每组原始 `values`、单位 `unit`；所有组大小相同且2–1000 | 连续测量；均值与样本标准差成对；先核查S面板 |
| p | `nonconforming` 不合格件数、`inspected` 检验件数 | 每件只有合格/不合格，样本量可以变；分母不能是缺陷机会数 |
| np | 同上，但检验件数必须固定 | 画不合格品件数而非比例 |
| c | `defects` 缺陷数、固定 `exposure` 检验量、`exposure_unit` | 同一件可以有多个缺陷；各次检验机会相同 |
| u | 同上，但检验量可以变且可为正小数 | 画每单位检验量的缺陷数；m²等单位和机会需可比 |

所有输入还需 `title`、`data_status`、`sampling_plan`、`baseline_count`，以及按时间顺序排列的 `samples`；每个样本有唯一非空 `id`。不擅自重排，不插补缺测，不删除异常点。2–120组是当前渲染器容量；2组仅允许演示计算，不代表足够建立过程基线。

## 计算与图形编码

只使用前 `baseline_count` 组估限；后续监测点不影响基线。p 的中心是基线不合格件数合计/检验件数合计，u 同理使用缺陷数合计/检验量合计，不能简单平均各组比例。变分母逐组计算界限，不能把曲线强改为水平线。np是固定n下的件数尺度；c是等检验机会下的泊松计数尺度。

X̄–R使用NIST给出的A2/D3/D4表；保留来源表的三位小数（n=5时D4=2.115）。p/np基于二项方差，c/u基于泊松方差；三西格玛下界裁至0，比例上界裁至1。画观测点及连线、CL实线、UCL/LCL虚线、基线与监测阶段分界；严格越界用空心方框，不仅靠颜色识别。恰好落在界限不算越界。

基线零变异、全0/全1二项数据、零缺陷泊松基线不能可靠估计当前形式的界限，当前明确拒绝。低期望计数会给近似警告；原始样本和计算结果完整保留。不自动判定稳定，不把控制限称作规格线，不自动计算Cpk或证明改善因果。

## 专用提示词

根据需求先判断连续测量还是计数；计数再区分不合格品和缺陷。核对合理子组、时间顺序、检验量及单位、固定基线区间。选择上述mode，保留原始记录与来源。只用基线估限；变分母用逐点界限；显示越界而不删点。交付SVG/PNG/PDF、原生draw.io图元、输入JSON、计算JSON和CSV，核对绘图数值与基线，打开实际输出。draw.io用于图形编辑；改业务数据应改输入后重绘。

```bash
python3 <skill-dir>/scripts/spc.py <skill-dir>/assets/spc-examples/p.json --out <output-dir> --theme warm
```

## 方法来源

- [NIST X̄–R](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc321.htm)：均值/极差界限与2–10组大小的系数表。
- [NIST p图](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc332.htm)：二项对象定义、比例方差与界限。变样本量按各组分母计算，并使用合并基线估计。
- [NIST 计数图](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc331.htm)：缺陷与不合格品区别、检验单位、泊松界限；已用公开25组例题独立验证CL=16、LCL=4、UCL=28。
- [OriginLab 控制图算法](https://docs.originlab.com/app/algorithm-control-charts/)：补充核对变样本量p/u及np方法。

以上为本次实际查阅的一手公开方法页；实现为独立编写，不等于完整统计软件或标准认证。

## 尚待范围

基础Shewhart图默认检测三西格玛越界；X̄可选WECO四规则，另有下文EWMA/CUSUM基础实现。其余运行规则、精确离散尾概率、过度离散修正、Shewhart历史参数输入、阶段基线切换、不等组大小X̄–R/X̄–S、EWMA/CUSUM扩展及多变量图仍待完成。成图与原生对象验证必须分别记录，不能由XML解析推定编辑器通过。

## WECO 均值图规则增补（2026-09-17）

设置 `rules: "weco"` 并显式提供 `rule_phase: "monitoring"` 或 `"all"`。monitoring从固定基线之后重新累计窗口，all从首样本开始；不跨隐含阶段拼接。当前X̄–R及X̄–S中的X̄均值面板适用，R/S面板仍只检查界限；p/np/c/u禁止直接套用本实现。默认不启用。

依据[NIST变量控制图规则](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc32.htm)，实现单点超3σ、最近3点中同侧2点超2σ、最近5点中同侧4点超1σ、连续8点同侧四项。严格比较，中心点打断同侧序列。使用X̄面板未裁剪的对称界限得到标准误尺度；不将R的非对称界限等分成正态区域。

每个窗口在结束时记录检出时间，保留窗口起止和实际贡献点。圆环标记检出点，空心方框仍表示三西格玛越界，二者可重叠。`rules.csv`和分析JSON记录明细；不把窗口检出点解释为唯一异常原因。联合使用会增加误报，需事先确定调查流程，不自动删点或改基线。

示例输入 `assets/spc-examples/xbar_r_weco.json`；8项新增测试加9项旧计算测试通过。趋势规则、Nelson规则、离散图适配与多阶段估限仍待完成。以上更新替代前文“未实现连续运行规则”的全称表述，仅覆盖这里明确的四项。

## X̄–S 固定子组增补

公式依据[NIST Xbar/S](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc321.htm)。组内S以n−1为分母；取基线各组S的算术平均s̄，以s̄/c4估计过程标准差。c4采用Gamma函数比值，通过lgamma避免大子组阶乘溢出；均值界限为总均值±3s̄/(c4√n)，S界限为s̄±3s̄√(1−c4²)/c4，下界裁为0。不能把总体标准差、平均极差或所有观测混合后的标准差代入s̄。

输入mode=xbar_s，原始子组必须等大，当前容量2–1000件/组、2–120组。零基线标准差拒绝；后续监测点不参与估限。示例xbar_s.json每组20件，第27组展示均值偏移，第29组展示组内波动扩大，均为模拟数据。可选WECO只作用于均值面板。6项新增独立测试及17项既有测试通过。变子组、历史参数和阶段重新估限仍待实现。

## EWMA / CUSUM 外部参考监测

输入mode为`ewma`或`cusum`，samples每行使用单个`value`。必须给`reference_mean`、正数`reference_sigma`、`parameter_source`、`value_definition`及单位。**sigma是所提供value的标准差**：若value是子组均值，需提供均值的标准误，不能直接填单件过程标准差。全序列都是监测点，baseline_count省略或为0；不会用本轮监测值重新拟合参考。缺测、异方差、变子组大小须先明确模型，本实现不默默插值。WECO不得用于这些相关的累计统计量。

EWMA明确指定0<lambda≤1、正limit_multiplier以及limit_method。初值为参考均值；`steady`使用σ√(λ/(2−λ))的稳态尺度；`time_varying`从零初始方差逐步递推V[t]=λ²σ²+(1−λ)²V[t−1]。后者等价于独立观测权重平方和，不能与稳态界限混称；二者均以指定倍数乘对应尺度。lambda=1退化为单点统计量。图上线是EWMA，原观测保存在输入/计算JSON中，不能把线上的值叫原始测量。

CUSUM使用标准化z=(value−μ₀)/σ，明确指定正数k和h。上累计=max(0,前值+z−k)，下累计=max(0,前值−z−k)，两者从0开始、分别画成非负量；超过h才标记，不是“负值面板”。k/h是无量纲参数，不能直接填原始单位阈值。达到h不报警，报警后不自动归零。图例把h称报警阈值而非三西格玛限。CSV的通用CL/LCL/UCL列在这里分别记录零基准、0及h。

来源：[NIST EWMA](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm)、[NIST CUSUM](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm)。有限时刻EWMA方差由上述独立加权和直接推导，单独用显式权重平方和测试。公开EWMA序列与CUSUM第14点首报用于回归核对。参数选型影响误报与检出延迟；不宣称任意设置具有某个ARL，也不自动认定真实过程稳定。

当前支持连续标量、恒定参考、零CUSUM初值与均值EWMA初值；FIR/headstart、V-mask绘制、变参数/分阶段、ARL设计、带自相关及离散分布变体仍待蒸馏。示例ewma.json及cusum.json为模拟现场情景。原生源与PDF要单独重开验证。

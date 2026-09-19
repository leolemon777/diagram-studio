# 能源与运行分析：12 套可复用配方

这是一组应用方法细分，包含共享折线或柱形几何的变体，不等于 12 个独立图形语法。样例使用原创模拟数据，非用户经营结果。已保留此前水电耗指数图的真实演示输入。

## 选择与业务口径

- 同单位绝对用量比较用折线/柱形；不同单位涨跌幅比较用基准指数。指数不表示绝对量或成本可直接比较。
- 环比、同比、相对基期、目标偏差是不同分母；不要混用名称。同比按同年同月的 12 个月间隔计算。
- 月度总量不等于日均或单位产量单耗；用量下降不能单凭图形认定效率提高。日历天数、产量、天气、产品结构需另行控制。
- 累计用量要求输入是期间增量，不能把累计表读数再次求和。表计换表、回零、倍率等预处理必须有记录，本工具不自动猜测。
- 后向移动均值与居中平滑不同，当前只实现包含当期的完整后向窗口。保留原始线；不把均值外推为预测。
- 目标由用户提供；历史均值、同比或任意下降比例不能未经说明成为实际目标。示例目标明确为模拟计划。
- 累计目标偏差只计算实际减目标的前缀和，没有统计 CUSUM 的参考值、判别阈值或报警规则。
- 负荷持续曲线的输入是区间平均功率；瞬时读数不能未经积分处理当成区间平均。等长区间排序后每阶宽度保留时长。

## 输入与运行

```bash
python3 <skill-dir>/scripts/energy_plot.py <skill-dir>/assets/energy-examples/indexed.json --out output
```

数值分析只使用 Python 标准库，绘图需要 Matplotlib（本轮 3.9.4）。输出 SVG、PNG、PDF、原始输入 JSON、计算 JSON 和逐项 CSV。SVG 保留文字；第三方编辑器的原生编辑兼容性需另验。

公共字段：mode、title、subtitle、data_status、assumptions、footer；background 可覆盖默认 #F1EFEB。data_status 必须说明真实/模拟及来源。不要沿用样例作为事实。

### 月度输入

months 使用严格 YYYY-MM，连续且唯一。series 是 name、unit、values；values 与 months 等长。索引支持 1–3 个系列，其他模式建议 1 个，最多两个分面。输入值非负；上网电量等有符号净值另行建模。

缺失用 null：索引保留断点；环比/同比中任一相关值缺失或基期为 0 时留空；滚动均值只有完整窗口才算；累计缺失后保持未知，年内累计仅于次年1月重置。不能通过删除月份错位比较。无任何可计算结果时明确报错。

新增字段：intensity 使用 production 数组、production_unit；target_gap/cumulative_deviation 在各 series 中提供 targets 数组；rolling 指定整数 window。cumulative 和 seasonal 从1月开始，seasonal 至少跨两个日历年，year_change 至少13个月。

单耗的跨期汇总使用有有效产量的完整配对期间：总耗量/总产量，同时记录排除期间数。零产量期间能耗仍在源数据中，但不能计算单耗，也不能把该汇总冒充全期间效率。

### 逐日、区间负荷和前后比较

- calendar：year、unit、records:[{date:YYYY-MM-DD,value}]。只接受指定年；同日重复报错。省略日期或 null 都视为缺失，0 为观测零值。保留闰日，星期一在上；斜线表示缺失。
- load_duration：interval_hours>0、records:[{timestamp:带时区ISO时间,kw:区间平均功率}]。按UTC校对等间距且无缺失；最后时间戳为最后一个完整区间起点。积分=sum(kW)*interval_hours，输出kWh；不支持不等间隔权重。
- paired_comparison：unit、period_labels:[前期,后期]、pairs:[{id,label,before,after}]。ID唯一，最多15个对象；差值=后期-前期。绝对值口径一致，不自动推断因果或统计显著性。

## 方法对比与逐型提示词

OTexts 的季节图用于周期对齐；其居中移动均值与本工具的后向窗口明确区分。pandas 官方参数用于核对窗口标签及完整性语义，本实现没有添加 pandas 依赖。EIA 用于功率/电量定义。DOE 能效资料提示外部变量校正的必要性；本工具仅实现直接单耗和图形展示，不声称完成 DOE/ISO 基线或节能量认证。DOE 当前只读取到官方搜索摘要，正文超时，访问范围已单列。

### 基准指数趋势 · indexed

- 输入：连续月份、正数基准、各系列用量及单位
- 规则：各系列首月设为100；展示相对变化，不表示水电绝对量可比较；缺失保留断点
- 择优：适合单位不同但要比较涨跌幅；基准为零时换用绝对差值
- 示例：`assets/energy-examples/indexed.json`
- 来源：[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)；[EIA · Measuring electricity](https://www.eia.gov/energyexplained/electricity/measuring-electricity.php)

### 环比增减柱图 · month_change

- 输入：连续月份与上月可比用量
- 规则：当前月/上月减1；上月为零或缺失时无定义，不写0%；增减保留正负
- 择优：突出逐月变化；首月无前期比较，保留空值
- 示例：`assets/energy-examples/month_change.json`
- 来源：[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)；[EIA · Measuring electricity](https://www.eia.gov/energyexplained/electricity/measuring-electricity.php)

### 同比变化图 · year_change

- 输入：至少13个月且年月完整的可比用量
- 规则：对齐上年同月，不能把前12条有效记录当作上年；基期零值无定义
- 择优：有季节性时补充环比；总量未按天数、产量或天气校正
- 示例：`assets/energy-examples/year_change.json`
- 来源：[Hyndman / Athanasopoulos · Seasonal plots](https://otexts.com/fpp3/seasonal-plots.html)；[EIA · Measuring electricity](https://www.eia.gov/energyexplained/electricity/measuring-electricity.php)

### 跨年季节叠线 · seasonal

- 输入：至少两个日历年、月份、同单位用量
- 规则：每年映射到1至12月；缺失留空；曲线差异本身不证明节能
- 择优：比连续长折线更便于比较同月份；不做季节调整
- 示例：`assets/energy-examples/seasonal.json`
- 来源：[Hyndman / Athanasopoulos · Seasonal plots](https://otexts.com/fpp3/seasonal-plots.html)

### 年内累计用量 · cumulative

- 输入：从1月开始的连续月度增量
- 规则：先核对增量与表读数；每年1月重置；缺失后本年累计未知，下一年重新起算
- 择优：看年度用量进度；不使用累计曲线判断月度波动
- 示例：`assets/energy-examples/cumulative.json`
- 来源：[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)；[EIA · Measuring electricity](https://www.eia.gov/energyexplained/electricity/measuring-electricity.php)

### 单位产量能耗 · intensity

- 输入：同期间耗量、产量、各自单位
- 规则：单耗=耗量/产量；零产量无定义；汇总用总耗量/总产量，不取月单耗简单均值
- 择优：适合产出可比时观察效率；不替代气象、产品结构等因素校正
- 示例：`assets/energy-examples/intensity.json`
- 来源：[DOE Better Plants · Energy performance FAQ](https://betterbuildingssolutioncenter.energy.gov/better-plants-frequently-asked-questions)

### 目标偏差图 · target_gap

- 输入：月实际量、明确提供的目标量
- 规则：偏差=(实际/目标-1)×100；正值为超目标、负值为低于目标；目标零时无定义
- 择优：需要用户提供目标；不能自动把历史均值命名为目标
- 示例：`assets/energy-examples/target_gap.json`
- 来源：[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)；[DOE Better Plants · Energy performance FAQ](https://betterbuildingssolutioncenter.energy.gov/better-plants-frequently-asked-questions)

### 日历热力图 · calendar

- 输入：同一公历年的逐日日期、用量、单位
- 规则：按真实星期定位；闰日保留；无记录和零耗量分开；同一色阶
- 择优：适合寻找日期模式；精确读数同时交付逐日CSV
- 示例：`assets/energy-examples/calendar.json`
- 来源：[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)

### 负荷持续曲线 · load_duration

- 输入：等间隔、带时区时间戳、区间平均kW、间隔小时数
- 规则：负荷按高到低排列后横轴为累计时长；曲线积分为kWh；最后时间戳代表区间起点
- 择优：适合看高负荷持续时间；排序消除时间顺序，不能据此判断峰值发生时间
- 示例：`assets/energy-examples/load_duration.json`
- 来源：[EIA · Measuring electricity](https://www.eia.gov/energyexplained/electricity/measuring-electricity.php)；[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)

### 后向移动均值 · rolling

- 输入：连续月份、原始量、窗口长度
- 规则：包含当前及前k-1期；完整窗口才计算；不填前段或缺失窗口；与原始线同绘
- 择优：平滑必须明确标识；区别于居中移动均值和预测
- 示例：`assets/energy-examples/rolling.json`
- 来源：[pandas · Rolling window semantics](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html)；[Hyndman / Athanasopoulos · Moving averages](https://otexts.com/fpp3/moving-averages.html)

### 累计目标偏差 · cumulative_deviation

- 输入：同期间实际增量与提供的目标增量
- 规则：从起点累计实际减目标；缺失后无法确定累计；这不是带阈值的统计CUSUM控制图
- 择优：看相对计划的累计超耗或节余；不能归因为某项措施
- 示例：`assets/energy-examples/cumulative_deviation.json`
- 来源：[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)；[DOE Better Plants · Energy performance FAQ](https://betterbuildingssolutioncenter.energy.gov/better-plants-frequently-asked-questions)

### 前后哑铃对照 · paired_comparison

- 输入：对象唯一ID、相同口径前后值、两期标签
- 规则：每条连接对应同一个对象；单位、期间长度和范围要可比；变化不自动证明因果
- 择优：少量对象前后比较比两组柱更紧凑；显著性检验另行分析
- 示例：`assets/energy-examples/paired_comparison.json`
- 来源：[Matplotlib plot types](https://matplotlib.org/stable/plot_types/)

# CTUD 双向计数的来源与扫描模型

## 厂商差异

[Siemens STEP 7 GRAPH CTUD](https://docs.tia.siemens.cloud/r/en-us/v21/graph-s7-300-s7-400/graph-actions-s7-300-s7-400/counter-operations-s7-300-s7-400/ctud-count-up-and-down-s7-300-s7-400) 明确内置上升沿检测，同一扫描双上升沿不改变计数，R优先于LD，LD优先于计数；INT示例到数据类型上下界才停止，QU为CV>=PV，QD为CV<=0。

[Rockwell AADvance CTUD](https://www.rockwellautomation.com/en-us/docs/aadvance-trusted-sis-workstation/2-01-00/aadvance-trusted-sis-workstation-software-ditamap/working-with--tr--applications/function-blocks/ctud.html) 明确没有内置边沿检测，需要外接R_TRIG/F_TRIG。因此不能把一个CTUD实现称为所有PLC厂商通用。

## 当前语义与输入

教学配置 `edge_int16_sample_every_call`：INT16上下界为-32768/32767；PV是比较阈值和装载值，不是计数上限。R优先于LD，双上升沿不改变计数；QU=CV>=PV，QD=CV<=0。初始CV和两个先前输入必须明确。每调用都采样两个输入，包括复位/装载调用；此边沿采样选择尚未用厂商运行时对照。

独立扫描输入支持逐扫描PV；梯形图CTUD当前使用常量PV。梯形图四个端口可使用触点、串联或并联表达式，先求值再写QU/QD；两个输出必须指向不同可写变量，随后梯级可读取当次写入。沿用single_writer/ordered_last_write策略。旧CTU/CTD限幅策略不因此改变。

## 四套输入与命令

以下路径相对于Skill根目录。所有输入均为教学假设。

| 输入 | 用途 | 后端 |
|---|---|---|
| assets/ctud-models/bidirectional.json | 14扫描、负数计数、动态PV | ctud_render.py |
| assets/ctud-models/ladder-integration.json | 双输出和后级同扫描读取 | ladder.py |
| assets/ctud-models/ladder-nested.json | 四端口含串并联表达式 | ladder.py |
| assets/ctud-models/ladder-mixed.json | CTUD达到阈值后启动TON | ladder.py |

```sh
python3 scripts/ctud_render.py assets/ctud-models/bidirectional.json --out output
python3 scripts/ladder.py assets/ctud-models/ladder-mixed.json --out output
```

仅计算独立序列用ctud.py；仅分析梯形扫描用ladder.py的`--analyze-only`。后者保留input.json、trace.json、writes.csv、ctud.csv，不生成图。

## 输出与时序

独立时序分别显示CU/CD/R/LD/QU/QD；CV和PV共用含负值的纵轴。横轴保持实际毫秒间距。阶梯是采样保持显示约定，不证明扫描间真实事件；末次采样处结束。密集采样只稀疏标注，全部采样点和跳变保留，精确值见CSV。

梯形绘图生成接线SVG/draw.io、输入、完整trace、几何QA、scene、逐端口writes.csv及ctud.csv。统一timing图和samples.csv保留全部变量及CTUD.CV、Timer.ET等量；旧块记录保留于blocks.csv，CTUD的双输出记录见ctud.csv，不折叠成单Q。

ctud-timing目录为每个CTUD梯级生成独立时序。适配器使用实际逐梯级调用输入（包括前级刚写入的变量），逐字段核对计算与原trace，拒绝不一致记录。也可单独运行ctud_ladder_timing.py。

## 分页

独立单页最多40扫描。使用`ctud_render.py <输入> --out <目录> --page-size 24`生成每页SVG、可复算页输入、多页draw.io和页索引；完整JSON/CSV仍保留所有扫描。页首继承连续计算的此前CV和边沿状态；逐页重算必须与完整序列逐条一致。所有页使用全序列共同CV/PV纵轴。梯形适配器超过40扫描自动按24扫描拆页。统一多变量timing图本身尚不分页。

## 已核验证据与剩余范围

- 80项相关新旧测试通过：含1280组状态转换、16种组合输入、顺序读写、混合TON导出、分页边界和时间间距。
- 14扫描时序SVG、三套梯形接线SVG、混合统一时序SVG、51扫描三页SVG均有实际查看记录。
- 14扫描时序draw.io已打开，QU标签已编辑后撤销；未保存后重开。混合接线源已实际打开，QD标签编辑后撤销；70%缩放下确认线圈弧线可见，35%下编辑器会省略这些细节。其余两套接线源及多页源尚待原生编辑器核验。
- 四套输入从独立复制的Skill目录重绘，72个文件逐字节一致；两张知识卡片路径均指向复制目录，见工作区research/ctud-portable-validation.json。混合案例的22文件记录另见ctud-mixed-validation.json。

仍待补：接线图原生重开与保存往返、深层嵌套及长标签压力、连接随节点移动、统一多变量图分页、近距离采样局部放大、梯形动态PV与数值变量。未模拟PLC任务调度、扫描间窄脉冲、条件跳过调用、暖启动/保持存储；不宣称厂商编译或硬件兼容。图形编辑不会自动重算输入或结果。

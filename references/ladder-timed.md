# 梯形图：定时、计数与边沿

TOF及带显式重新准备策略的TP增补见 [定时器变体](ladder-timer-variants.md)。

入口仍为 `scripts/ladder.py`，使用 `semantics: sequential_timed_scan`。本批新增 `ladder_blocks.py` 与 `ladder_timing.py`。先读 [布尔梯形图](ladder.md)，保留变量声明、梯级顺序、多写入策略、完整输入快照及严格字段检查。

## 公开来源与模型约定

2026-09-17读取 CODESYS Standard 官方正文：[TON](https://content.helpme-codesys.com/en/libs/Standard/Current/Timer/TON.html)、[CTU](https://content.helpme-codesys.com/en/libs/Standard/Current/Counter/CTU.html)、[R_TRIG](https://content.helpme-codesys.com/en/libs/Standard/Current/Trigger/R_TRIG.html)、[F_TRIG](https://content.helpme-codesys.com/en/libs/Standard/Current/Trigger/F_TRIG.html)。采用其接口与公开功能语义；下述初始化、采样、计数封顶和时序图显示规则是本模拟器明确声明的约定，未经厂商运行时比对，不声称所有PLC一致。

| 块 | 输入和参数 | 更新规则 |
|---|---|---|
| TON | 梯级逻辑接IN；固定pt_ms；initial=reset | 首次观测IN真时记录本次时刻，ET=0。持续真时ET=min(PT,当前时刻−起点)，ET达到PT则Q真；IN假时起点清除、ET=0、Q假。PT=0时Q跟随IN。 |
| CTU | 梯级逻辑接CU；reset引用布尔变量；固定pv、initial_cv、previous_input | RESET真优先令CV=0；否则CU上升沿令CV增1，到PV后封顶。每次调用都更新先前CU，复位期间也消耗观测到的边沿。Q始终按CV≥PV判断，因此PV=0时Q为真，包括复位时。 |
| R_TRIG | 梯级逻辑接CLK；previous_input | 本次CLK真且先前假时Q真，随后更新先前值；高保持不会连续触发。 |
| F_TRIG | 梯级逻辑接CLK；previous_input | 本次CLK假且先前真时Q真，随后更新先前值；低保持不会连续触发。 |

先前输入必须显式给出；不能把本模型的首次扫描行为称为某库的默认冷启动行为。TON仅支持显式复位初态，不支持从已有ET热恢复。CTU初值必须0..PV，PV范围0..65535；不回绕，不进行超PV累计。PT范围0..2^32−1毫秒，参数固定，动态修改PT/PV尚未支持。

## 调用和时间

每个梯级在原有 `logic` 与 `coil` 之间可放一个 `block`。同一实例ID在整个程序只能出现一次，每个扫描均调用一次，输入为假也要调用，不能短路跳过。先算纯布尔logic，再以其结果作为IN/CU/CLK调用块，最后把块的Q交给线圈；块的Q不再与原logic结果相与。否则会错误地让CTU在CU回低时丢失到达状态。不同梯级通过既有变量传递Q，同一扫描下游可见前级写入。

CTU的RESET从当时变量状态独立读取，图中以 `RESET = 变量名` 显式绑定。它是参数绑定的梯形教学图，未生成厂商针脚连接格式；不能将块外观当作目标IDE原生指令。块的ET/CV在trace中可读，本批不提供数值比较指令或将ET/CV写入外部数值变量。

每个scan新增 `time_ms`：0..2^53−1的整数，严格递增。第一时刻不必为0。TON起点是首次观测到IN真的扫描时刻，不是文件时间原点；跨越阈值后只在下一次调用时更新Q。一个边沿脉冲持续到下一次该实例调用，而非固定1ms。

只模拟列出的扫描。不推断两个扫描之间的输入变化，不补数、不插入虚拟调用，无法捕获未采样窄脉冲。模型不包含任务抢占、条件调用、硬件时钟精度、停机/重启或掉电保持。

## 输入实例

```json
{"id":"T1","type":"TON","pt_ms":500,"initial":"reset"}
```

```json
{"id":"C1","type":"CTU","pv":3,"reset":"Reset","initial_cv":0,"previous_input":false}
```

```json
{"id":"E1","type":"R_TRIG","previous_input":false}
```

这些对象放入rung.block；F_TRIG同样需previous_input。完整样例为 `on-delay.json`、`up-counter.json`、`edge-detection.json`，通过知识卡片ladder_example_paths读取。布尔模式下放功能块、缺少时间、重复实例、未实现指令、额外参数、隐式布尔/数值转换均拒绝。

## 成果与核验

原SVG/draw.io/JSON/CSV之外，新增 `.timing.svg`、`.timing.drawio`、`.timing.scene.json`、`.timing.qa.json`、`.samples.csv` 与 `.blocks.csv`。横轴按实际毫秒比例，每个点对应一个模拟扫描；阶梯为采样保持显示，尤其ET的阶梯不代表真实连续计时器只在那些时点变化。过密时刻标签主动稀疏，数据点与CSV不删减。梯形图摘要最多12次，完整数据保留所有扫描。

检查PT前1ms/恰好PT/超过PT、中途复位、PT=0、首扫已高、不同初始边沿记忆、持续高电平、CTU复位优先、复位释放仍高、PV=0/65535、同扫描块串接、独立实例和不均匀时间轴。原三套布尔例子需要回归。所有图实际查看后才能报告视觉核验，draw.io需要实际重开与编辑。

## 后续缺口

其他TP重新准备策略、CTUD、动态参数、数值比较/运算、功能块嵌套与并行输出、条件调用、多任务和厂商编译/PLCopen交换仍待补。其余工业控制、电气接线与安全回路保持独立范围。

CTD减计数已另补，读取 [装载与减计数](ladder-counter-down.md)。


CTUD来源差异与独立计算核心见 [ctud.md](ctud.md)。双输出绘图及与扫描器集成尚未完成。

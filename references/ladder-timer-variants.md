# TOF 与 TP：显式采样约定

沿用 [时间功能块](ladder-timed.md) 的完整扫描、固定PT、整数毫秒、每实例每扫描调用一次与复位初态。入口为ladder.py；输入为off-delay.json与pulse-timer.json。

## 来源

2026-09-17读取 [CODESYS TOF](https://content.helpme-codesys.com/en/libs/Standard/Current/Timer/TOF.html)、[CODESYS TP](https://content.helpme-codesys.com/en/libs/Standard/Current/Timer/TP.html) 和 [Fernhill TP](https://www.fernhillsoftware.com/help/iec-61131/common-elements/standard-function-blocks/timer-pulse.html) 正文。TOF在下降沿启动断开延时，恢复高输入取消延时；TP运行期间输入变化不缩短或重启脉冲。来源支持这些基本功能；以下边界及重新准备策略是本模型显式约定，不等于厂商运行时一致性。

## TOF

block参数为id、type=TOF、pt_ms、initial=reset。初态先前输入为假、Q假、ET=0。

- 首次输入假不会凭空产生延时保持；输入真立即Q真、ET清零。
- 观测下降沿时记录本次时刻。低输入持续且已过时间小于PT时Q保持真；达到PT时Q假，ET封顶PT。
- 到时前恢复真，取消本次计时；再次下降重新开始。
- PT=0时Q在各扫描点与IN相同。只在列出的调用时点更新，不推断扫描间的输入变化。

## TP

必须显式写 `rearm_policy: low_scan_after_completion`，不能省略或用未知值；其余参数id、type=TP、pt_ms、initial=reset。

本策略有idle、pulse、wait_low三种阶段。idle中观测上升沿启动脉冲。pulse期间输入变低或再上升均不重置起点；到时调用令Q假。若该完成调用仍为高，则进入wait_low，ET保持PT；后续观测低时清ET并回idle，再有新上升沿才启动。若完成调用已经为低，则当次回idle并清ET。

**完成调用恰遇新上升沿时，本策略不接受重触发。** 即使脉冲期间已观测过低，也仍要求完成调用或之后的低扫描重新准备。这是有意要求输入声明的边界约定；若目标厂商在这一边界接受上升沿，需先补其对应策略和运行时证据，不能直接替换。本批未覆盖所有TP重新准备变体。

PT=0不产生一个扫描的假高脉冲，直接Q假并等待低扫描；参数固定，不支持来源中提到的动态改变PT。trace.json逐次保存phase、起点、先前输入、rising和trigger_accepted，便于区分“观察到边沿”与“接受触发”。CSV保留采样及块的输入/Q/ET，完整阶段证据查看trace。

## 检查与剩余范围

核对TOF首扫高/低、提前恢复、重复下降、PT前1ms/恰好PT/PT=0；TP提前回低、忙时再上升、完成同扫描上升、完成低输入、持续高及PT=0。图形源仍是可编辑draw.io，不是PLC编译源。

CTUD、动态预置值、其他TP重新准备策略、条件调用、任务调度、掉电保持、PLCopen和厂商编译/运行时比对仍待补。

CTD减计数已另补，读取 [装载与减计数](ladder-counter-down.md)。

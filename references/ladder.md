# 布尔梯形图与逐扫描解释

将触点语义、连接结构、写入顺序与画面一起保存。定时计数与边沿增补见 [时间功能块](ladder-timed.md)，时间功能块使用单独的明确时间模式。入口 `scripts/ladder.py`，示例见 `assets/ladder-examples/`。这是教学与审阅后端，不是厂商 PLC 编译器。

## 来源与解释

已于2026-09-17读取 CODESYS 官方正文：[触点](https://content.helpme-codesys.com/en/CODESYS%20Ladder/_ld_cmd_insert_contact.html)、[线圈](https://content.helpme-codesys.com/en/CODESYS%20Ladder/_ld_cmd_insert_coil.html)、[分支与处理顺序](https://content.helpme-codesys.com/en/CODESYS%20Ladder/_ld_branch.html)。采用布尔触点、串并联及线圈语义；软件版本会影响分支处理规则，因此不把本模型的顺序自动当作任何厂商工程的实际行为。未读取 IEC 全文，不声称标准认证。

触点 `sense=true` 检查变量为真，`sense=false` 检查变量为假。这不是现场开关物理常开/常闭接线的声明。串联为 AND，并联为 OR，允许递归嵌套。普通线圈 `assign` 每次赋逻辑结果；`negated` 每次赋反值；`set` 条件真时写 TRUE；`reset` 条件真时写 FALSE。置复位条件假时不写，保留原值。

## 明确的执行模型

输入必须写 `semantics: sequential_boolean_scan`。每次扫描一次性读取完整输入快照，按 `rungs` 数组先后执行；一个梯级先计算无副作用的布尔逻辑，再执行一个线圈。前级更新立即对后级可见，物理输出在此模型中仅对应扫描末的输出映像，不模拟真实硬件。未执行到的定时行为、多任务抢占及异步 I/O 都不在模型内。

输入变量无初始值，每个扫描必须提供所有输入，不能把缺失当 FALSE。memory/output 要显式布尔 initial；初始值只用于模型开始，后续扫描继承状态，不代表断电保持配置。

默认 `write_policy: single_writer` 禁止同变量多个线圈。确实需要 S/R 多处写入时显式改为 `ordered_last_write`；同一扫描最后实际发生的写入决定最终值。不能只凭 S/R 字母声称固定置位优先或复位优先，梯级顺序必须核对。所有读值、写前/写后值和是否实际写入都保存在 trace.json。

## 输入与输出

```bash
python3 <skill-dir>/scripts/ladder.py <skill-dir>/assets/ladder-examples/start-hold.json --out <output-dir>
```

- 顶层：title、scope、data_status、semantics、write_policy、variables、rungs、scans。
- variables：id、label、role(input/memory/output)、source；memory/output 另需 initial。
- rungs：唯一 id、label、logic、coil；coil 有唯一 id、var、kind。
- logic 叶节点：id、kind=contact、var、sense=true/false（sense 为字符串）。组合节点：id、kind=series/parallel、children。
- scans：唯一 id、label、inputs；值必须是 JSON true/false，不接受数值、字符串自动转换。
- ID 为字母开头的 ASCII 字母/数字/下划线，最长24字符。变量可以被多个独立触点引用，图形元素 ID 不能重复。
- 上限：64变量、32梯级、120触点、8层嵌套、每个组合2..8子项、1000扫描。未知指令/字段明确拒绝，不能静默忽略定时器参数。

输出 SVG、逐对象可编辑 draw.io、源输入、scene.json、trace.json 和逐梯级 CSV。图上扫描摘要最多12次且明确标记；JSON/CSV保留全部。左右母线、触点竖线、取反斜线、线圈弧线和并联连接圆点有实际矢量几何。draw.io 是通用图形编辑源，编辑图形不自动回写 JSON 或执行逻辑。

## 三份示例与校验

1. start-hold：普通停止优先的启动保持；停止与启动同真、松开停止、运行允许丢失；后级指示读取同一扫描刚写入的记忆。
2. set-reset：先置位后复位，同真时复位胜出；调换梯级顺序结果相反；条件假保持不写。
3. nested-logic：自动/手动各自串联后并联，再串联就绪及取反报警；另一个取反线圈输出非运行状态。跨分支信号不能拼接成通路。

核验要同时看真值表、跨扫描状态、梯级读写记录和实际符号。已增补TON、CTU及上下沿检测的时间模式；其他计时/计数变体、任意功能块、目标厂商导入/编译、PLCopen XML、跳转、并行线圈、任务调度和掉电保持仍待补。继电器电路、电气联锁、急停与安全PLC仍是独立范围。

## 专用提示词

根据 {需求} 先列输入/记忆/输出及布尔含义，区分物理接线和逻辑取反。确认扫描模型和多写入策略，将逻辑建成有稳定 ID 的串并联树；列待机、启动、保持、停止、同真冲突等完整输入快照。生成梯形图与逐扫描结果，核对自保持、S/R顺序和下游同扫描读取，再实际打开 SVG 与可编辑源。用户未指定硬件时使用教学标注，不臆造厂商地址或安全控制结论。

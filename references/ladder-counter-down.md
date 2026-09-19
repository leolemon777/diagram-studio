# CTD 减计数：装载、边沿与零值保持

入口为 `scripts/ladder.py`，完整输入见 `assets/ladder-examples/down-counter.json`；沿用 [时间功能块](ladder-timed.md) 的扫描顺序和时间约定。

## 来源与明确边界

2026-09-17核对 [CODESYS CTD](https://content.helpme-codesys.com/en/libs/Standard/Current/Counter/CTD.html)：CD上升沿减一，LOAD装载PV，Q表示CV等于零，PV/CV为WORD。公开接口没有充分说明所有同时事件和初始化细节；以下装载优先、边沿记忆和零值饱和是本教学模拟器的显式合同，尚未与厂商运行时对照。

## 输入

```json
{"id":"C1","type":"CTD","pv":3,"load":"Load","initial_cv":0,"previous_input":false}
```

以上对象置于rung.block。梯级logic接CD，load绑定已声明的布尔变量，block.Q交给该梯级线圈。pv与initial_cv各为0..65535整数，初值允许大于PV；previous_input必须显式布尔值。未知字段和隐式类型转换拒绝。

## 更新顺序

1. 从当前变量状态读取LOAD；同扫描前级写入可见。
2. 根据先前CD与本次CD识别上升沿。
3. LOAD为真时CV=PV；否则上升沿令CV=max(0,CV-1)。
4. 每次调用都更新CD记忆，LOAD为真时也更新。因此LOAD释放而CD仍高不会再减一次。
5. Q=(CV==0)。初值为零时首扫Q已真，不表示现场作业已完成；PV为零的装载也令Q真。

每实例每扫描调用一次，输入低也调用。模型不补偿扫描间漏掉的窄脉冲，不模拟掉电保持或任务抢占。固定PV，不支持动态预置值。CTUD与厂商程序/PLCopen交换仍待实现。

## 输出与验证

15扫描示例覆盖装载3、三次上升沿归零、持续高不重复计数、零后不回绕、装载与边沿同真，以及装载释放仍高。完整trace保留before/after、load与rising；counter-controls.csv独立列出装载、边沿及CV变化，samples.csv与时序图显示每次扫描结果。时序CV轴容纳max(PV,initial_cv)，图中阶梯仅为采样保持显示。

梯形图摘要展示前12扫描，完整15扫描保留在JSON/CSV与时序图。draw.io是可编辑图形源，编辑图中文字不会自动修改逻辑输入或验算。

# 设施与工程平面模型

本批输入位于 `assets/facilities-engineering-models/`，统一由 `scripts/facilities_engineering.py` 校验和重绘。内容均为模拟数据；先替换尺寸、房间、设备、线路、流量和属地要求，再用于实际项目讨论。

## 入口与产物

```bash
python scripts/facilities_engineering.py assets/facilities-engineering-models/maintenance-office-layout.json --out output
```

每份输入生成 SVG、PNG、原输入 JSON、计算 JSON 和 QA JSON。`knowledge.py` 卡片的 `facilities_engineering_model_paths` 返回关联模型。当前模式：

- `facility-layout`：`office` 校验房间、设施、工位和带净宽证据的连续路线；`seating` 另校验座位编号、出口和无障碍席位。
- `electrical-telecom-plan`：设备、终端和线路必须属于同一电力或数据系统，端点位号唯一，线路保留回路/端口、线缆规格和证据。
- `security-access-plan`：授权区、门凭证规则和设备清册分开；摄像机扇区只允许声明为 `illustrative-only`。
- `evacuation-plan`：恰好一个当前位置、至少两个边界出口和至少两条路线；每段必须声明现场核对依据且未阻塞，所有出口从当前位置可达。
- `hvac-plan`：设备、送回排风终端、风管、流向和控制关系分开；按输入允许值检查 `送风 - 回风 - 排风`。
- `wiring-diagram`：设备端子、线号、导体规格和信号逐线对应；当前简单示例不允许一个端子被多条线复用。
- `single-line`：单电源径向图，校验可达、无环、多进线、节点额定值和只在变压器两侧改变电压。
- `plumbing-plan`：冷水、热水、排水分系统；每个器具至少有冷水和排水连接，排水管逐段保留正坡度。

`label_at` 只控制标注避让，不改变设备、节点或线路几何。编辑工程值时应重新运行分析与渲染，不能只改可见文字。

## 已验证示例

| 模型 | 核心检查 |
|---|---|
| maintenance-office-layout | 240 m²、8 工位、2 路线、最小声明净宽 1200 mm |
| maintenance-electrical-telecom-plan | 电力 3 路、数据 3 路、设备和终端位号唯一 |
| maintenance-training-seating | 84 席、2 无障碍席位、2 出口、2 走道 |
| maintenance-security-access-plan | 3 授权区、2 门、6 设备、覆盖仅为示意 |
| maintenance-evacuation-plan | 2 独立路线、2 可达边界出口、逐段核对证据 |
| maintenance-hvac-plan | 1600 L/s 送风、1300 L/s 回风、300 L/s 排风、平衡为 0 |
| maintenance-terminal-wiring | 4 设备、16 端子、8 条唯一线号 |
| maintenance-electrical-single-line | 8 节点、7 边、3 负荷、总负荷 335 kW |
| maintenance-plumbing-plan | 3 器具、10 管段、冷/热/排水 4/2/4 |

低压单线图做过 JSON 往返：将维修泵站从 180 kW 改为 210 kW 后重新计算为 365 kW，并重绘检查标签与汇总。

## 来源与边界

- 办公与座位路线参考 U.S. Access Board 的公开 ADA / accessible-route 指南语境。它不是其他地区项目的自动合规判定。
- 疏散图参考 OSHA 29 CFR 1910.36 和 Subpart E 的公开入口；出口数量、距离、耐火分隔、标志、集合点和演练仍须按属地要求核对。
- 暖通参考 ASHRAE 62.1/62.2 官方公开落地页的通风语境；当前模型未执行热负荷、静压、噪声、消防联动或完整规范计算。
- 电气类型保留 IEC 60617 官方公开产品页作为符号标准入口。未获取、复制或捆绑订阅制符号数据库；当前图形使用本 Skill 的中性矢量符号。
- 模型不是许可图、施工图、竣工图或盖章工程文件。实测底图、负荷计算、短路与保护整定、照度、热负荷、压力、防回流、消防、隐私和维护空间等结论均需合格专业人员确认。

## 提示词骨架

```text
为 {场所/系统} 创建 {办公室布局/座位/门禁/疏散/暖通/接线/单线/给排水} 图。
把真实尺寸、设备位号、端点、线路、管径/风量/负荷和来源写入 JSON；未知值标成模拟或待核对。
先运行语义校验，再渲染 SVG/PNG；检查连续路线、端点一致性、可达性、系统平衡和文字避让。
在图上保留用途和专业复核边界，不把示意模型表述成项目合规或施工结论。
```

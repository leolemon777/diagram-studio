# UML对象快照：输入与验证边界

当前object_snapshot.py校验输入，object_notation.py投影记法，object_render.py输出SVG/draw.io及输入、记法和QA。已关联ext-uml-object知识卡及object_example_paths，未加入v17发布包。

依据OMG UML 2.5.1第9.8节InstanceSpecifications：实例规格可以描述可能或实际存在的实例、部分或完整槽位；关联的实例表示链接。来源 https://www.omg.org/spec/UML/2.5.1/PDF ，本轮读取官方搜索提取的9.8.3段落，不声称已通读全文或核对完整图形记法。

输入：title、snapshot、非空assumptions、objects和links。
- 每对象：唯一id、name（可匿名）、classifiers列表、slots。无名且无类型的对象暂拒绝；这是当前输入限制，不宣称UML禁止。
- 每槽位：feature、values。值显式区分literal与reference。reference指向对象id；字面值允许JSON标量。空values、null、0、false各自保留，不能合并为“无值”。具体UML值规格映射尚待实现。
- 每链接：全局唯一id、association、两个ends，每端role与object。端点必须指向存在的实例。当前限二元链接，未覆盖n元关联。
- classifier名称目前只是引用标签，没有导入类模型，因此不检查属性归属、继承、类型和多重性；也不推断所有槽位已列出。链接与引用槽位分别保留，不自动认为它们重复。

教学输入assets/object-models/maintenance-snapshot.json含工单、维修员与匿名泵，展示普通值、对象引用、显式空列表、false、0和null的输入区别。三项测试覆盖标识和引用完整性、重复槽位及非有限数值拒绝。

后续必须补：实例标题下划线、槽位分区、链接/角色标签及布局；官方记法正文核对；SVG与原生编辑器实看；类模型约束、匿名/多分类器/多值槽位及n元链接变体。不要把此校验器称为完整UML验证器。

正文核对补充：已下载官方PDF并读取PDF第170页（印刷页128）第9.8.4节。实例标题为带下划线的“名称 : 类型”，多类型逗号分隔；链接连接实例，可标端名；槽位为特征名 = 值规格。文本对象引用使用实例名，不添加@。匿名引用暂用明确的本地身份注释[anonymous id=...]，这不是标准UML文本记法，成图阶段需采用图形引用或明确图例。object_notation.py保留此区别与空列表/null/0/false的区别，五项测试通过。PDF证据research/uml-2.5.1.pdf，提取段落research/uml-instance-notation.txt。

首张maintenance-snapshot样图已在浏览器实际查看，标题下划线、槽位分区、链接与端名位置清楚。六项模型/记法/导出测试通过，SVG下划线与draw.io字体位、链接端点绑定分别检查。已在draw.io以70%查看，status槽位编辑并撤销成功；保存往返与整体移动尚未验证。当前单行实例布局和下方独立链接通道只验证此样例；多链接共端、长端名、匿名引用与大型图仍需补，不能外推自动避障能力。

对象组合导出：draw.io标题、分隔线、槽位作为实例子单元，局部坐标保留；端名绑定所属实例，关联名作为边标签。实际以70%拖动工单实例向右上方，内部内容与端名跟随，链接保持连接，关联名随路径定位。固定路径点仍保留，不能声称任意拖动后自动避障。证据research/object-group-validation.json。SVG关联名仍采用静态布局，与draw.io沿边居中位置不同；语义一致但不宣称像素一致。

多链接补充：共同实例的链接端按连接数分配不同横向位置，实例宽度随端数扩展；自链接使用两个不同端点。三链接压力样例已实际查看，7项测试通过。线间交叉目前不带跳线/断口，不标连接点；大规模可读性、长角色名及多链接原生重开仍待核验。样例保留在工作区research/object-multilink.json，尚未计入发布输入。

长标签检查：端名与关联名按换行数计算高度并扩大通道间距，8项测试通过。实际查看压力SVG上中区域发现关联文字与其他竖向链接相交，因此本例视觉验收未通过。详见research/object-long-label-validation.json，仍需标签避线或明确遮罩方案。当前基础源已重绘，较早原生编辑证据只适用于各自记录的SHA，不能自动沿用于新源。

长标签复核：关联名改为选择其横向路径内最大的无竖线区；端名改为选择所属端点左右较大的无连接线半区，并按保守最窄宽度预留高度。独立测试把全部端名/关联名文字框与每一条竖向链接段做相交检查，未再发现穿字；浏览器实际查看压力SVG的上、下区域也通过。极长端名仍可能形成窄列并大量换行，多链接压力样例的原生编辑和更大规模自动布线仍未验证。

保存重开复核：从当前maintenance-snapshot.drawio在draw.io中把slot_job_0由status = "assigned"改为status = "roundtrip"并实际保存。结构比对确认26个单元ID、样式、父子关系、连线source/target绑定、顶点几何和路径点坐标均保持，唯一内容变化是该槽位文本；draw.io省略了分隔线几何中显式的零坐标，按数值等价处理。随后用实际保存文件重新导入draw.io并在70%查看，三项带下划线实例标题、槽位、端名和MaintenanceTarget链接均完整，修改后的状态可见。证据research/object-roundtrip-validation.json与research/object-snapshot-roundtrip.drawio。此证据只覆盖当前三实例单链接快照，不覆盖多链接压力源、类型/多重性或大规模自动布线。

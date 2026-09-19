# N-S结构化程序图输入模型

当前提供scripts/structured_program.py结构校验和scripts/structured_render.py成图。cn-1058知识卡已关联两套输入，structured_example_paths返回可移植路径。关联示例不代表全部验证完成。

输入为title、非空assumptions和有序body列表；所有节点id全局唯一。action含text；if含condition、then、else；while含condition和body；repeat含until和body；case含expression、branches（label/body）和default。空列表表示显式空操作序列。表达式和CASE标签目前仅为文本，不能声称已检查类型、常量范围重叠或可执行性。

最多500节点、12层嵌套、每CASE 1至8个显式分支。严格拒绝未知字段、重复ID、重复标签和任意goto结构。此范围是当前实现边界，不是N-S规范全部边界。尚未实现FOR、CALL、异常、并行和扩展跳出。

当前绘图规则：顺序块纵向排列；IF为分隔区域，CASE保持标签与分支绑定，默认分支在右；WHILE顶部判断、允许零次执行；REPEAT底部退出条件、至少执行一次且条件真时退出。不得将repeat-until误标为do-while。

来源：
- [Structorizer CASE文档](https://help.structorizer.fisch.lu/index.php?menu=52)：分支标签关联、默认分支、结构头与分支体。
- [Structorizer REPEAT文档](https://help.structorizer.fisch.lu/index.php?menu=55)：退出条件为真终止，循环体先执行。

校验器只检查嵌套结构并输出节点顺序和路径，不执行程序。

## 当前输出与核验

structured_render.py输出SVG、draw.io、input.json、structure.json与qa.json。
- assets/structured-models/batch-check.json：顺序、IF、WHILE与REPEAT嵌套。
- assets/structured-models/mode-selection.json：CASE、默认分支、显式空分支与不同长度的分支体。
- 条件和标签按换行数预留高度；CASE纵向分隔线从斜边交点延伸至分支底部。斜边内条件文字留在上部安全区域。
- 工作区六项结构与渲染测试通过，覆盖ID/跳转拒绝、嵌套路径、分支标签对应、默认分支顺序和多行文字高度。
- 两个示例及长条件压力样图已在浏览器实际查看；当前图中未见条件、标签与分支正文重叠。证据见工作区research/ns-layout-validation.json。

## 尚未完成

循环示例的原生编辑器打开、修改、保存重开；深嵌套和大规模组合的视觉压力验证；长条件图头的空间利用改进。当前宽度随分支数量扩展，不支持自动分页，不能声称适配任意画布。模型不执行条件，不校验CASE值域重叠。六项测试和三张样图不代表所有N-S变体已验证。

目录整合核验：两套输入的10个产物在独立临时目录、清除PYTHONPATH/PYTHONHOME后重绘，与交付文件逐字节一致；10个HTTP资源内容一致。知识页到示例目录的链接已通过实际浏览器查看。证据：工作区research/ns-integration-validation.json。尚未更新v16发布包。

CASE原生往返：mode-selection.drawio在draw.io以70%查看，修改默认分支文字并下载到research/ns-case-roundtrip.drawio，随后从实际下载文件重开并目视确认。35个单元、5条边的ID、样式、父级、几何、端点及路径点保持，仅_v20文字改变。XML几何子元素的序列化顺序不同，按as角色归一化；路径点数组顺序严格保留。证据research/ns-roundtrip-validation.json。此验证不等于可执行NSD格式，也未验证整体分支拖动或循环源。

## 嵌套与规模压力检查

工作区verify_ns_stress.py以30个固定随机种子组合顺序、IF、CASE、WHILE、REPEAT，另检查12层嵌套及500个顺序节点，共32例。独立于排版器的递归检查核对父子包含、顺序块邻接、分支横向次序、循环判断位置与文字高度，全部通过。最大画布宽8174、高35330（来自不同样例）。

18节点的混合嵌套样图已在浏览器查看上下区域：几何结构完整，但适配屏幕宽度后文字过小。因此layout_stress只记部分证据；不能把32例几何通过称为32例视觉验收。下一步应提供带结构定位的局部详图或分页，保留父级分支语义，不能简单截图切断循环体。证据research/ns-stress-validation.json。

## 大图屏幕阅读

scripts/structured_viewer.py INPUT --out DIR生成自包含离线HTML，保留完整SVG，提供整图总览、原尺寸滚动、节点定位和父级分支路径。节点选择不改变数据或裁断结构。18节点压力样图已实际操作深层n12定位与返回总览，文字可读、CASE/默认/真分支及循环上下文保留。两套目录示例均新增交互阅读链接。此功能改善屏幕阅读，不等于打印分页；手机、500节点导航和全部节点逐项操作仍未验。

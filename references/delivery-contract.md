# 公共交付协议

`scripts/delivery_contract.py` 为普通图、故事地图和后续专用后端提供共同的交付收口。它不替代各后端的语义校验和排版算法，只统一“输入冻结 → 内容保留检查 → 成品哈希 → 交付记录 → 可选版本快照”。

## 交付记录

`render.py` 每次成功生成都会写 `<brief>.delivery.json`，其中包含：

- `protocol_version`：当前为 `diagram-studio/delivery-1`；
- `version_id` 与 `input_sha256`：由冻结输入生成，可追踪同一输入版本；
- `files`：成品文件名与 SHA-256；
- `checks.geometry`、`checks.composition`、`checks.content_integrity`、`checks.browser_text_bounds`、`checks.manual_visual_review`、`checks.native_editor`：分别报告实际执行范围，不把未执行项写成通过；
- `delivery_scope`：说明生成和替换的边界。

`content_integrity` 会在输入提供稳定身份时检查源 ID、显式关系端点和显示文本是否仍在场景中。没有稳定 ID 的数据图记录 `not-applicable`，不伪造对象级编辑保证。序列消息的端点由时序后端的专用检查负责，公共协议只核对消息文字。

## 版本目录与失败保留

需要独立版本目录时：

```bash
python3 scripts/render.py assets/examples/02-workflow.json \
  --out output/workflow \
  --version-root output/workflow-versions
```

完成的交付会复制到 `output/workflow-versions/<version_id>/`，并附 `version.json`。不传 `--version-root` 时，输出目录本身仍按输入文件和交付记录管理版本；生成或内容检查失败会在替换前抛错，保留上一份成品。跨多个文件的替换不是操作系统级事务，发布前应保留上一输出目录。

验证已有交付：

```python
from scripts.delivery_contract import verify_receipt
verify_receipt("output/workflow/02-workflow.delivery.json")
```

哈希通过只说明文件未被改写；文字边界、人工视觉、原生编辑器与领域审核仍需分别完成并记录。

# Shared delivery contract

`scripts/delivery_contract.py` gives ordinary diagrams, story maps and future specialist backends one delivery closeout. It does not replace a backend's semantic or layout checks. It standardizes the handoff: freeze input → check preserved content → hash artifacts → write a receipt → optionally snapshot a version.

## Receipt

`render.py` writes `<brief>.delivery.json` after a successful run. It records:

- `protocol_version`, currently `diagram-studio/delivery-1`;
- `version_id` and `input_sha256`, derived from the frozen input;
- `files`, with SHA-256 for every delivered artifact;
- separate `geometry`, `composition`, `content_integrity`, browser text, manual review and native-editor statuses;
- `delivery_scope`, which states the replacement boundary.

When the input has stable identities, `content_integrity` checks source IDs, explicit relation endpoints and display text against the scene. Data charts without stable object IDs report `not-applicable`; they do not claim object-level editability. Sequence endpoints remain the sequence backend's responsibility while the shared check verifies message text.

## Version directories and failure preservation

Request an independent version snapshot with:

```bash
python3 scripts/render.py assets/examples/02-workflow.json \
  --out output/workflow \
  --version-root output/workflow-versions
```

The completed delivery is copied to `output/workflow-versions/<version_id>/` with `version.json`. Without `--version-root`, the output directory and receipt still identify the input version. Generation or content-check failure occurs before promotion and leaves the previous delivery in place. Promotion across multiple files is not an OS-level transaction, so keep the prior output directory before publishing.

Verify an existing receipt:

```python
from scripts.delivery_contract import verify_receipt
verify_receipt("output/workflow/02-workflow.delivery.json")
```

A passing hash only says the file was not changed after delivery. Text bounds, human visual review, native editing and domain review remain separate checks.

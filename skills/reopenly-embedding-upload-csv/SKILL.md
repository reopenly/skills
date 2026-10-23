---
name: reopenly-embedding-upload-csv
description: Import a CSV of anchor, positive, and negative training pairs into an embedding dataset in a ReOpenly embedding project.
compatibility: Requires Python 3.9+ and REOPENLY_API_KEY. Uses the ReOpenly customer API.
---

# Upload embedding training pairs from CSV

1. Confirm the local CSV path, ReOpenly owner/project slugs, and dataset ID. Verify the target project is an embedding project; this skill refuses text projects. The dataset ID can be found with `GET /api/v1/projects/{owner_slug}/{project_slug}/datasets`.
2. Inspect the CSV header and a few rows. The CSV must include `anchor`, `positive`, and `negative` columns. Explain that the ReOpenly import runs asynchronously and the helper waits for its terminal status. Never print or expose `REOPENLY_API_KEY`.
3. Run the helper bundled inside this skill (substitute its installed path):

```sh
python3 /path/to/reopenly-embedding-upload-csv/scripts/reopenly.py csv \
  --owner OWNER --project PROJECT --dataset-id DATASET_ID --file /path/to/pairs.csv
```

4. The helper uploads the CSV using the documented dataset-import workflow: create import, upload bytes, profile, preview with a `fail` invalid-row policy, confirm with the profiled SHA-256 and an idempotency key, then poll until completion. Report the final import status and counts. If a request fails ambiguously or the import is still running, inspect its status before starting another import; do not blindly rerun because duplicate pairs may result.

The API key must already be set in the environment as `REOPENLY_API_KEY`. Do not place it in command arguments, skill files, or logs.

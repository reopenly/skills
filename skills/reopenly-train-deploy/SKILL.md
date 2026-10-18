---
name: reopenly-train-deploy
description: Start a ReOpenly fine-tuning job, monitor it, and optionally publish its result as a hosted model alias. Use when asked to train or deploy a model in a ReOpenly project.
compatibility: Requires Python 3.9+ and REOPENLY_API_KEY. Training and inference can incur charges.
---

# Train and deploy

1. Confirm owner/project, base catalog model ID, selected dataset tags (no tags means all project chats), epoch count, sequence length, display name and kebab-case alias slug. Never invent a base model ID: ask the user or have them consult `GET /api/v1/base-models`.
2. Explain training is asynchronous and measured training time is billable. The helper asks for confirmation before creating a job unless `--yes` is supplied. Do not use `--yes` unless the user explicitly requested execution without another confirmation.
3. Run from repository root:

```sh
python3 skills/_shared/reopenly.py train \
  --owner OWNER --project PROJECT --base-model CATALOG_MODEL_ID \
  --tag support --epochs 3 --max-seq-length 2048 \
  --model-name 'Support assistant' --model-slug support-assistant --deploy
```

Repeat `--tag` for additional tags. With no `--tag`, all project chats are selected. `--deploy` creates a hosted alias after `model_available` becomes true; without it, the script only trains and reports the job ID. The script polls until a terminal failure or a model becomes available. Do not submit a second job just because polling is slow.

4. Report job ID and final status, and alias details if deployed. If deployment confirmation is declined, preserve the job ID so the alias can be created later. Do not retry a failed create blindly; check the project's job list first because job creation has no idempotency guarantee.

`REOPENLY_API_KEY` must be present in the environment. Do not reveal or store the key. Review the current API catalog/profile for supported model IDs and bounds; server defaults and limits can change.

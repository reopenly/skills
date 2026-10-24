---
name: reopenly-embedding-train-deploy
description: Train and optionally deploy an embedding model in a ReOpenly embedding project. Use when asked to fine-tune or publish an embedding model.
compatibility: Requires Python 3.9+ and REOPENLY_API_KEY. Training can incur charges.
---

# Train and deploy an embedding model

1. Confirm the owner/project slugs, embedding dataset ID, base artifact ID from the project's `GET /training-jobs/profiles` response, and number of full epochs. If deploying, confirm the hosted model display name and kebab-case alias slug. Never guess an artifact ID or model alias slug.
2. Explain that preview and estimate are advisory, the job runs asynchronously, and only measured training time is billed. The estimate's `admission_ceiling_credits` is a balance requirement, not the predicted charge. The helper verifies the project type, shows available base profiles, previews the selected dataset and steps, estimates admission credits, and asks for confirmation before creating a job. Do not use `--yes` unless the user explicitly requested execution without another confirmation.
3. Run the helper bundled inside this skill (substitute its installed path):

```sh
python3 /path/to/reopenly-embedding-train-deploy/scripts/reopenly.py embedding-train \
  --owner OWNER --project PROJECT --dataset-id DATASET_ID \
  --base-artifact-id BASE_ARTIFACT_ID --epochs 3 \
  --deploy --model-name 'Search encoder' --model-slug search-encoder
```

   The helper first discovers `planned_steps_per_epoch` with a large preview horizon, then previews, estimates and starts the requested whole number of epochs using `max_steps = planned_steps_per_epoch × epochs`. Optional embedding settings can be supplied in a JSON file with `--settings`; optional `--execution-limit-seconds` is applied consistently to preview, estimate and create.

4. The helper polls the job and deploys the alias only after `model_available` becomes true. Embedding aliases are created with `task: "embedding"` and a training-job source. Report the job ID, final status, actual cost when available, and hosted alias details. Do not submit a second create just because a request timed out; check the project job list first, as create has no idempotency key.

`REOPENLY_API_KEY` must be present in the environment. Do not reveal or store the key. Review the live profiles for supported base artifact IDs and setting bounds; these can change.

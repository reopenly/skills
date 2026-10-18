---
name: reopenly-import-huggingface
description: Fetch a question-and-answer dataset from Hugging Face and add its examples to a ReOpenly project. Use when asked to import Hugging Face datasets for fine-tuning.
compatibility: Requires Python 3.9+, the `datasets` Python package, and REOPENLY_API_KEY.
---

# Import a Hugging Face Q&A dataset

1. Confirm the Hugging Face dataset ID, optional configuration, split, owner/project slugs, question and answer column names, and any desired tags. Do not guess dataset fields or split.
2. Explain that the script downloads/streams dataset data and creates ReOpenly chat examples individually, using a thread pool of exactly five parallel upload requests. Confirm the size or use a limit for a trial import. For gated datasets, the user must configure Hugging Face authentication separately.
3. Run the helper bundled inside this skill (substitute its installed path):

```sh
python3 -m pip install datasets
python3 /path/to/reopenly-import-huggingface/scripts/reopenly.py huggingface \
  --owner OWNER --project PROJECT --dataset DATASET_ID --split train \
  --question-column question --answer-column answer --tag support --limit 100
```

Omit `--limit` (or set it to `0`) for the complete split. Add `--config CONFIG` if applicable, `--streaming` for streaming datasets, and repeated `--tag` flags as needed. Invalid rows fail by default; use `--invalid skip` only with user approval.

4. Summarize how many examples were uploaded. If an upload fails midway, do not rerun without checking the project first: duplicate examples may result.

The `REOPENLY_API_KEY` environment variable is required. Keep it secret and never echo it. The Hugging Face `datasets` package is an optional dependency used only for this skill.

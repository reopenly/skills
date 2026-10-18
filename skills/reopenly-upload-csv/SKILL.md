---
name: reopenly-upload-csv
description: Upload a local CSV containing question-and-answer examples into a ReOpenly project. Use when asked to import, upload, or add Q&A training data from a CSV.
compatibility: Requires Python 3.9+ and REOPENLY_API_KEY. Uses the ReOpenly customer API.
---

# Upload Q&A from CSV

1. Confirm the local CSV path, ReOpenly owner slug and project slug. Ask which columns contain questions and answers if they are not clearly named `question` and `answer`.
2. Ask which tag(s) to apply. Tags are useful for selecting training data later. Tell the user that each row becomes a chat with a user message and assistant message.
3. Inspect the CSV header and a few rows if available. Never print or expose `REOPENLY_API_KEY`.
4. Confirm malformed-row policy (`fail` by default; `skip` only if the user chooses it). The script uploads rows individually; if a request fails partway through, report how far it got and do not blindly rerun, because that may create duplicates.
5. Run the helper bundled inside this skill (substitute its installed path):

```sh
python3 /path/to/reopenly-upload-csv/scripts/reopenly.py csv \
  --owner OWNER --project PROJECT --file /path/to/data.csv \
  --question-column question --answer-column answer --tag support
```

Use repeated `--tag` flags for multiple tags. Use `--invalid skip` only when approved. Report the uploaded count and the target project.

The API key must already be set in the environment as `REOPENLY_API_KEY`. Do not place it in command arguments, skill files, or logs.

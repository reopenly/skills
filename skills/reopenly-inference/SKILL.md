---
name: reopenly-inference
description: Send a prompt to a ReOpenly project model and return its response. Use when asked to test, query, or run inference with a hosted ReOpenly model.
compatibility: Requires Python 3.9+ and REOPENLY_API_KEY. Calls may incur inference charges.
---

# Run inference

1. Confirm the owner/project, model alias (or permitted catalog model), and user prompt. Note that a successful inference may incur a charge.
2. Run the helper bundled inside this skill (substitute its installed path):

```sh
python3 /path/to/reopenly-inference/scripts/reopenly.py infer \
  --owner OWNER --project PROJECT --model MODEL_SLUG \
  --prompt 'Your question here' --max-tokens 256 --temperature 0.2
```

3. Present the assistant response and, when useful, token usage and finish reason from the JSON response. Never retry an ambiguous transport failure automatically; check whether the request may have completed to avoid duplicate work/charges.

The helper uses ReOpenly's project-scoped OpenAI-compatible chat completions API. Set `REOPENLY_API_KEY` in the environment and never include it in a prompt or command argument.

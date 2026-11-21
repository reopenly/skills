---
name: reopenly-inference
description: Run chat completions, legacy text completions, or embeddings with a ReOpenly project model. Use when asked to query a model or embed text.
compatibility: Requires Python 3.9+ and REOPENLY_API_KEY. Calls may incur inference charges.
---

# Run project inference

1. Confirm the owner/project, model reference, and operation. For generation, confirm the prompt and whether to use chat messages (`infer`) or a legacy text completion (`completion`). For embeddings, confirm all input strings and whether each is a `query` or `document`. Explain that calls can incur charges. Project embeddings are never saved to a dataset.
2. Run the helper bundled inside this skill (substitute its installed path). Chat completion:

```sh
python3 /path/to/reopenly-inference/scripts/reopenly.py infer \
  --owner OWNER --project PROJECT --model MODEL_SLUG \
  --prompt 'Your question here' --max-tokens 256 --temperature 0.2
```

For the legacy text-completion endpoint, use `completion` with the same arguments:

```sh
python3 /path/to/reopenly-inference/scripts/reopenly.py completion \
  --owner OWNER --project PROJECT --model MODEL_SLUG \
  --prompt 'Continue this text:' --max-tokens 128
```

For embeddings, repeat `--input` for each text (up to 64 inputs per request):

```sh
python3 /path/to/reopenly-inference/scripts/reopenly.py embedding \
  --owner OWNER --project PROJECT --model EMBEDDING_MODEL_SLUG \
  --input 'A search query' --input-type query --encoding-format float
```

3. For embeddings, use `--input-type query` for queries or `document` for passages when appropriate. The API accepts `float` or `base64` output, optional `--dimensions`, and optional `--truncate`. Inputs are limited to 512 tokens unless the hosted model was trained with a longer sequence length. A request is limited to 64 inputs and 32,768 total tokens; split or shorten oversized batches. If using `--truncate`, send only one input because a truncated input fills its entire input budget.

4. Present the response: the assistant text, usage and finish reason for generation; or vectors in input order and usage for embeddings. Do not treat absent/zero token counts as estimates. Set `REOPENLY_API_KEY` in the environment and never include it in a prompt or command argument.

The helper uses ReOpenly's project-scoped OpenAI-compatible endpoints. It uses a 360-second request timeout and retries only HTTP 503 responses that include `Retry-After`, waiting the requested delay. It does not retry HTTP 502, 504, or network errors; never retry an ambiguous transport failure automatically because the request may have completed and incurred a charge.

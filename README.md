# ReOpenly skills

Reusable skills for loading Q&A data into [ReOpenly](https://reopenly.com/), fine-tuning and deploying a model, and running inference. The skills use the ReOpenly customer API and read credentials from `REOPENLY_API_KEY`.

## Skills

| Skill | Purpose |
| --- | --- |
| `reopenly-qna-upload-csv` | Map a local CSV's question/answer columns into project chats. |
| `reopenly-qna-import-huggingface` | Export a Hugging Face dataset split to CSV and upload its Q&A rows. |
| `reopenly-embedding-upload-csv` | Import anchor/positive/negative pairs from CSV into an embedding dataset. |
| `reopenly-embedding-generate-dataset` | Use the current LLM to generate embedding pairs from CSV document chunks. |
| `reopenly-train-deploy` | Start and monitor fine-tuning; optionally create a hosted model alias. |
| `reopenly-inference` | Call a project model using chat completions. |

## Repository layout

```text
skills/
├── reopenly-qna-upload-csv/
│   ├── SKILL.md
│   └── scripts/reopenly.py
├── reopenly-qna-import-huggingface/
│   ├── SKILL.md
│   └── scripts/reopenly.py
├── reopenly-embedding-upload-csv/
│   ├── SKILL.md
│   └── scripts/reopenly.py
├── reopenly-embedding-generate-dataset/
│   ├── SKILL.md
│   └── scripts/csv_tools.py
├── reopenly-train-deploy/
│   ├── SKILL.md
│   └── scripts/reopenly.py
└── reopenly-inference/
    ├── SKILL.md
    └── scripts/reopenly.py
```

Each skill includes its own helper script so it remains self-contained when installed. The repository uses a visible, tool-neutral `skills/` directory and does not add agent-specific hidden folders.

## Prerequisites and credentials

- Python 3.9 or later.
- A ReOpenly account, an API key, and access to the target project. Create an account API key from ReOpenly's dashboard and set it in your shell:

  ```sh
  export REOPENLY_API_KEY='fnf_your_key'
  ```

  Do not commit the key, place it in scripts, pass it as a command-line argument, or print it. Prefer a secret manager or your shell's secure environment configuration.
- For Hugging Face import only: install the optional loader package with `python3 -m pip install datasets`. Gated/private datasets may also require Hugging Face authentication configured through the Hugging Face tooling.

The API helpers use only Python's standard library. The Hugging Face skill additionally requires the optional `datasets` package. After installing a skill, invoke its helper with Python from that skill's installed directory; for example:

```sh
python3 /path/to/reopenly-qna-upload-csv/scripts/reopenly.py --help
```

## Install

Install all six skills for the current project with the [`skills` CLI](https://github.com/vercel-labs/skills):

```sh
npx skills add reopenly/skills --skill '*' -a claude-code -a opencode
```

The CLI prompts for confirmation and installs the skills for Claude Code and OpenCode in the current project. To install globally for your user, add `-g`:

```sh
npx skills add reopenly/skills --skill '*' -a claude-code -a opencode -g
```

You can install one skill at a time by replacing `'*'` with a skill ID, for example `--skill reopenly-qna-upload-csv`. List available skills before installing with:

```sh
npx skills add reopenly/skills --list
```

The CLI supports many coding agents. Use `npx skills add --help` for the supported agent IDs and options. Once installed, ask your agent naturally to perform a task, or invoke the corresponding skill directly (for example, `/reopenly-train-deploy` in Claude Code).

## Usage examples

You can ask the agent naturally, for example:

- “Upload `./support.csv` to project `acme/helpdesk`; the columns are `query` and `response`, and tag them `support-v1`.”
- “Import `org/dataset` from Hugging Face, configuration `default`, split `train`, using columns `question` and `answer`. First limit it to 50 rows.”
- “Generate embedding pairs from the `chunk` column of `./documents.csv`, confirm the row count and token cost with me before using the current LLM, then save `./pairs.csv`.”
- “Train on tag `support-v1` with base model `<catalog-model-id>`, then deploy as `support-assistant`.”
- “Ask model `support-assistant` in project `acme/helpdesk`: How do I return an order?”

Or run the helper directly:

```sh
# CSV upload
python3 skills/reopenly-qna-upload-csv/scripts/reopenly.py csv \
  --owner acme --project helpdesk --file ./support.csv \
  --question-column query --answer-column response --tag support-v1

# Hugging Face dataset upload
python3 skills/reopenly-qna-import-huggingface/scripts/reopenly.py huggingface \
  --owner acme --project helpdesk --dataset org/dataset --split train \
  --question-column question --answer-column answer --tag support-v1 --limit 50

# Embedding pairs CSV upload (requires an embedding project and dataset ID)
python3 skills/reopenly-embedding-upload-csv/scripts/reopenly.py csv \
  --owner acme --project product-search --dataset-id DATASET_ID --file ./pairs.csv

# Inspect document chunks before LLM-assisted dataset generation
python3 skills/reopenly-embedding-generate-dataset/scripts/csv_tools.py inspect \
  --file ./documents.csv --column chunk

# Fine-tune and deploy (interactive confirmation is enabled by default)
python3 skills/reopenly-train-deploy/scripts/reopenly.py train \
  --owner acme --project helpdesk --base-model CATALOG_MODEL_ID \
  --tag support-v1 --epochs 3 --max-seq-length 2048 \
  --model-name 'Support assistant' --model-slug support-assistant --deploy

# Inference
python3 skills/reopenly-inference/scripts/reopenly.py infer \
  --owner acme --project helpdesk --model support-assistant \
  --prompt 'How do I return an order?'
```

See each skill's `SKILL.md` for its workflow and safety guidance. Q&A CSV and Hugging Face uploads create one chat per valid row. Embedding CSV imports use ReOpenly's asynchronous dataset-import workflow and require an embedding project plus a dataset ID. Embedding dataset generation uses the current LLM and requires explicit user confirmation after showing input size and generation count.

## API behavior and safety notes

- All project REST writes use `https://reopenly.com/api/v1/projects/{owner}/{project}/...` with a bearer token. Inference uses `https://reopenly.com/api/projects/{owner}/{project}/openai/v1/chat/completions`.
- Q&A upload creates a chat containing one `user` and one `assistant` message. Hugging Face uploads use a thread pool of five parallel API requests; CSV uploads are sequential. Embedding-pair uploads use asynchronous dataset imports and verify the target project type before creating an import.
- A training job is asynchronous. The script polls until a model is available or the job fails. Training charges are based on measured training time. The helper asks for confirmation before creating the job, and before deploying an alias. `--yes` bypasses those prompts; only use it when intended.
- ReOpenly's model catalog and training limits can change. Check `GET /api/v1/base-models` and the training documentation for currently supported model IDs and settings. The helper does not guess a catalog model ID.
- Inference may incur charges. Do not automatically retry an ambiguous network failure, which could duplicate a completed request.
- API keys are never written to disk by these scripts. Avoid shell tracing (`set -x`) while credentials are in the environment.

## Documentation

- [Authentication](https://reopenly.com/docs/getting-started/authentication/)
- [Quickstart](https://reopenly.com/docs/quickstart/)
- [Dataset chats](https://reopenly.com/docs/datasets/chats/)
- [Asynchronous dataset imports](https://reopenly.com/docs/datasets/imports/)
- [Embedding datasets](https://reopenly.com/docs/datasets/embedding-datasets/)
- [Training jobs](https://reopenly.com/docs/training/jobs/)
- [Hosted models](https://reopenly.com/docs/models/hosted-models/)
- [OpenAI-compatible inference](https://reopenly.com/docs/api/openai-compatible/)
- [OpenCode skills](https://opencode.ai/v2/docs/skills/)
- [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills)
- [`npx skills` CLI](https://github.com/vercel-labs/skills)

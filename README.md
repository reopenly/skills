# ReOpenly skills

Reusable skills for loading Q&A data into [ReOpenly](https://reopenly.com/), fine-tuning and deploying a model, and running inference. The skills use the ReOpenly customer API and read credentials from `REOPENLY_API_KEY`.

## Skills

| Skill | Purpose |
| --- | --- |
| `reopenly-upload-csv` | Map a local CSV's question/answer columns into project chats. |
| `reopenly-import-huggingface` | Load a Hugging Face dataset split and upload its Q&A rows. |
| `reopenly-train-deploy` | Start and monitor fine-tuning; optionally create a hosted model alias. |
| `reopenly-inference` | Call a project model using chat completions. |

## Repository layout

```text
skills/
├── _shared/reopenly.py       # dependency-free API helper (HF needs `datasets`)
├── reopenly-upload-csv/SKILL.md
├── reopenly-import-huggingface/SKILL.md
├── reopenly-train-deploy/SKILL.md
└── reopenly-inference/SKILL.md
```

The repository uses a visible, tool-neutral `skills/` directory. It does not add OpenCode- or Claude-specific hidden folders. Both tools support the `SKILL.md` format; installation copies or links the skill directories into the tool's normal skills location.

## Prerequisites and credentials

- Python 3.9 or later.
- A ReOpenly account, an API key, and access to the target project. Create an account API key from ReOpenly's dashboard and set it in your shell:

  ```sh
  export REOPENLY_API_KEY='fnf_your_key'
  ```

  Do not commit the key, place it in scripts, pass it as a command-line argument, or print it. Prefer a secret manager or your shell's secure environment configuration.
- For Hugging Face import only: install the optional loader package with `python3 -m pip install datasets`. Gated/private datasets may also require Hugging Face authentication configured through the Hugging Face tooling.

The shared helper uses only Python's standard library for ReOpenly API calls. To see available command options:

```sh
python3 skills/_shared/reopenly.py --help
```

## Install for OpenCode

OpenCode's global skills directory is `~/.config/opencode/skills/`. Clone this repository, then symlink the skill directories and shared helper into that location:

```sh
git clone https://github.com/reopenly/skills.git
mkdir -p ~/.config/opencode/skills
REOPENLY_SKILLS="$(cd reopenly-skills && pwd)/skills"
ln -s "$REOPENLY_SKILLS/_shared" ~/.config/opencode/skills/_shared
for skill in "$REOPENLY_SKILLS"/reopenly-*; do
  ln -s "$skill" ~/.config/opencode/skills/"$(basename "$skill")"
done
```

The links point into the clone, so keep it in place and pull updates there as needed. OpenCode discovers each linked folder's `SKILL.md` and can load the skills by their IDs, e.g. `@reopenly-upload-csv`. The helper path in the skill instructions is relative to the repository root; run it from that root.

## Install for Claude Code

Claude Code's personal skills directory is `~/.claude/skills/`. Symlink the skill folders and shared helper there:

```sh
git clone https://github.com/reopenly/skills.git
mkdir -p ~/.claude/skills
REOPENLY_SKILLS="$(cd reopenly-skills && pwd)/skills"
ln -s "$REOPENLY_SKILLS/_shared" ~/.claude/skills/_shared
for skill in "$REOPENLY_SKILLS"/reopenly-*; do
  ln -s "$skill" ~/.claude/skills/"$(basename "$skill")"
done
```

The links point into the clone, so keep it in place and pull updates there as needed. Claude Code makes skills available as slash commands, such as `/reopenly-train-deploy`, and may also invoke them automatically based on the request. Execute the helper from the cloned repository root.

To install for just one project instead of globally, use the equivalent project skills directory documented by your agent: `.opencode/skills/` for OpenCode or `.claude/skills/` for Claude Code. This repository itself intentionally does not contain those tool-specific paths.

## Usage examples

You can ask the agent naturally, for example:

- “Upload `./support.csv` to project `acme/helpdesk`; the columns are `query` and `response`, and tag them `support-v1`.”
- “Import `org/dataset` from Hugging Face, configuration `default`, split `train`, using columns `question` and `answer`. First limit it to 50 rows.”
- “Train on tag `support-v1` with base model `<catalog-model-id>`, then deploy as `support-assistant`.”
- “Ask model `support-assistant` in project `acme/helpdesk`: How do I return an order?”

Or run the helper directly:

```sh
# CSV upload
python3 skills/_shared/reopenly.py csv \
  --owner acme --project helpdesk --file ./support.csv \
  --question-column query --answer-column response --tag support-v1

# Hugging Face dataset upload
python3 skills/_shared/reopenly.py huggingface \
  --owner acme --project helpdesk --dataset org/dataset --split train \
  --question-column question --answer-column answer --tag support-v1 --limit 50

# Fine-tune and deploy (interactive confirmation is enabled by default)
python3 skills/_shared/reopenly.py train \
  --owner acme --project helpdesk --base-model CATALOG_MODEL_ID \
  --tag support-v1 --epochs 3 --max-seq-length 2048 \
  --model-name 'Support assistant' --model-slug support-assistant --deploy

# Inference
python3 skills/_shared/reopenly.py infer \
  --owner acme --project helpdesk --model support-assistant \
  --prompt 'How do I return an order?'
```

See each skill's `SKILL.md` for its workflow and safety guidance. CSV and Hugging Face uploads create one chat per valid row. The default behavior fails on invalid rows; `--invalid skip` skips them. Uploads proceed row by row, so a failure can leave partial results; check the project before retrying to avoid duplicates.

## API behavior and safety notes

- All project REST writes use `https://reopenly.com/api/v1/projects/{owner}/{project}/...` with a bearer token. Inference uses `https://reopenly.com/api/projects/{owner}/{project}/openai/v1/chat/completions`.
- Q&A upload creates a chat containing one `user` and one `assistant` message. Supply deliberate tags because training jobs select data by tags; when no tag is supplied, the helper omits tags.
- A training job is asynchronous. The script polls until a model is available or the job fails. Training charges are based on measured training time. The helper asks for confirmation before creating the job, and before deploying an alias. `--yes` bypasses those prompts; only use it when intended.
- ReOpenly's model catalog and training limits can change. Check `GET /api/v1/base-models` and the training documentation for currently supported model IDs and settings. The helper does not guess a catalog model ID.
- Inference may incur charges. Do not automatically retry an ambiguous network failure, which could duplicate a completed request.
- API keys are never written to disk by these scripts. Avoid shell tracing (`set -x`) while credentials are in the environment.

## Documentation

- [Authentication](https://reopenly.com/docs/getting-started/authentication/)
- [Quickstart](https://reopenly.com/docs/quickstart/)
- [Dataset chats](https://reopenly.com/docs/datasets/chats/)
- [Asynchronous dataset imports](https://reopenly.com/docs/datasets/imports/)
- [Training jobs](https://reopenly.com/docs/training/jobs/)
- [Hosted models](https://reopenly.com/docs/models/hosted-models/)
- [OpenAI-compatible inference](https://reopenly.com/docs/api/openai-compatible/)
- [OpenCode skills](https://opencode.ai/v2/docs/skills/)
- [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills)

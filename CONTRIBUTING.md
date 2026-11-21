# Contributing

Thanks for contributing ReOpenly skills. The repository is structured so each skill and its helper script can be installed together by the `npx skills` CLI.

## Local development with symlinks

To test changes in this repository with OpenCode or Claude Code, clone it and symlink the skill directories into the agent's project skill directory. The symlinks let edits in the clone appear immediately in the local agent installation.

### OpenCode

From the project where you want to test the skills:

```sh
git clone https://github.com/reopenly/skills.git reopenly-skills
mkdir -p ~/.opencode/skills
REOPENLY_SKILLS="$(cd reopenly-skills/skills && pwd)"
for skill in "$REOPENLY_SKILLS"/reopenly-*; do
  ln -s "$skill" ~/.opencode/skills/"$(basename "$skill")"
done
```

If the repository clone is not at `./skills`, set `REOPENLY_SKILLS` to the clone's `skills/` directory.

### Claude Code

From the project where you want to test the skills:

```sh
git clone https://github.com/reopenly/skills.git reopenly-skills
mkdir -p .claude/skills
REOPENLY_SKILLS="$(cd reopenly-skills/skills && pwd)"
for skill in "$REOPENLY_SKILLS"/reopenly-*; do
  ln -s "$skill" .claude/skills/"$(basename "$skill")"
done
```

The symlink destinations must not already exist. Remove only the specific test links when you are done; keep the repository clone itself if you want to continue contributing.

## Making changes

- Keep each `SKILL.md` focused on when to use the skill, required user inputs, safe execution, and how to report outcomes.
- The corresponding `scripts/reopenly.py` helper is bundled with that skill by the installer. If you change common API behavior, apply the change to each bundled helper so installed copies stay consistent.
- Keep credentials in `REOPENLY_API_KEY`; never commit credentials or print them.
- Run the Python syntax check on every helper you edit:

  ```sh
  find skills -path '*/scripts/reopenly.py' -print0 | xargs -0 -n1 python3 -m py_compile
  ```

- Update `README.md` when installation or user-facing behavior changes.

# Gemini CLI BOOTSTRAP.md

This file is read by Gemini CLI. The user has pointed you at this repo and asked you to set up the elephant/goldfish workflow in their target repo. Follow these steps.

## How to fetch the rest of this repo's content

There is no local working copy on the target machine; you got here by streaming this file's text through `gh api`. Fetch the remaining files the same way, into a fresh temporary directory:

```sh
EG_TMP=$(mktemp -d)
mkdir -p "$EG_TMP/gemini/commands" "$EG_TMP/shared"
for f in shared/eg-config.template.md gemini/gemini-md-snippet.md gemini/commands/eg-brainstorm.md gemini/commands/eg-prd.md gemini/commands/eg-fix-bug.md gemini/commands/eg-new-feature.md gemini/commands/eg-precommit-review.md; do
  gh api "repos/Raj9914/elephant-goldfish/contents/${f}" -H 'Accept: application/vnd.github.raw' > "$EG_TMP/${f}"
done
echo "$EG_TMP"
```

Every path below like `gemini/commands/<name>.md` means `$EG_TMP/<same path>`.

**How this install works:** the skills are copied into the target unchanged. Everything project-specific (commands, review hunt list, design rubric, commit policy) goes into one file, `.eg/config.md`, which the skills read at runtime. The same file is used by the Claude Code and Codex versions of this workflow. Updating the skills later is a plain re-copy; the config is never overwritten.

## Step 0: Confirm the target

The user invoked you from a working directory that is the target repo. Print its absolute path and ask the user to confirm before writing anything. If the target already has `.gemini/skills/eg-*` or `.eg/config.md`, say so: skills will be replaced with the new versions; an existing `.eg/config.md` is kept and only gaps are filled.

## Step 1: Inspect the stack

Read these files in the target if they exist (parallel reads):

- `GEMINI.md` (top of repo) — existing conventions, commit policy, PR workflow, tooling notes
- `package.json` → `scripts`, `dependencies`, `devDependencies` (Node / web stacks)
- `Gemfile` → linter, test framework, security scanner (Rails / Ruby)
- `pubspec.yaml` → Flutter / Dart
- `pyproject.toml` / `requirements.txt` / `setup.py` / `Pipfile` (Python)
- `go.mod` (Go), `Cargo.toml` (Rust), `composer.json` (PHP), `mix.exs` (Elixir)
- `tsconfig.json`, `playwright.config.ts`, `vitest.config.ts`, `jest.config.js`, etc.
- `Rakefile`, `Makefile`, `justfile`, `mise.toml`, `.tool-versions`, `.nvmrc`, `.ruby-version`
- `docker-compose.yml`, `Dockerfile` (for dev-server entrypoints)
- `.github/workflows/*.yml` (the CI commands tell you what the project considers "passing")

Also `git log --oneline -10` to learn the commit-message convention.

Also check `command -v codex` (it decides whether `second_opinion: codex` is possible).

## Step 2: Write `.eg/config.md`

Fill in `shared/eg-config.template.md` from what you found. Rules:
- Only write commands you verified exist (a package script, a CI step, a Makefile target). If unsure, leave the value empty and list it in the final report.
- **Review hunt list** and **Design rubric**: concrete, stack-specific items (e.g. N+1 queries and multi-tenant scoping for Rails; disposal and `setState` after dispose for Flutter; effect cleanup and hydration for React), not generic advice.
- **Goldfish → model** is not used by Gemini CLI; leave the default.

Print the filled config and ask the user to confirm or correct it before writing. Misreads here affect every later skill. Then write `.eg/config.md` and add `.eg/log.jsonl` to `.gitignore`. If `.eg/config.md` already existed, keep the user's values and only fill gaps.

## Step 3: Write and Install the Skills

For each of the five workflows (eg-brainstorm, eg-prd, eg-fix-bug, eg-new-feature, eg-precommit-review):

1. Create the skill directory: `mkdir -p .gemini/skills/<skill-name>`
2. Copy `gemini/commands/<skill-name>.md` unchanged to `.gemini/skills/<skill-name>/SKILL.md`
3. Automatically install the skill in the workspace using the `run_shell_command` tool:
   ```sh
   gemini skills install .gemini/skills/<skill-name> --scope workspace
   ```

## Step 4: Update GEMINI.md

Read the snippet from `$EG_TMP/gemini/gemini-md-snippet.md`. Tailor the placeholders in it to match the target's setup and inject it into the target's `GEMINI.md`.

- If the target already has a `GEMINI.md`, inject the snippet near the top.
- If no `GEMINI.md` exists, propose creating one and ask the user before writing.

## Step 5: Sanity-check the output

- Each `.gemini/skills/<name>/SKILL.md` is byte-identical to the fetched file (`cmp`).
- Every command written in `.eg/config.md` exists in the target.

## Step 6: Final report

Print to the user:
- `.eg/config.md` written, with anything left empty listed as "needs your input"
- Skill packages created and installed locally
- GEMINI.md change
- Anything you couldn't infer
- **IMPORTANT:** Instruct the user that they must run `/skills reload` in their interactive Gemini CLI session to activate the newly installed skills.

**Stop short of committing.** The user authorizes the commit when ready, following the target's commit convention.

## Updating

To update to newer skills, run this procedure again: the skills are re-copied unchanged and reinstalled, and `.eg/config.md` is kept. If the user hand-edited a `SKILL.md`, show the diff and offer to move those edits into `.eg/config.md` before overwriting.

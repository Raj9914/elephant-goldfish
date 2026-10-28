# Claude Code BOOTSTRAP.md

This file is read by Claude Code. The user has pointed you at this repo and asked you to set up the elephant/goldfish workflow in their target repo. Follow these steps.

## How this install works

The `eg-*` commands are generic and are never edited per project. Everything project-specific (lint/test commands, review hunt list, design rubric, goldfish model, commit policy) lives in one file in the target repo, `.eg/config.md`, which the commands read at runtime. The same file is used by the Codex and Gemini CLI versions of this workflow.

Updating later means reinstalling the commands; `.eg/config.md` is never overwritten.

## Step 0: Confirm the target

Print the target's absolute path (`git rev-parse --show-toplevel`) and ask the user to confirm before writing anything.

## Step 1: Install the commands

Ask the user (via `AskUserQuestion`) which install they want:

1. **Plugin (recommended)**: available in every repo, updates with `/plugin update`. The user runs these two lines themselves in the Claude Code prompt (they are slash commands, not shell commands):
   ```
   /plugin marketplace add Raj9914/elephant-goldfish
   /plugin install elephant-goldfish@elephant-goldfish
   ```
   Then they restart Claude Code and run `/eg-setup` in the target repo. **Stop here**: `/eg-setup` does the rest of this procedure.

2. **Project-local copy**: commands live in this repo's `.claude/commands/` (useful for sharing with a team through git without the plugin). Continue with Step 2.

## Step 2: Copy the commands (project-local install only)

Copy the seven command files unchanged into the target:

```sh
mkdir -p .claude/commands
for f in eg-setup eg-brainstorm eg-prd eg-fix-bug eg-new-feature eg-precommit-review eg-stats; do
  gh api "repos/Raj9914/elephant-goldfish/contents/claude/commands/${f}.md" -H 'Accept: application/vnd.github.raw' > ".claude/commands/${f}.md"
done
```

If older, per-project-rewritten `eg-*.md` files already exist there, first read them and note any project-specific content (custom gates, extra hunt items) so it can be moved into `.eg/config.md` in Step 3.

## Step 3: Write the project config

Read `.claude/commands/eg-setup.md` and follow it from its Step 1. It inspects the stack, writes `.eg/config.md` (after the user confirms it), updates `.gitignore` and `CLAUDE.md`, and moves any content noted in Step 2 into the config.

## Step 4: Final report

Print:
- Install type (plugin or project-local) and files written
- The `/eg-setup` report (config, `.gitignore`, `CLAUDE.md` changes, values that need the user's input)
- That the user should restart Claude Code if the commands don't appear yet, then type `/eg-` to see them

**Stop short of committing.** The user commits when ready.

## Updating

- Plugin: `/plugin update elephant-goldfish`.
- Project-local: re-run Step 2. The commands are never edited per project, so overwriting them is safe; `.eg/config.md` is untouched. If someone hand-edited a command, show the diff and offer to move the edit into `.eg/config.md` first.

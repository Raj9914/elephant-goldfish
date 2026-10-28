# Elephant/Goldfish Maintenance Prompts

## For users: updating a project

Commands and skills are never edited per project (project settings live in `.eg/config.md`), so updating is a reinstall:

- **Claude Code plugin:** `/plugin update elephant-goldfish`
- **Claude Code project-local install, Codex, Gemini CLI:** paste the install prompt from the README again. The commands/skills are re-copied unchanged; `.eg/config.md` is kept.

If you installed an older version that rewrote the commands for your project, paste this instead:

```markdown
# Migrate Elephant/Goldfish to the config-based version
1. Read my existing eg-* commands/skills (Claude: `.claude/commands/`; Gemini: `.gemini/skills/`).
2. Find the project-specific values in them (lint/test commands, dev URL, stack-specific hunt-list items, design rubric items, implementation order, commit policy).
3. Fetch `shared/eg-config.template.md` from https://github.com/Raj9914/elephant-goldfish and fill it in with those values. Show it to me, then write it to `.eg/config.md` after I confirm.
4. Re-run the install for my agent from the README. Show me any of my hand edits that the new files would drop, and offer to move them into `.eg/config.md` first.
5. Report what moved where.
```

## For maintainers: changing the workflow

1. **Shared goldfish prompts** (reviewer, diagnosis, design passes, disagreement procedure) live in `shared/`. Edit them there, then run:
   ```sh
   python3 scripts/sync_shared.py
   ```
   CI runs `python3 scripts/sync_shared.py --check` and fails if any adapter copy is stale.
2. **Tool-specific steps** live in `claude/commands/`, `codex/skills/` and `gemini/commands/`. When you change a step in one, apply the same logical change to the others with this prompt:

```markdown
# Propagate a workflow change
I changed the elephant/goldfish workflow in one adapter. Apply the same logical change to the other adapters in this repo:

1. Read the recent diff in `claude/commands/`, `codex/skills/` or `gemini/commands/`.
2. Apply the same change to the other two, using each platform's syntax:
   - Claude: `Agent` tool (with `model`), `AskUserQuestion`, `.claude/commands/` format.
   - Gemini: `invoke_agent`, `ask_user`, `run_shell_command`, `.gemini/skills/` format.
   - Codex: `SKILL.md` format, `spawn_agent` with `fork_context: false`, `$eg-` mentions.
3. Never edit text between `<!-- eg:shared ... -->` and `<!-- eg:end -->`; change the file in `shared/` and run `python3 scripts/sync_shared.py`.
4. Update `claude/snippet.md`, `codex/agents-md-snippet.md` and `gemini/gemini-md-snippet.md` if command descriptions changed.
5. Run `python3 scripts/sync_shared.py --check`, `claude plugin validate claude` and `claude plugin validate .`.
```

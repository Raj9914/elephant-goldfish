## Elephant/Goldfish workflow (slash commands)

The `eg-*` commands wrap an "elephant/goldfish" workflow: the **elephant** is the working session with full context (this file, repo state, conversation history); a **goldfish** is a fresh subagent with no prior context, ideally on a different model. For implementation work a goldfish stress-tests a problem doc, a design doc or a diff. For brainstorming and PRDs, several goldfish run in parallel with different lenses.

Project-specific settings (lint/test commands, review hunt list, design rubric, goldfish model) live in `.eg/config.md`. Edit that file, not the commands.

| Command | When to use |
|---|---|
| `/eg-brainstorm <rough idea>` | Early concept design. Parallel goldfish (technical / business / UX / contrarian / market) feed a concepts brief. |
| `/eg-prd <idea \| feature \| #issue>` | Build a PRD: codebase grounding, gap-filling questions, parallel research goldfish, synthesized PRD. |
| `/eg-fix-bug <description \| #issue \| URL>` | Problem doc, independent goldfish diagnosis, disagreements settled by running checks, failing test, fix, review, test gate. |
| `/eg-new-feature <description \| #issue \| URL>` | Scope confirm, design doc, three-goldfish design check (comprehension + critic + readiness), implement, review, test gate. |
| `/eg-precommit-review` | Independent review of the pending diff: parallel reviewers by lens on big diffs, severity-ranked findings, capped fix loop. |
| `/eg-stats` | Shows how often goldfish runs changed the outcome and what they cost (from `.eg/log.jsonl`). |
| `/eg-setup` | Creates or refreshes `.eg/config.md` for this repo. |

With the plugin install, the full names are `/elephant-goldfish:eg-…`; the short names work when nothing else uses them.

Each command stops short of committing. Authorize the commit explicitly when ready; the commit policy is in `.eg/config.md`.

**These commands are interactive by design.** Their `AskUserQuestion` gates run even when a directive asks Claude to work without clarifying questions. For a fully autonomous run, say "skip the framing questions and use defaults" in the same message that invokes the command; each command lists which gates still apply.

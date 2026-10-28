---
description: Create or refresh .eg/config.md (project commands, review rules, goldfish settings) for the elephant/goldfish workflow
argument-hint: [optional: "refresh" to re-inspect and update an existing config]
---

Set up the elephant/goldfish workflow for the current repo. The `eg-*` commands are generic; everything project-specific lives in one file, `.eg/config.md`, which this command writes. Updating the commands later never touches that file.

## Step 0: Confirm the target

Print the repo root (`git rev-parse --show-toplevel`) and ask the user to confirm it is the right project.

- If `.eg/config.md` already exists: read it, and use `AskUserQuestion` to ask whether to **refresh** (re-inspect the repo, keep the user's manual edits, fill gaps), **replace**, or **abort**. If `$ARGUMENTS` is "refresh", skip the question and refresh.
- If `.claude/commands/eg-*.md` files exist from an older install (copied and rewritten per project), note them for Step 5.

## Step 1: Inspect the stack

Read whichever of these exist (in parallel):

- Project instruction files: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` (conventions, commit policy, PR workflow)
- `package.json` (scripts, dependencies), `Gemfile`, `pubspec.yaml`, `pyproject.toml` / `requirements.txt` / `setup.py` / `Pipfile`, `go.mod`, `Cargo.toml`, `composer.json`, `mix.exs`
- Tool config: `tsconfig.json`, `playwright.config.*`, `vitest.config.*`, `jest.config.*`, linter configs
- `Makefile`, `justfile`, `Rakefile`, `mise.toml`, `.tool-versions`, `.nvmrc`, `.ruby-version`
- `docker-compose.yml`, `Dockerfile` (dev-server entrypoints)
- `.github/workflows/*.yml` (CI commands show what the project counts as "passing")
- Test folder layout (list the top-level test directories)

Also run `git log --oneline -15` (commit message style) and `git symbolic-ref --short refs/remotes/origin/HEAD` (default branch).

Check which UI tools this session actually has (look at the tool list for browser tools such as Playwright, Chrome DevTools or Claude in Chrome MCP). Record what exists; don't assume.

Check whether `codex` and `gemini` CLIs are installed (`command -v codex gemini`); this decides which `second_opinion` values are possible.

## Step 2: Fill in the config

Fill in the template below. Rules:
- Only write commands you verified exist (a `test` script in `package.json`, a CI step, a Makefile target). If unsure, leave the value empty and list it in the final report as "needs your input".
- **Review hunt list** and **Design rubric**: write concrete, stack-specific items, not generic advice. Examples:
  - Rails: N+1 (missing `includes`), mass assignment without `params.permit`, missing authorization checks, multi-tenant scoping (queries not filtered by current tenant), Sidekiq idempotency, raw SQL.
  - React/Solid/Vue: missing effect cleanup, stale closures, missing list keys, hydration mismatch, missing `await`, `any` casts.
  - Flutter: controllers/streams not disposed, `setState` after dispose, provider scope mismatch, platform divergence, schema version bump, stale generated `.g.dart`.
  - Python web: N+1 (`select_related`/`prefetch_related`), CSRF, session leaks, async/sync mixing, validation drift.
  - Cloudflare Workers: request-scope leaks, D1 transaction semantics, binding misuse, missing rate limits on auth.
  - Real-time audio: allocations in `process()`, lock-free invariants, sample-rate assumptions, NaN/Inf safety.
- **Goldfish → model**: default `sonnet`. If the main session already runs on Sonnet, suggest `opus` instead, so the goldfish is a different model than the elephant.
- **Goldfish → second_opinion**: `none` unless the user wants it and the CLI is installed.

Template (write it without the `eg:shared` / `eg:end` marker lines):

~~~~markdown
<!-- eg:shared shared/eg-config.template.md -->
# Elephant/Goldfish project config

<!--
This file lives at `.eg/config.md` in your project. Every eg-* command reads it at
runtime, so the commands themselves never need to be edited per project and can
be updated by simply reinstalling them.

Claude Code, Codex and Gemini CLI all read the same file.

Write values after the colon. Leave a value empty (or write `n/a`) when it does not
apply; the commands skip that step. `eg-setup` fills this in for you.
-->

## Project

- name:
- description: <one sentence: what this project is and who uses it>
- default_branch: <leave empty to auto-detect from origin/HEAD>
- docs_path: docs/
- brainstorm_path: docs/eg-brainstorms/
- prd_path: docs/prds/
- source_of_truth_docs: <PRDs or specs the design critic should check against, or n/a>

## Commands

Run each from the repo root.

- lint:
- typecheck:
- unit_test:
- e2e_test:
- e2e_skip_when: <e.g. "diff touches only models/workers with no UI or API change">
- security_scan:
- codegen:
- codegen_trigger: <which file changes require running codegen>
- baseline_setup: <extra step to run inside a clean checkout before lint, e.g. "ln -s {repo}/node_modules node_modules", or n/a>
- dev_start:
- dev_url:

## Validation

- strategy: <web | mobile | backend>
- ui_tools: <how the agent drives the UI, e.g. "Playwright MCP (mcp__playwright__*)", "Chrome DevTools MCP", "flutter run -d chrome", or n/a>

## Test tiers

<!-- One line per tier: name: folder: when to use it -->

- unit:
- integration:
- e2e:

## Review hunt list

<!-- Stack-specific bugs the reviewer must look for, on top of the universal list.
Be concrete, e.g. "N+1 queries: missing includes() on associations rendered in loops". -->

-

## Design rubric

<!-- Stack-specific questions the design critic must ask, e.g.
"Multi-tenancy: is every read/write scoped by current_company?" -->

-

## Implementation order

<!-- The order layers get built in, e.g. "1. migrations 2. models + unit tests 3. ..." -->

1.

## Per-layer verification

<!-- How to check each layer works before moving on. -->

-

## Always verify

<!-- Checks every feature must pass, e.g. "log in as another tenant and confirm no access". -->

-

## Commit policy

- convention: <style seen in git log, e.g. "imperative subject, optional `Fix #123:` prefix">
- rules: <e.g. "no Co-Authored-By trailers", or n/a>

## Goldfish

- model: sonnet
  <!-- Model for goldfish subagents. Use a DIFFERENT model than your main session
  so the goldfish does not share its blind spots. `inherit` = same as main session. -->
- second_opinion: none
  <!-- none | codex | gemini. Also runs the reviewer and bug diagnosis through another
  vendor's CLI (read-only). Costs more, catches more. -->
- review_lenses: bugs, security, tests
  <!-- Reviewers that run in parallel on round 1 of eg-precommit-review. -->
- parallel_review_min_lines: 150
  <!-- Diffs smaller than this get one general reviewer instead of one per lens. -->
- log: .eg/log.jsonl
  <!-- Where each goldfish run is recorded for eg-stats. `off` disables logging. -->
<!-- eg:end -->
~~~~

When refreshing, keep every value the user edited by hand unless it is now provably wrong (e.g. a script that no longer exists); list each change you make.

Print the filled config and ask the user to confirm or correct it via `AskUserQuestion` (options: "Looks right, write it", "I'll correct something in chat", "Abort"). Misreads here affect every later command.

## Step 3: Write the files

1. Write `.eg/config.md`.
2. Add `.eg/log.jsonl` to `.gitignore` (create the file if needed; don't duplicate the line). The config is meant to be committed; the log is personal.

## Step 4: Update CLAUDE.md

Add the section below to the project's `CLAUDE.md`, near the top (after the project overview, before other workflow sections). If a section with the same heading already exists, replace it. If there is no `CLAUDE.md`, ask before creating one.

~~~~markdown
<!-- eg:shared claude/snippet.md -->
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
<!-- eg:end -->
~~~~

## Step 5: Clean up an old install (if found in Step 0)

If `.claude/commands/eg-*.md` files exist from an older per-project install AND this command is running from the plugin, the old copies duplicate the plugin's commands. Show the user any project-specific content in them that is not in the new config (custom gates, extra hunt items), offer to move it into `.eg/config.md`, then ask via `AskUserQuestion` whether to delete the old copies. Never delete without a yes.

## Step 6: Final report

Print:
- Config written (path), with anything left empty under "needs your input"
- `.gitignore` and `CLAUDE.md` changes
- Old-install cleanup result, if any
- Suggested next step, e.g. "try `/eg-precommit-review` on your current changes"

**Do not commit.** The user commits when ready.

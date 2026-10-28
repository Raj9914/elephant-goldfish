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

---
name: "eg-fix-bug"
description: Fix a bug with Codex using problem doc, independent diagnosis, failing test, fix, review, and validation.
---

# EG Fix Bug Skill

Fix a bug using the elephant/goldfish workflow. Use the user's text around the `$eg-fix-bug` skill mention as the bug description. If no description is provided, ask for one.

If the bug description is a GitHub issue URL or `#<number>`, fetch it with `gh issue view <number> --json title,body,labels,comments` and seed the problem doc from it.

## Project Config

If `.eg/config.md` exists at the repo root, read it first. It is shared with the Claude Code and Gemini CLI versions of this workflow and lists the project's test commands, test tiers, UI validation tool and commit policy. Prefer its values over anything you infer.

## Triviality Gate

Skip the goldfish/test ceremony for typo fixes in copy/comments, dead-code removal, version bumps, formatter-only diffs, and single-line config tweaks. Still run `eg-precommit-review` and the test gate.

Run the full loop for everything else.

## Problem Doc

Print:

```text
PROBLEM DOC
- Symptom: <what the user observes>
- Repro: <steps, failing test, URL, log, screenshot, or "need to derive">
- Suspected area: <file/module/route/job/screen>
- Hypothesized root cause: <one sentence>
- Blast radius: <surfaces that could be affected>
- Fixed means: <specific test/behavior/output>
```

If there is no repro and the bug is not obvious from a single file read, stop and ask for a concrete repro path.

For UI bugs, use the project-appropriate manual verification path. Prefer Browser Use / the in-app browser for web apps, a simulator/device run for mobile apps, and curl/log/test reproduction for backend-only services. Start or identify the dev server from package scripts, AGENTS.md/CLAUDE.md, or CI docs when needed.

## Goldfish Diagnosis

The user invoked this skill, so a fresh diagnosis subagent is explicitly authorized.

Spawn a fresh Codex subagent with `fork_context: false`. Use `agent_type: "explorer"` for narrow codebase lookup when available; otherwise use default.

Send only the symptom and repro, not the elephant's hypothesized root cause. Send the text between the markers (markers excluded), with both `<FILL IN>` lines filled:

<!-- eg:shared shared/prompts/diagnosis.md -->
```
<<<DIAG_START>>>
Independent diagnosis of a bug in this repo. The project instruction file at the repo root (CLAUDE.md, AGENTS.md or GEMINI.md) describes the architecture; `.eg/config.md`, if present, lists the project's commands and test tiers.

Symptom: <FILL IN>
Repro: <FILL IN>

Investigate. Where in the codebase is the bug most likely to live? Cite specific file:line locations. List the top 1-3 candidate root causes ranked by likelihood. For each candidate give:
- the evidence in the code that supports it
- a concrete check that would prove or disprove it (a test, an assertion, a log line, a command) and what result each outcome would show

Do NOT propose a fix yet. Do NOT read commit messages or `.eg/log.jsonl`.

If a UI repro is needed and `.eg/config.md` names a UI tool under "Validation", you may use it against the running dev server.

End with the literal string `diagnosis complete`.
<<<DIAG_END>>>
```
<!-- eg:end -->

If `.eg/config.md` → `second_opinion` is `gemini` and the `gemini` CLI is installed, also run the same prompt read-only (`gemini --approval-mode plan -p "<prompt>"`) as a second goldfish.

<!-- eg:shared shared/procedures/settle-disagreement.md -->
### Compare, then settle disagreements with evidence

- **Agree** (the goldfish's top candidate matches your hypothesis): go on to the failing test. If the goldfish ran on the same model as you, say so: agreement between two copies of the same model is weaker evidence.
- **Disagree**: do NOT decide who is right just by re-reading code. Run a check:
  1. Take your hypothesis and the goldfish's top candidate (and a second opinion's, if one ran).
  2. For each, use the "would prove or disprove it" check the goldfish gave, or write one: the smallest test, assertion, log line or command whose result differs depending on which cause is real.
  3. Run them. Let the results decide.
  4. Print a short table: candidate / check / result / verdict.
  5. Delete throwaway checks (temporary logs, scratch scripts). If one check is a proper test that captures the bug, keep it; it becomes the failing test.
  6. If the checks are inconclusive, ask the user to choose between the candidates or to investigate further before writing any fix.

Update the problem doc with the confirmed root cause and tell the user whether it matched your first guess.
<!-- eg:end -->

Unless `.eg/config.md` → `log` is `off`, append one line to `.eg/log.jsonl`:

```sh
mkdir -p .eg && printf '%s\n' '{"ts":"<ISO time>","cmd":"eg-fix-bug","pass":"diagnosis","agent":"codex","outcome":"<agreed|disagreed>","winner":"<elephant|goldfish|both|unclear>","tokens":null}' >> .eg/log.jsonl
```

## Failing Test

Capture the bug as a failing test before fixing.

Choose the narrowest test tier that captures the bug. Infer test locations and commands from AGENTS.md, CLAUDE.md, package manifests, framework conventions, and CI config.

Run the new test and confirm it fails for the reason in the problem doc. If it fails for a different reason, fix the test before touching implementation.

For UI bugs where a full automated test is disproportionate, capture the repro as a manual verification script in the conversation: navigate, act, screenshot/log/console, and confirm the bug is observable. Re-run it after the fix.

## Fix

Implement the smallest change that makes the failing test green and matches "Fixed means." Avoid adjacent refactors and unrequested fallbacks.

Re-run the failing test. It must pass.

For UI bugs, re-run the original browser/simulator/manual repro after the code-level fix passes.

## Review

Use `$eg-precommit-review <bug summary>` or apply the same review procedure from the `eg-precommit-review` skill.

## Test Gate

Run:

```sh
<.eg/config.md unit_test and e2e_test commands; otherwise derive from AGENTS.md, CLAUDE.md, package manifests, and CI config>
```

All required tiers must pass. For UI bugs, re-verify the original repro through Browser Use / in-app browser or simulator.

## Final Report

Report:

- Bug summary
- Root cause
- Fix location
- Regression test
- Goldfish-vs-elephant agreement or divergence
- Review outcome, including verbatim rebuttals
- Test gate status

Stop short of staging or committing. Follow the commit policy in `.eg/config.md` or AGENTS.md/CLAUDE.md if the user later asks to commit.

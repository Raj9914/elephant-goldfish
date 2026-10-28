---
name: eg-fix-bug
description: Fix a bug using the elephant/goldfish workflow. Enforces a problem doc, goldfish diagnosis check, failing test, fix, and test gate.
---

Fix a bug using the elephant/goldfish workflow. The aim: write a problem doc, goldfish-check the diagnosis (so we are not anchored to the first hypothesis), capture the bug as a failing test, fix it, then run the test gate.

If the user provided a GitHub issue URL or `#<number>`, fetch it first with `run_shell_command` using `gh issue view <number> --json title,body,labels,comments` and seed the problem doc from it.

## Read the project config first

Read `.eg/config.md` at the repo root with `read_file`. It is shared with the Claude Code and Codex versions of this workflow and holds the project's commands, test tiers, UI validation tool and commit policy. Wherever this file says "config → X", use that value; an empty or `n/a` value means skip that step. If the file does not exist, infer from GEMINI.md, package manifests and CI config.

## Step 0: Triviality gate

**Skip the goldfish/test ceremony for:** typo fixes in copy or comments, dead-code removal, version bumps, formatter-only diffs, single-line config tweaks. Go straight to Step 5 (review/test gate).

**Run the full loop for everything else.**

## Step 1: Write the problem doc (in this conversation)

Print a tight problem doc to the user:

```
PROBLEM DOC
- Symptom: <what the user observes>
- Repro: <steps to reproduce, or "user did not provide; need to derive">
- Suspected area: <file/module/route/worker/job/screen>
- Hypothesised root cause: <one sentence>
- Blast radius: <which other surfaces could be affected>
- "Fixed" means: <specific test passes / specific behavior / specific output>
```

If the user gave no repro and the bug is not obvious, **stop and ask** for a repro path. Do NOT guess.

**How to reproduce, by config → `strategy`:**
- `web`: use the app at config → `dev_url` with config → `ui_tools` (start it with config → `dev_start` if needed).
- `mobile`: run on a simulator/device; capture a screenshot and the device log.
- `backend`: a `curl` against the local server, a failing test, or a log line.

## Step 2: Goldfish diagnosis check

Spawn a fresh agent with `invoke_agent` (`agent_name="generalist"` or `"codebase_investigator"`):

The goldfish gets ONLY the symptom + repro from Step 1. It does NOT get your hypothesised root cause.

**Prompt to send:** the text between the markers (markers excluded), with both `<FILL IN>` lines filled from Step 1.

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

If config → `second_opinion` is `codex` and the `codex` CLI is installed, also run the same prompt read-only (`codex exec --sandbox read-only "<prompt>"`) as a second goldfish.

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

Unless config → `log` is `off`, append one line to `.eg/log.jsonl`:

```sh
mkdir -p .eg && printf '%s\n' '{"ts":"<ISO time>","cmd":"eg-fix-bug","pass":"diagnosis","agent":"gemini","outcome":"<agreed|disagreed>","winner":"<elephant|goldfish|both|unclear>","tokens":null}' >> .eg/log.jsonl
```

## Step 3: Capture the bug as a failing test BEFORE fixing

The verification criterion lives in code, not in chat. Pick the right tier:

Use the narrowest tier from config → "Test tiers".

Write the test using `write_file` or `replace`. Run it via `run_shell_command`. Confirm it fails for the reason described in the problem doc. If it fails for a different reason, fix the test before touching the implementation.

For UI bugs where an automated test is out of proportion, capture the repro as a short manual script (navigate, act, screenshot/log) and re-run it after the fix.

## Step 4: Fix it

Implement the smallest change that turns the failing test green and matches the "Fixed means" criterion using `replace` or `write_file`.

Avoid adjacent refactors. Bug fix scope is the bug, nothing else.

Re-run the failing test. It must go green.

## Step 5: Hand off to review

Run the `eg-precommit-review` workflow and follow it fully. The reviewer is another goldfish that sees only the diff; do not replace it with a self-review.

## Step 6: Test gate

Execute the test gate via `run_shell_command`.

Run config → `unit_test`, plus config → `e2e_test` unless the diff matches config → `e2e_skip_when`, plus config → `security_scan` if set. Run each separately.

All required tiers must pass.

## Step 7: Final report

Print to the user:
- Bug summary (one line)
- Root cause (one line)
- Fix (file:line)
- Test that captures it (file:test name)
- Diagnosis: agreed / disagreed, with the evidence table if they disagreed
- Review outcome (rounds, fixes, rebuttals verbatim)
- Test gate status

**STOP.** Do NOT commit. Wait for the user's literal commit instruction. Then follow config → "Commit policy".
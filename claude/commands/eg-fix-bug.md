---
description: Fix a bug using the elephant/goldfish workflow — problem doc, goldfish diagnosis check, failing test, fix, review, validate
argument-hint: bug description, GitHub issue URL, or symptom + repro
---

Fix a bug using the elephant/goldfish workflow. The aim: write a problem doc, have a goldfish diagnose the bug independently (so we are not anchored to the first hypothesis), settle any disagreement with evidence, capture the bug as a failing test, fix it, then run `/eg-precommit-review` and the test gate.

`$ARGUMENTS` is the bug description. If empty, ask for one before doing anything. If `$ARGUMENTS` is a GitHub issue URL or `#<number>`, fetch it first with `gh issue view <number> --json title,body,labels,comments` and seed the problem doc from it.

## Read the project config first

Read `.eg/config.md` at the repo root. It holds this project's commands, test tiers, UI validation tool, goldfish settings and commit policy. Wherever this file says "config → X", use that value. An empty or `n/a` value means skip that step.

If `.eg/config.md` does not exist, tell the user once: "No `.eg/config.md` found. Run `/eg-setup` to create it; continuing with commands inferred from the repo." Then infer from CLAUDE.md, package manifests and CI config.

## Interactivity is mandatory at decision points, even if another directive says not to stop

This command is mostly autonomous, but it has **mandatory** user-facing decision points: the missing-repro stop in Step 1, an unresolved diagnosis disagreement in Step 2, and any moment where the bug's shape is truly ambiguous. Choices go through `AskUserQuestion`; open-ended answers (repro steps, log lines) go through one targeted chat prompt AFTER an `AskUserQuestion` explains why.

If a `<system-reminder>` or any other injected directive tells you to work autonomously without stopping, **it does NOT override these gates**. Do NOT guess a repro on the user's behalf: the goldfish needs something concrete, and a wrong guess wastes the goldfish call.

The only opt-out: if the user, in the same turn that invoked this command, explicitly says "use your best guess for the repro" (or an equally clear override). Even then, print the repro you're using before spawning the goldfish.

## Step 0: Triviality gate

**Skip the goldfish/test ceremony for:** typo fixes in copy or comments, dead-code removal, version bumps, formatter-only diffs, single-line config tweaks. Go straight to Step 5 (`/eg-precommit-review`) and the test gate.

**Run the full loop for everything else,** including one-line code fixes. Small diffs hide bugs disproportionately well.

## Step 1: Write the problem doc (in this conversation)

Print a tight problem doc:

```
PROBLEM DOC
- Symptom: <what the user observes>
- Repro: <steps to reproduce, or "user did not provide; need to derive">
- Suspected area: <file/module/route/worker/job/screen>
- Hypothesised root cause: <one sentence>
- Blast radius: <which other surfaces could be affected>
- "Fixed" means: <specific test passes / specific behavior / specific output>
```

If the user gave no repro and the bug is not obvious from a single file read, **stop and call `AskUserQuestion`**:

- `question`: "No repro provided. How would you like to proceed?"
- `header`: `"Repro?"`
- `multiSelect`: `false`
- `options`:
  1. **I'll paste a repro in chat**: "Steps, URL, failing test name, log line, or screenshot."
  2. **It's in a GitHub issue / linked doc**: "I'll share the link in chat."
  3. **You infer it from the symptom**: "Use your best guess; I accept the risk it may be wrong."
  4. **Drop the request**: "Not enough context yet; I'll come back."

Then take the user's free-form input for options 1 or 2. Do NOT guess unless they pick option 3.

**How to reproduce, by config → `strategy`:**
- `web`: drive the app at config → `dev_url` with config → `ui_tools` (start it with config → `dev_start` if it isn't running). Navigate, click, screenshot, read the console. Use whichever browser tool is actually available in this session; check the tool list rather than assuming a name.
- `mobile`: run on a simulator/device; screenshot and read the device log.
- `backend`: a `curl` against the local server, a failing test, or a log line.

## Step 2: Goldfish diagnosis (independent of your hypothesis)

Spawn a fresh agent with the `Agent` tool:
- `subagent_type: "general-purpose"` (or a read-only search agent such as `Explore` if one is listed in this session and the bug is narrow)
- `model:` config → `goldfish.model` (default `sonnet`; omit if `inherit`)
- `description: "Goldfish bug diagnosis"`

The goldfish gets ONLY the symptom and repro from Step 1. It does NOT get your hypothesised root cause; that asymmetry is the point.

Send the body between the markers (markers excluded), with the two `<FILL IN>` lines filled from Step 1:

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

If config → `goldfish.second_opinion` is `codex` or `gemini` and the CLI is installed, also run the same prompt through it in parallel, read-only (`codex exec --sandbox read-only "<prompt>"` or `gemini --approval-mode plan -p "<prompt>"`). Treat it as a second goldfish.

If the bug is tiny (1-3 line fix in a mechanically obvious location), you may skip the goldfish. When in doubt, run it.

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

## Step 3: Capture the bug as a failing test BEFORE fixing

The verification criterion lives in code, not in chat. Pick the narrowest tier from config → "Test tiers" that captures the bug.

Write the test. Run it. Confirm it fails **for the reason in the problem doc**. If it fails for a different reason, the test is wrong: fix the test before touching the implementation.

For UI bugs where a full automated test is out of proportion, capture the repro as a short script in the conversation (navigate, act, screenshot/console or device log) and confirm the bug is visible. Re-run it after the fix.

## Step 4: Fix it

Make the smallest change that turns the failing test green and meets "Fixed means".

Avoid: nearby refactors, defensive code for cases the bug did not show, fallbacks that hide future failures, unrequested feature flags. The scope is the bug, nothing else.

Re-run the failing test. It must pass. If it does not, you have not fixed the bug; do NOT rewrite the test.

For UI bugs, re-run the Step 1 repro too.

## Step 5: Hand off to `/eg-precommit-review`

Run the `eg-precommit-review` command (with the plugin installed its full name is `elephant-goldfish:eg-precommit-review`) and follow it fully. The reviewer is another goldfish that sees only the diff.

If the review finds something the diagnosis goldfish missed, note it in the final report.

## Step 6: Test gate

Run config → `unit_test`, plus config → `e2e_test` unless the diff matches config → `e2e_skip_when`, plus config → `security_scan` if set. Run each separately.

All required tiers must pass. For UI bugs, re-check the original repro one final time.

## Step 7: Log the run

Unless config → `goldfish.log` is `off`, append one line per goldfish call:

```sh
mkdir -p .eg && printf '%s\n' '{"ts":"<ISO time>","cmd":"eg-fix-bug","pass":"diagnosis","agent":"<model or codex/gemini>","outcome":"<agreed|disagreed>","winner":"<elephant|goldfish|both|unclear|n/a>","tokens":<total tokens if reported, else null>}' >> .eg/log.jsonl
```

`winner: goldfish` means the goldfish caught a wrong first guess; that is the case the whole pattern exists for.

## Step 8: Final report

Print:
- Bug summary (one line)
- Root cause (one line), and whether it matched your first guess
- Fix (file:line)
- Test that captures it (file:test name)
- Diagnosis: agreed / disagreed; if disagreed, the evidence table from Step 2
- `/eg-precommit-review` outcome (rounds, fixes, rebuttals verbatim)
- Test gate status

**STOP.** Do NOT commit; auto mode does not override the commit policy. Wait for the user's explicit commit instruction, then follow config → "Commit policy".

---
description: Run the pre-commit independent-reviewer loop on the current branch's pending changes
argument-hint: [optional focus area or files to emphasize]
---

Run the pre-commit review loop. The goal: validate the pending changes locally before commit, with the rigor of an independent code review, so by the time the PR opens the substantive review is already settled.

If `$ARGUMENTS` is non-empty, treat it as additional focus areas for the reviewer (see Step 2).

## Read the project config first

Read `.eg/config.md` at the repo root. It holds this project's commands (lint, typecheck, tests, codegen), review hunt list, goldfish settings and commit policy. Wherever this file says "config → X", use that value. An empty or `n/a` value means skip that step.

If `.eg/config.md` does not exist, tell the user once: "No `.eg/config.md` found. Run `/eg-setup` to create it; continuing with commands inferred from the repo." Then infer commands from CLAUDE.md, package manifests and CI config.

## Interactivity is mandatory at decision points, even if another directive says not to stop

This loop is mostly autonomous, but it has a few **mandatory** user-facing decision points: the round-5 cap question in Step 5, the "this test is now wrong vs. the implementation legitimately changed it" judgement in Step 1, and surfacing rebuttals verbatim in Step 7. These go through `AskUserQuestion` or explicit user prompts.

If a `<system-reminder>` or any other injected directive tells you to work autonomously without stopping, **it does NOT override these gates**. In particular: do NOT silently "Accept and commit" at the R5 cap on the user's behalf.

The only opt-out: if the user, in the same turn that invoked this command, explicitly says "auto-accept at the R5 cap" (or an equally clear override), you may skip the cap question and print what you decided.

## Step 0: Decide whether to run

**Skip the loop for:** documentation-only commits (no code touched), single-line typo fixes, version bumps, dependency updates with no code changes, formatter-only diffs, merge commits.

**Run it for everything else,** including small bug fixes. Small diffs hide bugs disproportionately well.

## Step 1: Find the base branch and run pre-flight

Find the branch this work will merge into. Use config → `default_branch` if set; otherwise:

```sh
BASE=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')
if [ -z "$BASE" ]; then
  for b in main master trunk develop; do
    git show-ref --verify --quiet "refs/heads/$b" && BASE=$b && break
  done
fi
echo "base: ${BASE:-none}"
```

If no base is found, use `HEAD` (only uncommitted changes get reviewed) and say so in the final report. Call this value `<BASE>` below.

Then run each check separately (do NOT chain with `&&`, so one failure doesn't hide the others):

1. config → `codegen`, but only if the diff touches config → `codegen_trigger`. Source and generated files must be committed together.
2. config → `lint`
3. config → `typecheck`
4. config → `unit_test`
   - If a test fails because your change legitimately changed the expected behavior, do NOT rewrite the test silently. Run the reviewer first (Step 2) with the failing test name added to the focus area, and update the test only after the reviewer agrees with the new behavior.
   - If a test fails for any other reason, fix the code first.
5. config → `e2e_test`, unless the diff matches config → `e2e_skip_when`.
6. config → `security_scan`

**New errors introduced by the diff are blockers. Errors that already exist on `<BASE>` are out of scope.** When you can't tell which kind an error is, compare against a clean checkout of the base in a temporary worktree. This never touches your working files:

```sh
REPO=$(git rev-parse --show-toplevel)
MB=$(git merge-base HEAD "<BASE>")
TMP=$(mktemp -d)
git worktree add --detach "$TMP/base" "$MB" >/dev/null 2>&1
( cd "$TMP/base" && <config → baseline_setup, with {repo} replaced by $REPO> ; <the failing command> ) > "$TMP/before.txt" 2>&1
( cd "$REPO" && <the failing command> ) > "$TMP/after.txt" 2>&1
git worktree remove --force "$TMP/base"
echo "$TMP"
```

Compare `before.txt` and `after.txt` by file + rule + message, ignoring line numbers (your edits shift them). Only messages that appear in `after.txt` and not in `before.txt` are blockers. Delete `$TMP` when done.

## Step 2: Spawn fresh independent reviewers

The reviewers must have NO implementation context. That asymmetry is what makes the review work.

**Pass the prompt EXACTLY.** Do NOT prepend the plan, the user's request, what you were trying to do, or any explanation of intent. Any framing breaks the asymmetry.

**Build the prompt** from the body between `<<<TEMPLATE_START>>>` and `<<<TEMPLATE_END>>>` below (markers excluded), with exactly these substitutions and no other edits:
- Every `<BASE>` → the base branch from Step 1.
- `[NO ADDITIONAL FOCUS]` → `Additionally focus on: <$ARGUMENTS verbatim>` if `$ARGUMENTS` is non-empty; otherwise delete that line.
- `[LENS: all]` → see "Which reviewers to run" below.

<!-- eg:shared shared/prompts/reviewer.md -->
```
<<<TEMPLATE_START>>>
Independent code review of the pending changes on this branch.

Collect every kind of pending change. Any one of these can be empty on its own:
- `git status` (working-tree state)
- `git diff` (unstaged changes)
- `git diff --cached` (staged changes)
- `git diff <BASE>...HEAD` (committed changes not yet on <BASE>)
- `git ls-files --others --exclude-standard` (new untracked files)

Read touched files in full where the diff context is not enough.

Do NOT read commit messages, branch descriptions, PR text, design docs or `.eg/log.jsonl`. Judge the code as written, not what its author says it is meant to do. That independence is the point of this review.

[LENS: all]

Find substantive issues. For each finding: cite file:line, name the issue, explain WHY it is a bug or risk (not just what the code does), and suggest a concrete fix.

Hunt for:
- Bugs: off-by-ones, null/undefined dereference, wrong variable used, type coercion gotchas, unhandled promise rejections, missing await, mutating function args, returning the wrong value on an error path
- Security: command injection, XSS, SQL injection, path traversal, prototype pollution, unsanitized input, secrets in URLs or logs, missing auth checks, missing CSRF, open redirects, IDOR (accessing another user's data via predictable IDs)
- Race conditions: shared state without locks, async ordering, double-submit, event handler re-entry, TOCTOU
- Edge cases: empty collections, NaN, Infinity, zero, negative and very large numbers, Unicode, timezones, concurrent access, network failure, partial writes
- Error handling: silent catches, swallowed errors, fallback paths that mask real failures, missing error propagation, throwing in finally/destructors
- Performance: N+1 queries, sync work in hot loops, unbounded growth, missing pagination
- Test coverage gaps: code paths not covered by any test tier. For bug fixes: is there a regression test that fails before the fix and passes after?
- Stack-specific items: if `.eg/config.md` exists, hunt for everything in its "Review hunt list" section too
- Project-rule violations from the project instruction file (CLAUDE.md, AGENTS.md or GEMINI.md); cite the section
- Dead code, leftover debug output (console.log, debugger, print, binding.pry), stale comments referencing removed code

Do NOT report:
- Style preferences (formatting, naming, ordering)
- Requests for explanatory comments unless the WHY is truly non-obvious
- Micro-refactors that do not fix a bug
- Speculative concerns without a concrete failure scenario

[NO ADDITIONAL FOCUS]

Output format: numbered list. Each finding starts with
`[severity: high|medium|low] [confidence: high|medium|low] file:line`
then the issue, why it matters, and the fix. Order by severity, highest first.
End the response with the literal string `no findings` if (and only if) you found nothing.
<<<TEMPLATE_END>>>
```
<!-- eg:end -->

### Which reviewers to run

Count changed lines (`git diff <BASE> --shortstat` plus untracked files).

- **Round 1, diff smaller than config → `parallel_review_min_lines` (default 150):** one reviewer. Replace `[LENS: all]` with nothing (delete the line).
- **Round 1, larger diff:** one reviewer per lens in config → `review_lenses` (default `bugs, security, tests`), **all in a single message so they run in parallel**. For each, replace `[LENS: all]` with:
  `Focus lens: <lens>. Spend your effort on <lens> issues; report other issues only if severity is high.`
- **Round 2 and later:** one reviewer, no lens (see Step 4).

Each reviewer is an `Agent` call with:
- `subagent_type: "general-purpose"`
- `model:` config → `goldfish.model` (default `sonnet`; omit the parameter if the value is `inherit`). A different model than the main session gives a more independent opinion.
- `description: "Independent pre-commit review (round N[, lens])"`

### Optional second opinion from another vendor

If config → `goldfish.second_opinion` is `codex` or `gemini`, and that CLI is installed, also run the same prompt (no lens) on round 1 only, in read-only mode, in parallel with the reviewers above:

```sh
# codex
codex exec --sandbox read-only "$(cat "$PROMPT_FILE")"
# gemini
gemini --approval-mode plan -p "$(cat "$PROMPT_FILE")"
```

Write the built prompt to a temp file first (`PROMPT_FILE=$(mktemp)`). If the CLI is missing or fails, note it in the final report and continue without it.

### Merge the results

Merge findings from all reviewers into one list. Two findings are duplicates if they point at the same file within ~5 lines and describe the same problem; keep the clearer one and note which reviewers raised it. A finding raised by two or more reviewers is stronger evidence; mention that in triage.

## Step 3: Triage the findings

Handle findings in order: severity high first, then medium, then low.

For each finding:
- **Fix it**: apply the change. Note the file:line touched.
- **Rebut it**: write a one-line reason. Valid reasons: (a) "not a bug because X", with X visible in the diff or codebase; (b) "out of scope: the diff doesn't touch that area"; (c) "intentional trade-off documented in [file:line or CLAUDE.md section]"; (d) "user explicitly asked for this in this conversation", quoting the user's exact words. Vague intent claims ("I meant to") are not valid.

Low-severity, low-confidence findings may be listed as "noted, not acted on" instead of fixed or rebutted, but they still go in the final report.

**Surface every rebuttal to the user verbatim** in the final report. No silent dismissals; no summarizing rebuttals away.

## Step 4: Keep a ledger and re-invoke

Before each new round, print:

```
Open findings going into round N:
- [round 1, security] file:line: fixed (not yet committed)
- [round 1, bugs] file:line: rebutted: <verbatim reason>
[...]
```

This keeps earlier findings from quietly disappearing.

Then run ONE fresh reviewer (no lens). Subagents are stateless, so send the FULL built prompt from Step 2 again, then a blank line, `---`, a blank line, and this addendum:

```
Previous round's fixes:
- file:line: what changed
[...]

Check each fix is correct and complete. Look for anything missed in the first pass, especially issues introduced by the fixes themselves.
```

Paste the real text. Do NOT send placeholder strings.

## Step 5: Loop with a hard cap

Repeat Steps 3-4 until the reviewer returns the literal string `no findings` AND every earlier finding is fixed, rebutted or noted.

**Hard cap: 5 rounds.** Stop if (a) you reach 5 rounds, or (b) a new finding lands in the same function as an earlier fix (or within ~10 lines of it). Repeated findings in the same place mean the fix approach is wrong, not that another review will help.

When the cap trips, print a short plain-language summary of open findings grouped by severity, then call `AskUserQuestion`:
- `question`: "Review hit the 5-round cap with N findings still open. What do you want to do?"
- `header`: `"R5 cap"`
- `multiSelect`: `false`
- `options`:
  1. **Accept and commit**: "Skip the open findings, commit as-is."
  2. **Keep working on fixes**: "Keep iterating past the cap. It may not converge; say stop anytime."
  3. **Abandon the change**: "Roll back and start over with a different approach."

"Accept and commit" → go to Step 6 (log) and Step 7 (report). "Keep working" → run round 6, and show the same summary + question after each later round. "Abandon" → stop and wait.

A typical loop is 2-3 rounds.

## Step 6: Log the run

Unless config → `goldfish.log` is `off`, append one JSON line per reviewer call to the log file (default `.eg/log.jsonl`; create `.eg/` if needed):

```sh
mkdir -p .eg && printf '%s\n' '{"ts":"<ISO time>","cmd":"eg-precommit-review","pass":"review","round":<N>,"lens":"<lens or all>","agent":"<model or codex/gemini>","findings":<n>,"fixed":<n>,"rebutted":<n>,"noted":<n>,"tokens":<total tokens if the tool result reported them, else null>}' >> .eg/log.jsonl
```

`/eg-stats` reads this file to show whether the goldfish passes are worth what they cost.

## Step 7: Final report

Print to the user:
- Base branch used
- Rounds run, and which reviewers ran (lenses, model, second opinion)
- Findings fixed (file:line each, with severity)
- Findings rebutted (with the **verbatim** one-line reason each)
- Findings noted but not acted on
- Pre-existing lint/typecheck/test errors treated as out of scope

**STOP here.** Do NOT run `git add` or `git commit`, and do NOT ask "want me to commit?", even in auto mode. Wait for the user's explicit commit instruction. When they give it, follow config → "Commit policy".

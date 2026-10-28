---
name: eg-precommit-review
description: Run the pre-commit independent-reviewer loop on the current branch's pending changes.
---

Run the pre-commit review loop. The goal: validate the pending changes locally before commit, with the rigor of an independent code review.

If the user gave a focus area, pass it to the reviewer (see Step 2).

## Read the project config first

Read `.eg/config.md` at the repo root with `read_file`. It is shared with the Claude Code and Codex versions of this workflow and holds the project's commands, review hunt list, review lenses and commit policy. Wherever this file says "config → X", use that value; an empty or `n/a` value means skip that step. If the file does not exist, infer commands from GEMINI.md, package manifests and CI config, and suggest creating it (see `gemini/BOOTSTRAP.md`).

## Step 0: Decide whether to run

**Skip the loop for:** documentation-only commits (no code touched), single-line typo fixes, version bumps, dependency updates with no code changes, formatter-only diffs, merge commits.

**Run it for everything else.**

## Step 1: Find the base branch and run pre-flight

Use config → `default_branch` if set; otherwise run with `run_shell_command`:

```sh
BASE=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')
if [ -z "$BASE" ]; then
  for b in main master trunk develop; do
    git show-ref --verify --quiet "refs/heads/$b" && BASE=$b && break
  done
fi
echo "base: ${BASE:-none}"
```

If none is found, use `HEAD`. Call this `<BASE>` below.

Then run each check separately with `run_shell_command` (do NOT chain with `&&`):

1. config → `codegen`, only if the diff touches config → `codegen_trigger`. Source and generated files must be committed together.
2. config → `lint`
3. config → `typecheck`
4. config → `unit_test`. If a test fails because your change legitimately changed the expected behavior, do NOT rewrite the test silently; have the reviewer check the new behavior first.
5. config → `e2e_test`, unless the diff matches config → `e2e_skip_when`.
6. config → `security_scan`

New errors introduced by the diff are blockers; errors that already exist on `<BASE>` are out of scope. When unsure which kind an error is, compare against a clean checkout in a temporary worktree, which never touches your working files:

```sh
REPO=$(git rev-parse --show-toplevel); MB=$(git merge-base HEAD "<BASE>"); TMP=$(mktemp -d)
git worktree add --detach "$TMP/base" "$MB" >/dev/null 2>&1
( cd "$TMP/base" && <config → baseline_setup, with {repo} replaced by $REPO> ; <the failing command> ) > "$TMP/before.txt" 2>&1
( cd "$REPO" && <the failing command> ) > "$TMP/after.txt" 2>&1
git worktree remove --force "$TMP/base"
```

Compare by file + rule + message, ignoring line numbers. Only messages new in `after.txt` are blockers.

## Step 2: Spawn fresh independent reviewers

Use `invoke_agent` with `agent_name: "generalist"`. The reviewer must have NO implementation context; that asymmetry is what makes the review work.

**Pass the prompt EXACTLY**: the text between `<<<TEMPLATE_START>>>` and `<<<TEMPLATE_END>>>` (markers excluded), with only these substitutions:
- Every `<BASE>` → the base branch.
- `[NO ADDITIONAL FOCUS]` → `Additionally focus on: <focus area verbatim>`, or delete the line if there is none.
- `[LENS: all]` → on round 1, if the diff is at least config → `parallel_review_min_lines` (default 150) changed lines, run one reviewer per lens in config → `review_lenses` (default `bugs, security, tests`), replacing it with `Focus lens: <lens>. Spend your effort on <lens> issues; report other issues only if severity is high.` Otherwise, and on every later round, run one reviewer and delete the line.

Do NOT add the plan, the user's request, commit messages or any explanation of intent.

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

If config → `second_opinion` is `codex` and the `codex` CLI is installed, also run the same prompt (no lens) on round 1, read-only: `codex exec --sandbox read-only "<prompt>"`.

Merge findings from all reviewers, dropping duplicates (same file within ~5 lines, same problem).

## Step 3: Triage the findings

Handle high-severity findings first. For each:
- **Fix it**: apply the change using `replace` or `write_file`; note the file:line.
- **Rebut it**: one line. Valid reasons: "not a bug because X" (X visible in the code); "out of scope: the diff doesn't touch that area"; "intentional trade-off documented in <file:line or GEMINI.md section>"; "user explicitly asked for this", quoting the user's exact words.

**Surface every rebuttal to the user verbatim** in the final report.

## Step 4: Keep a ledger and re-invoke

Before each new round, print:
```
Open findings going into round N:
- [round 1, security] file:line: fixed (not yet committed)
- [round 1, bugs] file:line: rebutted: <verbatim reason>
[...]
```

Then invoke ONE fresh reviewer (no lens) with the FULL prompt again, followed by a blank line, `---`, a blank line, and:

```
Previous round's fixes:
- file:line: what changed
[...]

Check each fix is correct and complete. Look for anything missed in the first pass, especially issues introduced by the fixes themselves.
```

## Step 5: Loop with a hard cap

Repeat Steps 3-4 until the reviewer returns `no findings` AND every earlier finding is fixed or rebutted.

**Hard cap: 5 rounds.** Also stop if a new finding lands in the same function as an earlier fix.

When the cap trips, print a short summary of open findings by severity, then call `ask_user`:
- `question`: "Review hit the 5-round cap with N findings still open. What do you want to do?"
- `header`: `"R5 cap"`
- `multiSelect`: `false`
- `options`:
  1. **Accept and commit**
  2. **Keep working on fixes**
  3. **Abandon the change**

## Step 6: Log the run

Unless config → `log` is `off`, append one line per reviewer call:

```sh
mkdir -p .eg && printf '%s\n' '{"ts":"<ISO time>","cmd":"eg-precommit-review","pass":"review","round":<N>,"lens":"<lens or all>","agent":"gemini","findings":<n>,"fixed":<n>,"rebutted":<n>,"noted":0,"tokens":null}' >> .eg/log.jsonl
```

## Step 7: Final report

Print to the user:
- Base branch used
- Rounds run and which lenses ran
- Findings fixed (file:line and severity each)
- Findings rebutted (verbatim)
- Pre-existing lint/typecheck/test errors treated as out of scope

**STOP here.** Do NOT commit. Wait for the user's explicit commit instruction, then follow config → "Commit policy".

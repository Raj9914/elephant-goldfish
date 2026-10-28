---
name: "eg-precommit-review"
description: Run a Codex-native pre-commit independent-review loop on pending changes.
---

# EG Precommit Review Skill

Run the pre-commit review loop. The goal is to validate pending changes locally before commit with a fresh reviewer that sees the diff cold.

If the user provides text around the `$eg-precommit-review` skill mention, treat it as an additional focus area for the reviewer.

## Project Config

If `.eg/config.md` exists at the repo root, read it first. It is shared with the Claude Code and Gemini CLI versions of this workflow and lists the project's lint/typecheck/test/codegen commands, review hunt list, review lenses and commit policy. Prefer its values over anything you infer. If it does not exist, infer commands from AGENTS.md, CLAUDE.md, package manifests and CI config.

## Base Branch

Find the branch this work will merge into. Use `.eg/config.md` → `default_branch` if set; otherwise:

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

## Preflight

Skip the loop for pure documentation-only commits, typo-only edits, version bumps, dependency updates with no code changes, formatter-only diffs, and merge commits.

Run it for everything else.

Run these checks sequentially, not chained:

```sh
<derive lint command from AGENTS.md, CLAUDE.md, package manifests, and CI config>
```

If the project has a separate typecheck/analyze step, run it:
```sh
<derive typecheck/analyze command>
```

```sh
<derive focused unit/integration test command>
```

If the project has E2E/system tests and the diff touches UI/API/user-visible behavior, run the relevant tier:
```sh
<derive E2E/system test command>
```
Skip only when the diff is purely internal logic/config/docs with no observable UI/API behavior.

If the project uses generated code and the diff touches generation inputs, regenerate first:
```sh
<derive codegen command>
```
Both source and generated files must be committed together.

New errors introduced by the diff are blockers. Pre-existing failures are out of scope. When unsure which kind an error is, run the same command in a temporary worktree at the merge-base, which never touches your working files:

```sh
REPO=$(git rev-parse --show-toplevel); MB=$(git merge-base HEAD "<BASE>"); TMP=$(mktemp -d)
git worktree add --detach "$TMP/base" "$MB" >/dev/null 2>&1
( cd "$TMP/base" && <.eg/config.md baseline_setup, if any> ; <command> ) > "$TMP/before.txt" 2>&1
( cd "$REPO" && <command> ) > "$TMP/after.txt" 2>&1
git worktree remove --force "$TMP/base"
```

Compare by file + rule + message, ignoring line numbers. Only messages new in `after.txt` are blockers.

## Goldfish Review

The user invoked this skill, so fresh subagent review is explicitly authorized.

Preferred path: spawn a fresh Codex subagent with `fork_context: false` and `agent_type: "default"`. If `spawn_agent` is unavailable, pipe the reviewer prompt into the Codex CLI fallback:

```sh
codex review --base <BASE> -
```

Pass only the reviewer prompt below (the text between the markers, markers excluded). Do not include the implementation plan, the original request, commit messages, or explanatory context. Make exactly these substitutions:

- Every `<BASE>` → the base branch.
- `[NO ADDITIONAL FOCUS]` → `Additionally focus on: <focus area verbatim>` if the user gave one; otherwise delete the line.
- `[LENS: all]` → on round 1, if the diff is at least `.eg/config.md` → `parallel_review_min_lines` (default 150) changed lines, spawn one reviewer per lens in `review_lenses` (default `bugs, security, tests`) in parallel, replacing it with `Focus lens: <lens>. Spend your effort on <lens> issues; report other issues only if severity is high.` Otherwise, and on every later round, use one reviewer and delete the line.

Merge findings from parallel reviewers, dropping duplicates (same file within ~5 lines, same problem), and triage high severity first.

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

## Triage

For each finding:

- Fix it, noting the file:line touched.
- Or rebut it with one line: `not a bug because ...`, `out of scope because ...`, `intentional trade-off documented in ...`, or `user explicitly asked for this: "..."`

Surface every rebuttal verbatim in the final report.

## Loop

Before each new round, print:

```text
Open findings going into round N:
- [from round 1] file:line — fixed
- [from round 1] file:line — rebutted: <verbatim reason>
```

Run another fresh goldfish review with the same prompt plus:

```text
Previous round's fixes:
- file:line — what changed

Verify each fix is correct and complete. Look for anything missed in the first pass, especially issues introduced by the fixes.
```

Stop when the reviewer returns `no findings` and all prior findings are fixed or rebutted.

Hard cap: 5 rounds. If the cap trips, summarize open findings and ask the user whether to accept, keep working, or abandon.

## Log The Run

Unless `.eg/config.md` → `log` is `off`, append one JSON line per reviewer call to `.eg/log.jsonl` (create `.eg/` if needed):

```sh
mkdir -p .eg && printf '%s\n' '{"ts":"<ISO time>","cmd":"eg-precommit-review","pass":"review","round":<N>,"lens":"<lens or all>","agent":"codex","findings":<n>,"fixed":<n>,"rebutted":<n>,"noted":0,"tokens":null}' >> .eg/log.jsonl
```

## Final Report

Report:

- Base branch used
- Rounds run, and which lenses ran
- Findings fixed
- Findings rebutted verbatim
- Pre-existing lint/typecheck/test failures treated as out of scope

Stop short of staging or committing. Follow the commit policy in `.eg/config.md` or AGENTS.md/CLAUDE.md if the user later asks to commit.

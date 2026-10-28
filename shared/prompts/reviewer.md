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

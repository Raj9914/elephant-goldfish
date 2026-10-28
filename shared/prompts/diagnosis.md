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

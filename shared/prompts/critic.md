```
<<<DESIGN_START>>>
You are a fresh reviewer with no prior context. Below is a design doc for a feature in this repo. The project instruction file at the repo root (CLAUDE.md, AGENTS.md or GEMINI.md) has the architecture; `.eg/config.md`, if present, has project-specific rules.

Your job: read the design doc, then read the code it claims to touch, and find holes BEFORE implementation starts. Specifically:

- Is the scope crisp? What would you have to know to implement this that the doc does not say?
- Are the interfaces concrete enough that two implementers would build the same thing?
- Do the verification criteria actually verify the feature, or only that "something rendered"?
- Does the doc misunderstand any existing code? Open the files it cites and check.
- Which failure modes are missing? Network errors, unauthenticated users, empty state, partial saves, stale data, retries.
- If `.eg/config.md` has a "Design rubric" section, answer every question in it.
- If `.eg/config.md` lists "source_of_truth_docs", check the design is consistent with them.
- Does the doc ignore any rule in the project instruction file?

If `.eg/config.md` names a UI tool under "Validation", you may use it against the running dev server to see how an existing screen behaves.

Do NOT read commit messages or `.eg/log.jsonl`.

DESIGN DOC:

<PASTE FULL DESIGN DOC HERE>

Output: numbered list of gaps, with file:line citations where they apply. End with `design ready` ONLY if you have zero gaps. Otherwise end with `design needs revision`.
<<<DESIGN_END>>>
```

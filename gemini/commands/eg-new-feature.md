---
name: eg-new-feature
description: Build a new feature using the elephant/goldfish workflow — design doc, goldfish design check, implement, review, validate.
---

Build a new feature using the elephant/goldfish workflow. The aim: design before code, let a fresh goldfish stress-test the design doc, then implement, review, and validate.

If the user gave a GitHub issue URL or `#<number>`, fetch it with `run_shell_command` using `gh issue view <number> --json title,body,labels,comments` and seed the design doc from it.

## Read the project config first

Read `.eg/config.md` at the repo root with `read_file`. It is shared with the Claude Code and Codex versions of this workflow and holds the project's commands, design rubric, implementation order, verification steps and commit policy. Wherever this file says "config → X", use that value; an empty or `n/a` value means skip that part. If the file does not exist, infer from GEMINI.md, package manifests and CI config.

If the project has its own `eg-*` skill for this kind of change, use it instead.

## Step 0: Confirm scope before designing

Restate the request back to the user in 1-2 sentences ("I read this as: <X>. Confirm or correct.").

If GEMINI.md documents current priorities or phases and this request falls outside them, **stop and confirm with the user** before designing.

Classify the surface area: pure logic (straightforward); API change (backwards compatibility; breaking changes need confirmation); schema change (migration + backfill); new background job (idempotency + retries); external integration (verify its contract); UI (existing patterns to mirror).

## Step 1: Write the design doc

Print the design doc to the user. For substantial features, propose writing it to config → `docs_path` using `write_file` and ask the user before creating the file.

Required sections:

```
DESIGN DOC
- Why: <user problem this solves; cite GH issue, conversation, or PRD section>
- Scope: <what is in; what is explicitly out>
- Surfaces touched: <files / routes / models / controllers / components / DB tables / external services>
- Interfaces: <component props, function signatures, API request/response shapes, DB columns, queue arguments>
- UX flow: <click-by-click for UI; request-by-request for backend>
- Rubric answers: <one line per item in config → "Design rubric">
- Failure modes: <what the user sees when each thing breaks; what the API returns>
- Verification criteria: <unit tests, E2E spec, manual steps>
- Out-of-scope follow-ups: <noted, not built>
```

If config → `source_of_truth_docs` lists PRDs or specs, cite their section numbers so the doc and the source stay aligned.

For UI work, sketch the visual structure in plain text or pseudo-JSX.

### No-code gate

**Do NOT edit, write, scaffold, or refactor code until BOTH Pass B (Critic) AND Pass C (Readiness) in Step 2 close with their ready tokens (`design ready` + `implementation ready`).** Article rule, paraphrased: *"I do not want you to create code. We are not going to create code. Resist your impulse."* This holds until the design doc passes both gates — even if the user asks to skip ahead, even if the change "looks trivial", even if it is "just one line".

If the user explicitly asks to skip the gate ("just write the code", "skip the design doc", etc.), restate the gate, name the still-open passes, and require an explicit override ("yes, override the no-code gate") before any `write_file` or `replace` call. The exception is the `eg-fix-bug` skill for trivial fixes covered by its own Step 0 triviality gate.

The design doc itself, test names mentioned in chat (not yet on disk), and read-only exploration (`read_file`, `read_many_files`, `run_shell_command` for `git status` / `git log` / `git diff`) are NOT code edits and are permitted.

## Step 2: Three-goldfish design check

Run the article's full design-stage protocol: three `invoke_agent` calls per round, run in parallel (or two on revisions — see below), each with no prior context. The combined gate is "ready iff critic AND readiness both sign off"; comprehension is informational.

Each pass uses `agent_name="generalist"` and gets ONLY the design doc (no chat history, no implementation intent, no other passes' output). The asymmetry is the value.

**Round 1 runs all three passes; round 2+ skips comprehension** (revisions are gap-driven, not structural — once the doc reads cleanly, it almost always still reads cleanly). On every round, run critic and readiness.

Send each pass the text between its markers (markers excluded), with `<PASTE FULL DESIGN DOC HERE>` replaced by the full doc.

### Pass A — Comprehension (round 1 only)

Verifies the doc reads cleanly to a cold reader.

<!-- eg:shared shared/prompts/comprehension.md -->
```
<<<COMPREHENSION_START>>>
You are a fresh reader with no prior context. Below is a design doc for a feature in this repo (see the project instruction file at the repo root: CLAUDE.md, AGENTS.md or GEMINI.md). Do NOT critique it yet. Your job is to check that the doc reads clearly to someone who walks in cold.

Output two short sections in this order:

## What this feature does
2-5 sentences in your own words. The user-visible change. Who triggers it, when, what they get back.

## How the existing system works (per the doc)
2-5 sentences summarizing the current behavior the doc says it touches.

End your output with EXACTLY one of these closing lines, on its own line:
- comprehension passed       (the doc reads cleanly; no ambiguous sections)
- comprehension unclear      (one or more sections are too vague to paraphrase)

If you mark it unclear, list the ambiguous sections by heading before the closing line. Do NOT critique architecture choices here; that is the critic's job.

DESIGN DOC:

<PASTE FULL DESIGN DOC HERE>
<<<COMPREHENSION_END>>>
```
<!-- eg:end -->

### Pass B — Critic (every round)

Finds gaps that block implementation.

<!-- eg:shared shared/prompts/critic.md -->
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
<!-- eg:end -->

### Pass C — Readiness (every round)

Stricter than the critic: not "is the design good?" but "is the design _executable_ in one pass?"

<!-- eg:shared shared/prompts/readiness.md -->
```
<<<READINESS_START>>>
You are a fresh implementer with no prior context. Below is a design doc for a feature in this repo. Imagine you've been told: "Implement this. First pass. No follow-up questions allowed." Could you?

For every interface, file path, function signature, API request/response shape, DB column, queue argument, component prop, message type and verification criterion in the doc, ask:
- Could I write the code without asking the author anything?
- Could I verify it works without asking what "works" means?
- Are the cited files and lines concrete enough that I'd open the right file and edit the right region?

Output a numbered list of EVERY question you would have to ask the author before you could ship. For each:
- The question, one sentence.
- The section of the doc that should have answered it.

If the list is empty, say "No open questions."

End with EXACTLY one of these closing lines, on its own line:
- implementation ready       (zero open questions; first-pass implementable)
- implementation not ready   (one or more open questions remain)

A design can be good and still fail this gate. The critic asks "is the design good?"; you ask "is the design executable?".

DESIGN DOC:

<PASTE FULL DESIGN DOC HERE>
<<<READINESS_END>>>
```
<!-- eg:end -->

### Triage and loop

A round is **ready** iff Pass B closes with `design ready` AND Pass C closes with `implementation ready`. Comprehension is informational: log it, surface it to the user, but do not gate progress on it. If comprehension returns `comprehension unclear` AND the round is otherwise ready, still proceed — but flag in the final report that the doc was unclear in places.

If a round is **not ready**, bundle the critic gaps and readiness open questions (and comprehension feedback if it returned unclear) into a single revise prompt with section labels (`=== CRITIC GAPS ===`, `=== READINESS OPEN QUESTIONS ===`, `=== COMPREHENSION FEEDBACK ===`). Tell the elephant to address EVERY numbered gap across BOTH the CRITIC GAPS and READINESS OPEN QUESTIONS sections — do not collapse or skip because the numbering restarts. Each gap is either: addressed in a doc revision, or rebutted with a verbatim reason citing GEMINI.md or the user's words. Print the revised doc back to the user once both gates close.

Then re-run Pass B and Pass C against the revised doc (skip Pass A — see above). If the round still does not converge after **three revisions**, the feature is under-specified — **stop and ask the user** for more direction via `ask_user`.

Unless config → `log` is `off`, append one line per pass to `.eg/log.jsonl`:

```sh
mkdir -p .eg && printf '%s\n' '{"ts":"<ISO time>","cmd":"eg-new-feature","pass":"<comprehension|critic|readiness>","round":<N>,"agent":"gemini","outcome":"<result line>","gaps":<n>,"fixed":<n>,"rebutted":<n>,"tokens":null}' >> .eg/log.jsonl
```

## Step 3: Implementation plan

Once the design doc is `design ready`, write a short ordered implementation plan in chat:

Follow config → "Implementation order". If empty: data/schema first, domain logic, service/API boundaries, UI components (leaf first), wiring/navigation last, with tests alongside each layer.

For trivial features (single-component change), skip this step.

## Step 4: Implement

**Pre-flight check before any code edit:** confirm Step 2 closed both Pass B (Critic) AND Pass C (Readiness). If either is still open, the no-code gate from Step 1 still applies — return to Step 2 instead of proceeding.

Follow the plan using `replace`, `write_file`, and `run_shell_command`. After each layer, briefly verify before moving on:

Use config → "Per-layer verification".

For UI changes, drive the feature yourself with config → `ui_tools` before reporting it done.

Run every check in config → "Always verify".

## Step 5: Hand off to review

Run the `eg-precommit-review` workflow with the feature name as the focus area, and follow it fully. Do not replace it with a self-review.

## Step 6: Test gate

Run config → `unit_test`, config → `e2e_test` (unless the diff matches config → `e2e_skip_when`), and config → `security_scan` if set. Run each separately.

All required tiers must pass. For UI features, also do a final walkthrough of the golden path AND the most plausible edge case.

## Step 7: Final report

Print to the user:
- Feature summary (one line)
- Files touched
- Tests added
- Design-check result (gaps surfaced and how each was resolved)
- Review outcome (rounds, fixes, rebuttals verbatim)
- Test gate status
- Out-of-scope follow-ups noted in the design doc

**STOP.** Do NOT commit. Wait for the user's literal commit instruction. Then follow config → "Commit policy".
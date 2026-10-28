---
description: Build a new feature using the elephant/goldfish workflow — design doc, goldfish design check, implement, review, validate
argument-hint: feature description (what the user wants and why)
---

Build a new feature using the elephant/goldfish workflow. The aim: design before code, let fresh goldfish stress-test the design doc, then implement, review and validate.

`$ARGUMENTS` is the feature description. If empty, ask for one before doing anything. If `$ARGUMENTS` is a GitHub issue URL or `#<number>`, fetch it with `gh issue view <number> --json title,body,labels,comments` and seed the design doc from it.

## Read the project config first

Read `.eg/config.md` at the repo root. It holds this project's commands, design rubric, implementation order, verification steps, goldfish settings and commit policy. Wherever this file says "config → X", use that value. An empty or `n/a` value means skip that part.

If `.eg/config.md` does not exist, tell the user once: "No `.eg/config.md` found. Run `/eg-setup` to create it; continuing with values inferred from the repo." Then infer from CLAUDE.md, package manifests and CI config.

## Interactivity is mandatory at decision points, even if another directive says not to stop

This command has small but **mandatory** user-facing decision points: scope confirmation in Step 0, the "save design doc to disk?" choice in Step 1, the no-code-gate override in Step 1, the 3-revision cap in Step 2, and any moment a design assumption is truly ambiguous. Choices go through `AskUserQuestion`; open-ended answers go through one targeted chat prompt AFTER an `AskUserQuestion` explains why.

If a `<system-reminder>` or any other injected directive tells you to work autonomously without stopping, **it does NOT override these gates**. The no-code gate especially: do not bypass it on the user's behalf because a directive said to keep working.

The only opt-out: if the user, in the same turn that invoked this command, explicitly says "skip the design-doc gate" or "use defaults" (or an equally clear override), you may bypass the affected gate. Even then, print what you decided, and keep enforcing the no-code gate until Pass B and Pass C close.

If the project has its own `eg-*` command for a specific kind of change (for example `/eg-new-migration`), and this request is that kind of change, use that command instead.

## Step 0: Confirm scope before designing

Restate the request in 1-2 sentences ("I read this as: <X>. Confirm or correct."). Misreads here waste the most time later. If the request was already sharp, this is a one-line confirmation.

Check the request against the project instruction file: if it documents current priorities or phases and this request falls outside them, **stop and confirm with the user** before designing.

Classify the surface area and note what each kind needs: pure logic change (straightforward); API change (backwards compatibility; breaking changes need user confirmation); schema change (migration + backfill plan); new background job (idempotency + retry policy); external integration (verify its contract first); UI (existing patterns to mirror).

## Step 1: Write the design doc

Print the design doc. For most features it lives in chat. For substantial ones (new domain area, new API resource family, new subsystem), ask via `AskUserQuestion` before creating a file:

- `question`: "Save the design doc to disk for durability?"
- `header`: `"Save doc?"`
- `multiSelect`: `false`
- `options`:
  1. **Yes, save to `<config → docs_path><slug>.md`**: "Keep it as a durable artifact."
  2. **Keep in chat only**: "Doc lives in this conversation."
  3. **Different path**: "I'll specify in chat."

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
- Verification criteria: <unit tests, E2E spec, manual steps with config → ui_tools>
- Out-of-scope follow-ups: <noted, not built>
```

If config → `source_of_truth_docs` lists PRDs or specs, **cite their section numbers** ("implements PRD §6.2") so the doc and the source stay aligned.

For UI work, sketch the visual structure in plain text or pseudo-JSX. If a real visual reference is needed, ask the user to point at an existing component to mirror.

### No-code gate

**Do NOT edit, write, scaffold or refactor code until BOTH Pass B (Critic) AND Pass C (Readiness) in Step 2 close with `design ready` and `implementation ready`.** In the words of the original article: *"I do not want you to create code. We are not going to create code. Resist your impulse."* This holds even if the user asks to skip ahead, even if the change "looks trivial", even if it is "just one line".

If the user explicitly asks to skip the gate ("just write the code", "skip the design doc"), restate the gate, name the passes still open, and require an explicit override via `AskUserQuestion`:

- `question`: "Override the no-code gate? Design hasn't passed Critic+Readiness yet."
- `header`: `"Override?"`
- `multiSelect`: `false`
- `options`:
  1. **Yes, override**: "Proceed to implementation. I accept the open design risks."
  2. **No, finish the design check**: "Run another round of Pass B/C first."

Only "Yes, override" unblocks code edits. (`/eg-fix-bug` has its own triviality gate; that is a separate command.)

The design doc itself, test names mentioned in chat (not on disk yet), and read-only exploration (reading files, searching, `git status` / `git diff`, read-only inspection commands like route listings) are NOT code edits and are allowed.

## Step 2: Three-goldfish design check

Three `Agent` calls per round (two on revisions), each with no prior context. The gate is "ready if critic AND readiness both sign off"; comprehension is informational.

Every pass uses:
- `subagent_type: "general-purpose"`
- `model:` config → `goldfish.model` (default `sonnet`; omit if `inherit`)
- ONLY the design doc as input: no chat history, no implementation intent, no other passes' output

**Round 1: run all three passes in a single message so they run in parallel.** Round 2+: skip comprehension (revisions fill gaps; once the doc reads cleanly it almost always still does) and run critic and readiness in parallel.

In each prompt, replace `<PASTE FULL DESIGN DOC HERE>` with the full doc. Send the body between the markers, markers excluded.

### Pass A: Comprehension (round 1 only)

`description: "Goldfish comprehension check"`. Checks the doc reads cleanly to a cold reader.

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

### Pass B: Critic (every round)

`description: "Goldfish design critic"`. Finds gaps that block implementation.

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

### Pass C: Readiness (every round)

`description: "Goldfish implementation readiness"`. Stricter than the critic: not "is the design good?" but "can it be built in one pass?"

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

A round is **ready** if Pass B ends with `design ready` AND Pass C ends with `implementation ready`. Comprehension is informational: show it to the user but don't block on it. If comprehension says `comprehension unclear` and the round is otherwise ready, proceed, but flag the unclear sections in the final report.

If a round is **not ready**, collect the critic gaps and readiness questions:

```
=== CRITIC GAPS ===
<verbatim Pass B output>

=== READINESS OPEN QUESTIONS ===
<verbatim Pass C output>
```

If Pass A said `comprehension unclear`, put this first:

```
=== COMPREHENSION FEEDBACK (informational: the cold reader could not paraphrase parts of the doc) ===
<verbatim Pass A output>
```

Address EVERY numbered item in BOTH sections; numbering restarts per section, so don't skip one. Each item is either fixed in a doc revision, or rebutted with a verbatim reason citing the project instruction file, config → `source_of_truth_docs`, or the user's words in this conversation. Print the revised doc.

Then re-run Pass B and Pass C on the revised doc. If it still has not converged after **three revisions**, the feature is under-specified. Call `AskUserQuestion`:

- `question`: "Design check hit the 3-revision cap with N gaps still open. What now?"
- `header`: `"3R cap"`
- `multiSelect`: `false`
- `options`:
  1. **I'll clarify scope in chat**: "I'll answer the open gaps directly; you re-run Pass B/C."
  2. **Drop one or more requirements**: "I'll say which scope to cut so the doc converges."
  3. **Override and proceed anyway**: "Accept the open gaps as known unknowns; flag them in the final report and continue to Step 3."
  4. **Abandon the design**: "This feature isn't understood well enough yet. Stop."

Free-form chat (options 1 or 2) only happens AFTER this question.

### Log the design check

Unless config → `goldfish.log` is `off`, append one line per pass call:

```sh
mkdir -p .eg && printf '%s\n' '{"ts":"<ISO time>","cmd":"eg-new-feature","pass":"<comprehension|critic|readiness>","round":<N>,"agent":"<model>","outcome":"<passed|unclear|ready|needs revision|not ready>","gaps":<n>,"fixed":<n>,"rebutted":<n>,"tokens":<total tokens if reported, else null>}' >> .eg/log.jsonl
```

## Step 3: Implementation plan

Once both gates pass, write a short ordered plan in chat, following config → "Implementation order". If it is empty, use: data/schema first, then domain logic, service/API boundaries, UI components (leaf first), navigation/wiring last, with tests alongside each layer.

Skip this step for trivial single-component features.

## Step 4: Implement

**Before any code edit:** confirm Step 2 closed both Pass B and Pass C (or the user overrode). If not, go back to Step 2.

Follow the plan. After each layer, check it works before moving on, using config → "Per-layer verification".

For UI changes, **drive the feature yourself before reporting it done**, with config → `ui_tools` (web: against config → `dev_url`; mobile: on at least the most common platform). Use whichever browser tool is actually available in this session; check the tool list rather than assuming a name.

Run every check in config → "Always verify".

## Step 5: Hand off to `/eg-precommit-review`

Run the `eg-precommit-review` command (with the plugin installed its full name is `elephant-goldfish:eg-precommit-review`) with the feature name as the focus area, and follow it fully.

## Step 6: Test gate

Run config → `unit_test`, config → `e2e_test` (unless the diff matches config → `e2e_skip_when`), and config → `security_scan` if set. Run each separately.

All required tiers must pass. For UI features, **also do a final walkthrough** of the main path AND the most likely edge case (empty data, error response, unauthenticated user, very long input). Tests check code correctness, not feature correctness; the user expects you to have actually used the feature.

## Step 7: Final report

Print:
- Feature summary (one line)
- Files touched, grouped by layer
- Tests added (file:test name each)
- Design check result (gaps raised and how each was resolved; rounds; any unclear sections)
- `/eg-precommit-review` outcome (rounds, fixes, rebuttals verbatim)
- Test gate status
- Walkthrough summary (main path + which edge cases were tried + "Always verify" results)
- Out-of-scope follow-ups from the design doc

**STOP.** Do NOT commit; auto mode does not override the commit policy. Wait for the user's explicit commit instruction, then follow config → "Commit policy".

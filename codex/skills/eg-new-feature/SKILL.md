---
name: "eg-new-feature"
description: Build a new feature with Codex using design doc, goldfish design check, implementation, review, and validation.
---

# EG New Feature Skill

Build a new feature using the elephant/goldfish workflow. Use the user's text around the `$eg-new-feature` skill mention as the feature description. If no description is provided, ask for one.

If the feature description is a GitHub issue URL or `#<number>`, fetch it with `gh issue view <number> --json title,body,labels,comments` and seed the design doc from it.

If `.eg/config.md` exists at the repo root, read it first. It is shared with the Claude Code and Gemini CLI versions of this workflow and holds the project's commands, design rubric, implementation order, verification steps and commit policy. Prefer its values over anything you infer.

Before designing, check AGENTS.md/CLAUDE.md for project-specific `eg-*` skills or workflow routing notes. If the request clearly belongs to a more specific local workflow, tell the user and switch only if they agree.

## Scope

Restate the request in one or two sentences and ask the user to confirm if the request is ambiguous or high-impact. For a sharp request, proceed after the restatement.

Do a surface-area sanity check based on the current repo: UI, API, database/schema, background job, external integration, generated code, mobile/platform-specific work, or backend-only logic. Stop for confirmation when the request appears high-impact, destructive, cross-tenant/auth-sensitive, or out of phase with documented project priorities.

## Design Doc

Print a design doc before coding. For substantial features, infer a project-appropriate docs path from AGENTS.md/CLAUDE.md or `docs/`, then ask before saving it.

```text
DESIGN DOC
- Why: <user problem this solves>
- Scope: <in scope and explicitly out>
- Surfaces touched: <files, routes, models, components, jobs, external services>
- Interfaces: <props, signatures, API shapes, DB columns, event payloads>
- UX flow: <click-by-click for UI or request-by-request for backend>
- Project-specific constraints: <auth/scoping, lifecycle, generated code, platform, performance, or other constraints discovered from the repo>
- Failure modes: <what breaks and what the user/API sees>
- Verification criteria: <unit tests, integration/E2E, manual Browser Use/simulator steps>
- Out-of-scope follow-ups: <noted, not built>
```

For UI work, sketch the structure in plain text or pseudo-JSX. If a visual reference is needed, ask for the existing component or screen to mirror.

### No-Code Gate

**Do NOT edit, write, scaffold, or refactor code until BOTH Pass B (Critic) AND Pass C (Readiness) in the next section close with their ready tokens (`design ready` + `implementation ready`).** Article rule, paraphrased: *"I do not want you to create code. We are not going to create code. Resist your impulse."* This holds until the design doc passes both gates — even if the user asks to skip ahead, even if the change "looks trivial", even if it is "just one line".

If the user explicitly asks to skip the gate ("just write the code", "skip the design doc", etc.), restate the gate, name the still-open passes, and require an explicit override ("yes, override the no-code gate") before any file write. The exception is the `$eg-fix-bug` skill for trivial fixes covered by its own triviality gate.

The design doc itself, test names mentioned in chat (not yet on disk), and read-only exploration (file reads, `git status` / `git log` / `git diff`, route/schema inspection) are NOT code edits and are permitted.

## Three-Goldfish Design Check

The user invoked this skill, so fresh design-check subagents are explicitly authorized.

Run the article's full design-stage protocol: three passes per round, spawned in parallel (or two on revisions — see below), each with no prior context. The combined gate is "ready iff critic AND readiness both sign off"; comprehension is informational.

For each pass, spawn a fresh Codex subagent with `fork_context: false` and `agent_type: "default"`. If `spawn_agent` is unavailable, run each pass locally as a separate cold prompt and keep implementation context out of the prompt. Each pass gets ONLY the design doc — no chat history, no implementation intent, no other passes' output.

**Round 1 runs all three passes; round 2+ skips comprehension** (revisions are gap-driven, not structural — once the doc reads cleanly, it almost always still reads cleanly). On every round, run critic and readiness.

Send each pass the text between its markers (markers excluded), with `<PASTE FULL DESIGN DOC HERE>` replaced by the full doc.

Unless `.eg/config.md` → `log` is `off`, append one line per pass to `.eg/log.jsonl`:

```sh
mkdir -p .eg && printf '%s\n' '{"ts":"<ISO time>","cmd":"eg-new-feature","pass":"<comprehension|critic|readiness>","round":<N>,"agent":"codex","outcome":"<result line>","gaps":<n>,"fixed":<n>,"rebutted":<n>,"tokens":null}' >> .eg/log.jsonl
```

### Pass A — Comprehension (round 1 only)

Verifies the doc reads cleanly to a cold reader. Send only:

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

Finds gaps that block implementation. Send only:

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

Stricter than the critic: not "is the design good?" but "is the design _executable_ in one pass?" Send only:

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

### Triage and Loop

A round is **ready** iff Pass B closes with `design ready` AND Pass C closes with `implementation ready`. Comprehension is informational: log it, surface it to the user, but do not gate progress on it. If comprehension returns `comprehension unclear` AND the round is otherwise ready, still proceed — but flag in the final report that the doc was unclear in places.

If a round is **not ready**, bundle the critic gaps and readiness open questions (and comprehension feedback if it returned unclear) into a single revise prompt with section labels (`=== CRITIC GAPS ===`, `=== READINESS OPEN QUESTIONS ===`, `=== COMPREHENSION FEEDBACK ===`). The elephant must address EVERY numbered gap across BOTH the CRITIC GAPS and READINESS OPEN QUESTIONS sections — do not collapse or skip because the numbering restarts. Each gap is either addressed in a revised doc, or rebutted with a verbatim reason citing AGENTS.md, CLAUDE.md, a PRD/source-of-truth doc, or the user's words.

Then re-run Pass B and Pass C against the revised doc (skip Pass A — see above). If the round still does not converge after three revisions, stop and ask the user for more direction.

## Implementation

**Pre-flight check before any code edit:** confirm the previous section closed both Pass B (Critic) AND Pass C (Readiness). If either is still open, the No-Code Gate from the Design Doc section still applies — return to the design check instead of proceeding.

Once the design is `design ready`, write a short ordered implementation plan.

Use `.eg/config.md` → "Implementation order" if set. Otherwise derive layer ordering from the stack and repo conventions. Typical order: data/schema first, domain/model logic, service/API boundaries, UI/components, navigation/routing, generated code, then tests and manual validation. Keep the plan short for trivial changes.

Implement in that order. After each layer, run a focused verification before moving on.

After each layer, run the checks in `.eg/config.md` → "Per-layer verification" if set, otherwise the narrowest useful verification: focused unit tests, typecheck/analyze, route/API smoke checks, generated-code validation, browser/simulator walkthroughs, or logs.

For UI changes, drive the feature in the browser or simulator before reporting it done. For backend-only changes, use focused tests, curl/API checks, logs, or equivalent runtime verification.

## Review

Use `$eg-precommit-review <feature name>` or apply the same review procedure from the `eg-precommit-review` skill.

## Test Gate

Run:

```sh
<.eg/config.md unit_test and e2e_test commands; otherwise derive from AGENTS.md, CLAUDE.md, package manifests, and CI config>
```

All required tiers must pass. For UI features, do a final Browser Use / in-app browser or simulator walkthrough of the golden path and one plausible edge case.

## Final Report

Report:

- Feature summary
- Files touched by layer
- Tests added
- Design-check result and gap resolutions
- Review outcome, including verbatim rebuttals
- Test gate status
- Manual walkthrough summary
- Out-of-scope follow-ups

Stop short of staging or committing. Follow the commit policy in `.eg/config.md` or AGENTS.md/CLAUDE.md if the user later asks to commit.

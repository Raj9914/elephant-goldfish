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

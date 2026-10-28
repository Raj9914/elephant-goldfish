---
description: Show whether elephant/goldfish runs are paying off — how often goldfish changed the outcome, and what they cost
argument-hint: [optional: number of days to include, default all]
---

Summarize the goldfish log so the user can decide whether the extra token cost is worth it.

Read the log path from `.eg/config.md` → Goldfish → `log` (default `.eg/log.jsonl`). If it is `off` or the file doesn't exist, say so and stop: "No goldfish runs logged yet. Runs are logged automatically by `/eg-fix-bug`, `/eg-new-feature` and `/eg-precommit-review`."

Run this, with `DAYS` set from `$ARGUMENTS` (empty = all time):

```sh
DAYS="<$ARGUMENTS or empty>" python3 - "<log path>" <<'PY'
import json, os, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

days = os.environ.get("DAYS", "").strip()
since = datetime.now(timezone.utc) - timedelta(days=int(days)) if days.isdigit() else None
rows = []
for line in open(sys.argv[1]):
    line = line.strip()
    if not line:
        continue
    try:
        r = json.loads(line)
    except json.JSONDecodeError:
        continue
    if since:
        try:
            ts = datetime.fromisoformat(r.get("ts", "").replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts < since:
                continue
        except ValueError:
            pass
    rows.append(r)

def useful(r):
    # A run "changed the outcome" if it caught something the elephant then acted on.
    if r.get("pass") == "diagnosis":
        return r.get("winner") == "goldfish"
    if r.get("pass") == "comprehension":
        return r.get("outcome") == "unclear"
    return (r.get("fixed") or 0) > 0

groups = defaultdict(list)
for r in rows:
    groups[(r.get("cmd", "?"), r.get("pass", "?"), r.get("agent", "?"))].append(r)

print(f"{'command':22} {'pass':14} {'agent':10} {'runs':>5} {'useful':>7} {'rate':>6} {'avg tokens':>11}")
for (cmd, p, agent), rs in sorted(groups.items()):
    u = sum(useful(r) for r in rs)
    toks = [r["tokens"] for r in rs if isinstance(r.get("tokens"), (int, float))]
    avg = f"{sum(toks) / len(toks):,.0f}" if toks else "n/a"
    print(f"{cmd:22} {p:14} {agent:10} {len(rs):5} {u:7} {u / len(rs):6.0%} {avg:>11}")

rebutted = sum(r.get("rebutted") or 0 for r in rows)
fixed = sum(r.get("fixed") or 0 for r in rows)
print(f"\nreview findings fixed: {fixed}, rebutted: {rebutted}"
      + (f" (rebut rate {rebutted / (fixed + rebutted):.0%})" if fixed + rebutted else ""))
PY
```

Then explain the table in plain words:
- **useful** = runs where the goldfish changed something: a review finding that got fixed, a diagnosis where the goldfish was right and the first guess was wrong, a design gap that got fixed, or an unclear-doc flag.
- Point out any pass with many runs and a useful rate near 0%: it costs tokens without changing outcomes, so suggest turning it down (e.g. raise `parallel_review_min_lines`, drop a lens from `review_lenses`, or use a cheaper `model`).
- A high rebut rate (over ~50%) means the reviewer raises many false alarms; suggest adding project context to the "Review hunt list" or trying a different `model`.
- If one lens or agent (e.g. a `codex` second opinion) finds things the others miss, say so.

Keep the summary to a few lines. Change no settings unless the user asks.

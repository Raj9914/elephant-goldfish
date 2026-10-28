### Compare, then settle disagreements with evidence

- **Agree** (the goldfish's top candidate matches your hypothesis): go on to the failing test. If the goldfish ran on the same model as you, say so: agreement between two copies of the same model is weaker evidence.
- **Disagree**: do NOT decide who is right just by re-reading code. Run a check:
  1. Take your hypothesis and the goldfish's top candidate (and a second opinion's, if one ran).
  2. For each, use the "would prove or disprove it" check the goldfish gave, or write one: the smallest test, assertion, log line or command whose result differs depending on which cause is real.
  3. Run them. Let the results decide.
  4. Print a short table: candidate / check / result / verdict.
  5. Delete throwaway checks (temporary logs, scratch scripts). If one check is a proper test that captures the bug, keep it; it becomes the failing test.
  6. If the checks are inconclusive, ask the user to choose between the candidates or to investigate further before writing any fix.

Update the problem doc with the confirmed root cause and tell the user whether it matched your first guess.

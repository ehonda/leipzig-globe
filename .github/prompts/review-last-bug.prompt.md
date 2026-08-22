---
name: review-last-bug
description: Independently review and repair the most recently completed Leipzig Globe bug
argument-hint: "[optional bug-specific instructions]"
agent: agent
---

Independently review the most recently completed Leipzig Globe bug.

Read and follow:
- [AGENTS.md](../../AGENTS.md)
- [CONTEXT.md](../../CONTEXT.md)
- [spec.md](../../spec.md)
- [BUGS.md](../../BUGS.md)
- [BUG_TRACKER.md](../../BUG_TRACKER.md)

## Identify the bug

Use the bug tracker and git history to identify the most recently completed bug
and its corresponding `Fix BG-NNN: ...` commit.

Review ONLY that bug. Do not begin the next bug.

## Review procedure

First perform the review WITHOUT editing files.

1. Read the bug's complete section in `BUGS.md`.
2. Inspect the implementation itself, not just the previous summary.
3. Inspect the bug-fix commit and relevant surrounding code.
4. Check every bug requirement individually.
5. Check every "Done when" criterion individually.
6. Run the relevant tests and validation yourself.
7. Look specifically for:
   - requirements that were skipped or only partially implemented;
   - tests that pass without actually proving the repair;
   - hard-coded assumptions contrary to the configuration contract;
   - incorrect error handling or unsupported happy-path assumptions;
   - regressions in the related implementation tasks;
   - repairs that conceal the symptom while leaving the root cause intact.

Do not assume that a bug is fixed because `BUG_TRACKER.md` marks it complete.

## If the review passes

Make no changes.

Report `PASS` and briefly state what was independently verified.

## If the review finds problems

After completing the audit:

1. fix all findings that belong to this bug;
2. add or strengthen tests where appropriate;
3. rerun relevant validation;
4. re-check every bug requirement;
5. commit the fixes as `Review fixes for BG-NNN`;
6. push the commit.

If the bug still cannot satisfy its requirements, mark it open again in
`BUG_TRACKER.md`, record a concise blocker there, commit and push that state.

Do not start the next bug.

In the final response, report:
- PASS or FIXED or BLOCKED;
- findings discovered;
- validation performed;
- any commit created.

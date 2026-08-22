---
name: implement-next-bug
description: Implement exactly the next open Leipzig Globe bug
argument-hint: "[optional bug-specific instructions]"
agent: agent
---

Implement exactly ONE bug in this repository.

Read and follow:
- [AGENTS.md](../../AGENTS.md)
- [CONTEXT.md](../../CONTEXT.md)
- [spec.md](../../spec.md)
- [BUGS.md](../../BUGS.md)
- [BUG_TRACKER.md](../../BUG_TRACKER.md)

## Procedure

1. Inspect `BUG_TRACKER.md`.
2. Select the first open bug.
3. Read that bug's complete section in `BUGS.md`, including every requirement
   and its "Done when" criteria.
4. Inspect the existing implementation before making changes.
5. Fix ONLY that bug, plus changes strictly necessary to support it.
6. Add or update automated tests appropriate to the bug.
7. Run all relevant validation, including the existing test/lint/format commands.
8. Before declaring completion, re-read the bug specification and explicitly
   verify every individual requirement and every "Done when" criterion against
   the actual implementation.

Do not:
- start the next bug;
- mark a bug complete merely because the visible symptom changed;
- weaken tests or acceptance criteria to make them pass;
- silently omit requirements;
- treat planned or stubbed functionality as fixed.

If any requirement cannot be satisfied, leave the bug unchecked and report the
blocker.

Only after every requirement is satisfied and validation passes:

1. mark the bug complete in `BUG_TRACKER.md`;
2. commit all changes with a message of the form `Fix BG-NNN: <bug title>`;
3. push the commit;
4. stop.

Your final response should summarize:
- what was fixed;
- validation performed;
- whether every bug requirement was satisfied;
- the commit created.

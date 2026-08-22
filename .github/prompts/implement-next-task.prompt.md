---
name: implement-next-task
description: Implement exactly the next incomplete Leipzig Globe task
argument-hint: "[optional task-specific instructions]"
agent: agent
---

Implement exactly ONE implementation task in this repository.

Read and follow:
- [AGENTS.md](../../AGENTS.md)
- [CONTEXT.md](../../CONTEXT.md)
- [spec.md](../../spec.md)
- [IMPLEMENTATION_TASKS.md](../../IMPLEMENTATION_TASKS.md)
- [TASK_TRACKER.md](../../TASK_TRACKER.md)

## Procedure

1. Inspect `TASK_TRACKER.md`.
2. Select the first incomplete task that does not require human action.
3. Read that task's complete section in `IMPLEMENTATION_TASKS.md`, including every requirement and its "Done when" criteria.
4. Inspect the existing implementation before making changes.
5. Implement ONLY that task, plus changes strictly necessary to support it.
6. Add or update automated tests appropriate to the task.
7. Run all relevant validation, including the existing test/lint/format commands.
8. Before declaring completion, re-read the task specification and explicitly verify every individual requirement and every "Done when" criterion against the actual implementation.

Do not:
- start the next task;
- mark a task complete merely because the main implementation exists;
- weaken tests or acceptance criteria to make them pass;
- silently omit requirements;
- treat planned or stubbed functionality as complete.

If any requirement cannot be satisfied, leave the task unchecked and report the blocker.

Only after every requirement is satisfied and validation passes:

1. mark the task complete in `TASK_TRACKER.md`;
2. commit all changes with a message of the form `Task N: <task title>`;
3. push the commit;
4. stop.

Your final response should summarize:
- what was implemented;
- validation performed;
- whether every task requirement was satisfied;
- the commit created.

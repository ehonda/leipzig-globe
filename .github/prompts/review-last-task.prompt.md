---
name: review-last-task
description: Independently review and repair the most recently completed task
argument-hint: "[optional task-specific instructions]"
agent: agent
---

Independently review the most recently completed Leipzig Globe implementation task.

Read and follow:
- [AGENTS.md](../../AGENTS.md)
- [CONTEXT.md](../../CONTEXT.md)
- [spec.md](../../spec.md)
- [IMPLEMENTATION_TASKS.md](../../IMPLEMENTATION_TASKS.md)
- [TASK_TRACKER.md](../../TASK_TRACKER.md)

## Identify the task

Use the task tracker and git history to identify the most recently completed implementation task and its corresponding `Task N: ...` commit.

Review ONLY that task. Do not begin the next task.

## Review procedure

First perform the review WITHOUT editing files.

1. Read the task's complete section in `IMPLEMENTATION_TASKS.md`.
2. Inspect the implementation itself, not just the agent's previous summary.
3. Inspect the task commit and relevant surrounding code.
4. Check every task requirement individually.
5. Check every "Done when" criterion individually.
6. Run the relevant tests and validation yourself.
7. Look specifically for:
   - requirements that were skipped or only partially implemented;
   - tests that pass without actually proving the requirement;
   - hard-coded assumptions contrary to the configuration contract;
   - incorrect error handling or unsupported happy-path assumptions;
   - regressions in earlier completed tasks;
   - implementations that look plausible but are mathematically, geometrically,
     physically, or semantically incorrect.

Do not assume that the task is correct because `TASK_TRACKER.md` marks it complete.

## If the review passes

Make no changes.

Report `PASS` and briefly state what was independently verified.

## If the review finds problems

After completing the audit:

1. fix all findings that belong to this task;
2. add or strengthen tests where appropriate;
3. rerun relevant validation;
4. re-check every requirement;
5. commit the fixes as `Review fixes for Task N`;
6. push the commit.

If the task still cannot satisfy its requirements, mark it incomplete again in
`TASK_TRACKER.md`, record a concise blocker there, commit and push that state.

Do not start Task N+1.

In the final response, report:
- PASS or FIXED or BLOCKED;
- findings discovered;
- validation performed;
- any commit created.

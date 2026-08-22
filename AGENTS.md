# Development Instructions

Use `uv` for all Python-related work. Create and manage the environment,
install dependencies, run tools, tests, and the application through `uv`;
do not invoke `pip` or a bare Python interpreter directly.

`IMPLEMENTATION_TASKS.md` is the authoritative implementation backlog.
`TASK_TRACKER.md` records completion state.
`MEMORY.md` is the lightweight project memory for recurring decisions, toolchain quirks, and edge-case rationale that do not yet warrant a formal ADR.

A task is complete only when every listed requirement and its "Done when"
criteria are actually satisfied and validated.

Do not weaken requirements or tests in order to declare a task complete.
Do not autonomously perform milestones explicitly requiring human action.

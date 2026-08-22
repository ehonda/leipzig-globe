# Development Instructions

Use `uv` for all Python-related work. Create and manage the environment,
install dependencies, run tools, tests, and the application through `uv`;
do not invoke `pip` or a bare Python interpreter directly.

`IMPLEMENTATION_TASKS.md` is the authoritative implementation backlog.
`TASK_TRACKER.md` records completion state.

A task is complete only when every listed requirement and its "Done when"
criteria are actually satisfied and validated.

Do not weaken requirements or tests in order to declare a task complete.
Do not autonomously perform milestones explicitly requiring human action.

## Running Python commands

The Python project is nested under `leipzig_globe/`, not at the repository root.
Always run `uv`, `pytest`, and other Python tooling from that project directory,
for example:

- `cd leipzig_globe && uv sync --group dev`
- `cd leipzig_globe && uv run pytest -q`
- `cd leipzig_globe && uv run leipzig-globe --help`

Running those commands from the repository root fails because `pyproject.toml`
exists only in `leipzig_globe/`, and `uv` will not find the project configuration
unless it is started from the correct working directory.

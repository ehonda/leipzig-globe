# Project Memory

This repository keeps a lightweight working memory for recurring patterns, edge cases, and rationale that do not yet justify a formal ADR but are important enough to preserve.

Use this file for:
- repeated implementation decisions and trade-offs
- operational gotchas or toolchain quirks
- context that is likely to matter again in future tasks
- clarifying when a pattern is the "third case" between a one-off fix and a full architectural decision

The goal is not to replace ADRs or specification docs. It is to store the practical memory of how this project actually works so future agents and contributors can pick up the same context quickly.

## Current memory entries

### 2026-08-22 — Python 3.15 upgrade attempt

The project currently targets Python 3.14 in the repo configuration and local `.python-version`, even though some formatting commands were temporarily run under 3.15 as a tooling workaround.

Why this matters:
- a 3.15-only upgrade was attempted, but the geospatial dependency stack (`pyproj` via `geopandas`) failed to build cleanly in this environment
- the repo was verified green on Python 3.14 after reverting
- this is a practical compatibility constraint, not an instruction to ignore future 3.15 support work entirely

The memory here is: do not assume a Python-version jump is safe without verifying the underlying geospatial build stack.

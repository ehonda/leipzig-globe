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

### 2026-08-23 — Windows `osmium-tool` setup

Task 4 requires the external `osmium` executable for cached PBF extraction.
The supported Windows package source is Conda-forge, not the MSYS2 package
repositories. Install it in an isolated user-local environment with a working
Conda or Micromamba installation:

```powershell
conda create --yes --prefix "$env:LOCALAPPDATA\osmium-tool" --channel conda-forge osmium-tool
```

Add `$env:LOCALAPPDATA\osmium-tool\Library\bin` to the user `PATH`, then open a
new terminal and verify with:

```powershell
osmium --version
```

The executable installed for this workspace is
`C:\Users\dennis\AppData\Local\osmium-tool\Library\bin\osmium.exe` (version
1.19.1). A real fixture PBF was passed through `extract_osm_features`; it
produced GeoJSON with the expected road geometry and tags.

Why this matters:

- current MSYS2 does not publish an `osmium-tool` CLI package, and the legacy
  `C:\msys64` installation is too old to update safely through its package
  metadata;
- the Debian WSL distribution on this machine is also an unsupported Buster
  release with retired package sources, so it cannot currently install the
  Debian package.

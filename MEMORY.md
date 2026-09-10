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

### 2026-08-23 — Windows `osmium` invocation and performance investigation

For the current PowerShell session, make the Conda-forge executable available
before running a real build:

```powershell
$env:PATH = "$env:LOCALAPPDATA\osmium-tool\Library\bin;$env:PATH"
uv run leipzig-globe build --output-dir output
```

In Python, use the configured command name `osmium` after checking it with
`shutil.which`; do not pass the absolute path returned by `which` to
`subprocess.run`. The current Windows installation accepts the PATH command
name but failed when invoked through its resolved absolute executable path.

The August real-source build was blocked by BG-004. A 255 MB Saxony PBF
expanded to a 534 MB temporary GeoJSON, and a boundary-first extraction attempt
still wrote a 753 MB partial Municipal Map before cancellation. Temporary build
artifacts were removed from `output/`. Do not retry the full build until the
feature-selection and performance work in BG-004 is complete. See the September
entry below for the replacement benchmark.

### 2026-09-10 — Bounded municipal extraction

The official file contains ten districts. Osmium reads only the **first**
GeoJSON feature as its extraction polygon; dissolve them before export to
WGS84. Use `smart` extraction to complete multipolygon relations, and source
district data from the official file rather than broad OSM administrative
relations. See [Osmium extract documentation](https://docs.osmcode.org/osmium/latest/osmium-extract.html).

Export a fixed tag schema and strip tags from referenced, nonmatching objects.
Unrestricted OSM tags become thousands of sparse GeoPandas columns, multiplying
GeoJSON output size. The export is now consumed feature by feature with a
100 MB cap; no unrestricted export is written. Explicit area/linear tag rules
avoid rendering every closed road as a filled polygon.

Prepare the detailed municipal polygon for repeated spatial predicates and
intersect only features crossing its boundary. Vectorizing an unprepared
predicate alone still took several minutes. One-metre topology-preserving
simplification occurs before exact clipping; validation allows only 0.1 µm
floating-point tolerance around the official boundary.

`uv run scripts/benchmark_map.py` reached the real map in 108.95 seconds on
Windows 11 / Python 3.14.6 / Osmium 1.19.1: 60,852 features, 35.50 MB Municipal
Map, 19.95 MB temporary export. The old renderer then painted a city polygon
over the road/water layers; checkpoint 01 intentionally preserves that defect.
Performance success does not establish rendering correctness.

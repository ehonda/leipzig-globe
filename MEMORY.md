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

The Conda-forge executable directory is part of the persistent user `PATH`.
Open a new terminal after installing it or changing `PATH`; real builds can
then run `uv run leipzig-globe build --output-dir output` directly.

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
Windows 10 (build 19045) / Python 3.14.3 / Osmium 1.19.1: 60,852 features, 35.50 MB Municipal
Map, 19.95 MB temporary export. The old renderer then painted a city polygon
over the road/water layers; checkpoint 01 intentionally preserves that defect.
Performance success does not establish rendering correctness.

### 2026-09-10 — Real map, texture and print pipeline

Checkpoint 02 completes a real offline build in 97.55 seconds, reaching the
map in 64.01 seconds. It retains 60,891 features in a 41.33 MB Municipal Map.
The 300 mm / 200 PPI texture is 7422 × 3711 pixels. Full artifacts remain
gitignored; the gallery, downsampled map/texture, rendered PDF page, two-gore
sample PDF and full-build report are tracked under `demos/02-real-globe/`.

Code is split into municipal extraction, `rendering.py`, `printing.py`,
`preview.py`, and orchestration/validation in `pipeline.py`. The earlier
placeholder functions were removed. Source-map geometry keeps its metric
aspect ratio; the texture stage applies the artificial non-uniform layout.
Leipzig's OSM city node anchors the equator. An explicit `center_lon_lat`
override is supported; deterministic fixtures without a city node use their
bounds centre. Default seam rotation is 15° to put central Leipzig inside a
gore rather than directly on a seam.

Labels use actual feature coordinates and nearby candidate positions (at
most 8 mm per axis in source-render coordinates). Safety checks consider
their entire bounding boxes in the final scaled/rotated placement. Preferred
landmarks win over identically named transport stops; omitted labels remain
in the report. In the current default build, Gewandhaus and
Völkerschlachtdenkmal are omitted at gore seams, and Thomaskirche/Mitte collide
with features. Leipzig, Plagwitz, Connewitz and Schönefeld are visible.

Windows Osmium command-line argument conversion loses non-ASCII filter text
such as `Völkerschlachtdenkmal`. Write **all tag expressions to a UTF-8 file**
and use `--expressions`. The offline fixture now explicitly checks umlauts.
Closed named landmarks need `building`/`historic`/`tourism`/`amenity` area rules
as well as their names; default Osmium export rules otherwise drop some of
these shapes or duplicate closed roads as areas.

Physical math is circumference = πD, pole-to-pole length = πD/2, equatorial
gore width = πD/N. The user confirmed on 2026-09-10 that the calculated two
portrait A4 tiles should replace the old four-row assumption. At 300 mm,
two gores fit across each page, giving 12 pages total. The nominal 2 mm
assembly overlap is measured at the equator and tapers with latitude.
SVG dimensions and the PDF use millimetres; ReportLab lengths are converted
to points explicitly. Calibration is checked from PDF drawing operators,
not just from its text label. Page and gore registration marks are separate.

Previews use analytic ray/sphere intersections and filtered texture sampling,
which gives an exact spherical surface without mesh faceting. They are never
used as print sources. The conservative municipal layout leaves blank regions
on the back and near the poles; selecting a different aesthetic is a later
visual iteration, not permission to remove outlying city areas.

Build validation verifies source checksums before derivation and artifact
checksums afterward. Reports use relative output paths and include only the
artifacts generated by the pipeline, not stale demos in `output/`. Fresh
source acquisition is still not pinned to a dated release (BG-005); preserve
the current source cache and its manifest. Hosted CI installs Osmium and
runs the real offline fixture. A final physical globe size and manual fit
test are still required before claiming the physical milestone complete.

The first hosted Ubuntu CI run passed at commit `05382e0`:
https://github.com/ehonda/leipzig-globe/actions/runs/34529763078.
Keep `.gitattributes` binary rules for PDFs/images: Windows `core.autocrlf`
otherwise tries to treat some PDF headers as text and may corrupt later
stream bytes or cross-reference offsets on checkout. The committed sample
was checked byte-for-byte against the inspected local PDF.

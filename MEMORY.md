# Project Memory

This repository keeps a lightweight working memory for recurring patterns, edge cases, and rationale that do not yet justify a formal ADR but are important enough to preserve.

Use this file for:
- repeated implementation decisions and trade-offs
- operational gotchas or toolchain quirks
- context that is likely to matter again in future tasks
- clarifying when a pattern is the "third case" between a one-off fix and a full architectural decision

The goal is not to replace ADRs or specification docs. It is to store the practical memory of how this project actually works so future agents and contributors can pick up the same context quickly.

## Current memory entries

### 2026-09-15 — Printed halves meet at the equator

The user found vertical overlap harder to assemble. The default
`layout.tile_overlap_mm` is now **0**, with `vertical_tile_mode: equator`:
upper and lower halves end at the equator and meet edge to edge. The side
registration crosses at the join mark the straight trim edge. The separate
2 mm side overlap between adjacent gores is unchanged. Explicit nonzero page
overlap remains supported for historical configurations.

`config/production-215mm-ocean.yaml` persists the 215 mm / 300 PPI / high-density
ocean settings used by Pages. The designated 184.62 mm test preset uses the same
settings except diameter. Current PDFs are under `output/equator-join/`, in
`test-print-184-62mm-ocean/` and `production-215mm-ocean/`. Older print-calibration
PDFs and checkpoint 07 remain historical and retain their overlap.

The latest Pages deployment at the time of this change was `b8eec30`, run
`34902293769`; its source matches the renderer used for these builds. Physical
fit and calibration still require the user's observations in `PHYSICAL_TEST.md`.

### 2026-09-14 — Printer calibration and the designated smaller test ball

The physical test target is **184.62 mm**, from the old ball's 580 mm measured
circumference, using `config/test-print-184-62mm-high-density.yaml`. The final
assembly remains **215 mm**. Do not substitute the final-size preset when asked
to regenerate the designated test print.

The user reported approximately 96 mm for a 100 mm ruler on an unidentified
Brother laser printer, versus 100 mm from the same PDF on their inkjet. Laser
print settings and the precise measurement remain unconfirmed. A4 fitted inside
4.2 mm margins scales to exactly 96%; this is a plausible diagnosis, not proof.

New PDFs start with a separate A4 100 × 100 mm calibration square, measured
between line centres in both axes. They omit the repeated rulers. Gore tile
numbers now start at PDF page 2; manifests identify `calibration_page: 1` and
`calibration_square_mm: [100, 100]`. Historical PDFs retain their legacy validation.

Gore IDs must be outside the artwork's clipping path and repeat on every tile:
placing them only at the full Gore's north end makes the lower-tile label vanish.
Text extraction alone misses this defect. Tests check graphics-state clipping,
physical text bounds and 4.2 mm printer-border clearance. Guides and attribution
also clear that border. Gore geometry, artwork placement and overlaps are unchanged.

Checkpoint 07 contains the calibrated three-gore sample for the **smaller ball**.
The refreshed full local test PDF has nine pages at
`output/print-calibration/test-print-184-62mm/leipzig-globe-print.pdf`.
The prior build is preserved; image hashes/placement and rendered Gore regions
were compared with it. Physical calibration, fit and assembly acceptance still
require human observations. Keep printer, paper and settings unchanged between
the calibration sheet and gores; repeat calibration when they change.

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
For physical assembly, `layout.vertical_tile_mode: equator` keeps a Gore whole
when it fits one page and otherwise makes two tiles whose overlap is centred on
the equator. The 184.62 mm old-ball and 215 mm target presets use this mode. It
must fail when a half-Gore plus half the tile overlap exceeds printable A4 height;
do not silently fall back to an uneven or multi-row split.

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

### 2026-09-13 — Reproducible sources and resumed preview work

The September source lock is now verified by two real clean acquisitions
(128.178 s and 120.575 s; identical source bytes and cache manifests).
`scripts/verify_source_acquisition.py` replaces the unverified bootstrap
downloader; it refuses nonempty destinations, checks the old cache before
and after, and writes repeatable acceptance evidence. Production downloads
stream into temporary files, enforce a 400 MB cap, and only replace files
after matching the expected SHA-256. Schema errors, conflicting checksums,
source-identity changes, interrupted transfers and changed bytes have tests.

The official boundary host responds to curl HEAD but repeatedly resets Python
GET requests. `data/sources/` archives the exact 522,791 official bytes with
license attribution, no geometry edits and no Git newline conversion. The
lock uses the immutable raw GitHub URL at commit `9047147`, while retaining
the official source URL and DL-DE/BY-2.0 evidence. The PBF is the dated
Geofabrik `sachsen-260901.osm.pbf`, not `latest`.

Default fetch/build cache is `.cache/sources-2026-09-01`. Both `.cache/` and
the user-created `.cache/pinned-2026-09` hold August inputs and were preserved;
the latter's directory name is misleading. `config/legacy-cache.yaml` keeps
the old inputs buildable. Never silently relabel or replace these manifests.

The user's GitHub Pages viewer and two presets were preserved. A parent
`output/` directory can contain preset build directories; validation now
prefers the parent's canonical report instead of rejecting nested reports.
The original build and the 215 mm preset both validate with 50 artifacts.
The browser-control tool failed before connection with missing `sandboxPolicy`
metadata, so this session has not visually verified the live site.

BG-006 reopens Task 6: the default 3,662-pixel source-map width is stretched
to 7,422, so output dimensions alone do not prove effective 200 PPI. Fix
source-raster density while preserving metric geometry, physical label sizes,
and safety checks; record actual sampling density and a new visual checkpoint.

Checkpoint 03 saves the September-source gallery and exact two-gore PDF:
98.57 s to map / 160.96 s total, 60,934 retained features, 41.36 MB Municipal
Map, 19.99 MB temporary export. Full build is `output/pinned-2026-09-01`;
compact evidence is `demos/03-pinned-sources`. About 38 GiB remained free.
This is a source-acquisition checkpoint and deliberately retains BG-006.

Visual inspection of checkpoint 03 also exposed BG-007: `Leipzig` labels
the tourism-information node `n670225761`, not city node `n21687149`.
The blanket tourism-first candidate ranking is wrong for geographic places.
Task 5 is reopened; fix semantic identity selection, persist source IDs in
label metadata, and test mixed-name city/landmark/sign/stop fixtures.

### 2026-09-13 — Effective source sampling and semantic label identity

Checkpoint 04 repairs BG-006/007. Source-map resolution is chosen from the
maximum final sampling requirement in either axis while retaining metric
aspect ratio: default 7423 × 7522 source pixels, then a single Lanczos resize
to 7422 × 3711. World Layout zoom is included before that resize, not applied
to a previously downsampled texture. Too-small supplied rasters are rejected.
Both source and scaled intermediate have 100 MP limits; preserve these guards
when increasing print PPI. Physical stroke/font/offset units use the source
sampling scale; seam/pole/crop checks use final texture coordinates instead.
`physical.map_sampling` records the dimensions, source-detail PPI and budget;
validation checks the actual raster dimensions. Old reports lack this field
and retain their legacy integrity validation, not proof of corrected PPI.

Place labels now prefer place nodes; genuine landmarks/attractions beat
same-named signs or stops. Stable ID/geometry tie breaks avoid input-order
selection, and metadata includes source IDs/tags for visible and omitted
labels. Correct Leipzig node `n21687149` anchors at the map centre but its
default label is omitted for feature collision. Do not restore the previous
information-sign label merely to make the word Leipzig visible.

The full build in `output/corrected-rendering` took 271.96 s to map / 410.76 s
total while sharing resources with tests. An isolated benchmark took 162.44 s
and produced the identical map hash. Run benchmarks separately from full tests
for representative timings. `benchmark_map.py` now defaults to its own
`output/map-benchmark/` folder and supports `--output-dir` / `--config-path`,
avoiding accidental replacement of a validated full build's map.
Checkpoint 04 persists the gallery, exact two-gore sample, report and benchmark.
All 94 local tests pass, including scale/crop safety and real offline validation.

The 215 mm / 300 PPI high-density preset was also rebuilt in
`output/corrected-215mm`: 7979 × 8086 source, 7978 × 3989 texture, 173.85 s to
map / 337.94 s total, 50 validated artifacts. Its report is archived with
checkpoint 04, and both Pages presets receive freshly exported WebP assets.
Existing builds and old source caches are preserved. `PHYSICAL_TEST.md` is
the explicit pending human observation record, not an assertion of physical fit.

Next audit finding is BG-008 / Task 14: `_strip_mesh` emits only the two edge
vertices per latitude row. The default equatorial triangle edge midpoint has
radius 0.9641789 instead of 1 (5.37 mm inward at D=300 mm). Subdivide across
gores and test triangle interiors, UVs and seams across multiple gore counts.
This affects browser Gore Assembly, not the sinusoidal printed gores or the
analytic static previews. The old edge-coordinate test alone did not prove
spherical surface accuracy.

### 2026-09-13 — Confirmed 215 mm reference, curved browser gores and Pages builds

The user confirmed **215 mm as the final globe diameter**, not just an alternate
preset. Both Python and YAML defaults now use 215 mm and equator-centred page
splits; default density remains 200 PPI / medium labels. The existing high-density
preset keeps 300 PPI / high labels. Historical 300 mm build reports and samples
remain historical; do not scale them in the print dialog for the new sphere.

BG-008 now subdivides each strip to at most 3 degrees of longitude per segment.
All interior vertices use the existing paper-to-sphere and paper-to-UV mappings.
Tests cover 4/12/24 gores, clockwise/counterclockwise order, 0/2/10 mm overlaps,
both globe sizes, triangle centroids/edges, conservative whole-triangle plane
distance, outward winding, UV inversion, neighbor seams and overlap boundaries.
The reference export has 1,452 vertices / 2,640 triangles per gore and a radial
error bound of 0.000389283 radius, or 0.04185 mm at 215 mm diameter.

Checkpoint 05's full builds are in `output/pages-build/default` and
`output/pages-build/globe-215mm-high-density`. Both validate 50 artifacts.
Default: 5321 × 5392 source, 5320 × 2660 texture, 93.63 seconds to map /
127.96 seconds total. High-density: 7979 × 8086 source, 7978 × 3989 texture,
76.35 seconds to map / 115.62 seconds total. Both use 12 exact-size A4 pages.
`demos/05-curved-gores/` contains the 215 mm print sample and build evidence.

Pages had successfully deployed fixes `1eb3cbf` and interim equator-split commit
`9140427`, but only uploaded tracked assets. It now runs checks and
`scripts/build_pages.py` on each main push, regenerates and validates both presets,
and uploads a fresh `output/pages-site/`. Cache only pinned inputs, not derived
outputs. `build.json` identifies the deployed revision, reports and file hashes;
revision query parameters cover JS/CSS, manifests and textures. An older rerun
cannot publish after main advances. Refresh open tabs after deployment. The
build script requires new output directories and preserves previous builds.

In-app browser access still fails before execution with missing `sandboxPolicy`.
Installed Edge works through `uv run --with playwright scripts/check_browser.py`.
Windows registers `.js` as `text/plain`, so a plain Python HTTP server silently
breaks module loading. The check script serves JavaScript as `text/javascript`
and binds only to loopback. Inspect polar overlays from North/South; at the
equatorial camera the safety rings are hidden behind the sphere's limb.

The Edge checks pass for both presets, all five overlays, camera/reset,
mouse drag/wheel, auto-rotation, touch drag/pinch and mobile controls.
BG-009 was found by exact canvas comparison after Reset: OrbitControls retains
damped rotation deltas when restoring a saved pose. Flush one update with damping
and auto-rotation disabled before applying camera shortcuts, then restore those
settings. This fixes the repeated-view check without weakening its assertion.
All 119 tests, Ruff and Black pass. Physical test/fit acceptance is still pending.

### 2026-09-14 — Exterior style experiment

`layout.exterior` supports `blank` (the CLI default), `terrain`, `ocean`, and
`fog`. Pages builds only the latter three with the 215 mm / 300 PPI / high-label
reference. Diameter/density alternatives are no longer offered in the viewer.
The selector preserves camera, mode and overlay state.

Keep `municipal-map.geojson` clipped to the official boundary. Rendering writes
an explicit municipal mask and metric viewport metadata for exterior variants;
terrain uses a separate `context-map.geojson` extracted from the same pinned PBF
within that rectangle. Context has no labels and never changes the city viewport,
source sampling scale or label candidates. It uses the existing road, water and
green-space classes, not elevation data. Context extraction retains the 100 MB
export limit and records its bounds, counts and timings in the report.

Exterior artwork is composited into the canonical texture before seam rotation,
so print gores, static views and both browser modes use the same design. Terrain
fades across the outer 8% of each map axis to a common ground colour; the plum
municipal outline fades there too. Widening the outline without that fade caused
a low-resolution polar artifact caught by the exact-edge regression test.
Ocean and fog use deterministic spherical fields plus an exterior coastal/fog
fringe. Fields agree across longitude wrap and become constant at each pole.
Cropping the municipality at texture edges is rejected for these variants.

The city raster stays identical across styles. The geometric mask preserves all
municipal interiors, holes and detached areas; existing labels extending beyond
the boundary retain their ink without copying rectangular paper backgrounds.
`scripts/save_exterior_checkpoint.py` validates shared city data/raster/labels,
gore geometry, city pixels and canonical wrap/poles, then saves a comparison.

More map detail, label tuning, the Völkerschlachtdenkmal omission and candidate
landmarks such as the football stadium are explicitly deferred in Tasks 16–18.
Physical printing and fit remain the human-only Task 13.

Completed local builds are `output/exterior-build/{terrain,ocean,fog}` and the
site is `output/exterior-site/`. Checkpoint 06 records 53 / 51 / 51 validated
artifacts, the cross-variant checks and successful Edge desktop/touch tests.
Terrain's context has 78,807 features / 50.56 MB. All three source maps are
7979 × 8086 and canonical textures 7978 × 3989; all print sets use 12 A4 pages.
The tracked `docs/assets/` snapshot now contains only these three variants.
The outline and fog were visually refined after the initial local builds;
their texture, gore, PDF and preview stages were refreshed and revalidated
without changing source rasters. Reports record that additional elapsed time.
Fresh Pages builds produce the final styles directly from the committed code.

Feature commit `60c5146` deployed successfully: hosted Tests run `34786971603`
passes all 128 tests in 37.22 seconds; Pages run `34786971606` rebuilt and
published all three styles. `deployment-check.json` in checkpoint 06 verifies
the exact revision, selector settings and 16 live asset hashes. The subsequent
completion record is a documentation-only `[skip ci]` commit; live `build.json`
intentionally identifies the tested runtime commit `60c5146`.

### 2026-09-14 — Exterior palette and boundary refinement

Terrain's municipal border uses violet ink with a pale outer halo; widths are
specified in physical millimetres and only exterior pixels are painted. Preserve
the wrap/pole fade when changing the border so it cannot produce a polar seam.

Ocean uses layered blue shallows and a narrow pale land shore. Its styling mask
detects the configured water ink in bounded row blocks before downsampling;
this lets visible lake/river crossings open into the ocean without a pale bar.
It is decorative styling, not a reconstruction of geography beyond the city.
Fog uses broader sage-grey clouds and a wide warm-paper fringe. All three keep
the municipal raster, label placement and geometry intact. Checkpoint 08 retains
the new comparison; checkpoint 06 remains the earlier design for reference.

### 2026-09-14 — Detail, label proportions and a bounded preview baseline

Tasks 16–18 were authorized together. Paths/tracks/steps and sports grounds
increase the municipal extract to 102,149 features / 63.64 MB. Keep the same
strict municipal clipping and separate bounded context extract (79.36 MB).
No general building/POI import was added. The 215 mm reference keeps its exact
viewport, source sampling, seam rotation and gore geometry.

The world layout roughly doubles horizontal glyph width if text is painted
with the geography's uncorrected aspect. Labels now counter-scale their x axis,
retain the existing displacement/safety limits, try wrapped names and a 2 mm
fallback, and prioritize curated names in configuration order. Curated placement
uses half-millimetre source steps; other names use one-millimetre steps. Record
the winning source ID, metric anchor, displayed text, font and leader, and count
all rejection reasons for omissions. The high-density reference reaches 80
visible labels versus 25 before. Six real landmark symbols are placed; full
Thomaskirche and Neues Rathaus labels still cannot fit safely and are explained
in checkpoint 09. Do not remove collisions or move their source anchors to force fit.

Pages retains exactly one Before snapshot at `69567a2` and rebuilds only Current.
Before came from the actual live deployment, with all 46 assets checked against
its `build.json`; local and hosted encoders/geometry serialization can yield
different bytes. Preserve `docs/baseline/**` with `-text` Git attributes and
check `snapshot.json` hashes plus the 16 MB budget. It occupies 11.86 MB; the
complete two-version site is 23.87 MB. Version selection preserves viewer state
and fetches only the selected version. GPU assets from replaced, stale and
failed loads are disposed.

Checkpoint 09's release builds used an isolated checkout, excluding the
separate printer-calibration edits. The print-scale comparison PDF is a visual
review sheet, not evidence of physical fit. An error toast overlays the bottom
of the browser canvas: failed-load tests compare the remaining artwork region
and separately assert the error message and retained version identity.

Runtime `b273fff` passed all 136 hosted tests and deployed successfully. All 97
published files and live current/before/current switching were verified in
checkpoint 09. A later documentation-only `[skip ci]` completion commit leaves
that runtime revision in `build.json` intentionally.

### 2026-09-14 — Composite labels, lake names and omitted land cover

The sparse southwest/east/north was partly an extraction/style gap: the pinned
map contains 74.48 km² of farmland. Task 19 adds mapped agricultural parcels,
orchards/vineyards, scrub, industry/commerce/farmyards, brownfield/construction
and quarries. Keep these subdued and distinct from parks, and apply the same
palette to bounded terrain context. Do not infer a land-use fill for untagged
areas. Municipal data grows from 102,149 / 63.64 MB to 106,062 / 69.36 MB.

Composite suppression matches exact nearby place names (within 5 km), and only
occurs after the composite is actually visible. It removes ten redundant labels
from five groups, including both user examples. A failed composite leaves its
components eligible. The high-density cap remains 80.

Retain OSM `water` tags. Named standing-water polygons of at least 5 hectares
are label candidates, ordered by area. A bounded 33 × 33 search covers the lake
extent; horizontal/wrapped text precedes a vertical fallback. Counter-scale
glyphs after rotation. Require the whole footprint inside water, including hole
exclusion, and keep road/rail/label/seam/pole checks. Cospudener See, Zwenkauer See
and Auensee fit; Kulkwitzer See and other rejected candidates remain recorded
with source identities and rejection counts in checkpoint 10.

The single frozen Before baseline advances to the actual `b273fff` deployment,
with all 46 asset hashes verified (11.98 MB). This avoids accumulating snapshots
or rebuilding historical commits. The preview includes a compact colour key.
Release work uses `output/landcover-release`, excluding separate printer edits.

The clean release passes 144 tests and validates all three 12-page A4 PDFs.
Cross-variant city rasters, labels, masks and gore geometry match; all city pixels
and wrap/pole continuity are preserved. Context is 87.67 MB; the complete
Before/Current site is 24.01 MB. Recorded build times are 356.16 / 149.26 / 140.34
seconds for terrain / ocean / fog; the fixed baseline adds no historical build.

Runtime `7103696` passed all 144 hosted tests (32.10 seconds) and deployed via
Pages run `34892862605`. Checkpoint 10 verifies all 97 published file hashes and
live Edge current/before/current switching, the correct commit link and the
expandable colour key. The completion record is documentation-only `[skip ci]`;
the deployed runtime remains `7103696`.

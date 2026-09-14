# 09 — More detail, natural-width labels and a fixed comparison

The 215 mm / 300 PPI reference now renders 80 labels (the configured cap),
compared with 25 before this pass. Subdued paths, tracks, steps and sports
grounds raise the municipal feature count to 102,149 and GeoJSON size to
63.64 MB. Individual building footprints and minor POIs remain outside this
detail pass. Geography, city viewport, sampling and gore geometry are unchanged.

`detail-comparison.jpg` pairs the stadium, centre and monument at identical
coordinates. `print-scale-comparison.pdf` is an A4 visual review sheet with
80 × 60 mm crops at the 215 mm globe's print scale. A rendered inspection
confirmed its page layout and German characters. Print at actual size if used
on paper; physical calibration, gluing and fit remain Task 13, pending human work.

Labels now cancel the world layout's unequal axis scaling. Curated names get
configuration-order priority, a finer search within the same displacement bound,
wrapped alternatives and a 2 mm fallback font. Seam/pole and feature collision
checks remain enforced. All six landmark symbols are checked against named OSM
geometries. Völkerschlachtdenkmal, Red Bull Arena, Gewandhaus and Nikolaikirche
have visible full labels. Thomaskirche's full label is omitted for feature
collision; Neues Rathaus's for label collision, with other rejected candidates
at seams. Both retain a marker at their actual location. `detail-evidence.json`
records their source IDs, coordinates and every rejection count.

Candidate references and the bounded version design are in
[`docs/preview-improvements.md`](../../docs/preview-improvements.md).

Before in Pages is the exact previous live `69567a2` snapshot: all 46 assets
were downloaded and verified against that deployment's `build.json`. It is
stored under `docs/baseline/`, with exact-byte Git attributes, checksums and a
16 MB ceiling. Local and hosted raster/manifest bytes can differ, so a local
re-export is not used to stand in for the previous live version. The print-scale
sheet compares the corresponding prior local canonical texture; its hash and
the new texture's hash are recorded in the evidence.

The release builds are under `output/preview-release/output/pages-build/`,
from an isolated checkout without the separate uncommitted printer-calibration
changes. They retain the committed 12-page Print Set behavior. Terrain took
260.75 seconds in its full local build; ocean took 139.66 seconds. Historical
timings include the prior sessions' workload and refreshed stages and should
not be read as a controlled performance benchmark.

Only the current three styles are regenerated. Before costs approximately
12 MB of static storage and no historical build time. Version changes preserve
camera, zoom, exterior, mode and overlays, loading only the selected version.

Validation: all 53 terrain artifacts and 51 each for ocean/fog pass, as do
identical-city/geometry, exact-wrap and uniform-pole checks. Edge passes both
versions in all styles and modes, preserved camera/overlays, failed-load
retention/retry, desktop interaction, mobile layout, touch drag and pinch.
The complete site is 23.87 MB (11.86 MB of frozen baseline). Fog's full local
build took 128.52 seconds. `browser-check.json` and representative screenshots
record the final interaction checks.

Deployment is verified at runtime commit `b273fff003c11adb719674db666585eff5eebc71`:
[136 hosted tests passed](https://github.com/ehonda/leipzig-globe/actions/runs/34884342222)
and [Pages deployed successfully](https://github.com/ehonda/leipzig-globe/actions/runs/34884342213).
All 97 published files match the live `build.json`; live Edge loaded Current,
switched to Before and back, and checked the exact commit link without page
errors. `deployment-check.json` retains every verified hash, and
`live-current.png` shows the hosted Back view. The completion record is a
documentation-only `[skip ci]` commit; it does not change the deployed runtime.

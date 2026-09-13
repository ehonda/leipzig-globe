# Visual checkpoints

These tracked images come from the cached real Leipzig sources. Full generated
data and print artifacts stay in gitignored `output/`.

## 01 — Extraction repaired, old renderer exposed

`01-extraction/leipzig-map.png` deliberately records the **broken old renderer**
after city-wide extraction was repaired. A city polygon is drawn over the roads
and water. This is evidence of the rendering defect, not a usable map.

`01-extraction/map-benchmark.json` records the first successful bounded run:
108.95 seconds to the map, 60,852 retained features, 35.50 MB Municipal Map,
19.95 MB temporary export. Run `uv run scripts/benchmark_map.py` to repeat with
the populated cache and Osmium on PATH.

## 02 — Real globe and printable gores

- `02-real-globe/globe-views.jpg`: six distinct views of the same printable
  texture, with filtering to keep fine roads from aliasing.
- `02-real-globe/leipzig-map.png`: the source map with true geographic label
  anchors, correct layer order and polygon holes.
- `02-real-globe/leipzig-texture.png`: a downsampled view of the full
  7422 × 3711 texture, centred on Leipzig and rotated by 15° for gore seams.
- `02-real-globe/print-page.png`: an actual rendered PDF page with two gores.
- `02-real-globe/test-print-two-gores.pdf`: two central adjacent gores across
  two A4 pages, at the exact default 300 mm globe scale. Physical testing is
  still pending; this is not an assertion that an unknown globe will fit.
- `02-real-globe/build-report.json`: provenance and measurements from the
  **full-resolution output build**, not checksums of the downsampled demo
  images. `checkpoint.json` describes the sample.

Blank regions on the back and near the poles are outside the municipal
footprint. The current layout preserves the full city extent; later visual
iterations can explore this tradeoff. Omitted labels are explicitly recorded
instead of being moved to invented map locations.

Map data: © OpenStreetMap contributors, https://www.openstreetmap.org/copyright.
Municipal boundary: Stadt Leipzig, Amt für Statistik und Wahlen,
Stadtbezirke_Leipzig_UTM33N (official open geodata). Source URLs and cache hashes
are recorded in `.cache/source-manifest.json`; later checkpoints should retain
their input provenance alongside the images.

## 03 — Pinned September inputs

`03-pinned-sources/` records a complete build from the tracked September source
lock: 98.57 seconds to the map, 160.96 seconds overall, 60,934 features,
41.36 MB Municipal Map and 19.99 MB temporary export. The 300 mm geometry still
produces twelve A4 pages with two vertical tiles per gore.

The gallery and `print-page.png` were visually inspected. The two-page PDF is
an exact-size adjacent-gore sample prepared with the PDF workflow; physical
testing is still pending. Images are downsampled; `build-report.json` describes
the full-resolution build in `output/pinned-2026-09-01`, not demo-image hashes.
`source-acquisition.json` records both real clean downloads and preservation of
the old cache. Boundary attribution and its precise DL-DE/BY-2.0 license are
in the report's source manifests and `data/sources/README.md`.

This checkpoint intentionally retains the source-resolution defect BG-006:
the source map is enlarged horizontally to the nominal 200 PPI texture.
It establishes reproducible inputs, not final print-quality acceptance.
Visual inspection also identified BG-007: the displayed Leipzig label belongs
to a same-named information sign north of the actual city centre. The next
rendering checkpoint must correct that candidate-selection error.

## 04 — Correct source resolution and label identities

`04-corrected-rendering/` uses the same pinned September inputs as checkpoint
03, now rendering a 7423 × 7522 metric source raster before producing the
7422 × 3711 texture. Neither axis is enlarged to manufacture resolution.
The source sampling and selected label identities are recorded in the full
Build Report and source-map metadata.

The gallery and rendered PDF page have been visually inspected. The erroneous
northern Leipzig label is gone: the correct city-node candidate is explicitly
omitted for feature collision. The exact-size, two-page sample still covers
two adjacent central gores at the default 300 mm scale; this does not establish
fit on an unknown physical sphere.

`map-benchmark.json` records an isolated 162.44-second real-source run. The
full build, which overlapped a test-suite run, reached the map in 271.96 seconds
and completed in 410.76 seconds. Both map images have the same SHA-256. The
Municipal Map is 41.36 MB and the temporary export 19.99 MB in both runs.

`215mm-build-report.json` records the refreshed high-density browser preset:
7979 × 8086 source pixels, 7978 × 3989 texture, at least 300 PPI of source
detail in both axes; 173.85 seconds to map / 337.94 seconds total. The preset's
full build remains in `output/corrected-215mm`; both presets' reduced browser
assets are published under `docs/assets/`. Older build directories are preserved.

## 05 — Curved browser gores and the confirmed 215 mm reference

`05-curved-gores/` records the new 215 mm / 200 PPI default with medium labels,
equator-centred page splits and a 5320 × 2660 texture. Its full validated build
is in `output/pages-build/default`; the regenerated 300 PPI high-density preset
is in `output/pages-build/globe-215mm-high-density` and has its own tracked report.
The print page and six-view gallery have been visually inspected. The exact-size
two-page sample contains adjacent Gores 07 and 08 for the final 215 mm sphere.
Physical printing, measurement and fit acceptance remain pending.

The browser mesh now includes interior cross-gore vertices. Its maximum inward
error is bounded by 0.04185 mm at the reference diameter, below 0.001 radius.
`before-300mm-gores.png` preserves the earlier visibly faceted browser view;
the new `default-gores.png` shows the repaired circular silhouette at 215 mm.
Browser screenshots are inspection evidence, not print sources.

## 06 — Outside Leipzig: terrain, ocean and fog

`06-exterior-variants/` compares the three exterior treatments at 215 mm / 300 PPI /
high label density. `comparison.jpg` shows front, back, north and south for each;
the individual texture images are downsampled inspection copies. Browser screenshots
record both modes and overlays, with interaction results in `browser-check.json`.
`mobile.png` is captured after the pinch/zoom test, rather than at the initial view.

Each style has its own full Build Report. `checkpoint.json` records artifact
validation, identical municipal data/raster/mask/labels and gore geometry, preservation
of city interior pixels, and exact canonical wrap/pole continuity. Full local builds
are in `output/exterior-build/{terrain,ocean,fog}`; the regenerated local site is
`output/exterior-site/`. Terrain includes a separate 78,807-feature context dataset
from the pinned September PBF. The Municipal Map remains clipped to Leipzig.

This experiment changes the exterior artwork only. More detail, label tuning and
landmark expansion are deferred in Tasks 16–18. The physical test remains pending;
checkpoint 05 remains the existing 215 mm test-print sample.

## 08 — Refined exterior styles

`08-exterior-refinements/` records the violet municipal border and pale halo,
layered ocean shallows with water-aware shore openings, and soft sage-grey fog.
It includes the four-view comparison, compact textures, full build reports and
browser evidence. The city raster, labels and geometry remain unchanged from
checkpoint 06. See its README for the local build's parallel calibration context.

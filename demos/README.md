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

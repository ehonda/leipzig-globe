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

Map data: © OpenStreetMap contributors, https://www.openstreetmap.org/copyright.
Municipal boundary: Stadt Leipzig, Amt für Statistik und Wahlen,
Stadtbezirke_Leipzig_UTM33N (official open geodata). Source URLs and cache hashes
are recorded in `.cache/source-manifest.json`; later checkpoints should retain
their input provenance alongside the images.

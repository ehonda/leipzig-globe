# Rendering Performance Handoff

## Next Focus

Resolve BG-004 so a populated-cache Windows build produces the real
`output/leipzig-map.png` in a practical, measured time.

## Current State

- `main` contains the prior data-driven renderer fixes at `aadb54f`.
- The working tree includes an uncommitted Osmium invocation change in
  `src/leipzig_globe/municipal_map.py` and its tests. It executes `osmium` by
  PATH name after availability checking, which fixes the Windows absolute-path
  invocation failure.
- The extractor now attempts WGS84 boundary-first PBF extraction before tag
  filtering. The focused test passes, but the actual build still generated an
  unacceptably large partial Municipal Map and was stopped.
- Generated temporary and partial GeoJSON artifacts were removed. The old
  synthetic `output/demo-map.png` remains and must not be used to validate the
  real pipeline.

## Evidence

- The cached Saxony PBF is 255 MB with 3,755,628 ways.
- The old extraction created a 534 MB temporary `osm-features.geojson`.
- The boundary-first attempt created a 753 MB partial
  `output/municipal-map.geojson`; it did not reach `leipzig-map.png`.
- The municipal boundary is an EPSG:25833 ten-feature district dataset and
  must be converted to EPSG:4326 before `osmium extract --polygon`.

## Resume Steps

1. Read [BUGS.md](../BUGS.md), especially BG-004, and the operational notes in
   [MEMORY.md](../MEMORY.md).
2. Profile the feature counts and output sizes after the PBF extract,
   tag-filter, and export stages. Verify that the PBF boundary extract is
   actually limiting feature counts.
3. Reduce retained tags and geometry before GeoPandas reads them. Prefer a
   bounded intermediate representation over a full GeoJSON export.
4. Add a reproducible performance check, then build from the populated cache
   and inspect the real `output/leipzig-map.png`.

## Suggested Skills

- `domain-modeling` if terms or artifact contracts in `CONTEXT.md` change.
- `python-fact-grounded-coding` to ground profiling and code changes in the
  selected interpreter, runtime measurements, and tests.

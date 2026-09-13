# Exterior refinements

The 215 mm / 300 PPI comparison refines the three treatments from checkpoint 06:

- Terrain has a violet municipal border with a pale halo, sized in physical
  millimetres so it remains visible at preview and print density.
- Ocean has a broad blue shelf, a soft shallow-water wash and a fine pale shore.
  The shore follows visible land ink and opens at lake/river water crossings;
  it does not add a beach across those openings or modify inland lakes.
- Fog uses broad, quiet sage-grey clouds and a warm paper transition that fits
  the map's existing palette.

`comparison.jpg` shows front, back, north and south. Texture and browser images
are inspection copies; full-resolution print sources remain in
`output/exterior-refined-build/{terrain,ocean,fog}`. The local site is
`output/exterior-refined-site/`.

`checkpoint.json` records full artifact validation, identical municipal data,
raster, mask, labels and gore geometry, preserved city interior pixels, and exact
canonical wrap/pole continuity. `browser-check.json` records the Edge interaction
checks. Historical checkpoints remain unchanged.

The local full build also includes the parallel print-calibration working-tree
changes present during this session. Those changes are owned by the calibration
task and are excluded from the exterior implementation commit; these local PDF
reports therefore do not claim to reproduce that commit's print pagination.
Hosted Pages rebuilds from its exact committed revision, recorded separately in
`deployment-check.json` after publication.

Physical printing and fit remain pending human work. Detail, label and landmark
improvements remain deferred.

## Published verification

Runtime commit `69567a2f7d4cbf5936f2608d8b36c286748d1b19` passed
[hosted Tests](https://github.com/ehonda/leipzig-globe/actions/runs/34789789687)
(130 tests in 30.04 seconds, Ruff and Black) and the
[Pages rebuild/deployment](https://github.com/ehonda/leipzig-globe/actions/runs/34789789716).
`deployment-check.json` verifies the live revision and 16 published file hashes:
HTML/JS/CSS, the style index, and each style's manifest, finished texture, report
and first gore texture. Refresh an existing Pages tab to load this revision.

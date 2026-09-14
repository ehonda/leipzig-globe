# Detail, labels and version comparison

Tasks 16–18 were authorized together on 14 September 2026. This pass adds
walking/cycling paths, tracks and steps in subdued ink, plus sports pitches,
stadiums and sports centres in a pale green. Individual buildings and minor
POIs remain excluded to keep the 215 mm map readable and extraction bounded.

Text now compensates for the unequal world-layout axes, preserving natural
glyph proportions in the canonical texture. Curated names follow configuration
order. Placement tries nearby positions on a finer grid, then wrapped names
and a 2 mm fallback font, with the existing 8 mm per-axis source displacement,
10 mm seam clearance, pole clearance and feature collision checks retained.
Reports identify the actual selected source, anchor, font, displayed text and
leader line; omissions count rejection reasons instead of reporting only the
last attempted position. Markers stay at actual landmark geometries.

The landmark set retains Völkerschlachtdenkmal, Thomaskirche and Gewandhaus and
adds Red Bull Arena, Nikolaikirche and Neues Rathaus. Place names keep their
existing semantic preference for place nodes over information signs.

Candidate identity and location references, checked on 14 September 2026:

| Landmark | Official reference | Selection |
| --- | --- | --- |
| Völkerschlachtdenkmal | [Leipzig Tourism](https://www.leipzig.travel/poi/voelkerschlachtdenkmal) | Existing monument; investigate and repair omission |
| Red Bull Arena | [Leipzig Tourism](https://www.leipzig.travel/poi/red-bull-arena) | Football stadium at Am Sportforum, distinct from the neighboring indoor arena |
| Nikolaikirche | [Leipzig Tourism](https://www.leipzig.travel/poi/nikolaikirche) | Central church and historic landmark |
| Neues Rathaus | [Leipzig Tourism](https://www.leipzig.travel/poi/neues-rathaus) | City hall in the southwest of the centre |

Exact OSM IDs, coordinates and placement outcomes are recorded in checkpoint
09's `detail-evidence.json`; geometry comes from the pinned September PBF.
The published 3D artwork and the print gores use the same canonical textures.
The checkpoint's A4 comparison shows paired crops at their actual 215 mm globe
print scale. It is a visual review sheet, not a physical fit test.

## A bounded before/current comparison

The viewer's Version selector preserves exterior, camera, zoom, mode and
overlays. Before is a fixed snapshot of `69567a2`, the last exterior refinement
before this work. Current is rebuilt from the deployed commit, whose link is
shown beneath the controls. Both versions offer terrain, ocean and fog at
215 mm / 300 PPI. Refresh an already open page after deployment.

`docs/baseline/` holds only the reduced browser assets and their provenance,
about 12 MB, under a checked 16 MB limit. `snapshot.json` guards the exact
historical hashes. Pages copies it and rebuilds only current artwork. The
browser fetches one selected version, never all history on initial load;
replaced GPU resources are disposed, including stale or failed requests.

This intentionally retains one baseline, not every commit. To move the baseline
in a later design iteration, replace that directory with a verified deployed
snapshot, update its hashes/revision and `docs/versions.json`, and rerun the
browser and baseline tests. `build.json` hashes both versions and the UI.

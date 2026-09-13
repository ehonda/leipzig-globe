# Leipzig Globe Bug Tracker

## Status

- [x] BG-001: Clean map renderer uses placeholder geometry (reopened defects repaired and tested)
- [x] BG-002: Globe texture is independently drawn, not transformed from the map (fallback removed; Zentrum and PPI corrected)
- [x] BG-003: Offline data stages are disconnected from `build`
- [x] BG-004: Municipal Map derivation does not finish in a practical time (real full builds reach the map below five minutes; intermediates below 100 MB)
- [x] BG-005: Fresh source acquisition is not pinned to reproducible releases (two real clean acquisitions verified)
- [x] BG-006: Source-map raster is upscaled below the declared effective PPI (both-axis source sampling verified; checkpoint 04)
- [x] BG-007: Generic tourism objects outrank the Leipzig city label (semantic selection, stable source IDs, real city node verified)
- [x] BG-008: Browser gore meshes are flat across each gore (whole-triangle error bound, UV/seam tests and inspected Edge views)
- [x] BG-009: Camera shortcuts retain orbit inertia (repeatable browser Reset verified after auto-rotation)

## Notes

- [BUGS.md](BUGS.md) is the authoritative defect backlog and defines the
  required repair and "Done when" criteria for every bug.
- Only mark a bug complete after every requirement in `BUGS.md` is satisfied
  and the relevant validation passes.

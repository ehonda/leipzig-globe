# Leipzig Globe Task Tracker

## Status

- [x] 1. Bootstrap the `uv` Python project (reviewed and corrected)
- [x] 2. Define configuration and artifact contracts
- [x] 3. Implement deterministic source acquisition (dated extract, immutable boundary mirror, two real clean acquisitions; BG-005)
- [x] 4. Derive the Municipal Map (all ten official districts; real-source benchmark and Osmium fixture verified)
- [x] 5. Render the clean Leipzig map (semantic label selection and selected source IDs verified; BG-007 repaired)
- [x] 6. Create the 2:1 Globe Texture (true both-axis source sampling, single downsample, allocation guards; BG-006 repaired)
- [x] 7. Generate SVG Gores (sinusoidal sampling, physical dimensions, overlap, outlines and alignment marks)
- [x] 8. Assemble the tiled A4 print PDF (calculated/equator-split layouts; dimensions and drawing operators checked)
- [x] 9. Generate the Preview Set (six different spherical views; optional safety overlays)
- [x] 10. Emit the Build Report (input and artifact checksums, relative paths, dimensions and timings)
- [x] 11. Expose the end-to-end CLI (real offline build and validation completed)
- [x] 12. Add automated validation (119 local tests pass; hosted offline-fixture workflow configured)
- [ ] 13. Perform the physical test-print milestone (blocked by human action)
- [x] 14. Add the basic interactive 3D preview (curved meshes, both presets, desktop/touch browser checks; BG-008/009 repaired)

- [ ] 15. Compare exterior styles (terrain, Continent Leipzig, fog of war) in the 215 mm high-density Pages preview — local builds, cross-variant invariants and Edge checks pass; deployment verification pending.
- [ ] 16. Increase map detail — deferred by user.
- [ ] 17. Tune labels — deferred by user.
- [ ] 18. Review/expand landmarks, including Völkerschlachtdenkmal and the football stadium — deferred by user.

## Notes

- Checkpoint 06 records all three 215 mm / 300 PPI exterior styles. Terrain
  validates 53 artifacts; ocean and fog validate 51 each. Shared city data,
  rasters, masks, labels, gore geometry and all city interior pixels agree;
  canonical wrap and pole checks pass. Edge checks cover the three styles,
  both modes, five overlays, camera/reset, mouse/touch controls, and rapid
  switching without moving the camera. See `demos/06-exterior-variants/`.

- Task 13 is a required human-action milestone and cannot be completed autonomously.
- [PHYSICAL_TEST.md](PHYSICAL_TEST.md) provides the pending measurement and assembly record; blank fields are not completion evidence.
- Remaining tasks are being implemented sequentially and committed as they are completed.
- 2026-09-10 audit found that the original 29 passing tests did not establish specification compliance. The quadrilateral gores, broken PDF loader, flat previews and hard-coded labels have been replaced. Checkpoints under `demos/` preserve the before/after evidence.
- The current physical sample is `demos/05-curved-gores/test-print-two-gores.pdf` for the confirmed **215 mm** final globe. Print at actual size; earlier samples are 300 mm.
- Hosted validation: [CI run 34529763078](https://github.com/ehonda/leipzig-globe/actions/runs/34529763078), commit `05382e0`, completed successfully on 2026-09-10.
- 2026-09-13: checkpoint 03 records two real clean source acquisitions and a
  validated September build. Parent and nested 215 mm legacy builds also
  validate; original caches remain unchanged. BG-006 is now the next software
  defect, so the print-quality milestone is not yet claimed complete.
- Checkpoint 04 closes BG-006/007: 7423 × 7522 source raster, correct Leipzig
  city-node identity (safely omitted for feature collision), and an inspected
  exact-size print sample. Isolated real map benchmark: 162.44 seconds,
  41.36 MB Municipal Map. Physical fit remains untested.
- 2026-09-13: the 184.62 mm old-ball and 215 mm target presets use equator-centred
  page splits. Each two-page Gore shares the configured 10 mm overlap equally
  around the equator; unsupported larger sizes fail instead of splitting unevenly.
- Checkpoint 05: both defaults now use the confirmed 215 mm diameter and
  equator-centred split. Both full builds validate 50 artifacts. Browser checks
  in installed Edge verify both modes/presets, overlays, camera/reset, mouse
  rotation/zoom, auto-rotation, touch drag/pinch and mobile control layout.
  The reset check found and repaired retained camera inertia (BG-009).
  Pages now tests, rebuilds and validates both presets on every main push.

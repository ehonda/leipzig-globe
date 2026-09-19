# Leipzig Globe Task Tracker

## Status

- [x] 1. Bootstrap the `uv` Python project (reviewed and corrected)
- [x] 2. Define configuration and artifact contracts
- [x] 3. Implement deterministic source acquisition (dated extract, immutable boundary mirror, two real clean acquisitions; BG-005)
- [x] 4. Derive the Municipal Map (all ten official districts; real-source benchmark and Osmium fixture verified)
- [x] 5. Render the clean Leipzig map (semantic label selection and selected source IDs verified; BG-007 repaired)
- [x] 6. Create the 2:1 Globe Texture (true both-axis source sampling, single downsample, allocation guards; BG-006 repaired)
- [x] 7. Generate SVG Gores (sinusoidal sampling, physical dimensions, overlap, outlines and alignment marks)
- [x] 8. Assemble the tiled A4 print PDF (calculated/equator-split layouts; separate two-axis calibration sheet; identifiers on every tile; printer-border clearance checked)
- [x] 9. Generate the Preview Set (six different spherical views; optional safety overlays)
- [x] 10. Emit the Build Report (input and artifact checksums, relative paths, dimensions and timings)
- [x] 11. Expose the end-to-end CLI (real offline build and validation completed)
- [x] 12. Add automated validation (144 hosted tests pass; local rendering and browser checks pass)
- [ ] 13. Perform the physical test-print milestone (blocked by human action)
- [x] 14. Add the basic interactive 3D preview (curved meshes, both presets, desktop/touch browser checks; BG-008/009 repaired)

- [x] 15. Compare exterior styles (terrain, Continent Leipzig, fog of war) in the 215 mm high-density Pages preview — full builds, cross-variant invariants, Edge checks and deployed assets verified.
- [x] 16. Increase map detail — paths and sports grounds; visual/print-scale/build validation and live deployment verified.
- [x] 17. Tune labels — 25 to 80 visible labels; natural proportions, preserved safety and documented omissions; deployed.
- [x] 18. Review/expand landmarks — six verified symbols, four full labels; two full-label omissions documented; before/current comparison deployed and verified.
- [x] 19. Clarify composite names, lakes and outer land cover — source/visual evidence, 144 hosted tests, all three print builds, browser checks and all 97 deployed files verified; live as `7103696`.
- [x] 20. End printed halves at the equator — zero-overlap defaults; persisted ocean production/test presets; both full builds validated and visually checked.

- 2026-09-20: equator mode now splits fitting Gores at the equator by default,
  including the 150 mm test print. `layout.split_fitting_gores_at_equator: false`
  restores whole fitting Gores without changing larger equator splits.

## Notes

- 2026-09-15: current prints are `output/equator-join/test-print-184-62mm-ocean/`
  (184.62 mm, 9 pages) and `output/equator-join/production-215mm-ocean/`
  (215 mm, 13 pages). Both use ocean / 300 PPI / high labels matching Pages
  revision `b8eec30`. Each validates 51 artifacts; all 12 joins per PDF were
  checked from actual clipping and image placement. PDFium renders confirm
  central upper/lower pages, identifiers and trim crosses. Production map,
  labels, texture and source data match the previous production build's hashes.
  The 30 print and 22 configuration/contract tests pass; Ruff and Black pass.
  Prior overlapping PDFs remain historical; physical acceptance is still pending.

- Checkpoint 09 is deployed at `b273fff`. Hosted CI passes all 136 tests; all
  97 published files match `build.json`, and live Edge verifies current/before/
  current switching and the deployed commit link. See
  `demos/09-detail-labels/deployment-check.json` and its README for run links.

- Checkpoint 08 refines the exterior styles with a violet border and halo,
  water-aware ocean shore and pale sage-grey fog. All 134 tests in the local
  working tree, Ruff, Black, full artifact/city/wrap/pole checks and Edge desktop/
  touch interactions pass. City source artifacts match checkpoint 06 byte for
  byte. Local builds include the separate calibration edits; see
  `demos/08-exterior-refinements/README.md` for that provenance distinction.

- Checkpoint 07 regenerates the designated 184.62 mm test print with a separate
  100 × 100 mm calibration sheet. Gore artwork and placement match the preceding
  PDF; guides and per-tile identifiers clear a 4.2 mm printer border. All 132 tests,
  Ruff and Black pass. Human calibration and assembly acceptance remain pending.

- Checkpoint 06 records all three 215 mm / 300 PPI exterior styles. Terrain
  validates 53 artifacts; ocean and fog validate 51 each. Shared city data,
  rasters, masks, labels, gore geometry and all city interior pixels agree;
  canonical wrap and pole checks pass. Edge checks cover the three styles,
  both modes, five overlays, camera/reset, mouse/touch controls, and rapid
  switching without moving the camera. See `demos/06-exterior-variants/`.
- Hosted verification for `60c5146`: [128 passing tests](https://github.com/ehonda/leipzig-globe/actions/runs/34786971603)
  and [successful Pages deployment](https://github.com/ehonda/leipzig-globe/actions/runs/34786971606).
  `demos/06-exterior-variants/deployment-check.json` verifies the exact live
  revision, three-option index and 16 published asset hashes.

- Task 13 is a required human-action milestone and cannot be completed autonomously.
- [PHYSICAL_TEST.md](PHYSICAL_TEST.md) provides the pending measurement and assembly record; blank fields are not completion evidence.
- Remaining tasks are being implemented sequentially and committed as they are completed.
- 2026-09-10 audit found that the original 29 passing tests did not establish specification compliance. The quadrilateral gores, broken PDF loader, flat previews and hard-coded labels have been replaced. Checkpoints under `demos/` preserve the before/after evidence.
- The current physical test target is **184.62 mm**, using
  `config/test-print-184-62mm-high-density.yaml`. The refreshed compact sample is
  `demos/07-print-calibration/test-print-three-gores.pdf`: one calibration sheet
  followed by two tiles containing three adjacent gores. The full test PDF is
  `output/print-calibration/test-print-184-62mm/leipzig-globe-print.pdf` (9 pages).
  The final globe remains **215 mm**; historical samples retain their original sizes.
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

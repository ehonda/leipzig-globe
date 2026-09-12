# Leipzig Globe Task Tracker

## Status

- [x] 1. Bootstrap the `uv` Python project (reviewed and corrected)
- [x] 2. Define configuration and artifact contracts
- [x] 3. Implement deterministic source acquisition (dated extract, immutable boundary mirror, two real clean acquisitions; BG-005)
- [x] 4. Derive the Municipal Map (all ten official districts; real-source benchmark and Osmium fixture verified)
- [ ] 5. Render the clean Leipzig map (reopened: same-named tourism information object displaces city label; BG-007)
- [ ] 6. Create the 2:1 Globe Texture (reopened: output dimensions pass, but source raster is horizontally upscaled; BG-006)
- [x] 7. Generate SVG Gores (sinusoidal sampling, physical dimensions, overlap, outlines and alignment marks)
- [x] 8. Assemble the tiled A4 print PDF (calculated two-row layout; dimensions and drawing operators checked)
- [x] 9. Generate the Preview Set (six different spherical views; optional safety overlays)
- [x] 10. Emit the Build Report (input and artifact checksums, relative paths, dimensions and timings)
- [x] 11. Expose the end-to-end CLI (real offline build and validation completed)
- [x] 12. Add automated validation (68 local tests pass; hosted offline-fixture workflow configured)
- [ ] 13. Perform the physical test-print milestone (blocked by human action)
- [x] 14. Add the basic interactive 3D preview (static Three.js viewer, generated WebP asset export, real gore assembly mode, mobile layout, and export geometry test)

## Notes

- Task 13 is a required human-action milestone and cannot be completed autonomously.
- Remaining tasks are being implemented sequentially and committed as they are completed.
- 2026-09-10 audit found that the original 29 passing tests did not establish specification compliance. The quadrilateral gores, broken PDF loader, flat previews and hard-coded labels have been replaced. Checkpoints under `demos/` preserve the before/after evidence.
- The physical sample is `demos/02-real-globe/test-print-two-gores.pdf` for a **300 mm** globe. Confirm the actual globe size and regenerate before judging fit; do not scale the PDF in the print dialog.
- Hosted validation: [CI run 34529763078](https://github.com/ehonda/leipzig-globe/actions/runs/34529763078), commit `05382e0`, completed successfully on 2026-09-10.
- 2026-09-13: checkpoint 03 records two real clean source acquisitions and a
  validated September build. Parent and nested 215 mm legacy builds also
  validate; original caches remain unchanged. BG-006 is now the next software
  defect, so the print-quality milestone is not yet claimed complete.

# Leipzig Globe Task Tracker

## Status

- [x] 1. Bootstrap the `uv` Python project (reviewed and corrected)
- [x] 2. Define configuration and artifact contracts
- [ ] 3. Implement deterministic source acquisition (reopened: rolling download is not a pinned release; BG-005)
- [x] 4. Derive the Municipal Map (all ten official districts; real-source benchmark and Osmium fixture verified)
- [x] 5. Render the clean Leipzig map (source labels, layer order, holes, collision and safety omissions)
- [x] 6. Create the 2:1 Globe Texture (circumference-based PPI, Zentrum anchor, pixel-exact seam rotation)
- [x] 7. Generate SVG Gores (sinusoidal sampling, physical dimensions, overlap, outlines and alignment marks)
- [x] 8. Assemble the tiled A4 print PDF (calculated two-row layout; dimensions and drawing operators checked)
- [x] 9. Generate the Preview Set (six different spherical views; optional safety overlays)
- [x] 10. Emit the Build Report (input and artifact checksums, relative paths, dimensions and timings)
- [x] 11. Expose the end-to-end CLI (real offline build and validation completed)
- [ ] 12. Add automated validation (46 local tests pass; CI fixture workflow added, first hosted run pending)
- [ ] 13. Perform the physical test-print milestone (blocked by human action)

## Notes

- Task 13 is a required human-action milestone and cannot be completed autonomously.
- Remaining tasks are being implemented sequentially and committed as they are completed.
- 2026-09-10 audit found that the original 29 passing tests did not establish specification compliance. The quadrilateral gores, broken PDF loader, flat previews and hard-coded labels have been replaced. Checkpoints under `demos/` preserve the before/after evidence.
- The physical sample is `demos/02-real-globe/test-print-two-gores.pdf` for a **300 mm** globe. Confirm the actual globe size and regenerate before judging fit; do not scale the PDF in the print dialog.

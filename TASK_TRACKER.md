# Leipzig Globe Task Tracker

## Status

- [x] 1. Bootstrap the `uv` Python project (reviewed and corrected)
- [x] 2. Define configuration and artifact contracts
- [x] 3. Implement deterministic source acquisition
- [ ] 4. Derive the Municipal Map (reopened: extraction used only the first official district)
- [ ] 5. Render the clean Leipzig map (reopened: label positions and layer rendering need repair)
- [ ] 6. Create the 2:1 Globe Texture
- [ ] 7. Generate SVG Gores
- [ ] 8. Assemble the tiled A4 print PDF
- [ ] 9. Generate the Preview Set
- [ ] 10. Emit the Build Report
- [ ] 11. Expose the end-to-end CLI
- [ ] 12. Add automated validation
- [ ] 13. Perform the physical test-print milestone (blocked by human action)

## Notes

- Task 13 is a required human-action milestone and cannot be completed autonomously.
- Remaining tasks are being implemented sequentially and committed as they are completed.
- 2026-09-10 audit: the existing 29 passing tests do not establish specification compliance. Gores are quadrilaterals, the PDF attempts to load SVG with a raster loader, and all six previews are flat texture copies. Tasks 6–12 remain open pending real implementations and meaningful validation.

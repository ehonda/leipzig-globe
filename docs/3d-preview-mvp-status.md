# 3D Preview MVP Status

## Implemented

- Static GitHub Pages-compatible viewer in `docs/`, with only relative asset URLs.
- Finished Globe mode: the generated equirectangular texture is rendered on an interactive sphere.
- Gore Assembly mode: one mesh per generated gore, textured from downsampled production gore PNGs.
- Preset selector populated from Python-exported configurations, allowing multiple independently generated globe variants in the same static site.
- Drag rotation, wheel/pinch zoom, auto-rotation, and responsive control layout.
- Deterministic Front, Back, North, South, and Reset camera controls.
- Independent nominal-seam, physical-cut-edge, overlap, equator, and pole safety-zone overlays.
- Python `export_web_preview()` and the `export-web-preview` CLI command export reduced WebP assets and a manifest containing the Python-derived spherical mesh and overlay geometry.
- Automated export contract coverage, including the first gore's equatorial seam coordinates.

## Intentionally Deferred

- Exploded gore view and adjustable explosion distance.
- Gore picking, highlighting, and metadata display.
- Opacity and wireframe/debug material controls.
- URL-controlled camera/debug presets.
- Screenshot or image export.
- Separate canonical-texture sampling mode within Gore Assembly; the MVP uses the actual generated gore images directly.
- Cross-browser automated visual-regression coverage (the Edge inspection script is opt-in).

## Regenerate Preview Assets

After a successful full build, run:

```powershell
uv run leipzig-globe export-web-preview --build-dir output --site-dir docs/assets --preset-id default
```

For local choices, export each validated build to the same `docs/assets/` directory with a distinct `--preset-id`, such as `globe-215mm-high-density`. The generated `presets.json` drives the selector. For hosted choices, also add the configuration to `scripts/build_pages.py`: Pages rebuilds and validates every listed preset from current code before deploying `output/pages-site/`. Tracked assets are inspection snapshots. See the repository README for publishing and `build.json` provenance.

## Checkpoint 04 asset refresh

Both presets use the pinned September sources and corrected renderer. The
300 mm preset was exported from `output/corrected-rendering`; the 215 mm /
300 PPI high-density preset from `output/corrected-215mm`. Both full builds
passed artifact validation. Their provenance reports are preserved under
`demos/04-corrected-rendering/`. Source rasters meet the final sampling demand
in both axes, and city labels no longer select same-named information signs.

The generated static views and default print page were visually inspected.
Live browser interaction is not newly verified by this asset refresh: the
browser-control tool failed before connection in this session. Existing
geometry/export unit tests are not a substitute for browser verification.

Checkpoint 04 exposed **BG-008**: Gore Assembly had one mesh segment across each
gore, producing an inward equatorial error of 5.37 mm at its 300 mm diameter.

## Checkpoint 05 — curved gores and 215 mm reference

BG-008 is repaired. Whole-triangle surface-error bounds, vertex UVs, seams,
overlaps and winding are tested for 4/12/24 gores and both gore orders. The new
215 mm reference surface error is below 0.04185 mm (0.000389283 radius).
The two presets now both use 215 mm, at 200 PPI / medium and 300 PPI / high density.

Installed Edge successfully loaded and exercised both modes and presets,
all five overlays, four camera views, Reset, mouse drag/wheel, auto-rotation,
touch drag, pinch zoom and the mobile control layout. The Reset check found
BG-009; camera shortcuts now clear pending inertia before setting their pose.
Run `uv run --with playwright scripts/check_browser.py --site output/pages-site`
after a complete Pages build. Screenshots and the result are in
`demos/05-curved-gores/`; `mobile.png` records the zoomed view after the pinch test.
In-app browser access remains unavailable due to its connection metadata error.

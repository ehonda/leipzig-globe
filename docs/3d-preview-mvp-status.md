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
- Automated browser visual-regression coverage.

## Regenerate Preview Assets

After a successful full build, run:

```powershell
uv run leipzig-globe export-web-preview --build-dir output --site-dir docs/assets --preset-id default
```

For additional choices, export each validated build to the same `docs/assets/` directory with a distinct `--preset-id`, such as `globe-215mm-high-density`. The generated `presets.json` drives the selector. Commit the generated `docs/assets/` files with the static viewer when publishing through GitHub Pages. The tracked GitHub Actions workflow deploys `docs/` on every push to `main`; configuration and publishing instructions are in the repository README.

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

Known open defect: **BG-008**. Gore Assembly has only one mesh segment across
each gore, making a faceted rather than sufficiently spherical surface (5.37 mm
inward at the default equator). Finished Globe and the printed gores use separate
geometry and are not affected. Task 14 is reopened pending cross-gore subdivision.

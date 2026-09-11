# 3D Preview MVP Status

## Implemented

- Static GitHub Pages-compatible viewer in `docs/`, with only relative asset URLs.
- Finished Globe mode: the generated equirectangular texture is rendered on an interactive sphere.
- Gore Assembly mode: one mesh per generated gore, textured from downsampled production gore PNGs.
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
- Automated browser visual-regression coverage and GitHub Pages deployment configuration.

## Regenerate Preview Assets

After a successful full build, run:

```powershell
uv run leipzig-globe export-web-preview --build-dir output --site-dir docs/assets
```

Commit the generated `docs/assets/` files with the static viewer when publishing through GitHub Pages. GitHub Pages should publish the `docs/` directory from the selected branch.
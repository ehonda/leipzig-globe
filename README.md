# Leipzig Globe

This project turns Leipzig's real municipal map into a printable globe texture,
sinusoidal gores, a tiled A4 PDF, and six spherical previews.

The repository also contains a static interactive preview under `docs/`. After
a successful build, generate its reduced browser assets with:

```bash
uv run leipzig-globe export-web-preview --build-dir output --site-dir docs/assets
```

Publish `docs/` with GitHub Pages to host the viewer. Its MVP scope and deferred
features are tracked in [docs/3d-preview-mvp-status.md](docs/3d-preview-mvp-status.md).

## Configure And Publish The 3D Preview

The checked-in [config/default.yaml](config/default.yaml) is the baseline. For
an alternate globe, create a small YAML override instead of changing that file.
Overrides are merged with the defaults, so they need contain only values that
should differ. The viewer's alternate preset is
[config/globe-215mm-high-density.yaml](config/globe-215mm-high-density.yaml):

```yaml
globe:
  diameter_mm: 215
  ppi: 300

layout:
  label_density: high
```

Useful settings include `globe.diameter_mm`, `globe.ppi`,
`globe.gore_count`, `globe.assembly_overlap_mm`, and the `layout` settings
`label_density` (`low`, `medium`, or `high`), `seam_offset_deg`,
`pole_safety_zone_mm`, `gore_order`, `curated_landmarks`, and
`show_railways`. Physical texture dimensions, gore geometry, and PDF tiling
are recalculated from the selected configuration. The validation step rejects
settings outside the supported physical and rendering limits.

To regenerate and publish the viewer with an override, use a separate build
directory, then replace the tracked static preview assets:

```powershell
uv run leipzig-globe build --config-path config/globe-215mm-high-density.yaml --output-dir output/globe-215mm-high-density
uv run leipzig-globe validate --output-dir output/globe-215mm-high-density
uv run leipzig-globe export-web-preview --build-dir output/globe-215mm-high-density --site-dir docs/assets --preset-id globe-215mm-high-density
git add config/globe-215mm-high-density.yaml docs/assets
git commit -m "Publish 215 mm high-density globe preview"
git push origin main
```

The GitHub Actions workflow in [.github/workflows/pages-deploy.yml](.github/workflows/pages-deploy.yml)
deploys `docs/` after every push to `main`. GitHub Pages is configured to use
that workflow, so no separate Pages action is needed after the push. The live
viewer is https://ehonda.github.io/leipzig-globe/. To offer multiple choices in
the selector, export each completed build to the same `docs/assets` directory
with a distinct `--preset-id`; the exporter updates `docs/assets/presets.json`.

See the tracked [visual checkpoints](demos/README.md), especially
[the globe gallery](demos/02-real-globe/globe-views.jpg) and
[two adjacent sample gores](demos/02-real-globe/test-print-two-gores.pdf).

## Create the demo image

From the repository root, run:

```bash
uv sync
uv run leipzig-globe fetch-data
uv run leipzig-globe build
uv run leipzig-globe validate
```

This generates a file at:

```text
output/leipzig-map.png
```

## What the demo shows

The generated map comes from the cached Saxony PBF clipped to all ten official
Leipzig districts. The same map supplies the texture, gores, PDF and previews.
It is useful for checking:

- land / water / road styling
- label density and placement
- pole-safety exclusion behavior
- seam-related label omission

## Notes

- Full-size artifacts live in gitignored `output/`; compact visual checkpoints
  and sample PDFs are tracked in `demos/`.
- The command uses the project’s default configuration from `config/default.yaml` and requires `osmium` on `PATH`.
- If you want to tweak the map look, modify `layout.label_density`, `layout.curated_landmarks`, or the `style` entries in the config before running the render command.

## Size and printing

The default is **300 mm diameter**, 12 gores, 200 PPI. The texture is
7422 × 3711 pixels. Each gore spans 471.24 mm pole to pole and 78.54 mm across
the equator before its 2 mm assembly overlap. That overlap tapers toward the
poles. The default PDF has 12 portrait A4 pages: two gores per pair of pages,
two vertical tiles, with 10 mm page overlap.

Change `globe.diameter_mm` in `config/default.yaml` or supply a partial YAML
override with `--config-path`. All physical dimensions and page tiles are
recalculated. If you measure the globe's equatorial circumference, divide it
by π to obtain the diameter. The final physical globe size is not yet known.

Print at **100% / actual size** and measure the 100 mm calibration line. Join
page tiles using matching crosses, then cut along the solid gore outline;
the dashed edge marks the nominal seam beneath the neighboring gore. Do not
use printer fitting or scaling to adapt to a different globe. A human must
test paper fit, glue behavior and label legibility before the full assembly.

## Reproducibility and performance

Builds are offline and verify the cached source manifest checksums before
processing. The Build Report records sources, all generated artifact hashes,
label omissions, physical dimensions, page count and extraction timings.
`validate` checks these files without rebuilding, including when a parent
output directory contains independent preset builds.

Fresh acquisition uses [config/source-lock.json](config/source-lock.json):
the dated Geofabrik Saxony extract for 2026-09-01 and an unchanged official
Leipzig boundary snapshot, with expected SHA-256 checksums and license metadata.
The boundary download is commit-addressed; its original official URL and
attribution remain recorded in the lock and [snapshot notes](data/sources/README.md).
Changed downloads fail before replacing any accepted file. Downloads are
streamed with a 400 MB per-file cap and failed partial files are removed.

The default cache is `.cache/sources-2026-09-01`. Preserve `.cache/` and its
original manifest for older checkpoints; use `--config-path config/legacy-cache.yaml`
to rebuild those inputs offline. An earlier copy at `.cache/pinned-2026-09`
also contains August inputs: the directory name alone does not establish provenance.
Changed source URLs or versions require a distinct cache, never relabeling old bytes.

To repeat the real two-clean-cache acceptance check (about 537 MB download),
choose two **empty or absent** directories:

```powershell
uv run scripts/verify_source_acquisition.py --first .cache/audit-new-1 --second .cache/audit-new-2
```

This records checksums, byte sizes, durations, identical manifests and unchanged
legacy inputs in `output/source-acquisition.json`. The script never clears caches.

On the documented Windows environment, real-source builds reach the map in
about one to two minutes, with Municipal Map GeoJSON well below 100 MB. Run:

```powershell
uv run scripts/benchmark_map.py
uv run pytest -q
uv run --with pymupdf scripts/save_checkpoint.py my-checkpoint
```

The benchmark produces `output/map-benchmark.json`. The checkpoint command
requires a completed, validated full build. See `MEMORY.md` for Windows
toolchain details and `TASK_TRACKER.md` for remaining work.

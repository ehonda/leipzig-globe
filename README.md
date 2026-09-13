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
should differ. The hosted viewer uses only the 215 mm high-density reference in
[config/globe-215mm-high-density.yaml](config/globe-215mm-high-density.yaml):

```yaml
globe:
  diameter_mm: 215
  ppi: 300

layout:
  label_density: high
  exterior: ocean
```

Useful settings include `globe.diameter_mm`, `globe.ppi`,
`globe.gore_count`, `globe.assembly_overlap_mm`, and the `layout` settings
`label_density` (`low`, `medium`, or `high`), `seam_offset_deg`,
`pole_safety_zone_mm`, `gore_order`, `curated_landmarks`, and
`show_railways`. Physical texture dimensions, gore geometry, and PDF tiling
are recalculated from the selected configuration. The validation step rejects
settings outside the supported physical and rendering limits.

`layout.exterior` selects `blank` (the CLI default), `terrain`, `ocean`, or `fog`.
The Pages selector compares **Surrounding terrain**, **Continent Leipzig**, and
**Fog of war**, all at 215 mm / 300 PPI / high label density. Switching keeps
the current camera and mode. Terrain uses real OSM roads, water and green space
within the existing municipal viewport, with a plum municipal outline and a
smooth fade at the texture wrap and poles. It is a cartographic map, not an
elevation model. Ocean and fog are decorative backgrounds outside the official
boundary. Leipzig's position, extent and label choices are shared by all three.

To inspect an override locally before publishing, use a separate build
directory and refresh the tracked preview snapshots:

```powershell
uv run leipzig-globe build --config-path config/globe-215mm-high-density.yaml --output-dir output/globe-215mm-high-density
uv run leipzig-globe validate --output-dir output/globe-215mm-high-density
uv run leipzig-globe export-web-preview --build-dir output/globe-215mm-high-density --site-dir docs/assets --preset-id globe-215mm-high-density
git add config/globe-215mm-high-density.yaml docs/assets
git commit -m "Publish 215 mm high-density globe preview"
git push origin main
```

The GitHub Actions workflow in [.github/workflows/pages-deploy.yml](.github/workflows/pages-deploy.yml)
rebuilds the site after every push to `main`. GitHub Pages is configured to use
that workflow, so no separate Pages action is needed after the push. The live
viewer is https://ehonda.github.io/leipzig-globe/. To offer multiple choices in
the selector, export each completed build to the same `docs/assets` directory
with a distinct `--preset-id`; the exporter updates `docs/assets/presets.json`.

The workflow runs checks, rebuilds **all three exterior variants** from the
pinned sources with the pushed code, validates them, and publishes a fresh
`output/pages-site/`. Only source downloads are cached; tracked `docs/assets/`
are local inspection snapshots. To add a hosted preset, also add its configuration
to `scripts/build_pages.py`. A failed check/build prevents publication.
`build.json` on the live site records the deployed commit, full build-report
links and file hashes. Asset URLs carry that commit to avoid stale cached meshes
or textures. Refresh an already open tab after deployment; it does not hot reload.
This follows GitHub's [custom Pages workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

To exercise the same build locally, run `uv run scripts/build_pages.py` with
new output directories (use `--output-dir` and `--site-dir` on subsequent runs).
Run `uv run --with playwright scripts/check_browser.py --site output/pages-site`
to verify the three variants in installed Edge; screenshots go to `output/browser-check`.

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

The confirmed final reference is **215 mm diameter**, 12 gores, 200 PPI. The texture is
5320 × 2660 pixels. Each gore spans 337.72 mm pole to pole and 56.29 mm across
the equator before its 2 mm assembly overlap. That overlap tapers toward the
poles. The default PDF has 12 portrait A4 pages: two gores per pair of pages,
two vertical tiles, with 10 mm page overlap centred on the equator. The high-density
preset keeps the same 215 mm diameter at 300 PPI with high label density.

Change `globe.diameter_mm` in `config/default.yaml` or supply a partial YAML
override with `--config-path`. All physical dimensions and page tiles are
recalculated. If you measure the globe's equatorial circumference, divide it
by π to obtain the diameter. Set `layout.vertical_tile_mode: equator` to centre
the page-tile overlap on the equator whenever a Gore needs two pages. Gores
that fit on one page remain whole; generation stops with a size-specific error
if a half-Gore plus half the overlap cannot fit the printable A4 height.

Print at **100% / actual size** and measure the 100 mm calibration line. Join
page tiles using matching crosses, then cut along the solid gore outline;
the dashed edge marks the nominal seam beneath the neighboring gore. Do not
use printer fitting or scaling to adapt to a different globe. A human must
test paper fit, glue behavior and label legibility before the full assembly.
Use [PHYSICAL_TEST.md](PHYSICAL_TEST.md) to record that required milestone.

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

The benchmark uses its own `output/map-benchmark/` directory, including
`map-benchmark.json`, so it does not overwrite an existing full build. Use
`--output-dir` or `--config-path` for a separate measurement. The checkpoint command
requires a completed, validated full build. See `MEMORY.md` for Windows
toolchain details and `TASK_TRACKER.md` for remaining work.

## Rendering resolution and label provenance

The metric source raster is sized for the final World Layout in **both** axes,
then downsampled once. Texture generation rejects undersized inputs rather
than declaring an enlarged image to be high-resolution. At the default size,
the texture is 5320 × 2660 pixels; the source's metric aspect ratio determines
its larger dimensions, recorded in the Build Report.
The source and scaled intermediate each have a 100-megapixel allocation cap;
large diameter/PPI/layout combinations may require reducing PPI or layout scale.
The report's `physical.map_sampling` records the actual sampling dimensions
and source-detail PPI; `validate` compares those dimensions with the files.

Label metadata records selected source IDs and tags, including for omissions.
Geographic place nodes take priority over same-named signs, while historic
landmarks and actual attractions beat transport stops or information boards.
The correct Leipzig city node is `n21687149`. In the 300 mm checkpoint 04 build,
its label is omitted for feature collision instead of being placed at a
same-named information sign. This is a reported cartographic omission, not a
license to move the label to an unrelated place.

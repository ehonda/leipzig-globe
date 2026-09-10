# Leipzig Globe

This project turns Leipzig's real municipal map into a printable globe texture,
sinusoidal gores, a tiled A4 PDF, and six spherical previews.

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
`validate` checks these files without rebuilding. **Fresh-cache acquisition
is not yet release-pinned**; [BG-005](BUGS.md) tracks this remaining defect.
Keep the current `.cache/` and its manifest to reproduce these checkpoints.

On the documented Windows environment, real-source builds reach the map in
about one to two minutes, with Municipal Map GeoJSON well below 100 MB. Run:

```powershell
$env:PATH = "$env:LOCALAPPDATA\osmium-tool\Library\bin;$env:PATH"
uv run scripts/benchmark_map.py
uv run pytest -q
uv run --with pymupdf scripts/save_checkpoint.py my-checkpoint
```

The benchmark produces `output/map-benchmark.json`. The checkpoint command
requires a completed, validated full build. See `MEMORY.md` for Windows
toolchain details and `TASK_TRACKER.md` for remaining work.

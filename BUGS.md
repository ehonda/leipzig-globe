# Leipzig Globe Bug Backlog

This backlog records verified defects and integration gaps. It defines the
required repair and acceptance criteria for each bug.

## BG-001: Clean map renderer uses placeholder geometry

- **Related task:** [Task 5: Render the clean Leipzig map](IMPLEMENTATION_TASKS.md#5-render-the-clean-leipzig-map)
- **Affected artifact:** `output/demo-map.png`
- **Observed behavior:** The map contains abstract polygons and broad, straight
  road bands instead of Leipzig municipal geometry.
- **Root cause:** `render_clean_map` creates hard-coded land, water, roads, and
  labels; it neither accepts nor renders the Task 4 Municipal Map dataset.
- **Required fix:** Render styled roads, waterways, parks, railways, districts,
  and configured landmarks from the clipped municipal GeoJSON. Preserve the
  existing label-collision, pole-safety, and gore-seam omission reporting.

**Done when:** Fixed fixture geometry produces recognizably data-driven map
output, and tests prove the renderer uses supplied municipal features rather
than placeholder drawing commands.

## BG-002: Globe texture is independently drawn, not transformed from the map

- **Related task:** [Task 6: Create the 2:1 Globe Texture](IMPLEMENTATION_TASKS.md#6-create-the-21-globe-texture)
- **Affected artifact:** `output/leipzig-texture.png`
- **Observed behavior:** The texture is unrelated to the clean-map artifact,
  so no real map content can survive into gore or preview outputs.
- **Root cause:** `generate_globe_texture` creates a second hard-coded image
  instead of transforming the rendered Municipal Map.
- **Required fix:** Transform the rendered map into the configured 2:1
  equirectangular texture, apply the non-uniform World Layout scale, center
  Leipzig Zentrum at the equator, and rotate only longitudinal placement for
  the configured seam offset.

**Done when:** The texture has exactly a 2:1 aspect ratio, derives visibly from
the rendered map, and seam-offset changes rotate its content without changing
the source-map pixels.

## BG-003: Offline data stages are disconnected from `build`

- **Related tasks:** [Task 4: Derive the Municipal Map](IMPLEMENTATION_TASKS.md#4-derive-the-municipal-map), [Task 5: Render the clean Leipzig map](IMPLEMENTATION_TASKS.md#5-render-the-clean-leipzig-map), and [Task 11: Expose the end-to-end CLI](IMPLEMENTATION_TASKS.md#11-expose-the-end-to-end-cli)
- **Affected workflow:** `uv run leipzig-globe build`
- **Observed behavior:** The build path generates synthetic artifacts without
  reading the cached OSM PBF, official boundary, or derived municipal GeoJSON.
- **Root cause:** `build_artifacts` calls placeholder rendering functions but
  does not call `derive_municipal_map_from_sources` or pass the resulting data
  to the renderer and texture stages.
- **Required fix:** Wire the offline build sequence as cached sources ->
  municipal map -> clean map -> globe texture -> gores, PDF, previews, and
  report. Record source-derived artifact paths and provenance in the report.

**Done when:** An offline fixture build proves every downstream artifact is
derived from the same Municipal Map and fails clearly when required cached
sources are missing.

## BG-004: Municipal Map derivation does not finish in a practical time

- **Related tasks:** [Task 4: Derive the Municipal Map](IMPLEMENTATION_TASKS.md#4-derive-the-municipal-map), [Task 5: Render the clean Leipzig map](IMPLEMENTATION_TASKS.md#5-render-the-clean-leipzig-map), and [Task 11: Expose the end-to-end CLI](IMPLEMENTATION_TASKS.md#11-expose-the-end-to-end-cli)
- **Affected workflow:** `uv run leipzig-globe build`
- **Observed behavior:** A real cached Leipzig build does not reach
  `output/leipzig-map.png` in a practical time. The 255 MB Saxony PBF first
  produced a 534 MB temporary GeoJSON; a boundary-first extraction attempt
  still produced a 753 MB partial Municipal Map before the build was stopped.
- **Root cause:** The derivation pipeline materializes too many OSM features
  and then asks GeoPandas to load, reproject, intersect, validate, and write
  them as GeoJSON. The pipeline lacks a bounded Leipzig-only data path and a
  performance acceptance check.
- **Required fix:** Profile feature counts and tag classes after each Osmium
  stage; reduce the extract to the exact feature classes and Leipzig extent
  needed by the renderer before GeoPandas loads it; avoid writing oversized
  intermediate GeoJSON when a smaller clipped format or streamed operation is
  available. Add a repeatable performance test or benchmark for the cached
  real-source build on the supported Windows environment.

**Done when:** A populated-cache build produces `output/leipzig-map.png` from
the real sources within five minutes on the documented Windows environment,
without leaving a temporary or Municipal Map GeoJSON larger than 100 MB, and
the measured feature counts and duration are recorded in the Build Report or
benchmark output.

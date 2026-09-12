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

## 2026-09-10 audit additions

- BG-001 is reopened: source geometry is used, but labels still use invented pixel positions; polygon holes are filled, drawing order follows OSM input order, and several road classes are misclassified.
- BG-002 is reopened: missing source images still trigger synthetic drawing; texture resolution uses globe diameter instead of circumference and can have an odd width; Zentrum is not explicitly anchored at the equator.
- BG-004 also includes a coverage defect: Osmium uses only the first GeoJSON feature, so the ten-feature district boundary must be dissolved before extraction. Arbitrary OSM tags become a wide, sparse GeoPandas table, inflating the subsequent GeoJSON. Use a fixed tag schema and profile spatial predicates as well as file I/O.
- Tasks 7–9 contain placeholders, despite callable functions: four-point gore outlines, no spherical resampling, a PDF raster loader given SVG paths, calibration lengths in points rather than millimetres, and six identical flat previews.

These rendering/printing audit findings are repaired in checkpoint 02. The
acquisition finding below was subsequently repaired in checkpoint 03.

## BG-005: Fresh source acquisition is not pinned to reproducible releases

- **Related task:** Task 3.
- **Observed behavior:** a populated cache is checksum-verified, including at
  build time, but a new cache downloads `sachsen-latest.osm.pbf` and accepts its
  newly calculated checksum. Two clean caches populated on different dates can
  therefore contain different inputs despite identical repository revisions.
- **Evidence:** `DEFAULT_OSM_PBF_URL`, `fetch_data_cache`, and CLI source metadata
  still use a rolling URL and the version label `sachsen-latest`. The existing
  cache's exact hashes are preserved in checkpoint reports. Geofabrik provides
  [dated extracts](https://download.geofabrik.de/europe/germany/sachsen.html).
- **Required fix:** select a dated, obtainable extract and a pinned official
  boundary snapshot, record expected checksums and precise license/version
  metadata in a tracked source lock, and verify new downloads before accepting
  them. Preserve the existing cache and its provenance when introducing a new
  source lock; never relabel old bytes as a new source version.

**Done when:** two clean cache acquisitions using the tracked source lock yield
the same verified inputs, changed upstream bytes fail clearly, and the existing
checkpoint cache remains usable offline. Tests must cover malformed manifests,
checksum mismatches and changed source URLs as well as successful acquisition.

2026-09-13 validation: two independent clean downloads took 128.178 and
120.575 seconds. Both produced the same 267,843,019-byte September PBF and
522,791-byte official boundary, matching the tracked lock and identical cache
manifests. Original August inputs remain unchanged and their existing full
build validates offline. The boundary mirror preserves exact source bytes
at commit `9047147d20aca1d1a46d5b372fc6d1ac018b208f`; official-host Python
downloads repeatedly reset, although a curl header request succeeds.

## BG-006: Source-map raster is upscaled below the declared effective PPI

- **Related task:** Task 6 (reopened).
- **Evidence:** the default checkpoint 02 source map is 3,662 × 3,711 pixels,
  then stretched horizontally to 7,422 × 3,711. Its horizontal source detail
  is about 99 PPI, not 200 PPI across a 300 mm globe's circumference.
- **Required fix:** budget the metric-aspect-ratio source raster for the final
  sampling density in both axes, including World Layout scaling. Preserve
  physical label/stroke sizes and seam/pole safety calculations when changing
  source resolution. Avoid an intermediate downsample followed by enlargement.
  Bound allocation and report effective source sampling, not just PNG DPI tags.

**Done when:** regression tests verify neither axis is upsampled in the supported
layout, scale changes retain the configured sampling density, and a real build
produces an inspected checkpoint without breaching the documented resource budget.

2026-09-13 validation (checkpoint 04): source raster 7423 × 7522,
texture 7422 × 3711, source sampling 200.05 / 405.44 PPI in x/y before the
single final downsample. World Layout scale changes are tested in both axes;
undersized inputs fail, and source/scaled allocations have 100 MP limits.
Font/stroke scaling and final-coordinate label safety use the correct source
and texture pixel scales. The isolated map benchmark takes 162.44 seconds
with the same map-image hash as the full build; Municipal Map remains 41.36 MB.

## BG-007: Generic tourism objects outrank the Leipzig city label

- **Related task:** Task 5 (reopened).
- **Evidence:** checkpoint 03 places the Leipzig label near map pixel
  (2119, 895), while its city node and equatorial centre are (1831, 1855.5).
  The selected OSM node `n670225761` is `tourism=information`, about 6.6 km
  north-east of the actual `place=city` node `n21687149`.
- **Root cause:** every tourism value gets a better name-candidate rank than
  `place=city`. The ranking intended to distinguish landmarks from bus stops
  instead selects a same-named information object over the city itself.
- **Required fix:** choose name candidates according to entity semantics:
  geographic place labels must prefer their place nodes, while actual curated
  landmarks must still beat same-named transport stops or information signs.
  Record selected source IDs/tags in label metadata so this can be audited.

**Done when:** deterministic mixed-name fixtures retain the right city and
landmark identities regardless of input ordering, and a new real checkpoint
anchors Leipzig to its actual city node (or explicitly reports safe omission).

2026-09-13 validation (checkpoint 04): place nodes outrank same-named tourism
objects; actual historic landmarks/attractions outrank signs and stops, with
stable source-ID/geometry tie breaks. Mixed-name fixtures pass in both input
orders. The real default build selects city node `n21687149` at map centre
(3711.5, 3761), and explicitly omits its label for feature collision. Visible
and omitted labels retain source IDs/tags; visible labels also record final
texture bounding boxes. Labels outside a scaled/cropped map are not reported
as rendered. The six-view gallery and PDF page were inspected.

## BG-008: Browser gore meshes are flat across each gore

- **Related task:** Task 14 (reopened).
- **Evidence:** the exported strip has 120 vertical segments but only one
  segment across the gore. Both edge vertices lie on the unit sphere, while
  their equatorial midpoint has radius 0.9641789 in the default preset — an
  inward error of 5.37 mm at a 300 mm globe diameter. `docs/globe.js` uses
  this geometry directly; checking the seam vertices alone misses the defect.
- **Required fix:** subdivide across the gore as well as along it, mapping
  every interior point through the authoritative paper-to-sphere transform
  with corresponding gore-image UVs. Keep cut/seam/overlap alignment and both
  presets intact. Regenerate the browser manifests and verify the actual view
  when browser tooling is available.

**Done when:** tests check triangle interiors, not just boundary vertices, for
4-, 12- and 24-gore configurations; maximum radial error stays below 0.001 of
the sphere radius (subpixel at an 800-pixel globe diameter), while UVs and
adjacent seam positions match the printed gore geometry.

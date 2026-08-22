# Leipzig Globe MVP Implementation Tasks

This backlog implements the confirmed Leipzig-only MVP. It assumes a default
300 mm globe but derives all dimensions and page layouts from configuration.

## 1. Bootstrap the `uv` Python project

- Create a `pyproject.toml`, `uv.lock`, Python package, and test layout.
- Add runtime dependencies for geospatial processing, raster rendering, SVG
  generation, PDF assembly, YAML configuration, and image previews.
- Add developer tooling for tests, linting, and formatting, all run through
  `uv`.
- Document `osmium` as a required system dependency and verify it before data
  processing.

**Done when:** `uv run` can invoke the package CLI and `uv run pytest` executes
an initially empty test suite.

## 2. Define configuration and artifact contracts

- Add a versioned default YAML configuration for a 300 mm, 12-gore, A4 build.
- Model globe diameter, gore count, assembly overlap, seam offset, PPI,
  non-uniform World Layout scale, pole safety zone, print margins, and tile
  overlap as validated settings.
- Define output paths for the Globe Texture, Gores, print PDF, Preview Set, and
  Build Report.
- Keep the application Leipzig-only; reject unsupported city configuration.

**Done when:** invalid physical or layout settings produce actionable CLI errors
before data processing starts.

## 3. Implement deterministic source acquisition

- Implement a `fetch-data` command that downloads the pinned Geofabrik Saxony
  OSM PBF and an official Leipzig Municipal Boundary source into a gitignored
  local cache.
- Store URLs, source versions or dates, checksums, and license metadata in a
  source manifest.
- Verify checksums before accepting cached or newly downloaded inputs.
- Make subsequent build stages offline-only.

**Done when:** a clean cache can be populated reproducibly and a checksum
mismatch fails the command.

## 4. Derive the Municipal Map

- Use `osmium` to extract relevant OSM features from the cached PBF.
- Load the official Municipal Boundary and clip roads, waterways, parks,
  railways, district data, and configured landmarks to it.
- Normalize all geometry into one metric working CRS appropriate to Leipzig.
- Produce an inspectable intermediate geospatial dataset for later stages.

**Done when:** no retained feature falls outside the Municipal Boundary and the
intermediate data can be regenerated without network access.

## 5. Render the clean Leipzig map

- Build a styled raster renderer with off-white land, muted blue water,
  restrained green parks, charcoal major roads, subdued secondary roads, and
  optional subtle railways.
- Render district labels and a small configuration-defined set of Curated
  Landmark labels in German.
- Suppress labels that collide with features, other labels, Gore seams, or the
  Pole Safety Zone; record omissions in the Build Report.
- Make style values and label density configurable.

**Done when:** the renderer emits a map image and a structured list of omitted
labels from fixed input data.

## 6. Create the 2:1 Globe Texture

- Transform the rendered Municipal Map into a 2:1 equirectangular Globe
  Texture using the configured non-uniform World Layout scale.
- Place Leipzig Zentrum prominently at the equator and arrange the outskirts
  toward artificial poles.
- Apply the configured Seam Offset without changing the underlying Municipal
  Map.
- Emit a high-resolution PNG at the configured effective PPI, defaulting to
  200 PPI for the configured physical size.

**Done when:** the texture has exactly a 2:1 pixel aspect ratio and changing
the seam offset only rotates its longitudinal placement.

## 7. Generate SVG Gores

- Generate an equal count of classic pole-to-pole Gores with a symmetric
  sinusoidal outline whose width follows $\cos(\text{latitude})$.
- Sample the Globe Texture into each Gore while preserving the configured gore
  order and seam alignment.
- Apply Assembly Overlap to one long edge and add cut outlines, numbering,
  optional centerlines, and alignment marks.
- Produce one SVG per Gore plus a machine-readable geometry manifest.

**Done when:** all 12 default Gores are complete, adjacent images align at their
edges, and the calculated equatorial widths match the configured circumference.

## 8. Assemble the tiled A4 print PDF

- Compute Page Tiles dynamically from physical dimensions, paper size,
  configurable printable margin, and tile overlap.
- At the default size, support the expected four vertical rows and two Gores per
  row where they fit; do not hard-code that arrangement.
- Include page identifiers, tile registration marks, a 100 mm calibration line,
  cut lines, Gore identifiers, and OSM attribution in each page's outer margin.
- Prevent automatic fitting or rescaling in the PDF metadata and instructions.

**Done when:** the PDF dimensions are exact, every page has a calibration mark,
and all Gore coverage is represented by one or more aligned Page Tiles.

## 9. Generate the Preview Set

- Render the Globe Texture onto a spherical mesh and create static front, back,
  left, right, north-pole, and south-pole images.
- Add optional non-printing seam and pole-safety overlays for inspection.
- Store preview metadata that links each viewpoint to the configuration and
  source manifest used to produce it.

**Done when:** all six expected viewpoint images are generated from the same
Globe Texture used for the Gores.

## 10. Emit the Build Report

- Write a machine-readable report containing configuration, source provenance,
  checksums, generated artifact paths, physical dimensions, tile counts, and
  omitted labels.
- Include full OpenStreetMap attribution and the official-boundary source
  attribution.

**Done when:** the report lets a later build be traced to its exact inputs and
configuration.

## 11. Expose the end-to-end CLI

- Provide `fetch-data`, `build`, and `validate` commands.
- Make `build` run all offline stages in dependency order and write outputs into
  a chosen directory without modifying cached source data.
- Make `validate` check an existing output directory without rebuilding it.
- Print concise next actions and failure locations for expected error cases.

**Done when:** the documented default commands produce a complete Print Set
from a populated cache.

## 12. Add automated validation

- Test configuration validation, source checksum enforcement, geometry math,
  2:1 texture dimensions, gore count and outlines, physical PDF dimensions,
  page-tile continuity, calibration marks, attribution, and declared artifacts.
- Add a small deterministic fixture dataset so tests do not fetch external data.
- Run the end-to-end build on the fixture in CI.

**Done when:** the suite catches malformed source manifests, broken gore
coverage, missing output artifacts, and changed physical dimensions.

## 13. Perform the physical test-print milestone

- Produce two or three adjacent default-size Gores and their needed Page Tiles.
- Print at 100% scale, measure the calibration line, and assemble the sample on
  a representative sphere.
- Record observed fit, overlap behavior, seam alignment, label legibility, and
  any correction required for paper stretch or glue shrinkage.

**Done when:** the observations are documented as follow-up issues or accepted
as the baseline for a complete physical build.

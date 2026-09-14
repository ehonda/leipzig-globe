# Leipzig Globe MVP Implementation Tasks

This backlog implements the confirmed Leipzig-only MVP. It assumes a default
215 mm globe (confirmed final size on 2026-09-13) but derives all dimensions
and page layouts from configuration.

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

- Add a versioned default YAML configuration for a 215 mm, 12-gore, A4 build.
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
- At the default size, support the calculated two vertical rows and two Gores per
  row where they fit; do not hard-code that arrangement.

  Confirmed 2026-09-10: pole-to-pole length is half the circumference, so a
  300 mm globe needs 471.24 mm Gores and two portrait A4 Page Tiles vertically.
  Recalculate the layout for other diameters, margins, and overlaps.
  The confirmed 215 mm reference uses 337.72 mm Gores, also two per pair of A4
  pages, with the page overlap centred on the equator.
- Support an optional equator split for Gores that need two pages. Centre the
  configured page overlap on the equator, keep Gores that fit on one page whole,
  and reject sizes whose half-Gores do not fit the printable page height.
- Include page identifiers, tile registration marks, cut lines, Gore identifiers
  on every tile, and OSM attribution. Keep guides and identifiers inside a
  4.2 mm printer border without changing Gore dimensions or overlap.
- Start the PDF with a separate A4 calibration sheet containing an exact
  100 × 100 mm square, safely inset from the edges, for measurement in both axes.
  User revision 2026-09-14: this replaces the ruler repeated on every page.
- Prevent automatic fitting or rescaling in the PDF metadata and instructions.

**Done when:** the PDF and calibration-square dimensions are exact, the first
page checks both axes, every Gore tile has a visible identifier, and all Gore
coverage is represented by one or more aligned Page Tiles.

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
- Print at 100% scale, measure both axes of the calibration square, and assemble the sample on
  a representative sphere.
- Record observed fit, overlap behavior, seam alignment, label legibility, and
  any correction required for paper stretch or glue shrinkage.

**Done when:** the observations are documented as follow-up issues or accepted
as the baseline for a complete physical build.

## 14. Add the basic interactive 3D preview

- Export reduced WebP versions of the canonical texture and actual generated
  gore images, together with a browser manifest derived from print geometry.
- Provide a static Three.js viewer under `docs/`, suitable for GitHub Pages.
- Support Finished Globe and Gore Assembly modes, mouse/touch rotation, zoom,
  auto-rotation, camera shortcuts, and nominal-seam, cut-edge, overlap,
  equator, and pole safety-zone overlays.
- Keep exploded view, gore selection, metadata panels, URL state, and export
  functions outside this bounded MVP.
- Maintain an explicit status document describing implemented and deferred
  viewer functionality and the asset-regeneration command.

**Done when:** a completed build can export all browser assets, the static
viewer loads both modes from only those assets, and the export has automated
geometry coverage.

## 15. Compare treatments outside the municipal boundary

- Build three exterior styles: real surrounding OSM geography with a visible
  municipal outline and smooth wrap/poles; ocean around "Continent Leipzig";
  and unexplored terrain represented by fog of war.
- Preserve municipal clipping, all city areas, map placement, label selection,
  source sampling density, and physical gore geometry across variants.
- Keep surrounding features in a separate bounded dataset with source provenance;
  never substitute invented geography for real context.
- Generate canonical textures and matching gores, expose a style selector in
  Pages for the 215 mm / 300 PPI / high-label-density reference only, and retain
  camera and preview mode when switching styles.
- Validate city preservation, contextual feature placement, wrap/pole continuity,
  full builds and browser operation. Record a visual checkpoint.
- Refinement requested 2026-09-14: distinguish the terrain boundary from transport
  lines with a violet border and light halo; soften the ocean coast while opening
  the pale shoreline at water crossings; harmonize fog with the map's paper and
  sage palette. Rebuild and verify all three styles before publishing.

**Done when:** all three styles can be compared in the deployed Pages preview,
with validated matching print artifacts and recorded visual evidence.

## 16. Increase map detail

- Review additional feature classes and visual detail at the 215 mm print scale.
- Compare readability, density and build cost before selecting changes.

**Done when:** agreed detail improvements have visual and print-scale validation.
Authorized 2026-09-14: subdued walking/cycling paths, tracks/steps and sports
grounds; retain the 215 mm reference and bounded extraction. Record paired
print-scale crops and build cost against the last exterior refinement.

## 17. Tune label selection and placement

- Review visible and omitted labels, priorities, collisions and seam/pole safety.
- Agree which labels matter before adjusting selection or placement rules.

**Done when:** the agreed label set is rendered or omissions are explained with
source identity and placement evidence. Authorized 2026-09-14: retain the
configured place/landmark set, compensate text for unequal world-layout axes,
try wrapped labels and nearby placements, and preserve seam/pole/collision safety.

## 18. Review and expand landmarks

- Investigate why the configured Völkerschlachtdenkmal is absent from the preview;
  use the build's omission report to distinguish missing data from unsafe placement.
- Consider the football stadium and research other candidate Leipzig landmarks.
- Agree candidates and validate feature identity, symbol/label rendering and fit.

**Done when:** agreed landmarks are visible and verified against their real
locations. Authorized 2026-09-14: add Red Bull Arena, Nikolaikirche and Neues
Rathaus alongside the existing landmarks, with source-anchored symbols and
auditable placement/omission evidence. Compare before/current in Pages using
one frozen recent baseline with bounded assets and no historical rebuilds.

## 19. Clarify composite names, lakes and outer land cover

- Authorized 2026-09-14: retain composite place labels instead of nearby
  component names, including Böhlitz-Ehrenberg and Dölitz-Dösen.
- Add source-identified lake names where the full label fits inside visible
  water, keeping label, road, seam and pole safety.
- Investigate sparse southwestern, eastern and northern areas in the pinned
  source data. Render agricultural, scrub and developed land distinctly.
- Compare against the previous live version with one bounded Before snapshot.

**Done when:** source evidence and regional comparisons are recorded, all three
styles and print artifacts validate, and the committed changes pass hosted
tests and appear in the deployed Pages preview.

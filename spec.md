# Leipzig Globe — Initial Design Spec

## Goal

Create a printable map of Leipzig that can be applied to a physical globe, replacing the normal world map.

The output should be suitable for a DIY build using a blank or repurposed globe, with the map printed as traditional globe **gores** (long tapered segments) and glued onto the sphere.

## Initial Target

- Globe diameter: configurable, initially assume **25–30 cm**
- Number of gores: **12**
- Gore width: 30° longitude equivalent
- Map source: Leipzig city map / OpenStreetMap / official Leipzig open geodata
- Primary output:
  - print-ready **PDF**
  - optionally SVG/PNG intermediates
- Paper:
  - thin printable paper preferred
  - individual gores may span multiple A4 pages if necessary

## Design Concept

Treat Leipzig as a fictional spherical world ("Planet Leipzig"), rather than attempting to preserve a geographically meaningful globe projection.

The complete Leipzig municipal area should be transformed into a rectangular texture and then projected onto a sphere.

Preferred layout:

- recognizable / dense urban areas near the globe's equator
- less important outskirts toward the artificial poles
- Leipzig city centre positioned prominently
- avoid important labels close to poles because distortion becomes extreme
- preserve approximate neighborhood relationships where practical

Exact geographic accuracy is secondary to:

1. recognizability
2. visual quality
3. readable labels
4. clean assembly

## Pipeline

Implement a reproducible pipeline:

```text
map data
  ↓
render Leipzig map
  ↓
crop / simplify / style
  ↓
create 2:1 equirectangular texture
  ↓
transform texture into 12 globe gores
  ↓
add cut / alignment guides
  ↓
layout for printing
  ↓
PDF
```

## Map Rendering

The renderer should support configurable styling.

Initial style:

- light / neutral background
- major roads clearly visible
- secondary roads visible but subdued
- waterways and lakes distinct
- parks / green areas visible
- railway lines optional
- neighborhood / district names
- selected landmarks optional
- no unnecessary POI clutter

Important labels should remain legible after printing on a ~25–30 cm sphere.

Prefer vector rendering where practical.

## Globe Texture

Generate a **2:1 equirectangular source texture**.

Configurable parameters should include:

- map bounding box
- map rotation
- city-centre position
- horizontal scaling
- vertical scaling
- map styling
- label density
- artificial north/south pole locations

The source texture does not need to preserve a conventional map projection.

## Gore Generation

Generate **12 equal globe gores** from the source texture.

Requirements:

- correct spherical taper toward both poles
- small configurable overlap between neighboring gores
- optional centerline
- optional gore numbering
- optional alignment marks
- clear cut outline
- optional trim / bleed area

Example numbering:

```text
Gore 01
Gore 02
...
Gore 12
```

Adjacent gores should make alignment obvious during assembly.

## Print Layout

Generate a print-ready PDF for a configurable physical globe diameter.

Configuration:

```yaml
globe_diameter_mm: 300
gore_count: 12
paper_size: A4
overlap_mm: 2
print_scale: 1.0
```

Requirements:

- exact physical dimensions
- no automatic printer scaling assumed
- include a calibration ruler / 100 mm test line
- optionally tile long gores across multiple pages
- provide clear page-to-page alignment marks where tiling is required

## Outputs

Recommended project outputs:

```text
output/
├── leipzig-texture.svg
├── leipzig-texture.png
├── gores/
│   ├── gore-01.svg
│   ├── gore-02.svg
│   └── ...
├── leipzig-globe-print.pdf
└── preview/
    └── globe-preview.png
```

## Preview / Validation

Before printing, generate a rendered 3D preview of the globe texture.

The preview should help detect:

- distorted important areas
- labels near gore seams
- labels near poles
- badly positioned seams
- excessive map density
- discontinuities between adjacent gores

Ideally provide an interactive or rotatable preview, but a set of rendered viewpoints is sufficient initially.

## Seam Placement

Avoid placing gore seams through highly recognizable areas where possible.

Prefer seams through:

- parks
- lakes
- low-density outskirts
- industrial areas
- other visually forgiving regions

Provide a configurable longitudinal offset so seam placement can be optimized without changing the underlying map.

## Implementation Preferences

Prefer a scriptable, reproducible workflow suitable for a coding agent.

Possible stack:

- Python
- GeoPandas / Shapely / pyproj for geodata
- OpenStreetMap data via OSMnx or downloaded extracts
- SVG generation for vector outputs
- Pillow / CairoSVG as needed
- matplotlib or custom geometry for previews
- ReportLab / SVG-to-PDF tooling for final print layout

Avoid workflows that require manual GUI editing for normal iteration.

## Configuration

Keep visual and physical parameters in a config file, e.g.:

```yaml
globe:
  diameter_mm: 300
  gore_count: 12
  overlap_mm: 2

map:
  center: leipzig
  rotation_deg: 0
  label_density: medium
  style: clean

print:
  paper: A4
  calibration_mark: true
  page_alignment_marks: true
```

## MVP

The first usable version should:

1. obtain suitable Leipzig map data
2. render a clean city map
3. transform it into a 2:1 spherical texture
4. generate 12 correctly shaped gores
5. size them for a 300 mm globe
6. produce a tiled A4 PDF
7. include cut lines, overlap, numbering, and calibration marks
8. generate a visual globe preview

## Later Improvements

Potential follow-ups:

- alternative map styles
- vintage / historical Leipzig map
- custom landmarks and icons
- manually optimized label placement
- custom seam placement
- configurable focus on Leipzig Zentrum
- different globe diameters
- support arbitrary cities
- physical test-print mode using only 2–3 neighboring gores
- compensation for paper stretch / glue shrinkage

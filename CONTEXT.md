# Leipzig Globe

Leipzig Globe turns a stylized map of Leipzig into printable paper pieces for covering a physical globe. It treats Leipzig as a fictional spherical world rather than as conventional cartography.

## Language

**Planet Leipzig**:
The fictional spherical world represented by the Leipzig map.
_Avoid_: world map, geographic globe

**Globe Texture**:
A 2:1 equirectangular image of Planet Leipzig used as the source for globe construction.
_Avoid_: map image, texture map

**Gore**:
A tapered, pole-to-pole printable segment that covers one equal longitudinal portion of the globe.
_Avoid_: strip, panel

**Print Set**:
The tiled A4 PDF and its assembly marks sized for a particular physical globe.
_Avoid_: printout, template

**Source Extract**:
The pinned regional OpenStreetMap data file from which Leipzig municipal map data is derived.
_Avoid_: live map data, OSM download

**Municipal Map**:
The Leipzig administrative-area map after being clipped from the Source Extract.
_Avoid_: Leipzig map, city map

**Municipal Boundary**:
The pinned official geographic extent that defines which source features belong to the Municipal Map.
_Avoid_: OSM boundary, city limits

**Seam Offset**:
The configured longitudinal rotation that determines where adjacent Gores meet on the Globe Texture.
_Avoid_: seam position, map rotation

**Curated Landmark**:
A configuration-selected Leipzig landmark eligible for a visible label alongside district names.
_Avoid_: POI, point of interest

**World Layout**:
The non-uniformly scaled arrangement of the Municipal Map that fills the Globe Texture.
_Avoid_: projection, map transform

**Pole Safety Zone**:
The area near an artificial pole where labels are not eligible for placement.
_Avoid_: polar exclusion area, pole margin

**Build Report**:
The machine-readable account of generated artifacts and labels omitted from a Print Set.
_Avoid_: log, output summary

**Preview Set**:
The static rendered views used to inspect Planet Leipzig before printing.
_Avoid_: 3D viewer, preview image

**Page Tile**:
An A4-sized section of a Print Set that joins neighboring sections using registration marks and a configurable overlap.
_Avoid_: page, sheet

**Assembly Overlap**:
The configured portion of a Gore that lies beneath its neighboring Gore when attached to the physical globe.
_Avoid_: bleed, join margin

**Leipzig Build**:
A build of Planet Leipzig; supporting other cities is outside the current product scope.
_Avoid_: city build, generic globe build

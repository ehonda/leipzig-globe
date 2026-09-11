# Interactive 3D Globe Preview — Implementation Spec

## 1. Purpose

Add an interactive browser-based 3D preview of the Leipzig globe.

The preview should allow us to inspect how the generated globe looks before printing and physically assembling the gores.

The initial target is a static HTML application suitable for hosting with GitHub Pages.

The viewer should eventually support two distinct forms of validation:

1. **Finished globe preview**
   - Wrap the canonical equirectangular Leipzig texture around a sphere.
   - Validate the intended appearance of the finished globe.

2. **Gore assembly preview**
   - Render the generated globe as individually modeled gore pieces.
   - Validate how the actual generated gores reconstruct the sphere.
   - Visualize seams, overlaps, gore ordering, and assembly geometry.

The Python build pipeline remains authoritative for globe geometry and generated assets. The browser viewer is primarily a visualization layer.

---

## 2. Goals

### Required

- Interactive 3D globe in a browser.
- Mouse/touch rotation.
- Zoom.
- Use the generated Leipzig globe texture.
- Render correctly as a sphere.
- Work as a static site.
- Be deployable through GitHub Pages.
- Integrate with the existing Python-based build pipeline without replacing it.

### Strongly desired

- Toggle gore seam lines.
- Toggle pole safety-zone indicators.
- Auto-rotation.
- Camera shortcuts such as:
  - front
  - back
  - north pole
  - south pole
- Render the globe as 12 separately modeled gores.
- Exploded view showing how individual gores form the sphere.
- Highlight individual gores.
- Visualize:
  - nominal seams
  - physical cut edges
  - assembly overlap

### Nice to have

- Select a gore by clicking it.
- Display gore number and metadata.
- Opacity controls.
- Wireframe/debug mode.
- Adjustable exploded-view distance.
- URL parameters for selecting a useful initial camera/debug state.
- Screenshot/export functionality, if this can be added without significant complexity.

---

## 3. Non-goals

The browser application should **not** become a second implementation of the globe-generation pipeline.

In particular:

- Do not implement OSM data acquisition in JavaScript.
- Do not reproduce the map rendering pipeline in JavaScript.
- Do not make JavaScript independently calculate configuration values that Python can export.
- Do not replace deterministic Python preview generation.
- Do not require a server-side component.
- Do not require a complex frontend framework unless future requirements clearly justify one.

Python remains the source of truth for:

- globe diameter
- gore count
- overlap
- gore geometry
- texture generation
- print geometry
- seam geometry
- cut geometry
- configuration validation

---

## 4. Proposed technology

Use **Three.js** for browser rendering.

Use `OrbitControls` for:

- rotation
- zoom
- optional panning

Prefer a lightweight static frontend:

```text
HTML
CSS
JavaScript ES modules
Three.js
```

Avoid introducing React, Vue, Vite, or another frontend build system for the initial implementation.

A build system can be introduced later if the viewer becomes complex enough to justify it.

---

## 5. High-level architecture

```text
Existing Python pipeline
        │
        ├── canonical globe texture
        │
        ├── generated gore images
        │
        ├── geometry information
        │
        └── print configuration
        │
        ▼
Web preview export step
        │
        ├── reduced web texture
        ├── reduced gore textures
        └── preview-manifest.json
        │
        ▼
Static Three.js viewer
        │
        ├── Finished Globe mode
        ├── Gore Assembly mode
        └── Debug overlays
```

The web viewer should consume generated artifacts rather than reproduce Python configuration logic.

---

# 6. Viewer modes

## 6.1 Finished Globe mode

Render a conventional Three.js sphere using the canonical 2:1 equirectangular globe texture.

Conceptually:

```text
SphereGeometry
    +
equirectangular Leipzig texture
    =
interactive finished globe
```

This mode answers:

> What is the intended final globe supposed to look like?

It should be the simplest and most reliable mode.

### Required controls

- rotate
- zoom
- reset camera

### Desired controls

- auto rotate
- show gore seams
- show equator
- show pole safety zones
- front view
- back view
- north pole view
- south pole view

---

## 6.2 Gore Assembly mode

Render the sphere as one separate mesh per gore.

For the current configuration this means 12 meshes.

Each gore should occupy precisely the spherical region represented by its printed gore.

This mode answers:

> How do the generated physical pieces reconstruct the globe?

Individual gore meshes allow:

- seam visualization
- gore highlighting
- exploded views
- overlap visualization
- debugging individual generated pieces

---

# 7. Gore geometry

The web implementation must use the same mathematical model as the Python gore generator.

However, JavaScript should preferably consume geometry/configuration exported by Python rather than independently infer configuration values.

For a globe with:

- circumference `C`
- gore count `N`
- gore height `H = C / 2`
- equatorial gore width `W = C / N`

the existing gore geometry uses a sinusoidal taper.

For vertical position `y` on the gore:

```text
taper = sin(π * y / H)
```

The nominal gore boundaries are approximately:

```text
left  = -W/2 * taper
right = +W/2 * taper
```

The cut boundary additionally contains the configured overlap:

```text
cut_right = (W/2 + overlap) * taper
```

A point `(x, y)` on a gore can be mapped back to the globe approximately through:

```text
latitude = π/2 - π*y/H
```

and:

```text
longitude_fraction =
    (slot + 0.5) / N
    + x / (C * cos(latitude))
```

then:

```text
longitude = 2π * longitude_fraction
```

and spherical coordinates:

```text
X = cos(latitude) * sin(longitude)
Y = sin(latitude)
Z = cos(latitude) * cos(longitude)
```

Exact conventions must match the existing Python implementation, including:

- longitude orientation
- gore ordering
- seam ownership
- texture orientation
- overlap direction
- pole handling

Do not duplicate formulas blindly if equivalent geometry can be exported directly from Python.

---

# 8. Gore mesh generation

Each gore should be represented by a sufficiently subdivided mesh.

A useful conceptual grid is:

```text
vertical segments:   ~100–200
horizontal segments: ~10–30
```

Exact values should be chosen experimentally.

The mesh must be sufficiently smooth that:

- curved gore edges appear smooth
- texture distortion is not visibly polygonal
- seams between neighboring gores align accurately

Avoid unnecessarily dense geometry.

---

# 9. Texture strategies

Support two stages of gore rendering.

## 9.1 Stage A — canonical texture sampling

Initially, all gore meshes may sample the same canonical equirectangular globe texture.

This validates:

- spherical gore geometry
- gore ordering
- seam locations
- exploded-view behavior

This is simpler to implement.

---

## 9.2 Stage B — actual generated gore textures

The final validation mode should use the actual generated gore images.

Conceptually:

```text
canonical map
    ↓
Python gore generation
    ↓
actual generated gore PNG
    ↓
3D gore mesh
    ↓
assembled virtual globe
```

This is preferable because it tests more of the production pipeline.

It can reveal bugs such as:

- incorrect crop boundaries
- texture shifts
- orientation mistakes
- seam discontinuities
- overlap errors
- incorrect gore ordering

A finished-sphere preview might not expose those problems.

---

# 10. Exploded view

Provide a slider such as:

```text
Assembly
assembled ───────────── exploded
```

At zero:

```text
all gores form the sphere
```

At increasing values:

```text
each gore moves outward from the sphere
```

Prefer radial displacement based on each gore's central longitude.

The exploded view should preserve each gore's orientation.

This should make the relationship between neighboring pieces visually obvious.

---

# 11. Seam and overlap visualization

Provide independent debug toggles for:

- nominal seam
- cut edge
- overlap area

Suggested interpretation:

```text
nominal seam
    = where neighboring gores should meet

cut edge
    = physical edge of the printed piece

overlap
    = area intentionally extending past the nominal seam
```

The overlap should taper toward the poles in exactly the same way as the generated physical gore.

The visualization should make it possible to answer:

> Which gore overlaps which neighbor?

and:

> How large is the overlap at this latitude?

---

# 12. Gore selection

Each gore should have a stable identifier.

For example:

```text
Gore 01
Gore 02
...
Gore 12
```

Clicking a gore should optionally:

- highlight it
- display its number
- display its longitude slot
- display relevant geometry metadata

Useful metadata may include:

```text
gore index
longitude slot
nominal equatorial width
overlap
globe diameter
```

Do not expose implementation details that are not useful for debugging or assembly.

---

# 13. Preview manifest

Python should generate a small web-specific manifest.

Possible format:

```json
{
  "schema_version": 1,
  "diameter_mm": 300,
  "circumference_mm": 942.4778,
  "gore_count": 12,
  "gore_height_mm": 471.2389,
  "gore_width_mm": 78.5398,
  "assembly_overlap_mm": 2,
  "gore_order": "clockwise",
  "texture": "assets/texture.webp",
  "gores": [
    {
      "index": 0,
      "slot": 0,
      "texture": "assets/gores/gore-01.webp"
    }
  ]
}
```

This is illustrative rather than normative.

Prefer reusing information already present in existing build or geometry manifests rather than creating unnecessary parallel representations.

If practical, either:

1. extend an existing manifest with web-preview fields, or
2. derive the web manifest directly from an existing authoritative manifest.

---

# 14. Web asset generation

Do not commit full-resolution print assets solely for the web viewer.

Generate reduced assets for browser use.

Possible targets:

```text
finished texture:
2048 × 1024 WebP

higher quality option:
4096 × 2048 WebP
```

Generated gore textures should similarly be reduced to an appropriate browser resolution.

Web assets should be visually sufficient for inspection while loading quickly.

The exact compression settings should be chosen experimentally.

---

# 15. Suggested repository layout

One possible layout:

```text
docs/
├── index.html
├── globe.js
├── style.css
└── assets/
    ├── preview-manifest.json
    ├── texture.webp
    └── gores/
        ├── gore-01.webp
        ├── gore-02.webp
        ├── gore-03.webp
        └── ...
```

If `docs/` conflicts with future documentation organization, alternatives are acceptable.

The important requirement is that the entire deployed viewer remains static.

---

# 16. Python integration

Introduce a Python export step conceptually similar to:

```python
export_web_preview(...)
```

Responsibilities:

1. obtain authoritative build/configuration data
2. create/downsample the canonical browser texture
3. create/downsample browser gore textures
4. export any geometry needed by JavaScript
5. write the preview manifest
6. place all generated assets in the static-site asset directory

The browser should require no knowledge of where the original build cache resides.

---

# 17. Git tracking

Production output may remain ignored.

For example:

```text
output/
.cache/
```

should remain transient if that matches the existing project design.

Small web-preview artifacts may be committed if this makes GitHub Pages simple and deterministic.

Conceptually:

```text
full production build
      │
      ├── print assets
      │      → ignored build output
      │
      ├── existing demo/checkpoint assets
      │
      └── reduced web assets
             → tracked static site
```

Alternatively, GitHub Actions may generate the web assets during deployment if this later becomes preferable.

For the first implementation, favor simplicity over deployment sophistication.

---

# 18. GitHub Pages

The viewer must be compatible with GitHub Pages.

No server-side functionality should be required.

Possible deployment:

```text
main
└── docs/
```

Configure GitHub Pages to publish the static contents of `docs/`.

All asset references must work correctly when hosted below a repository path such as:

```text
https://<user>.github.io/leipzig-globe/
```

Avoid assumptions that the site is hosted at `/`.

Prefer relative asset URLs.

---

# 19. UI layout

Keep the UI simple.

Example:

```text
┌───────────────────────────────────────────────┐
│ Planet Leipzig — 3D Preview                 │
├───────────────────────────────────────────────┤
│                                               │
│                                               │
│                  3D GLOBE                     │
│                                               │
│                                               │
├───────────────────────────────────────────────┤
│ Mode: [Finished Globe ▼]                      │
│                                               │
│ [ ] Gore seams                                │
│ [ ] Cut edges                                 │
│ [ ] Overlap                                   │
│ [ ] Wireframe                                 │
│ [ ] Auto rotate                               │
│                                               │
│ Assembly: [────────●────────]                  │
│                                               │
│ [Front] [Back] [North] [South] [Reset]       │
└───────────────────────────────────────────────┘
```

The 3D view should remain the primary focus.

Do not turn the viewer into a large dashboard.

---

# 20. Mobile support

The viewer should remain usable on:

- desktop browsers
- tablets
- modern phones

Touch controls should support:

- drag to rotate
- pinch to zoom

Controls may collapse or reflow on narrow screens.

Desktop remains the primary debugging environment.

---

# 21. Camera defaults

Choose a default orientation that shows a recognizable portion of Leipzig.

Provide deterministic shortcuts:

```text
Front
Back
North
South
Reset
```

The exact meaning of "front" should be defined consistently by the existing globe coordinate system.

---

# 22. Lighting and appearance

The preview is primarily for validating the printed map, so lighting must not obscure texture colors.

Use simple lighting such as:

```text
ambient light
+
soft directional light
```

Avoid:

- dramatic shadows
- strong color casts
- excessive reflections
- photorealistic material effects

A subtle spherical appearance is desirable, but map readability is more important.

A debug mode may optionally render the texture without lighting.

---

# 23. Coordinate/orientation tests

Add tests or deterministic checks for known reference points.

At minimum verify:

- equator maps to the middle of each gore
- north pole converges correctly
- south pole converges correctly
- gore 1 meets gore 2 at the expected seam
- last gore meets first gore correctly
- longitude orientation is not mirrored
- generated texture is not vertically inverted

Where practical, encode these tests in Python rather than relying exclusively on manual inspection.

---

# 24. Performance

Target smooth interaction on ordinary desktop hardware and recent phones.

Avoid:

- unnecessarily large textures
- one draw call per tiny mesh element
- excessively dense tessellation
- repeated texture loading
- expensive per-frame geometry rebuilding

Geometry should normally be built once.

Exploded-view animation should modify mesh transforms rather than regenerate meshes.

---

# 25. Development stages

## Stage 1 — interactive finished globe

Implement:

- static HTML page
- Three.js scene
- sphere
- canonical reduced Leipzig texture
- OrbitControls
- resize handling
- reset camera
- optional auto rotate

Acceptance criteria:

- globe loads from static files
- globe can be rotated
- globe can be zoomed
- texture orientation is correct
- page works through GitHub Pages

---

## Stage 2 — debug overlays

Add:

- equator
- gore seam lines
- pole safety-zone visualization
- fixed camera shortcuts

Acceptance criteria:

- seams align with expected gore boundaries
- overlays can be toggled independently

---

## Stage 3 — separate gore meshes

Replace or supplement the sphere with individually generated spherical gore meshes.

Add:

- Finished Globe / Gores mode switch
- gore selection
- exploded view

Acceptance criteria:

- all gores reconstruct the same sphere
- neighboring seams align
- first and last gore align
- exploded mode preserves proper ordering

---

## Stage 4 — actual generated gore textures

Use downsampled versions of the real generated gore textures.

Acceptance criteria:

- assembled gore view visually matches Finished Globe mode
- seam continuity can be inspected
- any difference between canonical-texture mode and generated-gore mode is visible

---

## Stage 5 — overlap diagnostics

Add:

- nominal seam
- physical cut edge
- overlap highlighting

Acceptance criteria:

- overlap size agrees with Python configuration
- overlap tapers correctly toward poles
- overlap direction is obvious

---

# 26. Definition of done

The feature is complete when:

- an interactive globe is publicly accessible through GitHub Pages
- users can rotate and zoom the globe
- Finished Globe mode displays the generated Leipzig texture correctly
- Gore Assembly mode displays individual generated gores
- assembled gores recreate the finished globe
- exploded view clearly shows the relationship between pieces
- seams and overlap can be inspected
- the viewer derives geometry/configuration from Python-generated data
- no server is required
- documentation explains how to regenerate preview assets and deploy the viewer

---

# 27. Guiding principle

The 3D preview should function as a **digital assembly simulator**, not merely as a decorative 3D globe.

Its primary purpose is to increase confidence that the generated printable pieces will reconstruct the intended physical globe before paper, ink, adhesive, and assembly time are spent.

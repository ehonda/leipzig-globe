# Interactive 3D Globe Preview — Design Rationale

## Context

The Leipzig Globe project generates a map of Leipzig intended to be physically assembled onto a spherical globe.

The existing pipeline already provides several important representations of the same globe:

1. a canonical 2:1 equirectangular globe texture
2. printable sinusoidal gores derived from that texture
3. geometric metadata describing the generated pieces
4. static preview images showing the globe from fixed viewpoints

Before committing to a physical test assembly, it would be useful to inspect the result interactively.

The key question is not only:

> Does the map look good when projected onto a sphere?

but also:

> Do the exact generated physical pieces appear to reconstruct that sphere correctly?

These are related but different validation problems.

---

# Decision

Add a lightweight static browser-based 3D viewer using **Three.js**.

The viewer will eventually contain two complementary preview modes:

1. **Finished Globe**
   - render the canonical equirectangular texture directly on a sphere

2. **Gore Assembly**
   - reconstruct the sphere from separately modeled generated gores

The viewer will be deployable through **GitHub Pages**.

The existing Python code remains authoritative for globe generation and geometry.

---

# Why an interactive preview is useful

The existing fixed preview images are useful because they are:

- deterministic
- easy to generate during tests
- suitable for regression comparison
- independent of browser/WebGL behavior

They should therefore remain.

However, fixed viewpoints make it cumbersome to inspect arbitrary locations.

An interactive globe provides immediate inspection of:

- any region of Leipzig
- poles
- seam boundaries
- text orientation
- label distortion
- map density
- problematic transitions
- features near gore boundaries

Rotation and zoom are especially useful when deciding whether the generated result is ready for a physical test.

The interactive viewer complements rather than replaces deterministic image previews.

---

# Why start from the canonical equirectangular texture

The project already has a natural intermediate representation:

```text
2:1 equirectangular globe texture
```

This representation is exactly what conventional 3D sphere rendering expects.

Therefore the simplest first implementation is:

```text
canonical texture
       +
Three.js SphereGeometry
       =
interactive globe
```

No additional map projection is necessary in the browser.

This makes the initial implementation both small and low-risk.

---

# Why a simple textured sphere is not enough

A textured sphere validates the desired final appearance.

It does **not**, by itself, validate the actual print artifacts.

Consider the pipeline:

```text
map data
    ↓
canonical globe texture
    ↓
gore generation
    ↓
print files
    ↓
physical assembly
```

If the first browser preview renders only the canonical texture:

```text
canonical globe texture
    ↓
browser sphere
```

then the gore-generation stage is bypassed completely.

A bug affecting the generated physical pieces might therefore remain invisible.

Possible examples include:

- incorrect gore crop
- one-pixel offset
- mirrored gore
- incorrect gore number
- wrong seam longitude
- incorrect overlap sampling
- wrong neighbor content in an overlap
- output scaling mistake

For this reason, the eventual viewer should also reconstruct the globe from the actual generated gores.

---

# Two validation layers

The viewer should intentionally provide two layers of validation.

## Layer 1 — intended result

```text
canonical texture
      ↓
sphere
```

Question answered:

> What should the final globe look like?

This isolates map rendering and spherical projection.

---

## Layer 2 — generated physical artifacts

```text
canonical texture
      ↓
gore generator
      ↓
generated gore images
      ↓
3D gore meshes
      ↓
assembled sphere
```

Question answered:

> What do the generated pieces actually reconstruct?

When both views agree, confidence in the pipeline is substantially higher.

---

# Why Three.js

Several technical approaches were considered.

## Matplotlib

The project already uses Python and static rendering.

Advantages:

- already compatible with the existing stack
- deterministic
- excellent for generated screenshots
- easy to integrate with tests

Disadvantages:

- not naturally interactive in a static GitHub Pages site
- browser interaction would require another layer anyway
- separately manipulating 12 textured pieces is not its primary use case

Conclusion:

Continue using Matplotlib/static Python rendering for deterministic previews, but not as the interactive viewer.

---

## Plotly

Advantages:

- interactive browser output
- strong Python integration
- can produce standalone HTML
- easy camera interaction

Disadvantages:

- textured spherical surfaces are not Plotly's strongest use case
- independently textured gore meshes would become awkward
- exploded physical-piece visualization is outside its normal visualization model
- lower-level geometry control would be more cumbersome

Conclusion:

Reasonable for a simple sphere prototype but less suitable for the intended assembly simulator.

---

## PyVista / VTK

Advantages:

- excellent scientific 3D rendering
- powerful mesh handling
- Python-centric

Disadvantages:

- considerably heavier
- browser deployment is more involved
- excessive complexity for a small static visualization

Conclusion:

Technically capable but unnecessarily heavyweight.

---

## globe.gl

Advantages:

- convenient interactive globe abstraction
- built on Three.js
- good for geographic visualization

Disadvantages:

- optimized around conventional globe visualization
- separately modeled physical gores require lower-level mesh control
- custom cut edges and overlap geometry push beyond its main abstraction

Conclusion:

Useful for conventional globes but offers little benefit once custom gore geometry becomes central.

---

## Three.js

Advantages:

- purpose-built browser 3D engine
- mature
- excellent WebGL support
- straightforward texture mapping
- full control over arbitrary meshes
- independent objects can represent each gore
- OrbitControls provides expected globe interaction
- works as a purely static application
- ideal for GitHub Pages
- no framework required

Disadvantages:

- introduces JavaScript into a mostly Python project
- some globe geometry must be represented on the browser side

Conclusion:

Three.js offers the best balance between simplicity and control.

---

# Why introducing JavaScript is acceptable

The existing implementation is primarily Python.

At first glance, adding JavaScript may seem undesirable because it introduces another language and ecosystem.

However, the distinction between responsibilities is important.

Python remains responsible for:

```text
data acquisition
map rendering
projection
globe configuration
gore geometry
print generation
asset generation
validation
```

JavaScript is responsible only for:

```text
interactive display
camera movement
mesh visibility
debug overlays
selection
animation
```

Three.js is therefore a **viewer**, not a second globe generator.

This boundary keeps the additional technology surface small.

---

# Avoiding duplicated geometry logic

A major design risk would be implementing two independent interpretations of the same configuration.

For example:

```text
Python:
diameter = 300 mm
overlap = 2 mm
12 gores

JavaScript:
independently calculates all geometry
```

Over time these implementations could diverge.

Then the browser preview might look correct according to JavaScript while the print generator behaves differently.

The preferred flow is therefore:

```text
Python source of truth
       ↓
generated manifest/assets
       ↓
JavaScript visualization
```

The browser should consume authoritative information generated by Python.

Where practical, geometry itself should be exported rather than reconstructed from duplicated formulas.

---

# Why a preview manifest is useful

The browser needs some information beyond image files.

Examples include:

- number of gores
- globe diameter
- gore order
- overlap
- texture path
- gore texture paths
- seam information

A small generated manifest provides a clean boundary:

```text
Python pipeline
      ↓
preview-manifest.json
      ↓
browser
```

This has several benefits:

- no parsing Python configuration files in JavaScript
- no assumptions about project directory layout
- schema can be versioned
- browser assets become self-contained
- static deployment becomes easy

The manifest should be treated as a generated interface, not as another manually maintained configuration file.

---

# Why render separate gore meshes

If all gores are rendered as one ordinary sphere, there is no concept of an individual physical piece.

Separate meshes allow each gore to be:

- selected
- hidden
- highlighted
- moved
- rendered in wireframe
- given its own generated texture

This creates useful capabilities almost for free once the geometry exists.

The most important is the exploded view.

---

# Why an exploded view is valuable

Physical assembly is difficult to reason about from flat SVGs alone.

An exploded view provides a direct visual connection between:

```text
flat piece number
```

and:

```text
location on final sphere
```

With 12 separate meshes, each piece can move outward from the center.

At zero displacement:

```text
complete sphere
```

At larger displacement:

```text
12 separated spherical strips
```

This makes several concepts immediately obvious:

- gore ordering
- neighbor relationships
- seam location
- pole convergence
- orientation
- assembly sequence

It should therefore be treated as a core debugging feature rather than a visual gimmick.

---

# Why visualize both seams and cut edges

The physical gore has more than one relevant boundary.

There is a conceptual or nominal boundary where two gores meet.

There is also the actual paper cut boundary, which may include overlap.

These should not be conflated.

The viewer should distinguish:

```text
nominal seam
```

from:

```text
physical cut edge
```

and from:

```text
overlap region
```

This directly mirrors the real assembly problem.

A person applying the pieces should be able to understand:

- where the final seam should lie
- which piece extends across it
- how far the overlap extends

---

# Why use the real gore textures eventually

A first gore implementation can map the original equirectangular texture directly onto each spherical strip.

That is useful because it isolates geometry.

However, it still bypasses part of the production pipeline.

The stronger test uses the same image artifacts intended for printing.

Then:

```text
printed gore image
```

becomes the source texture for:

```text
virtual gore piece
```

The digital simulation therefore gets much closer to:

```text
print → cut → wrap → assemble
```

without consuming any physical materials.

---

# Why browser assets should be downsampled

Print assets are intentionally high resolution.

That resolution is unnecessary for an interactive browser preview.

Large images would:

- increase repository size
- increase GitHub Pages transfer size
- consume more GPU memory
- increase texture upload time
- reduce mobile usability

The browser should therefore receive purpose-built preview assets.

For example:

```text
print:
~7400 × 3700 or higher

web preview:
2048 × 1024
or
4096 × 2048
```

The preview is intended for visual inspection, not printing.

The print pipeline remains unchanged.

---

# Why generated web assets may be committed

The project already distinguishes generated production artifacts from useful checked-in examples/checkpoints.

Large transient build output should continue to be ignored.

A small set of optimized browser assets is different because those files are effectively part of the published site.

Possible structure:

```text
docs/
├── viewer code
└── assets/
    └── small generated preview files
```

Committing these files initially makes GitHub Pages extremely simple.

A later CI workflow can regenerate them automatically if this becomes useful.

There is no need to make deployment automation complex during the first implementation.

---

# Why GitHub Pages

The viewer requires only:

```text
HTML
CSS
JavaScript
JSON
images
```

There is no dynamic backend requirement.

GitHub Pages therefore provides:

- free static hosting
- direct association with the repository
- simple sharing
- easy deployment
- no separate infrastructure

This makes it well suited to the project.

---

# Why avoid a frontend framework initially

React, Vue, Svelte, or similar frameworks would work.

However, the initial application has a small state model:

```text
current mode
selected gore
debug toggles
camera
explosion amount
```

Three.js already handles the difficult part.

Adding a framework would introduce:

- package management
- build configuration
- dependencies
- deployment steps
- more code organization decisions

without solving a current problem.

Plain JavaScript is therefore preferable initially.

A frontend framework can be introduced later if UI complexity genuinely warrants it.

---

# Relationship to the existing static previews

The interactive viewer should not replace the existing deterministic preview generation.

The two tools serve different purposes.

## Static Python previews

Best for:

- regression tests
- automated artifact generation
- visual checkpointing
- documentation
- deterministic comparisons

## Interactive browser preview

Best for:

- exploratory inspection
- arbitrary viewpoints
- zoom
- seam inspection
- understanding assembly
- exploded gore visualization

Both are useful and should coexist.

---

# Recommended implementation sequence

The feature should be developed incrementally so errors remain easy to isolate.

## Step 1 — sphere

Render the canonical texture on a normal sphere.

This establishes:

- renderer
- camera
- texture orientation
- GitHub Pages deployment

---

## Step 2 — overlays

Add:

- equator
- gore seams
- pole regions

This validates the coordinate convention.

---

## Step 3 — individual gore geometry

Construct one mesh per gore while still using the canonical texture.

This isolates geometry from image-generation concerns.

---

## Step 4 — exploded view

Move the gore objects outward.

This validates:

- object orientation
- gore ordering
- neighbor relationships

---

## Step 5 — generated gore images

Texture each object using the corresponding generated gore image.

Now the actual output pipeline is under test.

---

## Step 6 — overlap diagnostics

Render:

- nominal seam
- cut edge
- overlap

At this point the viewer becomes a genuine digital assembly simulator.

---

# Alternatives rejected

## Browser-only generation

It would be possible to move much of the generation pipeline into JavaScript.

Rejected because:

- duplicates Python functionality
- makes consistency harder
- provides little benefit
- browser is not intended to be authoritative

---

## Exporting a prebuilt 3D model only

Python could generate a GLTF/GLB model and the browser could merely display it.

This remains a possible future optimization.

It was not selected as the primary design because:

- debug controls may need access to logical gore metadata
- changing visual modes is straightforward when meshes are constructed in the viewer
- the geometry is simple enough to render directly
- avoiding another generated binary artifact simplifies development

If the browser-side mesh implementation becomes unnecessarily complex, exporting GLTF from Python should be reconsidered.

---

## Replacing current static previews

Rejected.

Interactive inspection and deterministic generated previews solve different problems.

---

# Risks

## Geometry divergence

Risk:

JavaScript and Python calculate subtly different gore geometry.

Mitigation:

Export authoritative values or geometry from Python wherever practical.

---

## Texture orientation mistakes

Risk:

Different UV conventions produce:

- mirrored image
- vertical inversion
- longitude offset

Mitigation:

Use deterministic reference points and tests.

---

## Seam artifacts caused only by rendering

Risk:

GPU texture filtering can make seams appear even when source imagery is correct.

Mitigation:

Compare Finished Globe mode against Gore mode and understand filtering behavior before treating tiny visual differences as generation bugs.

---

## Excessive complexity

Risk:

The viewer grows into an unrelated frontend application.

Mitigation:

Keep its purpose narrow:

> inspect and understand the generated globe and its physical gores.

---

## Repository bloat

Risk:

Generated web assets become too large.

Mitigation:

Use downsampled compressed assets specifically for browser use.

---

# Expected outcome

Once implemented, the project will have three increasingly realistic validation levels:

```text
1. Static rendered previews
      ↓
2. Interactive canonical sphere
      ↓
3. Interactive assembly from generated gores
      ↓
4. Physical test assembly
```

Each stage is more expensive than the previous one.

The interactive gore simulator should catch many classes of errors before reaching stage 4.

That reduces the cost of experimentation in:

- printing
- cutting
- adhesive
- test globes
- assembly time

---

# Final rationale

Three.js is not being introduced because the project needs a general-purpose web frontend.

It is being introduced because the browser is an excellent environment for inspecting a 3D object interactively.

The core design principle is:

> Generate with Python; inspect with Three.js.

The canonical sphere provides a clear visualization of the intended result.

Separate gore meshes provide a simulation of the actual assembly process.

Together, these create a useful bridge between the existing deterministic software pipeline and the eventual physical globe.

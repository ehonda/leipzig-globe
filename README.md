# Leipzig Globe

This project renders a data-driven Leipzig map from the cached OSM and official-boundary sources. A synthetic demo is deliberately not available because it cannot validate the map pipeline.

## Create the demo image

From the repository root, run:

```bash
uv sync
uv run leipzig-globe fetch-data
uv run leipzig-globe build
```

This generates a file at:

```text
output/leipzig-map.png
```

## What the demo shows

The generated image is a data-driven preview of the Leipzig map render, not the final globe texture or gore layout. It is useful for checking:

- land / water / road styling
- label density and placement
- pole-safety exclusion behavior
- seam-related label omission

## Notes

- This is a 2D preview from the current implementation, not a finished printable globe.
- The command uses the project’s default configuration from `config/default.yaml` and requires `osmium` on `PATH`.
- If you want to tweak the map look, modify `layout.label_density`, `layout.curated_landmarks`, or the `style` entries in the config before running the render command.

# Leipzig Globe

This project is currently at the map-rendering stage of the Leipzig Globe MVP. The easiest way to create a viewable demo image is to render the stylized city map as a PNG.

## Create the demo image

From the repository root, run:

```bash
uv sync
uv run python -c "from leipzig_globe.pipeline import render_clean_map; from leipzig_globe.config import DEFAULT_CONFIG; render_clean_map(DEFAULT_CONFIG, 'output/demo-map.png')"
```

This generates a file at:

```text
output/demo-map.png
```

## What the demo shows

The generated image is a current-stage preview of the Leipzig map render, not the final globe texture or gore layout. It is useful for checking:

- land / water / road styling
- label density and placement
- pole-safety exclusion behavior
- seam-related label omission

## Notes

- This is a 2D preview from the current implementation, not a finished printable globe.
- The command uses the project’s default configuration from `config/default.yaml`.
- If you want to tweak the map look, modify `layout.label_density`, `layout.curated_landmarks`, or the `style` entries in the config before running the render command.

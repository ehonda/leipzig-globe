"""Orthographic sphere views sampled from the exact printable texture."""

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

VIEWPOINTS = {
    "front": (0, 0),
    "back": (180, 0),
    "left": (-90, 0),
    "right": (90, 0),
    "north": (0, 90),
    "south": (0, -90),
}


def generate_preview_set(
    texture_path, output_dir, *, config=None, provenance=None, size=800
):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    with Image.open(texture_path) as image:
        sample_width = max(2, round(size * 0.46 * 2 * math.pi))
        sample_width += sample_width % 2
        texture = np.asarray(
            image.convert("RGB").resize(
                (sample_width, sample_width // 2), Image.Resampling.LANCZOS
            )
        )
    coords = (np.arange(size) + 0.5 - size / 2) / (size * 0.46)
    x, y = np.meshgrid(coords, -coords)
    radius2 = x * x + y * y
    mask = radius2 <= 1
    z = np.sqrt(np.maximum(0, 1 - radius2))
    paths = []
    for name, (longitude, latitude) in VIEWPOINTS.items():
        lon0, lat0 = math.radians(longitude), math.radians(latitude)
        lat = np.arcsin(np.clip(y * math.cos(lat0) + z * math.sin(lat0), -1, 1))
        lon = lon0 + np.arctan2(x, z * math.cos(lat0) - y * math.sin(lat0))
        u = ((lon / (2 * math.pi) + 0.5) * texture.shape[1] - 0.5) % texture.shape[1]
        v = np.clip(
            (0.5 - lat / math.pi) * texture.shape[0] - 0.5,
            0,
            texture.shape[0] - 1,
        )
        x0, y0 = u.astype(int), v.astype(int)
        x1, y1 = (x0 + 1) % texture.shape[1], np.minimum(y0 + 1, texture.shape[0] - 1)
        fx, fy = (u - x0)[..., None], (v - y0)[..., None]
        rgb = (texture[y0, x0] * (1 - fx) + texture[y0, x1] * fx) * (1 - fy) + (
            texture[y1, x0] * (1 - fx) + texture[y1, x1] * fx
        ) * fy
        if config and config["layout"].get("preview_overlays", False):
            seam = (
                np.abs(
                    ((lon / (2 * math.pi) + 0.5) * config["globe"]["gore_count"] + 0.5)
                    % 1
                    - 0.5
                )
                < 0.008
            )
            polar = (
                np.abs(lat)
                > math.pi / 2
                - 2
                * config["layout"]["pole_safety_zone_mm"]
                / config["globe"]["diameter_mm"]
            )
            rgb[seam] = 0.4 * rgb[seam] + 0.6 * np.array([200, 50, 50])
            rgb[polar] = 0.75 * rgb[polar] + 0.25 * np.array([200, 50, 50])
        # Gentle lighting makes curvature visible without hiding cartography.
        shade = 0.72 + 0.28 * np.clip(0.25 * x + 0.35 * y + 0.9 * z, 0, 1)
        result = np.full((size, size, 3), 247, dtype=np.uint8)
        result[mask] = np.clip(rgb[mask] * shade[mask, None], 0, 255).astype(np.uint8)
        path = root / f"{name}.png"
        Image.fromarray(result).save(path)
        paths.append(path)
    (root / "metadata.json").write_text(
        json.dumps(
            {
                "texture": str(texture_path),
                "viewpoints_deg": VIEWPOINTS,
                "config": config,
                "source_provenance": provenance,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return paths

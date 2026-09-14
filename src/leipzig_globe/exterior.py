"""Exterior geography and spherical-safe decorative backgrounds.

The Municipal Map stays clipped to Leipzig. Context is a separate, bounded OSM
extract, rendered in the municipal viewport without moving its centre or labels.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely
from PIL import Image, ImageChops, ImageFilter

from .municipal_map import WORKING_CRS, derive_municipal_map, extract_osm_features
from .rendering import _paint, feature_kind, scaled_texture_dimensions

EXTERIORS = {
    "blank": ("Original blank", "The municipal map on its original paper background."),
    "terrain": (
        "Surrounding terrain",
        (
            "Real surrounding roads, water and green space. A violet border with a pale halo marks Leipzig; "
            "geography fades into muted ground at the wrap and poles."
        ),
    ),
    "ocean": (
        "Continent Leipzig",
        "Leipzig becomes an island continent, with soft shallows and a pale shoreline that opens at lakes and rivers.",
    ),
    "fog": (
        "Fog of war",
        "Unexplored country disappears into soft sage-grey mist, fading from the map's warm paper tones.",
    ),
}


def build_context_map(source_pbf, source_map, output_path, config):
    """Extract only the fixed map rectangle, retaining the existing export budget."""
    source_map = Path(source_map)
    metadata = json.loads(source_map.with_suffix(".json").read_text(encoding="utf-8"))
    cx, cy = metadata["center_metric"]
    sx, sy = metadata["span_metric"]
    viewport = shapely.box(cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2)
    extent = gpd.GeoDataFrame(geometry=[viewport], crs=WORKING_CRS)
    output_path = Path(output_path)
    with tempfile.TemporaryDirectory(dir=output_path.parent) as temporary:
        extent_path = Path(temporary) / "viewport.geojson"
        extent.to_file(extent_path, driver="GeoJSON")
        features = Path(temporary) / "context.geojson"
        metrics = {}
        extract_osm_features(
            source_pbf, features, boundary_path=extent_path, metrics=metrics
        )
        result = derive_municipal_map(extent, features, output_path=output_path)
    render_context_map(output_path, source_map, config)
    return {
        "feature_count": result["feature_count"],
        "viewport_metric": list(viewport.bounds),
        "stages": metrics,
    }


def render_context_map(context, source_map, config):
    """Render context in exactly the same projection and stroke scale as Leipzig."""
    source_map = Path(source_map)
    metadata = json.loads(source_map.with_suffix(".json").read_text(encoding="utf-8"))
    width, height = metadata["sampling"]["source_pixels"]
    cx, cy = metadata["center_metric"]
    sx, sy = metadata["span_metric"]
    frame = gpd.read_file(context).to_crs(WORKING_CRS)

    def project(coords):
        return np.column_stack(
            (
                (coords[:, 0] - cx) * width / sx + width / 2,
                height / 2 - (coords[:, 1] - cy) * height / sy,
            )
        )

    geometries = shapely.transform(frame.geometry.array, project)
    layers = {
        kind: []
        for kind in (
            "park",
            "sport",
            "water",
            "path",
            "rail",
            "secondary_road",
            "major_road",
        )
    }
    for row, geometry in zip(frame.to_dict("records"), geometries, strict=True):
        kind = feature_kind(row)
        if kind in layers:
            layers[kind].append(geometry)
    palette = config["style"]
    image = Image.new("RGB", (width, height), tuple(palette["land"]))
    px_mm = (
        config["globe"]["ppi"]
        / 25.4
        * height
        / metadata["sampling"]["texture_pixels"][1]
    )
    strokes = {
        "water": 0.16,
        "path": 0.09,
        "rail": 0.12,
        "secondary_road": 0.13,
        "major_road": 0.32,
    }
    for kind, items in layers.items():
        if kind == "rail" and not config["layout"]["show_railways"]:
            continue
        for geometry in items:
            _paint(
                image,
                geometry,
                tuple(palette[kind]),
                max(1, round(strokes.get(kind, 0.1) * px_mm)),
            )
    image.save(source_map.with_suffix(".context.png"))


def _smooth(value):
    value = np.clip(value, 0, 1)
    return value * value * (3 - 2 * value)


def spherical_background(size, kind):
    """Deterministic 3-D fields: periodic at longitude wrap, constant at each pole.

    Work in small row blocks to avoid full-size floating-point RGB allocations.
    """
    width, height = size
    result = np.empty((height, width, 3), dtype=np.uint8)
    longitude = np.linspace(0, 2 * np.pi, width, dtype=np.float32)[None, :]
    for start in range(0, height, 64):
        latitude = np.linspace(np.pi / 2, -np.pi / 2, height, dtype=np.float32)[
            start : start + 64, None
        ]
        radius = np.maximum(0, np.cos(latitude))
        x, y, z = (
            radius * np.cos(longitude),
            radius * np.sin(longitude),
            np.sin(latitude),
        )
        if kind == "ocean":
            field = 0.5 + 0.22 * np.sin(3 * x + 2 * z) * np.cos(3 * y - z)
            low, high = np.array([65, 117, 147]), np.array([86, 141, 164])
        elif kind == "fog":
            field = 0.5 + 0.24 * np.sin(5 * x + 3 * z + np.sin(4 * y)) * np.cos(
                4 * y - 3 * z
            )
            field += (
                0.08
                * np.sin(13 * x + 2 * np.sin(7 * y) + 5 * z)
                * np.cos(11 * y - 6 * z + 2 * np.sin(5 * x))
            )
            low, high = np.array([191, 203, 190]), np.array([244, 240, 229])
        else:
            field = np.zeros_like(x)
            low = high = np.array([218, 222, 207])
        result[start : start + 64] = np.rint(
            low + field[..., None] * (high - low)
        ).astype(np.uint8)
    # Exact matching edge samples also survive the subsequent seam rotation.
    result[:, -1] = result[:, 0]
    result[0] = result[0, 0]
    result[-1] = result[-1, 0]
    return Image.fromarray(result)


def _placed(source, size, scaled, mode, fill):
    with Image.open(source) as image:
        resized = image.convert(mode).resize(scaled, Image.Resampling.LANCZOS)
    result = Image.new(mode, size, fill)
    result.paste(resized, ((size[0] - scaled[0]) // 2, (size[1] - scaled[1]) // 2))
    return result


def _coastal_land_mask(city, mask, water_color):
    """Use visible map-water ink to open the decorative shore at water crossings.

    This is a styling mask, not new geography. Read at full resolution before
    reducing so narrow water and antialiased lake edges contribute coverage.
    Roads and labels over water remain part of the unchanged municipal raster.
    """
    water = Image.new("L", city.size)
    for top in range(0, city.height, 64):
        box = (0, top, city.width, min(top + 64, city.height))
        pixels = np.asarray(city.crop(box)).astype(np.int16)
        difference = np.max(np.abs(pixels - np.asarray(water_color)), axis=2)
        coverage = np.rint(255 * (1 - _smooth((difference - 8) / 24)))
        water.paste(Image.fromarray(coverage.astype(np.uint8)), box)
    water = ImageChops.multiply(water, mask)
    small_size = (
        min(city.width, 1600),
        max(1, round(city.height * min(city.width, 1600) / city.width)),
    )
    small = mask.resize(small_size, Image.Resampling.LANCZOS)
    water = water.resize(small_size, Image.Resampling.LANCZOS)
    # Give water openings a little breathing room so a river mouth does not
    # acquire a pale bar from the land on either side.
    water = water.filter(ImageFilter.MaxFilter(5))
    return ImageChops.subtract(small, water)


def compose_exterior(city, source_map, config):
    """Replace only exterior pixels, then keep existing labels outside the outline."""
    kind = config["layout"]["exterior"]
    scaled = scaled_texture_dimensions(config)
    mask = _placed(source_map.with_suffix(".boundary.png"), city.size, scaled, "L", 0)
    background = spherical_background(city.size, kind)
    width, height = city.size
    # A world layout that crops the municipality cannot promise a smooth join.
    if any(
        mask.crop(box).getbbox()
        for box in (
            (0, 0, width, 1),
            (0, height - 1, width, height),
            (0, 0, 1, height),
            (width - 1, 0, width, height),
        )
    ):
        raise ValueError(
            "Exterior variants require the entire municipality inside the texture edges; reduce World Layout scale."
        )
    if kind == "terrain":
        context = _placed(
            source_map.with_suffix(".context.png"),
            city.size,
            scaled,
            "RGB",
            tuple(config["style"]["land"]),
        )
        # Ease real features into a common colour over the outer 8% of each axis.
        # Account for smaller source placement too, avoiding a hard padding edge.
        x = np.arange(width, dtype=np.float32)
        y = np.arange(height, dtype=np.float32)
        left, top = max(0, (width - scaled[0]) // 2), max(0, (height - scaled[1]) // 2)
        wx = _smooth(
            np.minimum(x - left, width - 1 - left - x) / (0.08 * min(width, scaled[0]))
        )
        wy = _smooth(
            np.minimum(y - top, height - 1 - top - y) / (0.08 * min(height, scaled[1]))
        )
        fade = Image.fromarray(
            np.rint(255 * wy[:, None] * wx[None, :]).astype(np.uint8)
        )
        background = Image.composite(context, background, fade)
        # Physical widths keep the border legible at both preview and print
        # density. The light casing separates violet ink from roads and rails.
        for millimetres, color in ((1.05, (250, 245, 237)), (0.65, (156, 75, 137))):
            radius = max(1, round(millimetres * config["globe"]["ppi"] / 25.4))
            rim = ImageChops.subtract(
                mask.filter(ImageFilter.MaxFilter(2 * radius + 1)), mask
            )
            background.paste(color, mask=ImageChops.multiply(rim, fade))
    else:
        # Work at bounded resolution for a wide, soft coastal shelf / fog fringe.
        small = mask.resize(
            (min(width, 1600), max(1, round(height * min(width, 1600) / width))),
            Image.Resampling.LANCZOS,
        )
        x = np.linspace(0, 1, width, dtype=np.float32)
        y = np.linspace(0, 1, height, dtype=np.float32)
        fade = Image.fromarray(
            np.rint(
                255
                * _smooth(np.minimum(y, 1 - y) / 0.03)[:, None]
                * _smooth(np.minimum(x, 1 - x) / 0.03)[None, :]
            ).astype(np.uint8)
        )

        def wash(coverage, radius, color):
            fringe = coverage.filter(
                ImageFilter.GaussianBlur(max(0.6, small.width * radius))
            )
            fringe = fringe.point(lambda value: min(255, value * 2))
            fringe = fringe.resize(city.size, Image.Resampling.BILINEAR)
            background.paste(color, mask=ImageChops.multiply(fringe, fade))

        if kind == "ocean":
            # The broad shelf shares the map's water colour. A narrower pale
            # wash follows land only, allowing cut-off lakes to meet the sea
            # without a fabricated beach across their water.
            water_color = tuple(config["style"]["water"])
            land = _coastal_land_mask(city, mask, water_color)
            wash(small, 0.016, water_color)
            wash(land, 0.0035, (181, 209, 210))
            wash(land, 0.0009, (230, 232, 217))
        else:
            # Broad, quiet paper mist softens angular administrative edges;
            # the low-contrast spherical field remains visible farther out.
            wash(small, 0.026, tuple(config["style"]["land"]))
    result = Image.composite(city, background, mask)
    # Label candidates can sit just outside the municipal polygon. Preserve their
    # actual ink (not rectangular paper boxes), using the original label metadata.
    metadata = json.loads(source_map.with_suffix(".json").read_text(encoding="utf-8"))
    source_width, source_height = metadata["sampling"]["source_pixels"]
    offset_x, offset_y = (width - scaled[0]) // 2, (height - scaled[1]) // 2
    for label in metadata["rendered_labels"]:
        a, b, c, d = label["bbox"]
        box = (
            max(0, int(a / source_width * scaled[0]) + offset_x),
            max(0, int(b / source_height * scaled[1]) + offset_y),
            min(width, int(np.ceil(c / source_width * scaled[0])) + offset_x),
            min(height, int(np.ceil(d / source_height * scaled[1])) + offset_y),
        )
        ink = city.crop(box)
        paper = Image.new("RGB", ink.size, tuple(config["style"]["background"]))
        ink_mask = (
            ImageChops.difference(ink, paper)
            .convert("L")
            .point(lambda value: 255 if value else 0)
        )
        result.paste(ink, box, ink_mask)
    return result

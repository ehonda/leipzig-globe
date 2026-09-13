"""Data-driven cartography and the artificial Leipzig world layout."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib
import numpy as np
import shapely
from PIL import Image, ImageChops, ImageDraw, ImageFont
from pyproj import Transformer

from .config import validate_config
from .municipal_map import WORKING_CRS

MAX_SOURCE_PIXELS = 100_000_000
PLACE_LABELS = {"city", "suburb", "quarter", "neighbourhood"}


def scaled_texture_dimensions(config):
    cfg = validate_config(config)
    width, height = texture_dimensions(cfg)
    return (
        max(1, math.ceil(width * cfg["layout"]["world_layout_scale_x"])),
        max(1, math.ceil(height * cfg["layout"]["world_layout_scale_y"])),
    )


def source_map_dimensions(config, aspect_ratio):
    """Keep metric aspect while meeting the final sampling demand in both axes."""
    cfg = validate_config(config)
    if not math.isfinite(aspect_ratio) or not 0.5 <= aspect_ratio <= 2:
        raise ValueError("Source-map aspect ratio must be between 0.5 and 2.")
    scaled_width, scaled_height = scaled_texture_dimensions(cfg)
    _, texture_height = texture_dimensions(cfg)
    height = math.ceil(max(texture_height, scaled_height, scaled_width / aspect_ratio))
    width = math.ceil(height * aspect_ratio)
    if width * height > MAX_SOURCE_PIXELS:
        raise ValueError(
            "Requested PPI and World Layout scale exceed the 100-megapixel "
            "source-map budget; reduce PPI or layout scale."
        )
    return width, height


def _label_identity(row):
    tags = {
        key: row[key]
        for key in (
            "place",
            "kind",
            "historic",
            "tourism",
            "amenity",
            "building",
            "highway",
            "railway",
        )
        if isinstance(row.get(key), str) and row[key]
    }
    if tags.get("place") in PLACE_LABELS:
        rank = 0
    elif (
        tags.get("historic") not in {None, "no"}
        or tags.get("tourism")
        in {"attraction", "museum", "artwork", "gallery", "viewpoint"}
        or tags.get("amenity") in {"place_of_worship", "theatre", "concert_hall"}
    ):
        rank = 1
    elif tags.get("kind") == "district":
        rank = 2
    elif tags.get("building") not in {None, "no"}:
        rank = 3
    else:
        rank = 4
    identifier = row.get("id")
    identity = {
        "source_id": identifier if isinstance(identifier, str) else None,
        "source_tags": tags,
    }
    # Geometry provides a stable final tie-break even for fixtures without IDs.
    return rank, identity, (identity["source_id"] or "", row["geometry"].wkb_hex)


def texture_dimensions(config: dict[str, Any]) -> tuple[int, int]:
    globe = validate_config(config)["globe"]
    # Equatorial circumference, not diameter, determines printed resolution.
    height = max(1, math.ceil(math.pi * globe["diameter_mm"] * globe["ppi"] / 50.8))
    return 2 * height, height


def feature_kind(row: dict) -> str:
    explicit = row.get("kind")
    if isinstance(explicit, str):
        return {"road": "major_road"}.get(explicit, explicit)
    if row.get("natural") == "water" or row.get("waterway") in {
        "river",
        "canal",
        "stream",
        "ditch",
    }:
        return "water"
    if (
        row.get("natural") in {"wood", "grassland", "wetland"}
        or row.get("landuse")
        in {"forest", "grass", "meadow", "recreation_ground", "allotments"}
        or row.get("leisure") in {"park", "garden", "nature_reserve"}
    ):
        return "park"
    if row.get("railway") in {"rail", "tram", "light_rail", "narrow_gauge"}:
        return "rail"
    if row.get("highway") in {
        "motorway",
        "motorway_link",
        "trunk",
        "trunk_link",
        "primary",
        "primary_link",
    }:
        return "major_road"
    if isinstance(row.get("highway"), str):
        return "secondary_road"
    return "label"


def _paint(image: Image.Image, geometry, color, width=1):
    """Composite polygon holes transparently so underlying layers survive."""
    if geometry.is_empty:
        return
    if (
        geometry.geom_type.startswith("Multi")
        or geometry.geom_type == "GeometryCollection"
    ):
        for part in geometry.geoms:
            _paint(image, part, color, width)
    elif geometry.geom_type == "Polygon":
        if not geometry.interiors:
            ImageDraw.Draw(image).polygon(list(geometry.exterior.coords), fill=color)
            return
        x0, y0, x1, y1 = geometry.bounds
        left, top = max(0, math.floor(x0)), max(0, math.floor(y0))
        right, bottom = min(image.width, math.ceil(x1) + 1), min(
            image.height, math.ceil(y1) + 1
        )
        if right <= left or bottom <= top:
            return
        mask = Image.new("L", (right - left, bottom - top), 0)
        draw = ImageDraw.Draw(mask)

        def coords(ring):
            return [(x - left, y - top) for x, y in ring.coords]

        draw.polygon(coords(geometry.exterior), fill=255)
        for ring in geometry.interiors:
            draw.polygon(coords(ring), fill=0)
        image.paste(color, (left, top, right, bottom), mask)
    elif geometry.geom_type in {"LineString", "LinearRing"}:
        ImageDraw.Draw(image).line(
            list(geometry.coords), fill=color, width=width, joint="curve"
        )


def render_clean_map(config, output_path, municipal_map=None):
    cfg = validate_config(config)
    if municipal_map is None:
        raise ValueError("Municipal map data is required before rendering.")
    frame = (
        gpd.read_file(municipal_map)
        if isinstance(municipal_map, (str, Path))
        else municipal_map.copy()
    )
    if frame.crs is None:
        raise ValueError("Municipal map data is missing a CRS.")
    frame = frame.to_crs(WORKING_CRS)
    if frame.empty:
        raise ValueError("Municipal map contains no features.")
    texture_width, texture_height = texture_dimensions(cfg)
    bounds = frame.total_bounds
    # The real OSM city node anchors Zentrum; deterministic fixtures use their
    # bounds centre unless the caller supplies an explicit WGS84 centre.
    center = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)
    records = frame.to_dict("records")
    for row in records:
        if row.get("place") == "city" and row.get("name") == "Leipzig":
            point = row["geometry"].representative_point()
            center = (point.x, point.y)
            break
    if cfg["layout"].get("center_lon_lat"):
        center = Transformer.from_crs(4326, WORKING_CRS, always_xy=True).transform(
            *cfg["layout"]["center_lon_lat"]
        )
    span_x = max(center[0] - bounds[0], bounds[2] - center[0], 1) * 2.06
    span_y = max(center[1] - bounds[1], bounds[3] - center[1], 1) * 2.06
    # Degenerate fixtures or narrow extents must not allocate a gigantic image.
    span_y = max(span_y, span_x / 2)
    span_x = max(span_x, span_y / 2)
    width, height = source_map_dimensions(cfg, span_x / span_y)
    sampling_scale = height / texture_height
    scaled_width, scaled_height = scaled_texture_dimensions(cfg)
    placement_x = (texture_width - scaled_width) // 2
    placement_y = (texture_height - scaled_height) // 2

    def project(coords):
        return np.column_stack(
            (
                (coords[:, 0] - center[0]) * width / span_x + width / 2,
                height / 2 - (coords[:, 1] - center[1]) * height / span_y,
            )
        )

    projected = shapely.transform(frame.geometry.array, project)
    palette = {key: tuple(value) for key, value in cfg["style"].items()}
    image = Image.new("RGB", (width, height), palette["background"])
    texture_px_mm = cfg["globe"]["ppi"] / 25.4
    px_mm = texture_px_mm * sampling_scale
    layers = {
        "land": [],
        "district": [],
        "park": [],
        "water": [],
        "rail": [],
        "secondary_road": [],
        "major_road": [],
        "label": [],
    }
    for row, geom in zip(records, projected, strict=True):
        layers.setdefault(feature_kind(row), []).append((row, geom))
    strokes = {"water": 0.16, "rail": 0.12, "secondary_road": 0.13, "major_road": 0.32}
    collision_features = []
    for kind, features in layers.items():
        if (
            kind == "label"
            or kind == "rail"
            and not cfg["layout"].get("show_railways", True)
        ):
            continue
        color = palette["land" if kind == "district" else kind]
        stroke = max(1, round(strokes.get(kind, 0.1) * px_mm))
        for _, geom in features:
            _paint(image, geom, color, stroke)
            if kind in {"water", "major_road", "rail"}:
                collision_features.append(
                    geom.buffer(stroke / 2)
                    if geom.geom_type.endswith("LineString")
                    else geom
                )
    tree = shapely.STRtree(collision_features)
    candidates = {}
    curated = cfg["layout"]["curated_landmarks"]
    for row, geom in zip(records, projected, strict=True):
        name = row.get("name:de")
        if not isinstance(name, str) or not name:
            name = row.get("name")
        if not isinstance(name, str) or not name:
            continue
        is_curated = name in curated
        district = row.get("kind") == "district" or row.get("place") in PLACE_LABELS
        if is_curated or district:
            entity_rank, identity, tie_break = _label_identity(row)
            priority = (
                0 if is_curated else 1 if row.get("kind") == "district" else 2,
                entity_rank,
                name,
                tie_break,
            )
            point = geom.representative_point()
            candidate = (priority, point.x, point.y, identity)
            if name not in candidates or priority < candidates[name][0]:
                candidates[name] = candidate
    omitted = [
        {"label": name, "reason": "not_found_in_municipal_map"}
        for name in curated
        if name not in candidates
    ]
    density = {"low": 20, "medium": 45, "high": 80}[cfg["layout"]["label_density"]]
    font_path = Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"
    font = ImageFont.truetype(
        str(font_path), round(max(8, 2.5 * texture_px_mm) * sampling_scale)
    )
    draw = ImageDraw.Draw(image)
    visible = []
    seam_shift = round(cfg["globe"]["seam_offset_deg"] / 360 * texture_width)
    seam_step = texture_width / cfg["globe"]["gore_count"]
    seam_margin = cfg["layout"]["gore_seam_margin_mm"] * texture_px_mm
    pole_margin = cfg["layout"]["pole_safety_zone_mm"] * texture_px_mm
    for name, (_, x, y, identity) in sorted(
        candidates.items(), key=lambda item: item[1][0]
    ):
        if len(visible) >= density:
            omitted.append({"label": name, "reason": "label_density", **identity})
            continue
        reason = "feature_collision"
        offsets = sorted(
            ((dx, dy) for dx in range(-8, 9, 2) for dy in range(-8, 9, 2)),
            key=lambda p: (p[0] ** 2 + p[1] ** 2, p),
        )
        for dx, dy in offsets:
            pos = (x + dx * px_mm, y + dy * px_mm)
            bbox = draw.textbbox(
                pos,
                name,
                font=font,
                anchor="mm",
                stroke_width=max(1, round(0.25 * px_mm)),
            )
            # Safety is evaluated in the final, scaled world placement.
            tx0, tx1 = (
                bbox[i] / width * scaled_width + placement_x + seam_shift
                for i in (0, 2)
            )
            ty0, ty1 = (bbox[i] / height * scaled_height + placement_y for i in (1, 3))
            if ty0 < pole_margin or ty1 > texture_height - pole_margin:
                reason = "pole_safety_zone"
                continue
            if tx0 - seam_shift < 0 or tx1 - seam_shift > texture_width:
                reason = "world_layout_crop"
                continue
            if math.floor((tx0 - seam_margin) / seam_step) != math.floor(
                (tx1 + seam_margin) / seam_step
            ):
                reason = "gore_seam"
                continue
            box = shapely.box(*bbox)
            if bbox[0] < 0 or bbox[2] > width or bbox[1] < 0 or bbox[3] > height:
                reason = "map_edge"
                continue
            if any(box.intersects(shapely.box(*prior["bbox"])) for prior in visible):
                reason = "label_collision"
                continue
            if len(tree.query(box, predicate="intersects")):
                reason = "feature_collision"
                continue
            draw.text(
                pos,
                name,
                font=font,
                fill=palette["label"],
                anchor="mm",
                stroke_width=max(1, round(0.25 * px_mm)),
                stroke_fill=palette["background"],
            )
            visible.append(
                {
                    "label": name,
                    "bbox": list(bbox),
                    "anchor_px": [x, y],
                    "position_px": list(pos),
                    "texture_bbox_unwrapped": [tx0, ty0, tx1, ty1],
                    **identity,
                }
            )
            break
        else:
            omitted.append(
                {"label": name, "reason": reason, "anchor_px": [x, y], **identity}
            )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, dpi=(cfg["globe"]["ppi"], cfg["globe"]["ppi"]))
    if cfg["layout"]["exterior"] != "blank":
        boundary = shapely.union_all(
            [
                geom
                for row, geom in zip(records, projected, strict=True)
                if row.get("kind") in {"district", "land"}
            ]
        )
        if boundary.is_empty:
            raise ValueError("Exterior variants require municipal boundary polygons.")
        mask = Image.new("L", image.size, 0)
        _paint(mask, boundary, 255)
        mask.save(path.with_suffix(".boundary.png"))
    metadata = {
        "center_metric": list(center),
        "center_pixel": [width / 2, height / 2],
        "bounds_metric": bounds.tolist(),
        "span_metric": [span_x, span_y],
        "crs": WORKING_CRS,
        "sampling": {
            "source_pixels": [width, height],
            "scaled_map_pixels": [scaled_width, scaled_height],
            "texture_pixels": [texture_width, texture_height],
            "source_pixels_per_output_pixel": [
                width / scaled_width,
                height / scaled_height,
            ],
            "source_effective_ppi": [
                width
                / scaled_width
                * texture_width
                * 25.4
                / (math.pi * cfg["globe"]["diameter_mm"]),
                height
                / scaled_height
                * texture_height
                * 50.8
                / (math.pi * cfg["globe"]["diameter_mm"]),
            ],
            "source_pixel_budget": MAX_SOURCE_PIXELS,
        },
        "rendered_labels": visible,
        "omitted_labels": omitted,
    }
    path.with_suffix(".json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "image_path": path,
        "width_px": width,
        "height_px": height,
        "rendered_labels": [entry["label"] for entry in visible],
        "omitted_labels": omitted,
        "layout": metadata,
    }


def generate_globe_texture(config, output_path, *, source_map=None):
    cfg = validate_config(config)
    path = Path(output_path)
    source = Path(source_map) if source_map else path.parent / cfg["paths"]["map_file"]
    if not source.is_file():
        raise FileNotFoundError(f"Rendered map not found: {source}")
    width, height = texture_dimensions(cfg)
    scaled_width, scaled_height = scaled_texture_dimensions(cfg)
    with Image.open(source) as loaded:
        if loaded.width * loaded.height > MAX_SOURCE_PIXELS:
            raise ValueError("Source map exceeds the 100-megapixel source-map budget.")
        if loaded.width < scaled_width or loaded.height < scaled_height:
            raise ValueError(
                "Source map has insufficient resolution for the requested effective PPI; rerender the map."
            )
        base = loaded.convert("RGB").resize(
            (scaled_width, scaled_height), Image.Resampling.LANCZOS
        )
    texture = Image.new("RGB", (width, height), tuple(cfg["style"]["background"]))
    texture.paste(base, ((width - scaled_width) // 2, (height - scaled_height) // 2))
    if cfg["layout"]["exterior"] != "blank":
        from .exterior import compose_exterior

        texture = compose_exterior(texture, source, cfg)
    texture = ImageChops.offset(
        texture, round(cfg["globe"]["seam_offset_deg"] / 360 * width), 0
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    texture.save(path, dpi=(cfg["globe"]["ppi"], cfg["globe"]["ppi"]))
    return path

"""Export browser-sized assets and authoritative geometry for the static viewer."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from PIL import Image

from .config import validate_config

FINISHED_TEXTURE_WIDTH = 2048
GORE_TEXTURE_HEIGHT = 1600
GORE_VERTICAL_SEGMENTS = 120
GORE_MAX_LONGITUDE_STEP = math.radians(3)
PRESET_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def _write_webp(source: Path, destination: Path, *, max_width: int, max_height: int):
    with Image.open(source) as image:
        scale = min(1, max_width / image.width, max_height / image.height)
        size = (
            max(1, round(image.width * scale)),
            max(1, round(image.height * scale)),
        )
        resized = image.convert("RGBA" if "A" in image.getbands() else "RGB").resize(
            size, Image.Resampling.LANCZOS
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        resized.save(destination, format="WEBP", quality=90, method=6)


def _resample(points: list[list[float]], segments: int) -> list[list[float]]:
    return [
        points[round(index * (len(points) - 1) / segments)]
        for index in range(segments + 1)
    ]


def _spherical_point(
    point: list[float], gore: dict[str, Any], config: dict[str, Any]
) -> list[float]:
    globe = config["globe"]
    height = float(gore["pole_to_pole_mm"])
    inset = float(gore["inset_mm"])
    y_mm = float(point[1]) - inset
    x_mm = float(point[0]) - inset - float(gore["equator_width_mm"]) / 2
    latitude = math.pi / 2 - math.pi * y_mm / height
    taper = math.sin(math.pi * y_mm / height)
    if abs(taper) < 1e-12:
        longitude_fraction = (int(gore["longitude_slot"]) + 0.5) / globe["gore_count"]
    else:
        longitude_fraction = (int(gore["longitude_slot"]) + 0.5) / globe[
            "gore_count"
        ] + x_mm / (math.pi * globe["diameter_mm"] * taper)
    longitude = 2 * math.pi * longitude_fraction
    cos_latitude = math.cos(latitude)
    return [
        cos_latitude * math.sin(longitude),
        math.sin(latitude),
        cos_latitude * math.cos(longitude),
    ]


def _texture_uv(point: list[float], gore: dict[str, Any]) -> list[float]:
    return [
        float(point[0]) / float(gore["width_mm"]),
        1 - float(point[1]) / float(gore["height_mm"]),
    ]


def _strip_mesh(
    left: list[list[float]],
    right: list[list[float]],
    gore: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, list[float] | list[int]]:
    positions: list[float] = []
    uvs: list[float] = []
    indices: list[int] = []
    # Paper width shrinks with latitude; recover the angular span before
    # subdividing. This also handles the narrower overlap strip and wide gores.
    radius = config["globe"]["diameter_mm"] / 2
    spans = []
    for a, b in zip(left, right, strict=True):
        taper = math.sin(math.pi * (a[1] - gore["inset_mm"]) / gore["pole_to_pole_mm"])
        if abs(taper) > 1e-12:
            spans.append(abs(b[0] - a[0]) / (radius * taper))
    segments = max(1, math.ceil(max(spans, default=0) / GORE_MAX_LONGITUDE_STEP))
    stride = segments + 1
    for left_point, right_point in zip(left, right, strict=True):
        for column in range(stride):
            fraction = column / segments
            point = [a + (b - a) * fraction for a, b in zip(left_point, right_point)]
            positions.extend(_spherical_point(point, gore, config))
            uvs.extend(_texture_uv(point, gore))
    for row in range(len(left) - 1):
        for column in range(segments):
            start = row * stride + column
            indices.extend(
                (
                    start,
                    start + stride,
                    start + 1,
                    start + 1,
                    start + stride,
                    start + stride + 1,
                )
            )
    return {"positions": positions, "uvs": uvs, "indices": indices}


def _line_points(
    points: list[list[float]], gore: dict[str, Any], config: dict[str, Any]
) -> list[float]:
    return [
        coordinate
        for point in points
        for coordinate in _spherical_point(point, gore, config)
    ]


def _export_gore(gore: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    outline = gore["outline_mm"]
    half = len(outline) // 2
    left = _resample(outline[:half], GORE_VERTICAL_SEGMENTS)
    right = _resample(list(reversed(outline[half:])), GORE_VERTICAL_SEGMENTS)
    seam = _resample(gore["seam_mm"], GORE_VERTICAL_SEGMENTS)
    return {
        "id": f"Gore {int(gore['index']) + 1:02d}",
        "index": gore["index"],
        "longitude_slot": gore["longitude_slot"],
        "equator_width_mm": gore["equator_width_mm"],
        "overlap_equator_mm": gore["overlap_equator_mm"],
        "texture": f"gores/{Path(gore['png']).with_suffix('.webp').name}",
        "mesh": _strip_mesh(left, right, gore, config),
        "nominal_seam": _line_points(seam, gore, config),
        "cut_outline": _line_points(left + list(reversed(right)), gore, config),
        "overlap_mesh": _strip_mesh(seam, right, gore, config),
    }


def _validate_preset_id(preset_id: str) -> str:
    if not PRESET_ID_PATTERN.fullmatch(preset_id):
        raise ValueError(
            "Preset ID must contain lowercase letters, numbers, and single hyphens."
        )
    return preset_id


def _preset_entry(preset_id: str, config: dict[str, Any]) -> dict[str, Any]:
    from .exterior import EXTERIORS

    globe = config["globe"]
    layout = config["layout"]
    diameter = globe["diameter_mm"]
    return {
        "id": preset_id,
        "label": (
            f"{diameter:g} mm - {layout['label_density']} labels"
            if layout["exterior"] == "blank"
            else EXTERIORS[layout["exterior"]][0]
        ),
        "description": EXTERIORS[layout["exterior"]][1],
        "exterior": layout["exterior"],
        "manifest": f"{preset_id}/preview-manifest.json",
        "diameter_mm": diameter,
        "gore_count": globe["gore_count"],
        "label_density": layout["label_density"],
        "ppi": globe["ppi"],
    }


def _write_preset_index(
    site_root: Path, preset_id: str, config: dict[str, Any]
) -> Path:
    index_path = site_root / "presets.json"
    entries = {}
    if index_path.is_file():
        existing = json.loads(index_path.read_text(encoding="utf-8"))
        for entry in existing.get("presets", []):
            if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                entries[entry["id"]] = entry
    entries[preset_id] = _preset_entry(preset_id, config)
    presets = sorted(
        entries.values(),
        key=lambda entry: (
            {"terrain": 0, "ocean": 1, "fog": 2, "blank": 3}.get(
                entry.get("exterior"), 4
            ),
            entry["id"],
        ),
    )
    index_path.write_text(
        json.dumps(
            {"schema_version": 1, "presets": presets}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    return index_path


def export_web_preview(
    texture_path: str | Path,
    gore_dir: str | Path,
    output_dir: str | Path,
    *,
    config: dict[str, Any] | None = None,
    preset_id: str = "default",
) -> Path:
    """Write reduced WebP assets and a manifest for the static Three.js viewer."""
    texture = Path(texture_path)
    root = Path(gore_dir)
    site_root = Path(output_dir)
    preset = _validate_preset_id(preset_id)
    destination = site_root / preset
    manifest_path = root / "geometry-manifest.json"
    if not texture.is_file():
        raise FileNotFoundError(f"Globe texture not found: {texture}")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Gore geometry manifest not found: {manifest_path}")
    geometry = json.loads(manifest_path.read_text(encoding="utf-8"))
    cfg = validate_config(config if config is not None else geometry["config"])
    gores = geometry.get("gores", [])
    if len(gores) != cfg["globe"]["gore_count"]:
        raise ValueError("Gore geometry does not match the configured gore count.")

    _write_webp(
        texture,
        destination / "texture.webp",
        max_width=FINISHED_TEXTURE_WIDTH,
        max_height=FINISHED_TEXTURE_WIDTH // 2,
    )
    exported_gores = []
    for gore in gores:
        source = root / gore["png"]
        if not source.is_file():
            raise FileNotFoundError(f"Gore texture not found: {source}")
        _write_webp(
            source,
            destination / "gores" / Path(gore["png"]).with_suffix(".webp").name,
            max_width=GORE_TEXTURE_HEIGHT,
            max_height=GORE_TEXTURE_HEIGHT,
        )
        exported_gores.append(_export_gore(gore, cfg))

    preview_manifest = {
        "schema_version": 1,
        "preset_id": preset,
        "exterior": cfg["layout"]["exterior"],
        "city": cfg["city"],
        "texture": "texture.webp",
        "diameter_mm": cfg["globe"]["diameter_mm"],
        "circumference_mm": math.pi * cfg["globe"]["diameter_mm"],
        "gore_count": cfg["globe"]["gore_count"],
        "gore_order": cfg["layout"]["gore_order"],
        "assembly_overlap_mm": cfg["globe"]["assembly_overlap_mm"],
        "pole_safety_zone_mm": cfg["layout"]["pole_safety_zone_mm"],
        "gores": exported_gores,
    }
    exported_manifest = destination / "preview-manifest.json"
    destination.mkdir(parents=True, exist_ok=True)
    exported_manifest.write_text(
        json.dumps(preview_manifest, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    _write_preset_index(site_root, preset, cfg)
    return exported_manifest

from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "city": "Leipzig",
    "globe": {
        "diameter_mm": 300,
        "gore_count": 12,
        "assembly_overlap_mm": 2,
        "seam_offset_deg": 0,
        "ppi": 200,
        "paper_size": "A4",
    },
    "layout": {
        "tile_overlap_mm": 10,
        "print_margin_mm": 10,
        "pole_safety_zone_mm": 20,
        "seam_offset_deg": 0,
        "gore_seam_margin_mm": 10,
        "world_layout_scale_x": 1.0,
        "world_layout_scale_y": 1.0,
        "gore_order": "clockwise",
        "label_density": "medium",
        "curated_landmarks": [
            "Leipzig",
            "Mitte",
            "Connewitz",
            "Schönefeld",
            "Plagwitz",
        ],
        "source_cache_dir": ".cache",
    },
    "paths": {
        "output_dir": "output",
        "map_file": "leipzig-map.png",
        "texture_file": "leipzig-texture.png",
        "gore_dir": "gores",
        "pdf_file": "leipzig-globe-print.pdf",
        "preview_dir": "preview",
        "report_file": "build-report.json",
    },
}


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _validate_non_negative_number(name: str, value: Any) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"Invalid {name}: expected a non-negative number.")
    numeric = float(value)
    if numeric < 0:
        raise ValueError(f"Invalid {name}: must be zero or greater.")
    return numeric


def _validate_positive_number(name: str, value: Any) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"Invalid {name}: expected a positive number.")
    numeric = float(value)
    if numeric <= 0:
        raise ValueError(f"Invalid {name}: must be greater than zero.")
    return numeric


def _validate_seam_offset(name: str, value: Any) -> float:
    number = _validate_non_negative_number(name, value)
    if number > 360:
        raise ValueError(f"Invalid {name}: must be between 0 and 360 degrees.")
    return number


def validate_config(config: Mapping[str, Any] | None) -> dict[str, Any]:
    merged = _deep_merge(DEFAULT_CONFIG, config or {})
    city = str(merged.get("city", "")).strip()
    if not city:
        raise ValueError("Configuration is missing a city. Supported city: Leipzig.")
    if city.lower() != "leipzig":
        raise ValueError(
            f"Unsupported city configuration: {city!r}. Only Leipzig is supported."
        )
    merged["city"] = "Leipzig"

    globe = merged.get("globe", {})
    layout = merged.get("layout", {})

    globe["diameter_mm"] = _validate_positive_number(
        "globe.diameter_mm", globe.get("diameter_mm")
    )
    gore_count = globe.get("gore_count")
    if (
        not isinstance(gore_count, int)
        or isinstance(gore_count, bool)
        or gore_count <= 0
    ):
        raise ValueError(
            "Invalid globe settings: gore_count must be a positive integer."
        )
    globe["gore_count"] = gore_count
    globe["assembly_overlap_mm"] = _validate_non_negative_number(
        "globe.assembly_overlap_mm", globe.get("assembly_overlap_mm")
    )
    globe["ppi"] = _validate_positive_number("globe.ppi", globe.get("ppi"))
    paper_size = str(globe.get("paper_size", "A4")).upper()
    if paper_size not in {"A4"}:
        raise ValueError(
            f"Unsupported paper size: {paper_size!r}. Only A4 is currently supported."
        )
    globe["paper_size"] = paper_size

    layout["tile_overlap_mm"] = _validate_non_negative_number(
        "layout.tile_overlap_mm", layout.get("tile_overlap_mm")
    )
    layout["print_margin_mm"] = _validate_non_negative_number(
        "layout.print_margin_mm", layout.get("print_margin_mm")
    )
    layout["pole_safety_zone_mm"] = _validate_non_negative_number(
        "layout.pole_safety_zone_mm", layout.get("pole_safety_zone_mm")
    )
    layout["gore_seam_margin_mm"] = _validate_non_negative_number(
        "layout.gore_seam_margin_mm",
        layout.get("gore_seam_margin_mm", DEFAULT_CONFIG["layout"]["gore_seam_margin_mm"]),
    )
    layout["world_layout_scale_x"] = _validate_positive_number(
        "layout.world_layout_scale_x", layout.get("world_layout_scale_x")
    )
    layout["world_layout_scale_y"] = _validate_positive_number(
        "layout.world_layout_scale_y", layout.get("world_layout_scale_y")
    )

    curated_landmarks = layout.get("curated_landmarks", DEFAULT_CONFIG["layout"]["curated_landmarks"])
    if curated_landmarks is None:
        curated_landmarks = []
    if not isinstance(curated_landmarks, list) or not all(
        isinstance(item, str) and item.strip() for item in curated_landmarks
    ):
        raise ValueError(
            "Invalid layout settings: curated_landmarks must be a list of non-empty strings."
        )
    layout["curated_landmarks"] = [str(item).strip() for item in curated_landmarks]

    seam_offset = _validate_seam_offset(
        "globe.seam_offset_deg",
        globe.get("seam_offset_deg", layout.get("seam_offset_deg", 0)),
    )
    globe["seam_offset_deg"] = seam_offset
    layout_seam = _validate_seam_offset(
        "layout.seam_offset_deg",
        layout.get("seam_offset_deg", globe.get("seam_offset_deg", 0)),
    )
    layout["seam_offset_deg"] = layout_seam
    if abs(globe["seam_offset_deg"] - layout["seam_offset_deg"]) > 1e-9:
        raise ValueError(
            "globe.seam_offset_deg and layout.seam_offset_deg must match when both are configured."
        )

    gore_order = str(layout.get("gore_order", "clockwise")).lower()
    if gore_order not in {"clockwise", "counterclockwise"}:
        raise ValueError(
            "Invalid layout settings: gore_order must be 'clockwise' or 'counterclockwise'."
        )
    layout["gore_order"] = gore_order

    label_density = str(layout.get("label_density", "medium")).lower()
    if label_density not in {"low", "medium", "high"}:
        raise ValueError(
            "Invalid layout settings: label_density must be 'low', 'medium', or 'high'."
        )
    layout["label_density"] = label_density

    return merged


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        default_path = default_config_path()
        if default_path.exists():
            source = default_path
        else:
            return validate_config(DEFAULT_CONFIG)
    else:
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(f"Configuration file not found: {source}")

    contents = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if not isinstance(contents, dict):
        raise TypeError("Configuration file must contain a YAML mapping.")

    merged = _deep_merge(DEFAULT_CONFIG, contents)
    return validate_config(merged)


try:
    from leipzig_globe import __version__
except ImportError:  # pragma: no cover
    __version__ = "0.1.0"


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "default.yaml"

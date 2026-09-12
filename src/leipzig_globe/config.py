from __future__ import annotations

import copy
import math
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
        "seam_offset_deg": 15,
        "ppi": 200,
        "paper_size": "A4",
    },
    "style": {
        "background": [247, 244, 238],
        "land": [247, 244, 238],
        "water": [132, 178, 198],
        "park": [186, 210, 188],
        "major_road": [92, 100, 105],
        "secondary_road": [170, 169, 161],
        "rail": [140, 145, 150],
        "label": [70, 71, 73],
    },
    "layout": {
        "tile_overlap_mm": 10,
        "print_margin_mm": 10,
        "pole_safety_zone_mm": 20,
        "seam_offset_deg": 15,
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
            "Völkerschlachtdenkmal",
            "Thomaskirche",
            "Gewandhaus",
        ],
        "source_cache_dir": ".cache/sources-2026-09-01",
        "show_railways": True,
        "gore_centerlines": False,
        "gore_numbering": True,
        "preview_overlays": False,
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
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError(f"Invalid {name}: must be zero or greater.")
    return numeric


def _validate_positive_number(name: str, value: Any) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"Invalid {name}: expected a positive number.")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"Invalid {name}: must be greater than zero.")
    return numeric


def _validate_seam_offset(name: str, value: Any) -> float:
    number = _validate_non_negative_number(name, value)
    if number > 360:
        raise ValueError(f"Invalid {name}: must be between 0 and 360 degrees.")
    return number


def _validate_rgb_triplet(name: str, value: Any) -> list[int]:
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate.startswith("#") or len(candidate) != 7:
            raise ValueError(
                f"Invalid {name}: expected an RGB triplet like [r, g, b] or '#RRGGBB'."
            )
        try:
            return [int(candidate[i : i + 2], 16) for i in (1, 3, 5)]
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise ValueError(
                f"Invalid {name}: unable to parse hexadecimal color."
            ) from exc

    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"Invalid {name}: expected a 3-item RGB triplet.")

    rgb = []
    for index, component in enumerate(value):
        if not isinstance(component, (int, float)) or isinstance(component, bool):
            raise TypeError(f"Invalid {name}[{index}]: expected a numeric channel.")
        channel = round(component)
        if not 0 <= channel <= 255:
            raise ValueError(
                f"Invalid {name}[{index}]: channel must be between 0 and 255."
            )
        rgb.append(int(channel))
    return rgb


def validate_config(config: Mapping[str, Any] | None) -> dict[str, Any]:
    if config is not None and not isinstance(config, Mapping):
        raise TypeError("Configuration must be a mapping.")
    merged = _deep_merge(DEFAULT_CONFIG, config or {})
    if merged["version"] != 1:
        raise ValueError("Unsupported configuration version; expected version 1.")
    for section in ("globe", "style", "layout", "paths"):
        if not isinstance(merged[section], Mapping):
            raise TypeError(f"Configuration section {section} must be a mapping.")
    if config:
        supplied_globe = config.get("globe", {})
        supplied_layout = config.get("layout", {})
        if (
            "seam_offset_deg" in supplied_globe
            and "seam_offset_deg" not in supplied_layout
        ):
            merged["layout"]["seam_offset_deg"] = supplied_globe["seam_offset_deg"]
        elif (
            "seam_offset_deg" in supplied_layout
            and "seam_offset_deg" not in supplied_globe
        ):
            merged["globe"]["seam_offset_deg"] = supplied_layout["seam_offset_deg"]
    city = str(merged.get("city", "")).strip()
    if not city:
        raise ValueError("Configuration is missing a city. Supported city: Leipzig.")
    if city.lower() != "leipzig":
        raise ValueError(
            f"Unsupported city configuration: {city!r}. Only Leipzig is supported."
        )
    merged["city"] = "Leipzig"

    globe = merged.get("globe", {})
    style = merged.get("style", {})
    layout = merged.get("layout", {})

    for key in DEFAULT_CONFIG["style"]:
        default_value = DEFAULT_CONFIG["style"][key]
        style[key] = _validate_rgb_triplet(
            f"style.{key}", style.get(key, default_value)
        )
    merged["style"] = style

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
        layout.get(
            "gore_seam_margin_mm", DEFAULT_CONFIG["layout"]["gore_seam_margin_mm"]
        ),
    )
    layout["world_layout_scale_x"] = _validate_positive_number(
        "layout.world_layout_scale_x", layout.get("world_layout_scale_x")
    )
    layout["world_layout_scale_y"] = _validate_positive_number(
        "layout.world_layout_scale_y", layout.get("world_layout_scale_y")
    )

    curated_landmarks = layout.get(
        "curated_landmarks", DEFAULT_CONFIG["layout"]["curated_landmarks"]
    )
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

    margin = layout["print_margin_mm"]
    if not 8 <= margin <= 40:
        raise ValueError(
            "layout.print_margin_mm must be between 8 and 40 mm to fit print guides and calibration."
        )
    if layout["tile_overlap_mm"] >= min(210 - 2 * margin, 297 - 2 * margin):
        raise ValueError(
            "layout.tile_overlap_mm must be smaller than the printable page."
        )
    circumference = math.pi * globe["diameter_mm"]
    if globe["assembly_overlap_mm"] >= circumference / globe["gore_count"] / 2:
        raise ValueError(
            "globe.assembly_overlap_mm must be less than half a gore equatorial width."
        )
    if layout["pole_safety_zone_mm"] >= circumference / 4:
        raise ValueError("layout.pole_safety_zone_mm leaves no nonpolar map area.")
    if (circumference * globe["ppi"] / 25.4) ** 2 / 2 > 100_000_000:
        raise ValueError(
            "Requested diameter and PPI exceed the 100-megapixel texture budget; reduce PPI."
        )
    for key in (
        "show_railways",
        "gore_centerlines",
        "gore_numbering",
        "preview_overlays",
    ):
        if not isinstance(layout[key], bool):
            raise TypeError(f"layout.{key} must be true or false.")
    center = layout.get("center_lon_lat")
    if center is not None:
        if (
            not isinstance(center, (list, tuple))
            or len(center) != 2
            or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in center)
        ):
            raise ValueError(
                "layout.center_lon_lat must contain two finite WGS84 coordinates."
            )
        if not (12.2 <= center[0] <= 12.6 and 51.2 <= center[1] <= 51.5):
            raise ValueError("layout.center_lon_lat must lie within Leipzig.")
    for key, value in merged["paths"].items():
        if key == "output_dir":
            continue
        if (
            not isinstance(value, str)
            or not value
            or Path(value).is_absolute()
            or ".." in Path(value).parts
        ):
            raise ValueError(
                f"paths.{key} must be a relative path inside the output directory."
            )

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

    return validate_config(contents)


try:
    from leipzig_globe import __version__
except ImportError:  # pragma: no cover
    __version__ = "0.1.0"


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "default.yaml"

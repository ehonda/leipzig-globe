from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping

import yaml

DEFAULT_CONFIG: dict[str, Any] = {
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
        "world_layout_scale_x": 1.0,
        "world_layout_scale_y": 1.0,
        "gore_order": "clockwise",
        "source_cache_dir": ".cache",
    },
    "paths": {
        "output_dir": "output",
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


def validate_config(config: Mapping[str, Any]) -> dict[str, Any]:
    merged = _deep_merge(DEFAULT_CONFIG, config)
    globe = merged.get("globe", {})
    layout = merged.get("layout", {})

    if not isinstance(globe.get("diameter_mm"), (int, float)) or globe["diameter_mm"] <= 0:
        raise ValueError("Invalid globe settings: diameter_mm must be a positive number.")
    if not isinstance(globe.get("gore_count"), int) or globe["gore_count"] <= 0:
        raise ValueError("Invalid globe settings: gore_count must be a positive integer.")
    if not isinstance(globe.get("assembly_overlap_mm"), (int, float)) or globe["assembly_overlap_mm"] < 0:
        raise ValueError("Invalid globe settings: assembly_overlap_mm must be zero or greater.")
    if not isinstance(globe.get("ppi"), (int, float)) or globe["ppi"] <= 0:
        raise ValueError("Invalid globe settings: ppi must be a positive number.")
    if not isinstance(layout.get("print_margin_mm"), (int, float)) or layout["print_margin_mm"] < 0:
        raise ValueError("Invalid layout settings: print_margin_mm must be zero or greater.")
    seam = float(layout.get("seam_offset_deg", 0))
    if seam < 0 or seam > 360:
        raise ValueError("Invalid layout settings: seam_offset_deg must be between 0 and 360 degrees.")

    return merged


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config = copy.deepcopy(DEFAULT_CONFIG)
    if path is None:
        return validate_config(config)

    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Configuration file not found: {source}")

    contents = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if not isinstance(contents, dict):
        raise ValueError("Configuration file must contain a YAML mapping.")

    merged = _deep_merge(config, contents)
    return validate_config(merged)


try:
    from leipzig_globe import __version__
except Exception:  # pragma: no cover
    __version__ = "0.1.0"


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "default.yaml"

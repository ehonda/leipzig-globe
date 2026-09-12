"""Offline build orchestration and artifact validation."""

from __future__ import annotations

import json
import math
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from .config import load_config, validate_config
from .fetcher import compute_sha256, load_source_manifests, verify_manifest
from .municipal_map import derive_municipal_map_from_sources
from .preview import VIEWPOINTS, generate_preview_set
from .printing import build_gore_set, build_pdf, gore_outline_points
from .rendering import (
    generate_globe_texture,
    render_clean_map,
    scaled_texture_dimensions,
    texture_dimensions,
)

__all__ = [
    "build_artifacts",
    "build_gore_set",
    "build_pdf",
    "ensure_osmium_available",
    "generate_globe_texture",
    "generate_preview_set",
    "gore_outline_points",
    "render_clean_map",
    "texture_dimensions",
    "validate_output_directory",
]


def ensure_osmium_available():
    if shutil.which("osmium") is None:
        raise RuntimeError(
            "Osmium is required. Install osmium-tool and add it to PATH."
        )


def _cached_source_paths(config):
    cache = Path(config["layout"]["source_cache_dir"])
    sources = {
        "osm_pbf": cache / "sachsen-latest.osm.pbf",
        "municipal_boundary": cache / "leipzig-municipal-boundary.geojson",
    }
    for path in sources.values():
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing required cached source: {path}. Run fetch-data first."
            )
    manifests = load_source_manifests(cache)
    for path in sources.values():
        manifest = manifests.get(path.name)
        if manifest is None or not manifest.expected_digest:
            raise ValueError(
                f"Missing source manifest/checksum for {path.name}; run fetch-data first."
            )
        verify_manifest(manifest, path)
    return sources, {
        key: manifests[path.name].as_dict() for key, path in sources.items()
    }


def write_build_report(
    config,
    output_dir,
    artifact_paths,
    *,
    omitted_labels=None,
    source_provenance=None,
    performance=None,
    physical=None,
):
    root = Path(output_dir)
    report = root / config["paths"]["report_file"]
    report.parent.mkdir(parents=True, exist_ok=True)
    hashes = {}
    generated = []
    for key, values in artifact_paths.items():
        if key in {"report", "gore_dir"}:
            continue
        generated.extend(
            root / value for value in (values if isinstance(values, list) else [values])
        )
    for key in ("map", "pdf"):
        if key in artifact_paths:
            suffix = ".json" if key == "map" else ".tiles.json"
            generated.append((root / artifact_paths[key]).with_suffix(suffix))
    for value in artifact_paths.get("gore_files", []):
        generated.extend(
            (root / value).with_suffix(suffix) for suffix in (".json", ".png")
        )
    if artifact_paths.get("gore_dir"):
        generated.append(root / artifact_paths["gore_dir"] / "geometry-manifest.json")
    if artifact_paths.get("preview"):
        generated.append((root / artifact_paths["preview"][0]).parent / "metadata.json")
    for path in sorted(set(generated)):
        if path.is_file():
            hashes[path.relative_to(root).as_posix()] = compute_sha256(path)
    payload = {
        "schema_version": 1,
        "city": "Leipzig",
        "config": config,
        "source_provenance": source_provenance or {},
        "artifacts": artifact_paths,
        "artifact_sha256": hashes,
        "omitted_labels": omitted_labels or [],
        "performance": performance or {},
        "physical": physical or {},
        "attribution": [
            "© OpenStreetMap contributors, https://www.openstreetmap.org/copyright",
            "Stadt Leipzig, Amt für Statistik und Wahlen — Stadtbezirke_Leipzig_UTM33N (official open geodata)",
        ],
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }
    report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def build_artifacts(
    config: dict[str, Any] | None = None, output_dir: str | Path = "output"
):
    cfg = validate_config(config if config is not None else load_config())
    work = Path(output_dir)
    work.mkdir(parents=True, exist_ok=True)
    sources, manifests = _cached_source_paths(cfg)
    started = time.perf_counter()
    municipal = derive_municipal_map_from_sources(
        sources["municipal_boundary"],
        sources["osm_pbf"],
        work / "municipal-map.geojson",
        curated_landmarks=cfg["layout"]["curated_landmarks"],
    )
    municipal_path = Path(municipal["output_path"])
    map_path = work / cfg["paths"]["map_file"]
    rendered = render_clean_map(cfg, map_path, municipal_map=municipal_path)
    performance = dict(municipal.get("performance", {}))
    performance.update(
        seconds_to_map=time.perf_counter() - started,
        municipal_feature_count=municipal["feature_count"],
        municipal_bytes=municipal_path.stat().st_size,
        municipal_tag_counts=municipal.get("tag_counts", {}),
    )
    texture = work / cfg["paths"]["texture_file"]
    generate_globe_texture(cfg, texture, source_map=map_path)
    gore_dir = work / cfg["paths"]["gore_dir"]
    gores = build_gore_set(texture, gore_dir, cfg)
    pdf = work / cfg["paths"]["pdf_file"]
    build_pdf(gores, pdf, config=cfg)
    provenance = {key: str(path) for key, path in sources.items()}
    provenance["manifests"] = manifests
    previews = generate_preview_set(
        texture, work / cfg["paths"]["preview_dir"], config=cfg, provenance=provenance
    )
    paths = {
        "municipal_map": municipal_path,
        "map": map_path,
        "texture": texture,
        "gore_dir": gore_dir,
        "pdf": pdf,
        "report": work / cfg["paths"]["report_file"],
    }
    artifacts = {key: path.relative_to(work).as_posix() for key, path in paths.items()}
    artifacts["gore_files"] = [path.relative_to(work).as_posix() for path in gores]
    artifacts["preview"] = [path.relative_to(work).as_posix() for path in previews]
    tile_path = pdf.with_suffix(".tiles.json")
    tiles = json.loads(tile_path.read_text()) if tile_path.exists() else {}
    physical = {
        "diameter_mm": cfg["globe"]["diameter_mm"],
        "circumference_mm": math.pi * cfg["globe"]["diameter_mm"],
        "pole_to_pole_mm": math.pi * cfg["globe"]["diameter_mm"] / 2,
        "texture_pixels": list(texture_dimensions(cfg)),
        "map_sampling": rendered.get("layout", {}).get("sampling"),
        "tile_count": len(tiles.get("tiles", [])),
    }
    performance["total_seconds"] = time.perf_counter() - started
    report = write_build_report(
        cfg,
        work,
        artifacts,
        omitted_labels=rendered["omitted_labels"],
        source_provenance=provenance,
        performance=performance,
        physical=physical,
    )
    return {
        **paths,
        "gores": gores,
        "preview": previews,
        "report": report,
        "omitted_labels": rendered["omitted_labels"],
    }


def validate_output_directory(output_dir):
    from pypdf import PdfReader

    root = Path(output_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Output directory not found: {root}")
    reports = []
    # A parent build may contain independent preset builds. Prefer its own
    # canonical report; nested reports must not make that build ambiguous.
    canonical = root / "build-report.json"
    candidates = [canonical] if canonical.is_file() else root.rglob("*.json")
    for path in candidates:
        with path.open(encoding="utf-8") as handle:
            if "artifact_sha256" in handle.read(20000):
                reports.append(path)
    if len(reports) != 1:
        raise ValueError("Expected exactly one Build Report with artifact checksums.")
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    cfg = validate_config(report["config"])

    def artifact(relative):
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError(f"Artifact path escapes output directory: {relative}")
        if not path.is_file():
            raise FileNotFoundError(f"Missing required artifact: {relative}")
        return path

    hashes = report.get("artifact_sha256")
    if not hashes:
        raise ValueError("Build Report has no artifact checksums.")
    for relative, digest in hashes.items():
        if compute_sha256(artifact(relative)) != digest:
            raise ValueError(f"Artifact checksum mismatch: {relative}")
    entries = report["artifacts"]
    for key in ("map", "texture", "municipal_map", "pdf"):
        artifact(entries[key])
    with Image.open(artifact(entries["texture"])) as texture:
        if texture.size != texture_dimensions(cfg):
            raise ValueError(
                "Texture dimensions do not match physical PPI / exact 2:1 ratio."
            )
    sampling = report.get("physical", {}).get("map_sampling")
    if sampling is not None:
        with Image.open(artifact(entries["map"])) as source_map:
            source_size = source_map.size
        scaled_size = scaled_texture_dimensions(cfg)
        if (
            list(source_size) != sampling["source_pixels"]
            or list(scaled_size) != sampling["scaled_map_pixels"]
            or list(texture_dimensions(cfg)) != sampling["texture_pixels"]
        ):
            raise ValueError(
                "Map sampling metadata does not match actual raster dimensions."
            )
        if any(
            source < scaled
            for source, scaled in zip(source_size, scaled_size, strict=True)
        ):
            raise ValueError(
                "Source map has insufficient sampling density for the requested PPI."
            )
    gores = entries["gore_files"]
    if len(gores) != cfg["globe"]["gore_count"] or len(set(gores)) != len(gores):
        raise ValueError("Gore count does not match configuration.")
    preview_names = {Path(path).stem for path in entries["preview"]}
    if preview_names != set(VIEWPOINTS):
        raise ValueError("Preview Set is missing a viewpoint.")
    for path in [*gores, *entries["preview"]]:
        artifact(path)
    reader = PdfReader(artifact(entries["pdf"]))
    tile_manifest = json.loads(
        artifact(str(Path(entries["pdf"]).with_suffix(".tiles.json"))).read_text()
    )
    if len(reader.pages) != len(tile_manifest["tiles"]):
        raise ValueError("PDF pages do not match Page Tiles.")
    for page in reader.pages:
        if (
            abs(float(page.mediabox.width) - 210 * 72 / 25.4) > 0.01
            or abs(float(page.mediabox.height) - 297 * 72 / 25.4) > 0.01
        ):
            raise ValueError("PDF page dimensions are not A4.")
        text = page.extract_text()
        if "100 mm" not in text or "OpenStreetMap" not in text:
            raise ValueError("PDF page lacks calibration or attribution.")
    if (
        reader.trailer["/Root"].get("/ViewerPreferences", {}).get("/PrintScaling")
        != "/None"
    ):
        raise ValueError("PDF must disable automatic print scaling.")
    return {"status": "valid", "output_dir": str(root), "artifacts": list(hashes)}

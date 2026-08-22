from __future__ import annotations

import hashlib
import json

import pytest

from leipzig_globe.config import (
    default_config_path,
    load_config,
    validate_config,
)
from leipzig_globe.fetcher import (
    DEFAULT_LEIPZIG_BOUNDARY_URL,
    SourceManifest,
    compute_sha256,
    fetch_data_cache,
    load_source_manifests,
    verify_manifest,
)
from leipzig_globe.pipeline import render_clean_map


def test_default_config_sets_expected_mvp_values():
    config = load_config()

    assert config["version"] == 1
    assert config["city"] == "Leipzig"
    assert config["globe"]["diameter_mm"] == 300
    assert config["globe"]["gore_count"] == 12
    assert config["globe"]["assembly_overlap_mm"] == 2
    assert config["layout"]["seam_offset_deg"] == 0
    assert config["layout"]["tile_overlap_mm"] == 10
    assert config["paths"]["texture_file"] == "leipzig-texture.png"
    assert default_config_path().exists()


def test_invalid_configuration_raises_actionable_error():
    bad_config = {
        "city": "Berlin",
        "globe": {
            "diameter_mm": 0,
            "gore_count": 0,
            "assembly_overlap_mm": -1,
            "seam_offset_deg": 361,
            "ppi": 0,
        },
        "layout": {
            "tile_overlap_mm": -1,
            "print_margin_mm": -1,
            "pole_safety_zone_mm": -1,
            "world_layout_scale_x": 0,
            "world_layout_scale_y": 0,
            "seam_offset_deg": 361,
        },
    }

    with pytest.raises(
        ValueError,
        match="Leipzig|diameter_mm|gore_count|assembly_overlap_mm|tile_overlap_mm|print_margin_mm|pole_safety_zone_mm|world_layout_scale_x|world_layout_scale_y|seam_offset_deg|ppi",
    ):
        validate_config(bad_config)


def test_default_boundary_source_points_to_current_official_city_dataset():
    assert DEFAULT_LEIPZIG_BOUNDARY_URL.startswith("https://static.leipzig.de/")
    assert "Stadtbezirke_Leipzig_UTM33N" in DEFAULT_LEIPZIG_BOUNDARY_URL
    assert DEFAULT_LEIPZIG_BOUNDARY_URL.endswith(".json")


def test_source_manifest_checksum_verification(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    data_file = source_dir / "sample.osm.pbf"
    data_file.write_bytes(b"example-data")

    manifest = SourceManifest(
        source_name="sample",
        url="https://example.com/sample.osm.pbf",
        checksum="3d5a90e1a2b3e32bafc47f1f4f7d8a61d4f5e9b90d9e6b8d6c1b2c4d5ae0c8b",
        sha256="0f2b27f9f7d7d8f7d307f4e0b5fc72957f62d363fef6a6f33a0f1fa1b8890eed",
        file_name="sample.osm.pbf",
        metadata={"license": "example"},
    )

    with pytest.raises(ValueError, match="checksum"):
        verify_manifest(manifest, data_file)


def test_build_manifest_is_serializable(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "globe": {"diameter_mm": 300},
        "source": {"kind": "fixture"},
        "artifacts": {"texture": "texture.png"},
    }
    manifest_path.write_text(json.dumps(manifest))

    payload = json.loads(manifest_path.read_text())
    assert payload["globe"]["diameter_mm"] == 300
    assert payload["artifacts"]["texture"].endswith("texture.png")


def test_fetch_data_cache_writes_deterministic_manifest(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    sample_bytes = b"fixture-osm-data"
    file_path = cache_dir / "sachsen-latest.osm.pbf"
    file_path.write_bytes(sample_bytes)

    manifest = SourceManifest(
        source_name="sachsen-latest",
        url="https://download.geofabrik.de/europe/germany/sachsen-latest.osm.pbf",
        file_name="sachsen-latest.osm.pbf",
        sha256=hashlib.sha256(sample_bytes).hexdigest(),
        metadata={
            "license": "OpenStreetMap © Contributors",
            "source_version": "2024-01-01",
        },
    )

    stored = fetch_data_cache(cache_dir, manifest)
    assert stored == file_path

    payload = json.loads((cache_dir / "source-manifest.json").read_text())
    assert payload["source_name"] == "sachsen-latest"
    assert payload["sha256"] == hashlib.sha256(sample_bytes).hexdigest()
    assert payload["metadata"]["source_version"] == "2024-01-01"
    assert "fetched_at_utc" not in payload


def test_fetch_data_cache_rejects_checksum_mismatch(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    file_path = cache_dir / "sachsen-latest.osm.pbf"
    file_path.write_bytes(b"fixture-osm-data")

    manifest = SourceManifest(
        source_name="sachsen-latest",
        url="https://download.geofabrik.de/europe/germany/sachsen-latest.osm.pbf",
        file_name="sachsen-latest.osm.pbf",
        sha256="0" * 64,
        metadata={"license": "OpenStreetMap © Contributors"},
    )

    with pytest.raises(ValueError, match="checksum mismatch"):
        fetch_data_cache(cache_dir, manifest)


def test_fetch_data_cache_retains_all_manifests_for_multiple_sources(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    first_path = cache_dir / "source-a.bin"
    second_path = cache_dir / "source-b.bin"
    first_path.write_bytes(b"alpha-data")
    second_path.write_bytes(b"beta-data")

    first_manifest = SourceManifest(
        source_name="source-a",
        url="https://example.com/source-a.bin",
        file_name="source-a.bin",
        sha256=compute_sha256(first_path),
        metadata={"license": "example", "source_version": "2024-01-01"},
    )
    second_manifest = SourceManifest(
        source_name="source-b",
        url="https://example.com/source-b.bin",
        file_name="source-b.bin",
        sha256=compute_sha256(second_path),
        metadata={"license": "example", "source_version": "2024-01-02"},
    )

    fetch_data_cache(cache_dir, first_manifest)
    fetch_data_cache(cache_dir, second_manifest)

    manifests = load_source_manifests(cache_dir)
    assert set(manifests) == {"source-a.bin", "source-b.bin"}
    assert manifests["source-a.bin"].sha256 == compute_sha256(first_path)
    assert manifests["source-b.bin"].sha256 == compute_sha256(second_path)


def test_render_clean_map_generates_png_and_omitted_label_report(tmp_path):
    config = {
        "city": "Leipzig",
        "globe": {
            "diameter_mm": 300,
            "gore_count": 12,
            "assembly_overlap_mm": 2,
            "ppi": 200,
            "paper_size": "A4",
        },
        "layout": {
            "tile_overlap_mm": 10,
            "print_margin_mm": 10,
            "pole_safety_zone_mm": 20,
            "world_layout_scale_x": 1.0,
            "world_layout_scale_y": 1.0,
            "gore_order": "clockwise",
            "label_density": "medium",
        },
        "paths": {"map_file": "leipzig-map.png"},
    }

    output_path = tmp_path / "leipzig-map.png"
    result = render_clean_map(config, output_path)
    report_path = tmp_path / "build-report.json"
    report_payload = {
        "config": config,
        "omitted_labels": result["omitted_labels"],
    }
    report_path.write_text(json.dumps(report_payload), encoding="utf-8")

    assert output_path.exists()
    assert result["image_path"] == output_path
    assert isinstance(result["omitted_labels"], list)
    assert result["omitted_labels"]
    assert "label" in result["omitted_labels"][0]
    assert "reason" in result["omitted_labels"][0]
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["omitted_labels"] == result["omitted_labels"]


def test_render_clean_map_omits_labels_near_gore_seams(tmp_path):
    config = {
        "city": "Leipzig",
        "globe": {
            "diameter_mm": 300,
            "gore_count": 12,
            "assembly_overlap_mm": 2,
            "seam_offset_deg": 90,
            "ppi": 200,
            "paper_size": "A4",
        },
        "layout": {
            "tile_overlap_mm": 10,
            "print_margin_mm": 10,
            "pole_safety_zone_mm": 20,
            "seam_offset_deg": 90,
            "world_layout_scale_x": 1.0,
            "world_layout_scale_y": 1.0,
            "gore_order": "clockwise",
            "label_density": "medium",
            "gore_seam_margin_mm": 10,
            "curated_landmarks": ["Mitte", "Connewitz", "Schönefeld"],
        },
        "paths": {"map_file": "leipzig-map.png"},
    }

    output_path = tmp_path / "leipzig-map.png"
    result = render_clean_map(config, output_path)

    assert output_path.exists()
    assert any(entry["reason"] == "gore_seam" for entry in result["omitted_labels"])
    assert isinstance(result["rendered_labels"], list)
    assert result["omitted_labels"]

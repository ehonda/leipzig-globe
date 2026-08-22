from __future__ import annotations

import hashlib
import json
from pathlib import Path

import geopandas as gpd
import pytest
from PIL import Image, ImageDraw
from shapely.geometry import LineString, Polygon

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
from leipzig_globe.pipeline import (
    build_artifacts,
    generate_globe_texture,
    render_clean_map,
)


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


def test_render_clean_map_uses_configured_style_palette(tmp_path):
    config = {
        "city": "Leipzig",
        "globe": {
            "diameter_mm": 300,
            "gore_count": 12,
            "assembly_overlap_mm": 2,
            "ppi": 200,
            "paper_size": "A4",
        },
        "style": {
            "background": [10, 20, 30],
            "land": [40, 50, 60],
            "water": [70, 80, 90],
            "park": [100, 110, 120],
            "major_road": [130, 140, 150],
            "secondary_road": [160, 170, 180],
            "rail": [190, 200, 210],
            "label": [220, 230, 240],
        },
        "layout": {
            "tile_overlap_mm": 10,
            "print_margin_mm": 10,
            "pole_safety_zone_mm": 20,
            "world_layout_scale_x": 1.0,
            "world_layout_scale_y": 1.0,
            "gore_order": "clockwise",
            "label_density": "medium",
            "gore_seam_margin_mm": 10,
        },
        "paths": {"map_file": "leipzig-map.png"},
    }

    cfg = validate_config(config)
    assert cfg["style"]["background"] == [10, 20, 30]

    municipal_map = gpd.GeoDataFrame(
        {"kind": ["land"]},
        geometry=[Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])],
        crs="EPSG:32633",
    )
    output_path = tmp_path / "styled-map.png"
    render_clean_map(config, output_path, municipal_map=municipal_map)

    image = Image.open(output_path).convert("RGB")
    assert image.getpixel((0, 0)) == (10, 20, 30)
    assert image.getpixel((int(image.width * 0.42), int(image.height * 0.45))) == (
        40,
        50,
        60,
    )


def test_render_clean_map_uses_supplied_municipal_geometry(tmp_path):
    config = {
        "city": "Leipzig",
        "globe": {
            "diameter_mm": 300,
            "gore_count": 12,
            "assembly_overlap_mm": 2,
            "ppi": 200,
            "paper_size": "A4",
        },
        "style": {
            "background": [255, 255, 255],
            "land": [200, 210, 200],
            "water": [40, 80, 120],
            "park": [150, 200, 160],
            "major_road": [90, 90, 90],
            "secondary_road": [150, 150, 150],
            "rail": [120, 130, 140],
            "label": [20, 20, 20],
        },
        "layout": {
            "tile_overlap_mm": 10,
            "print_margin_mm": 10,
            "pole_safety_zone_mm": 20,
            "world_layout_scale_x": 1.0,
            "world_layout_scale_y": 1.0,
            "gore_order": "clockwise",
            "label_density": "low",
            "gore_seam_margin_mm": 10,
            "curated_landmarks": ["Leipzig"],
        },
        "paths": {"map_file": "leipzig-map.png"},
    }
    municipal_map = gpd.GeoDataFrame(
        {"kind": ["water", "road"]},
        geometry=[
            Polygon([(0, 0), (100, 0), (100, 100), (0, 100)]),
            LineString([(0, 50), (100, 50)]),
        ],
        crs="EPSG:32633",
    )

    output_path = tmp_path / "leipzig-data-map.png"
    result = render_clean_map(config, output_path, municipal_map=municipal_map)

    image = Image.open(output_path).convert("RGB")
    assert image.getpixel((image.width // 2, image.height // 2)) == (90, 90, 90)
    assert image.getpixel((image.width // 2 - image.height // 4, image.height // 4)) == (
        40,
        80,
        120,
    )
    assert result["image_path"] == output_path


def test_render_clean_map_preserves_municipal_geometry_aspect_ratio(tmp_path):
    municipal_map = gpd.GeoDataFrame(
        {"kind": ["water"]},
        geometry=[Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])],
        crs="EPSG:32633",
    )
    output_path = tmp_path / "aspect-ratio-map.png"

    render_clean_map({}, output_path, municipal_map=municipal_map)

    image = Image.open(output_path).convert("RGB")
    water = (132, 178, 198)
    xs: list[int] = []
    ys: list[int] = []
    for y in range(image.height):
        for x in range(image.width):
            if image.getpixel((x, y)) == water:
                xs.append(x)
                ys.append(y)

    assert xs and ys
    assert max(xs) - min(xs) == pytest.approx(max(ys) - min(ys), abs=2)


def test_render_clean_map_classifies_raw_osm_highway_tags(tmp_path):
    municipal_map = gpd.GeoDataFrame(
        {"highway": ["residential"]},
        geometry=[LineString([(0, 50), (100, 50)])],
        crs="EPSG:32633",
    )
    output_path = tmp_path / "raw-osm-tags.png"

    render_clean_map({}, output_path, municipal_map=municipal_map)

    image = Image.open(output_path).convert("RGB")
    assert image.getpixel((image.width // 2, image.height // 2)) == (72, 76, 81)


def test_render_clean_map_requires_municipal_geometry(tmp_path):
    with pytest.raises(ValueError, match="Municipal map data is required"):
        render_clean_map({}, tmp_path / "synthetic-map.png")


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

    municipal_map = gpd.GeoDataFrame(
        {"kind": ["land"]},
        geometry=[Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])],
        crs="EPSG:32633",
    )
    output_path = tmp_path / "leipzig-map.png"
    result = render_clean_map(config, output_path, municipal_map=municipal_map)
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


def test_generate_globe_texture_uses_rendered_map_and_rotates_for_seam_offset(
    tmp_path,
):
    config = {
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
            "world_layout_scale_x": 1.0,
            "world_layout_scale_y": 1.0,
            "gore_order": "clockwise",
            "label_density": "medium",
            "gore_seam_margin_mm": 10,
            "curated_landmarks": ["Leipzig"],
            "seam_offset_deg": 0,
        },
        "style": {
            "background": [255, 255, 255],
            "land": [200, 210, 200],
            "water": [40, 80, 120],
            "park": [150, 200, 160],
            "major_road": [90, 90, 90],
            "secondary_road": [150, 150, 150],
            "rail": [120, 130, 140],
            "label": [20, 20, 20],
        },
        "paths": {"map_file": "leipzig-map.png"},
    }
    source_map = tmp_path / "rendered-map.png"
    image = Image.new("RGB", (1200, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((300, 150, 900, 450), fill=(28, 60, 90))
    draw.line((0, 300, 1200, 300), fill=(50, 50, 50), width=8)
    image.save(source_map)

    texture_path = tmp_path / "leipzig-texture.png"
    generate_globe_texture(config, texture_path, source_map=source_map)

    texture = Image.open(texture_path).convert("RGB")
    assert texture.size[0] == texture.size[1] * 2
    assert texture.getpixel((1000, 550)) == (28, 60, 90)
    assert texture.getpixel((1500, 550)) != (28, 60, 90)

    offset_cfg = {
        **config,
        "globe": {**config["globe"], "seam_offset_deg": 90},
        "layout": {**config["layout"], "seam_offset_deg": 90},
    }
    offset_texture_path = tmp_path / "leipzig-texture-rotated.png"
    generate_globe_texture(offset_cfg, offset_texture_path, source_map=source_map)

    offset_texture = Image.open(offset_texture_path).convert("RGB")
    assert offset_texture.size == texture.size
    assert offset_texture.tobytes() != texture.tobytes()
    assert offset_texture.getpixel((1500, 550)) == (28, 60, 90)
    assert texture.getpixel((1500, 550)) != (28, 60, 90)


def test_build_artifacts_requires_cached_sources_before_rendering(tmp_path):
    config = {
        "city": "Leipzig",
        "globe": {
            "diameter_mm": 300,
            "gore_count": 12,
            "assembly_overlap_mm": 2,
            "seam_offset_deg": 0,
            "ppi": 200,
            "paper_size": "A4",
        },
        "style": {
            "background": [255, 255, 255],
            "land": [200, 210, 200],
            "water": [40, 80, 120],
            "park": [150, 200, 160],
            "major_road": [90, 90, 90],
            "secondary_road": [150, 150, 150],
            "rail": [120, 130, 140],
            "label": [20, 20, 20],
        },
        "layout": {
            "tile_overlap_mm": 10,
            "print_margin_mm": 10,
            "pole_safety_zone_mm": 20,
            "seam_offset_deg": 0,
            "world_layout_scale_x": 1.0,
            "world_layout_scale_y": 1.0,
            "gore_order": "clockwise",
            "label_density": "medium",
            "gore_seam_margin_mm": 10,
            "source_cache_dir": str(tmp_path / ".cache"),
        },
        "paths": {
            "map_file": "leipzig-map.png",
            "texture_file": "leipzig-texture.png",
            "gore_dir": "gores",
            "pdf_file": "leipzig-globe-print.pdf",
            "preview_dir": "preview",
            "report_file": "build-report.json",
        },
    }

    with pytest.raises(FileNotFoundError, match="sachsen-latest.osm.pbf|leipzig-municipal-boundary.geojson"):
        build_artifacts(config, tmp_path / "output")


def test_build_artifacts_records_offline_source_provenance(tmp_path, monkeypatch):
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    osm_file = cache_dir / "sachsen-latest.osm.pbf"
    boundary_file = cache_dir / "leipzig-municipal-boundary.geojson"
    osm_file.write_bytes(b"fixture-osm")
    gpd.GeoDataFrame(
        geometry=[Polygon([(0, 0), (1000, 0), (1000, 1000), (0, 1000)])],
        crs="EPSG:32633",
    ).to_file(boundary_file, driver="GeoJSON")

    config = {
        "city": "Leipzig",
        "globe": {
            "diameter_mm": 300,
            "gore_count": 12,
            "assembly_overlap_mm": 2,
            "seam_offset_deg": 0,
            "ppi": 200,
            "paper_size": "A4",
        },
        "style": {
            "background": [255, 255, 255],
            "land": [200, 210, 200],
            "water": [40, 80, 120],
            "park": [150, 200, 160],
            "major_road": [90, 90, 90],
            "secondary_road": [150, 150, 150],
            "rail": [120, 130, 140],
            "label": [20, 20, 20],
        },
        "layout": {
            "tile_overlap_mm": 10,
            "print_margin_mm": 10,
            "pole_safety_zone_mm": 20,
            "seam_offset_deg": 0,
            "world_layout_scale_x": 1.0,
            "world_layout_scale_y": 1.0,
            "gore_order": "clockwise",
            "label_density": "medium",
            "gore_seam_margin_mm": 10,
            "source_cache_dir": str(cache_dir),
        },
        "paths": {
            "map_file": "leipzig-map.png",
            "texture_file": "leipzig-texture.png",
            "gore_dir": "gores",
            "pdf_file": "leipzig-globe-print.pdf",
            "preview_dir": "preview",
            "report_file": "build-report.json",
        },
    }

    def fake_derive(boundary_path, source_pbf, output_path, **kwargs):
        gpd.GeoDataFrame(
            {"kind": ["road"]},
            geometry=[LineString([(100, 100), (900, 900)])],
            crs="EPSG:32633",
        ).to_file(output_path, driver="GeoJSON")
        return {
            "feature_count": 1,
            "crs": "EPSG:32633",
            "output_path": Path(output_path),
        }

    monkeypatch.setattr(
        "leipzig_globe.pipeline.derive_municipal_map_from_sources",
        fake_derive,
    )

    def fake_render(config, output_path, municipal_map=None):
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (200, 100), color=(255, 255, 255))
        image.save(output_file)
        return {
            "image_path": output_file,
            "omitted_labels": [{"label": "Leipzig", "reason": "pole_safety_zone"}],
            "rendered_labels": ["Leipzig"],
            "width_px": image.width,
            "height_px": image.height,
        }

    monkeypatch.setattr("leipzig_globe.pipeline.render_clean_map", fake_render)

    def fake_texture(config, output_path, *, source_map=None):
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (200, 100), color=(0, 0, 0)).save(output_file)
        return output_file

    monkeypatch.setattr("leipzig_globe.pipeline.generate_globe_texture", fake_texture)
    monkeypatch.setattr(
        "leipzig_globe.pipeline.build_gore_set",
        lambda texture_path, gore_dir, config: [gore_dir / "gore-01.svg"],
    )
    monkeypatch.setattr(
        "leipzig_globe.pipeline.build_pdf",
        lambda gore_files, output_path: Path(output_path),
    )
    monkeypatch.setattr(
        "leipzig_globe.pipeline.generate_preview_set",
        lambda texture_path, output_dir: [Path(output_dir) / "front.png"],
    )

    output_dir = tmp_path / "output"
    result = build_artifacts(config, output_dir)

    assert Path(result["municipal_map"]).exists()
    report = json.loads((output_dir / "build-report.json").read_text(encoding="utf-8"))
    assert report["source_provenance"]["osm_pbf"] == str(osm_file)
    assert report["source_provenance"]["municipal_boundary"] == str(boundary_file)
    assert report["artifacts"]["municipal_map"] == str(result["municipal_map"])


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

    municipal_map = gpd.GeoDataFrame(
        {"kind": ["land"]},
        geometry=[Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])],
        crs="EPSG:32633",
    )
    output_path = tmp_path / "leipzig-map.png"
    result = render_clean_map(config, output_path, municipal_map=municipal_map)

    assert output_path.exists()
    assert any(entry["reason"] == "gore_seam" for entry in result["omitted_labels"])
    assert isinstance(result["rendered_labels"], list)
    assert result["omitted_labels"]

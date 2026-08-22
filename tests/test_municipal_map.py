from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, Polygon

from leipzig_globe.municipal_map import (
    OSM_FEATURE_FILTERS,
    derive_municipal_map,
    derive_municipal_map_from_sources,
    extract_osm_features,
)


def test_derive_municipal_map_clips_features_to_boundary(tmp_path):
    boundary = Polygon([(0, 0), (1000, 0), (1000, 1000), (0, 1000)])
    kept = LineString([(100, 100), (900, 900)])
    outside = LineString([(1200, 100), (1500, 900)])

    boundary_gdf = gpd.GeoDataFrame(
        {"name": ["leipzig"]},
        geometry=[boundary],
        crs="EPSG:32633",
    )
    feature_gdf = gpd.GeoDataFrame(
        {"kind": ["road", "road"]},
        geometry=[kept, outside],
        crs="EPSG:32633",
    )

    output_path = tmp_path / "municipal-map.geojson"
    result = derive_municipal_map(boundary_gdf, feature_gdf, output_path=output_path)

    assert result["feature_count"] == 1
    assert result["crs"] == "EPSG:32633"
    assert result["output_path"] == output_path

    clipped = gpd.read_file(output_path)
    assert len(clipped) == 1
    assert clipped.iloc[0]["kind"] == "road"
    assert clipped.geometry.iloc[0].within(boundary)


def test_derive_municipal_map_normalizes_empty_features_to_metric_crs(tmp_path):
    boundary_gdf = gpd.GeoDataFrame(
        geometry=[Polygon([(12.2, 51.2), (12.3, 51.2), (12.3, 51.3), (12.2, 51.3)])],
        crs="EPSG:4326",
    )
    features = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    output_path = tmp_path / "municipal-map.geojson"

    result = derive_municipal_map(boundary_gdf, features, output_path=output_path)

    assert result["feature_count"] == 0
    assert result["crs"] == "EPSG:32633"
    assert gpd.read_file(output_path).crs.to_string() == "EPSG:32633"


def test_derive_municipal_map_requires_a_polygonal_boundary():
    boundary_gdf = gpd.GeoDataFrame(
        geometry=[LineString([(0, 0), (1000, 1000)])], crs="EPSG:32633"
    )
    features = gpd.GeoDataFrame(geometry=[Point(10, 10)], crs="EPSG:32633")

    with pytest.raises(ValueError, match="polygonal"):
        derive_municipal_map(boundary_gdf, features)


def test_extract_osm_features_uses_cached_pbf_and_osmium(tmp_path, monkeypatch):
    source_pbf = tmp_path / "sachsen-latest.osm.pbf"
    source_pbf.write_bytes(b"fixture")
    output_path = tmp_path / "features.geojson"
    commands: list[list[str]] = []

    monkeypatch.setattr("leipzig_globe.municipal_map.shutil.which", lambda _: "osmium")

    def run(command, *, check):
        commands.append(command)
        if command[1] == "export":
            output_path.write_text('{"type": "FeatureCollection", "features": []}')

    monkeypatch.setattr("leipzig_globe.municipal_map.subprocess.run", run)

    result = extract_osm_features(source_pbf, output_path)

    assert result == output_path
    assert commands[0][1] == "tags-filter"
    assert commands[0][-len(OSM_FEATURE_FILTERS) :] == list(OSM_FEATURE_FILTERS)
    assert commands[1][1] == "export"
    assert str(source_pbf) in commands[0]
    assert output_path.exists()


def test_extract_osm_features_requires_osmium(tmp_path, monkeypatch):
    source_pbf = tmp_path / "sachsen-latest.osm.pbf"
    source_pbf.write_bytes(b"fixture")
    monkeypatch.setattr("leipzig_globe.municipal_map.shutil.which", lambda _: None)

    with pytest.raises(RuntimeError, match="Osmium"):
        extract_osm_features(source_pbf, tmp_path / "features.geojson")


def test_derive_municipal_map_from_sources_uses_only_cached_inputs(
    tmp_path, monkeypatch
):
    boundary_path = tmp_path / "boundary.geojson"
    gpd.GeoDataFrame(
        geometry=[Polygon([(0, 0), (1000, 0), (1000, 1000), (0, 1000)])],
        crs="EPSG:32633",
    ).to_file(boundary_path, driver="GeoJSON")
    source_pbf = tmp_path / "sachsen-latest.osm.pbf"
    source_pbf.write_bytes(b"fixture")
    output_path = tmp_path / "municipal-map.geojson"

    def extract(_, extracted_features, **__):
        gpd.GeoDataFrame(
            {"kind": ["road"]},
            geometry=[LineString([(100, 100), (900, 900)])],
            crs="EPSG:32633",
        ).to_file(extracted_features, driver="GeoJSON")

    monkeypatch.setattr("leipzig_globe.municipal_map.extract_osm_features", extract)

    result = derive_municipal_map_from_sources(boundary_path, source_pbf, output_path)

    assert result["feature_count"] == 1
    assert gpd.read_file(output_path).iloc[0]["kind"] == "road"

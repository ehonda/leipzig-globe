from __future__ import annotations

import io
import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, Polygon

from leipzig_globe.municipal_map import (
    OSM_FEATURE_FILTERS,
    derive_municipal_map,
    derive_municipal_map_from_sources,
    extract_osm_features,
)


@pytest.fixture
def fake_export(monkeypatch):
    class Process:
        returncode = 0

        def __init__(self, command, **kwargs):
            self.stdout = io.BytesIO()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def wait(self):
            return self.returncode

    monkeypatch.setattr("leipzig_globe.municipal_map.subprocess.Popen", Process)
    monkeypatch.setattr("leipzig_globe.municipal_map._pbf_profile", lambda *args: {})


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


def test_extract_osm_features_uses_cached_pbf_and_osmium(
    tmp_path, monkeypatch, fake_export
):
    source_pbf = tmp_path / "sachsen-latest.osm.pbf"
    source_pbf.write_bytes(b"fixture")
    output_path = tmp_path / "features.geojson"
    commands: list[list[str]] = []

    monkeypatch.setattr(
        "leipzig_globe.municipal_map.shutil.which",
        lambda _: r"C:\\Users\\dennis\\AppData\\Local\\osmium-tool\\Library\\bin\\osmium.exe",
    )

    def run(command, *, check):
        commands.append(command)
        if command[1] == "export":
            output_path.write_text('{"type": "FeatureCollection", "features": []}')

    monkeypatch.setattr("leipzig_globe.municipal_map.subprocess.run", run)

    result = extract_osm_features(source_pbf, output_path)

    assert result == output_path
    assert commands[0][0] == "osmium"
    assert commands[0][1] == "tags-filter"
    assert commands[0][-len(OSM_FEATURE_FILTERS) :] == list(OSM_FEATURE_FILTERS)
    assert "--remove-tags" in commands[0]
    assert str(source_pbf) in commands[0]
    assert output_path.exists()


def test_extract_osm_features_requires_osmium(tmp_path, monkeypatch):
    source_pbf = tmp_path / "sachsen-latest.osm.pbf"
    source_pbf.write_bytes(b"fixture")
    monkeypatch.setattr("leipzig_globe.municipal_map.shutil.which", lambda _: None)

    with pytest.raises(RuntimeError, match="Osmium"):
        extract_osm_features(source_pbf, tmp_path / "features.geojson")


def test_extract_osm_features_clips_to_wgs84_boundary_before_tag_filtering(
    tmp_path, monkeypatch, fake_export
):
    source_pbf = tmp_path / "sachsen-latest.osm.pbf"
    source_pbf.write_bytes(b"fixture")
    boundary_path = tmp_path / "boundary.geojson"
    gpd.GeoDataFrame(
        geometry=[Polygon([(300000, 5700000), (301000, 5700000), (301000, 5701000)])],
        crs="EPSG:32633",
    ).to_file(boundary_path, driver="GeoJSON")
    output_path = tmp_path / "features.geojson"
    commands: list[list[str]] = []

    monkeypatch.setattr("leipzig_globe.municipal_map.shutil.which", lambda _: "osmium")

    def run(command, *, check):
        commands.append(command)
        if command[1] == "export":
            output_path.write_text('{"type": "FeatureCollection", "features": []}')

    monkeypatch.setattr("leipzig_globe.municipal_map.subprocess.run", run)

    extract_osm_features(source_pbf, output_path, boundary_path=boundary_path)

    assert [command[1] for command in commands] == [
        "extract",
        "tags-filter",
    ]
    assert "--polygon" in commands[0]
    polygon_path = Path(commands[0][commands[0].index("--polygon") + 1])
    assert polygon_path.name == "municipal-boundary-wgs84.geojson"


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


def test_extract_combines_all_districts_and_strips_unneeded_tags(tmp_path):
    """Exercise the real CLI: a mocked command cannot catch first-feature loss."""
    import shutil

    if shutil.which("osmium") is None:
        pytest.skip("osmium-tool is required for the real extraction fixture")
    source = tmp_path / "fixture.osm"
    source.write_text(
        """<osm version="0.6">
      <node id="1" lat="51.30" lon="12.30"/>
      <node id="2" lat="51.31" lon="12.31"/>
      <node id="3" lat="51.40" lon="12.50"/>
      <node id="4" lat="51.41" lon="12.51"/>
      <node id="5" lat="52.00" lon="13.00"/>
      <node id="6" lat="52.01" lon="13.01"/>
      <way id="1"><nd ref="1"/><nd ref="2"/><tag k="highway" v="primary"/><tag k="name" v="First"/><tag k="unneeded" v="discard"/></way>
      <way id="2"><nd ref="3"/><nd ref="4"/><tag k="highway" v="residential"/><tag k="name" v="Second"/></way>
      <way id="3"><nd ref="5"/><nd ref="6"/><tag k="highway" v="primary"/><tag k="name" v="Outside"/></way>
    </osm>""",
        encoding="utf-8",
    )
    from shapely.geometry import box

    boundary = tmp_path / "districts.geojson"
    gpd.GeoDataFrame(
        geometry=[box(12.29, 51.29, 12.32, 51.32), box(12.49, 51.39, 12.52, 51.42)],
        crs=4326,
    ).to_crs(25833).to_file(boundary)
    metrics = {}
    output = extract_osm_features(
        source, tmp_path / "features.geojson", boundary_path=boundary, metrics=metrics
    )
    data = json.loads(output.read_text(encoding="utf-8"))
    assert {f["properties"]["name"] for f in data["features"]} == {"First", "Second"}
    assert all("unneeded" not in f["properties"] for f in data["features"])
    assert metrics["export"]["feature_count"] == 2
    assert metrics["filter"]["objects"]["ways"] == 2

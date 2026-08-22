from __future__ import annotations

import geopandas as gpd
from shapely.geometry import LineString, Polygon

from leipzig_globe.municipal_map import derive_municipal_map


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
    assert clipped.geometry.iloc[0].within(boundary)

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.ops import unary_union

WORKING_CRS = "EPSG:32633"
OSM_FEATURE_FILTERS = (
    "w/highway",
    "w/waterway",
    "w/railway",
    "w/leisure=park",
    "wr/natural=water",
    "r/boundary=administrative",
    "n/place",
    "n/amenity",
    "n/tourism",
    "n/historic",
)


def _as_geodataframe(data: gpd.GeoDataFrame | str | Path) -> gpd.GeoDataFrame:
    if isinstance(data, gpd.GeoDataFrame):
        return data.copy()
    path = Path(data)
    if not path.exists():
        raise FileNotFoundError(f"GeoData source not found: {path}")
    return gpd.read_file(path)


def _ensure_working_crs(
    frame: gpd.GeoDataFrame, *, target_crs: str = WORKING_CRS
) -> gpd.GeoDataFrame:
    if frame.crs is None:
        raise ValueError(
            "GeoDataFrame is missing a CRS and cannot be normalized for Leipzig."
        )
    if frame.crs.is_geographic:
        return frame.to_crs(target_crs)
    if frame.crs.to_string() != target_crs:
        return frame.to_crs(target_crs)
    return frame


def extract_osm_features(
    source_pbf: str | Path,
    output_path: str | Path,
    *,
    boundary_path: str | Path | None = None,
    osmium_path: str = "osmium",
) -> Path:
    """Extract Task 4 feature classes from a cached OSM PBF without network access."""
    source_path = Path(source_pbf)
    if not source_path.exists():
        raise FileNotFoundError(f"Cached OSM PBF not found: {source_path}")
    if shutil.which(osmium_path) is None:
        raise RuntimeError(
            "Osmium is required for map extraction. Install the `osmium-tool` binary and ensure it is on your PATH."
        )

    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target_path.parent) as temporary_dir:
        input_pbf = source_path
        if boundary_path is not None:
            boundary = _as_geodataframe(boundary_path)
            if boundary.crs is None:
                raise ValueError("Municipal boundary is missing a CRS.")
            polygon_path = Path(temporary_dir) / "municipal-boundary-wgs84.geojson"
            boundary.to_crs("EPSG:4326").to_file(polygon_path, driver="GeoJSON")
            input_pbf = Path(temporary_dir) / "municipal-extract.osm.pbf"
            subprocess.run(
                [
                    osmium_path,
                    "extract",
                    "--overwrite",
                    "--polygon",
                    str(polygon_path),
                    "--output",
                    str(input_pbf),
                    str(source_path),
                ],
                check=True,
            )
        filtered_pbf = Path(temporary_dir) / "leipzig-features.osm.pbf"
        subprocess.run(
            [
                osmium_path,
                "tags-filter",
                "--overwrite",
                "-o",
                str(filtered_pbf),
                str(input_pbf),
                *OSM_FEATURE_FILTERS,
            ],
            check=True,
        )
        subprocess.run(
            [
                osmium_path,
                "export",
                "--overwrite",
                "-o",
                str(target_path),
                str(filtered_pbf),
            ],
            check=True,
        )
    return target_path


def derive_municipal_map_from_sources(
    boundary_path: str | Path,
    source_pbf: str | Path,
    output_path: str | Path,
    *,
    working_crs: str = WORKING_CRS,
    osmium_path: str = "osmium",
) -> dict[str, Any]:
    """Derive the offline Municipal Map from the two cached Task 3 sources."""
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target_path.parent) as temporary_dir:
        extracted_features = Path(temporary_dir) / "osm-features.geojson"
        extract_osm_features(
            source_pbf,
            extracted_features,
            boundary_path=boundary_path,
            osmium_path=osmium_path,
        )
        return derive_municipal_map(
            boundary_path,
            extracted_features,
            output_path=target_path,
            working_crs=working_crs,
        )


def derive_municipal_map(
    boundary: gpd.GeoDataFrame | str | Path,
    features: gpd.GeoDataFrame | str | Path,
    *,
    output_path: str | Path | None = None,
    working_crs: str = WORKING_CRS,
) -> dict[str, Any]:
    """Clip OSM-derived features to the official Leipzig municipal boundary.

    The resulting GeoJSON is intended as the offline intermediate dataset that later
    build stages can use without any network dependency.
    """
    boundary_gdf = _as_geodataframe(boundary)
    feature_gdf = _as_geodataframe(features)

    if boundary_gdf.empty:
        raise ValueError("Municipal boundary is empty; cannot derive a municipal map.")

    boundary_gdf = _ensure_working_crs(boundary_gdf, target_crs=working_crs)
    feature_gdf = _ensure_working_crs(feature_gdf, target_crs=working_crs)

    boundary_geom = unary_union(boundary_gdf.geometry.dropna())
    if boundary_geom.is_empty or boundary_geom.geom_type not in {
        "Polygon",
        "MultiPolygon",
    }:
        raise ValueError("Municipal boundary contains no valid polygonal geometry.")

    cleaned = feature_gdf.copy()
    cleaned = cleaned[cleaned.geometry.notna()].copy()
    if cleaned.empty:
        target_path = (
            Path(output_path)
            if output_path is not None
            else Path(".cache") / "municipal-map.geojson"
        )
        if output_path is not None:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            gpd.GeoDataFrame(geometry=[], crs=working_crs).to_file(
                target_path, driver="GeoJSON"
            )
        return {
            "feature_count": 0,
            "crs": working_crs,
            "output_path": target_path,
        }

    clipped_geometry = cleaned.geometry.intersection(boundary_geom)
    retained = cleaned.loc[~clipped_geometry.is_empty].copy()
    retained["geometry"] = clipped_geometry[~clipped_geometry.is_empty]

    if retained.empty:
        if output_path is not None:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            gpd.GeoDataFrame(geometry=[], crs=working_crs).to_file(
                target, driver="GeoJSON"
            )
        return {
            "feature_count": 0,
            "crs": working_crs,
            "output_path": Path(output_path) if output_path is not None else None,
        }

    retained = retained.set_crs(working_crs, allow_override=True)
    outside = retained.geometry.apply(lambda geom: not boundary_geom.covers(geom))
    if outside.any():
        raise ValueError(
            "Derived municipal map retains features outside the municipal boundary."
        )

    target_path = (
        Path(output_path)
        if output_path is not None
        else Path(".cache") / "municipal-map.geojson"
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    retained.to_file(target_path, driver="GeoJSON")

    return {
        "feature_count": len(retained),
        "crs": retained.crs.to_string() if retained.crs else working_crs,
        "output_path": target_path,
    }

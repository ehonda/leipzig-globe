from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.ops import unary_union

WORKING_CRS = "EPSG:32633"


def _as_geodataframe(data: gpd.GeoDataFrame | str | Path) -> gpd.GeoDataFrame:
    if isinstance(data, gpd.GeoDataFrame):
        return data.copy()
    path = Path(data)
    if not path.exists():
        raise FileNotFoundError(f"GeoData source not found: {path}")
    return gpd.read_file(path)


def _ensure_working_crs(frame: gpd.GeoDataFrame, *, target_crs: str = WORKING_CRS) -> gpd.GeoDataFrame:
    if frame.crs is None:
        raise ValueError("GeoDataFrame is missing a CRS and cannot be normalized for Leipzig.")
    if frame.crs.is_geographic:
        return frame.to_crs(target_crs)
    if frame.crs.to_string() != target_crs:
        return frame.to_crs(target_crs)
    return frame


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
    if feature_gdf.empty:
        empty = gpd.GeoDataFrame(geometry=[], crs=boundary_gdf.crs)
        if output_path is not None:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            empty.to_file(target, driver="GeoJSON")
        return {
            "feature_count": 0,
            "crs": boundary_gdf.crs.to_string() if boundary_gdf.crs else working_crs,
            "output_path": Path(output_path) if output_path is not None else None,
        }

    boundary_gdf = _ensure_working_crs(boundary_gdf, target_crs=working_crs)
    feature_gdf = _ensure_working_crs(feature_gdf, target_crs=working_crs)

    boundary_geom = unary_union(boundary_gdf.geometry.dropna())
    if boundary_geom.is_empty:
        raise ValueError("Municipal boundary contains no valid polygonal geometry.")

    cleaned = feature_gdf[["geometry"]].copy() if "geometry" in feature_gdf.columns else feature_gdf.copy()
    cleaned = cleaned[cleaned.geometry.notna()].copy()
    if cleaned.empty:
        if output_path is not None:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            gpd.GeoDataFrame(geometry=[], crs=working_crs).to_file(target, driver="GeoJSON")
        return {
            "feature_count": 0,
            "crs": working_crs,
            "output_path": Path(output_path) if output_path is not None else None,
        }

    clipped_geometry = cleaned.geometry.intersection(boundary_geom)
    retained = cleaned.loc[~clipped_geometry.is_empty].copy()
    retained["geometry"] = clipped_geometry[~clipped_geometry.is_empty]

    if retained.empty:
        if output_path is not None:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            gpd.GeoDataFrame(geometry=[], crs=working_crs).to_file(target, driver="GeoJSON")
        return {
            "feature_count": 0,
            "crs": working_crs,
            "output_path": Path(output_path) if output_path is not None else None,
        }

    retained = retained.set_crs(working_crs, allow_override=True)
    outside = retained.geometry.apply(lambda geom: not geom.within(boundary_geom))
    if outside.any():
        raise ValueError("Derived municipal map retains features outside the municipal boundary.")

    target_path = Path(output_path) if output_path is not None else Path(".cache") / "municipal-map.geojson"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    retained.to_file(target_path, driver="GeoJSON")

    return {
        "feature_count": len(retained),
        "crs": retained.crs.to_string() if retained.crs else working_crs,
        "output_path": target_path,
    }

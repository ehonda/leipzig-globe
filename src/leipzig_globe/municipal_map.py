from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import shapely
from shapely.ops import unary_union

WORKING_CRS = "EPSG:32633"
OSM_FEATURE_FILTERS = (
    "w/highway=motorway,motorway_link,trunk,trunk_link,primary,primary_link,secondary,secondary_link,tertiary,tertiary_link,residential,unclassified,living_street,service,pedestrian",
    "w/waterway=river,canal,stream,ditch",
    "w/railway=rail,tram,light_rail,narrow_gauge",
    "w/highway=footway,cycleway,path,track,steps",
    "wr/leisure=pitch,stadium,sports_centre",
    "wr/leisure=park,garden,nature_reserve",
    "wr/natural=water",
    "wr/natural=wood,grassland,wetland",
    "wr/landuse=forest,grass,meadow,recreation_ground,allotments",
    "n/place=city,suburb,quarter,neighbourhood",
)
RETAINED_TAGS = (
    "name",
    "name:de",
    "highway",
    "waterway",
    "railway",
    "leisure",
    "natural",
    "landuse",
    "place",
    "area",
    "building",
    "historic",
    "tourism",
    "amenity",
)
MAX_GEOJSON_BYTES = 100_000_000


def _pbf_profile(path: Path, osmium_path: str) -> dict[str, Any]:
    info = json.loads(
        subprocess.check_output([osmium_path, "fileinfo", "-e", "-j", str(path)])
    )
    tags = subprocess.check_output(
        [osmium_path, "tags-count", str(path), *RETAINED_TAGS[2:]],
        text=True,
        encoding="utf-8",
    )
    return {
        "bytes": path.stat().st_size,
        "objects": info["data"]["count"],
        "tags": tags.splitlines(),
    }


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
    curated_landmarks: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
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
        stages = metrics if metrics is not None else {}
        started = time.perf_counter()
        input_pbf = source_path
        if boundary_path is not None:
            boundary = _as_geodataframe(boundary_path)
            if boundary.crs is None:
                raise ValueError("Municipal boundary is missing a CRS.")
            polygon_path = Path(temporary_dir) / "municipal-boundary-wgs84.geojson"
            # Osmium reads only the FIRST feature: dissolve all ten districts.
            boundary.to_crs("EPSG:4326").dissolve().to_file(
                polygon_path, driver="GeoJSON"
            )
            input_pbf = Path(temporary_dir) / "municipal-extract.osm.pbf"
            subprocess.run(
                [
                    osmium_path,
                    "extract",
                    "--strategy=smart",
                    "--overwrite",
                    "--polygon",
                    str(polygon_path),
                    "--output",
                    str(input_pbf),
                    str(source_path),
                ],
                check=True,
            )
            stages["extract"] = {
                "seconds": time.perf_counter() - started,
                **_pbf_profile(input_pbf, osmium_path),
            }
        started = time.perf_counter()
        filtered_pbf = Path(temporary_dir) / "leipzig-features.osm.pbf"
        filters = list(OSM_FEATURE_FILTERS)
        # Name filters are an OR, so every configured name remains eligible.
        for name in curated_landmarks or []:
            if any(char in name for char in "=,!*"):
                raise ValueError(
                    "Curated landmark names cannot contain Osmium filter metacharacters (=,!*)."
                )
            filters.extend([f"nwr/name={name}", f"nwr/name:de={name}"])
        expressions = Path(temporary_dir) / "feature-filters.txt"
        expressions.write_text("\n".join(filters) + "\n", encoding="utf-8")
        subprocess.run(
            [
                osmium_path,
                "tags-filter",
                "--remove-tags",
                "--expressions",
                str(expressions),
                "--overwrite",
                "-o",
                str(filtered_pbf),
                str(input_pbf),
            ],
            check=True,
        )
        stages["filter"] = {
            "seconds": time.perf_counter() - started,
            **_pbf_profile(filtered_pbf, osmium_path),
        }
        export_config = Path(temporary_dir) / "export.json"
        export_config.write_text(
            json.dumps(
                {
                    "include_tags": list(RETAINED_TAGS),
                    "area_tags": [
                        "natural",
                        "landuse",
                        "leisure",
                        "area=yes",
                        "building",
                        "historic",
                        "tourism",
                        "amenity",
                    ],
                    "linear_tags": ["highway", "waterway", "railway"],
                }
            ),
            encoding="utf-8",
        )
        started = time.perf_counter()
        command = [
            osmium_path,
            "export",
            "--config",
            str(export_config),
            "--add-unique-id=type_id",
            "-f",
            "geojsonseq",
            "-x",
            "print_record_separator=false",
            str(filtered_pbf),
        ]
        count = 0
        tag_counts: Counter[str] = Counter()
        # Consume one feature at a time; never materialize an unrestricted OSM
        # export on disk or ask GDAL to infer thousands of sparse tag columns.
        with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
            try:
                with target_path.open("wb") as output:
                    output.write(b'{"type":"FeatureCollection","features":[')
                    for line in process.stdout:
                        feature = json.loads(line)
                        tags = feature["properties"]
                        tag_counts.update(
                            key for key in tags if key in RETAINED_TAGS[2:]
                        )
                        if count:
                            output.write(b",")
                        encoded = json.dumps(
                            feature, ensure_ascii=False, separators=(",", ":")
                        ).encode("utf-8")
                        if output.tell() + len(encoded) + 2 > MAX_GEOJSON_BYTES:
                            raise ValueError(
                                "OSM export exceeded the 100 MB GeoJSON budget."
                            )
                        output.write(encoded)
                        count += 1
                    output.write(b"]}")
                if process.wait() != 0:
                    raise subprocess.CalledProcessError(process.returncode, command)
            except BaseException:
                process.kill()
                process.wait()
                target_path.unlink(missing_ok=True)
                raise
        export_bytes = target_path.stat().st_size
        if export_bytes > MAX_GEOJSON_BYTES:
            target_path.unlink()
            raise ValueError(
                "OSM export exceeded the 100 MB GeoJSON budget; removed oversized export."
            )
        stages["export"] = {
            "seconds": time.perf_counter() - started,
            "bytes": export_bytes,
            "feature_count": count,
            "tag_counts": dict(tag_counts),
        }
    return target_path


def derive_municipal_map_from_sources(
    boundary_path: str | Path,
    source_pbf: str | Path,
    output_path: str | Path,
    *,
    working_crs: str = WORKING_CRS,
    osmium_path: str = "osmium",
    curated_landmarks: list[str] | None = None,
) -> dict[str, Any]:
    """Derive the offline Municipal Map from the two cached Task 3 sources."""
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target_path.parent) as temporary_dir:
        metrics: dict[str, Any] = {}
        started = time.perf_counter()
        extracted_features = Path(temporary_dir) / "osm-features.geojson"
        extract_osm_features(
            source_pbf,
            extracted_features,
            boundary_path=boundary_path,
            osmium_path=osmium_path,
            curated_landmarks=curated_landmarks,
            metrics=metrics,
        )
        result = derive_municipal_map(
            boundary_path,
            extracted_features,
            output_path=target_path,
            working_crs=working_crs,
            include_districts=True,
        )
        result["performance"] = metrics
        result["performance"]["derive_seconds"] = time.perf_counter() - started
        return result


def derive_municipal_map(
    boundary: gpd.GeoDataFrame | str | Path,
    features: gpd.GeoDataFrame | str | Path,
    *,
    output_path: str | Path | None = None,
    working_crs: str = WORKING_CRS,
    include_districts: bool = False,
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

    # Spatial preselection and vectorized validation avoid expensive per-row
    # checks against the complete, detailed municipal outline.
    shapely.prepare(boundary_geom)
    cleaned = cleaned[shapely.intersects(boundary_geom, cleaned.geometry.array)].copy()
    cleaned["geometry"] = cleaned.geometry.make_valid().simplify(
        1.0, preserve_topology=True
    )
    clipped_geometry = cleaned.geometry.copy()
    crossing = ~shapely.covers(boundary_geom, cleaned.geometry.array)
    clipped_geometry.loc[crossing] = cleaned.loc[crossing].geometry.intersection(
        boundary_geom
    )
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
    tolerance_boundary = boundary_geom.buffer(1e-7)
    shapely.prepare(tolerance_boundary)
    outside = ~shapely.covers(tolerance_boundary, retained.geometry.array)
    if outside.any():
        raise ValueError(
            "Derived municipal map retains features outside the municipal boundary."
        )

    if include_districts:
        districts = boundary_gdf[["geometry"]].copy()
        districts["name"] = boundary_gdf.get(
            "Name", boundary_gdf.get("name", "Leipzig")
        )
        districts["kind"] = "district"
        retained = gpd.GeoDataFrame(
            pd.concat([districts, retained], ignore_index=True), crs=working_crs
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
        "bytes": target_path.stat().st_size,
        "tag_counts": {
            key: dict(Counter(retained[key].dropna()))
            for key in RETAINED_TAGS[2:]
            if key in retained
        },
    }

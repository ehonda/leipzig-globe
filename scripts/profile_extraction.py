"""Profile the legacy PBF stages without producing their oversized GeoJSON."""

import json
import subprocess
import tempfile
import time
from pathlib import Path

import geopandas as gpd


def main():
    cache = Path(".cache")
    results = {}
    with tempfile.TemporaryDirectory(dir="output") as directory:
        root = Path(directory)
        boundary = gpd.read_file(cache / "leipzig-municipal-boundary.geojson")
        polygon = root / "boundary.geojson"
        boundary.to_crs(4326).to_file(polygon, driver="GeoJSON")
        extract = root / "extract.osm.pbf"
        filtered = root / "filtered.osm.pbf"
        stages = [
            (
                "legacy_extract",
                [
                    "extract",
                    "-p",
                    str(polygon),
                    "-o",
                    str(extract),
                    str(cache / "sachsen-latest.osm.pbf"),
                ],
                extract,
            ),
            (
                "legacy_filter",
                [
                    "tags-filter",
                    str(extract),
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
                    "-o",
                    str(filtered),
                ],
                filtered,
            ),
        ]
        for name, command, path in stages:
            start = time.perf_counter()
            subprocess.run(["osmium", *command], check=True)
            duration = time.perf_counter() - start
            info = json.loads(
                subprocess.check_output(["osmium", "fileinfo", "-e", "-j", str(path)])
            )
            tags = subprocess.check_output(
                [
                    "osmium",
                    "tags-count",
                    str(path),
                    "highway",
                    "waterway",
                    "railway",
                    "leisure",
                    "natural",
                    "boundary",
                    "place",
                    "amenity",
                    "tourism",
                    "historic",
                ],
                text=True,
            )
            results[name] = {
                "seconds": duration,
                "bytes": path.stat().st_size,
                "fileinfo": info,
                "tags": tags,
            }
            print(json.dumps({name: results[name]}, indent=2), flush=True)
    Path("output/legacy-extraction-profile.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

"""Repeatable, offline BG-004 acceptance check on a populated source cache."""

import json
import platform
import time
from pathlib import Path

from leipzig_globe.config import load_config
from leipzig_globe.municipal_map import derive_municipal_map_from_sources
from leipzig_globe.pipeline import render_clean_map


def main():
    config = load_config()
    output = Path(config["paths"]["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    cache = Path(config["layout"]["source_cache_dir"])
    started = time.perf_counter()
    result = derive_municipal_map_from_sources(
        cache / "leipzig-municipal-boundary.geojson",
        cache / "sachsen-latest.osm.pbf",
        output / "municipal-map.geojson",
        curated_landmarks=config["layout"]["curated_landmarks"],
    )
    print(json.dumps(result, default=str, indent=2), flush=True)
    render_clean_map(
        config, output / "leipzig-map.png", municipal_map=result["output_path"]
    )
    result.update(
        seconds_to_map=time.perf_counter() - started,
        platform=platform.platform(),
        python=platform.python_version(),
    )
    (output / "map-benchmark.json").write_text(
        json.dumps(result, default=str, indent=2), encoding="utf-8"
    )
    print(
        f"Map produced in {result['seconds_to_map']:.2f}s; Municipal Map {result['bytes'] / 1_000_000:.2f} MB",
        flush=True,
    )
    assert result["seconds_to_map"] < 300, "BG-004 exceeded five minutes"
    assert result["bytes"] < 100_000_000, "BG-004 exceeded 100 MB"


if __name__ == "__main__":
    main()

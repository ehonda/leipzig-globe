"""Acquire candidate pinned inputs separately from the existing source cache."""

import hashlib
import json
from pathlib import Path

import requests

from leipzig_globe.fetcher import DEFAULT_LEIPZIG_BOUNDARY_URL


def main():
    root = Path(".cache/source-lock-bootstrap")
    root.mkdir(parents=True, exist_ok=True)
    urls = {
        "sachsen-latest.osm.pbf": "https://download.geofabrik.de/europe/germany/sachsen-260901.osm.pbf",
        "leipzig-municipal-boundary.geojson": DEFAULT_LEIPZIG_BOUNDARY_URL,
    }
    results = {}
    for name, url in urls.items():
        path = root / name
        sha, md5 = hashlib.sha256(), hashlib.md5()
        with requests.get(url, stream=True, timeout=(15, 60)) as response:
            response.raise_for_status()
            with path.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    handle.write(chunk)
                    sha.update(chunk)
                    md5.update(chunk)
                    if handle.tell() > 400_000_000:
                        raise ValueError("Candidate source exceeded 400 MB budget")
        results[name] = {
            "url": url,
            "sha256": sha.hexdigest(),
            "md5": md5.hexdigest(),
            "bytes": path.stat().st_size,
        }
        print(json.dumps({name: results[name]}), flush=True)
    (root / "measurements.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

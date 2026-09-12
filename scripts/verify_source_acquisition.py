"""Two real, clean acquisitions; preserve existing caches and record evidence.

Run through uv. This downloads about 537 MB and keeps both verified caches.
Both destination directories must be absent or empty, including on reruns.
"""

import argparse
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

from leipzig_globe.fetcher import (
    DEFAULT_CACHE_DIR,
    DEFAULT_SOURCE_LOCK,
    compute_sha256,
    fetch_data_sources,
    load_source_lock,
    load_source_manifests,
    verify_manifest,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=Path, default=Path(DEFAULT_CACHE_DIR))
    parser.add_argument(
        "--second", type=Path, default=Path(".cache/acquisition-audit-2")
    )
    parser.add_argument("--legacy", type=Path, default=Path(".cache"))
    parser.add_argument(
        "--report", type=Path, default=Path("output/source-acquisition.json")
    )
    args = parser.parse_args()
    if args.first.resolve() == args.second.resolve():
        raise ValueError("The two clean acquisition directories must differ.")
    for root in (args.first, args.second):
        if root.exists() and (not root.is_dir() or any(root.iterdir())):
            raise ValueError(
                f"Refusing to reuse nonempty acquisition directory: {root}"
            )
    legacy = load_source_manifests(args.legacy)
    legacy_before = {
        name: verify_manifest(manifest, args.legacy / name)
        for name, manifest in legacy.items()
    }
    sources = load_source_lock()
    measurements = []
    for root in (args.first, args.second):
        started = time.perf_counter()
        print(f"Acquiring pinned sources into clean {root}", flush=True)
        fetch_data_sources(root, sources)
        result = {
            "cache": root.as_posix(),
            "seconds": round(time.perf_counter() - started, 3),
            "manifest_sha256": compute_sha256(root / "source-manifest.json"),
            "sources": {
                source.file_name: {
                    "sha256": verify_manifest(source, root / source.file_name),
                    "bytes": (root / source.file_name).stat().st_size,
                }
                for source in sources
            },
        }
        measurements.append(result)
        print(json.dumps(result), flush=True)
    if measurements[0]["sources"] != measurements[1]["sources"]:
        raise ValueError("Clean acquisitions produced different inputs.")
    if measurements[0]["manifest_sha256"] != measurements[1]["manifest_sha256"]:
        raise ValueError("Clean acquisitions produced different provenance.")
    legacy_after = {
        name: verify_manifest(manifest, args.legacy / name)
        for name, manifest in load_source_manifests(args.legacy).items()
    }
    if legacy_before != legacy_after:
        raise ValueError("Legacy cache changed during acquisition.")
    report = {
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "source_lock_sha256": compute_sha256(DEFAULT_SOURCE_LOCK),
        "acquisitions": measurements,
        "identical_inputs_and_manifests": True,
        "unchanged_verified_legacy_sources": legacy_after,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Verified two independent acquisitions; evidence: {args.report}", flush=True)


if __name__ == "__main__":
    main()

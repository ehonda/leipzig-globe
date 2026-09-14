"""Build the three 215 mm high-density exterior variants from current code.

Run through uv. Output directories must be new so a failed run cannot reuse an
old manifest. Only pinned source downloads are cached between hosted builds.
"""

import argparse
import json
import os
import re
import shutil
from pathlib import Path

from leipzig_globe.config import load_config
from leipzig_globe.fetcher import compute_sha256, fetch_data_sources, load_source_lock
from leipzig_globe.pipeline import build_artifacts, validate_output_directory
from leipzig_globe.web_preview import export_web_preview


def copy_baseline(source, destination):
    snapshot = json.loads((source / "snapshot.json").read_text(encoding="utf-8"))
    files = {
        path.relative_to(source).as_posix(): path
        for path in (source / "assets").rglob("*")
        if path.is_file()
    }
    if sum(path.stat().st_size for path in files.values()) > 16_000_000:
        raise ValueError("The fixed comparison baseline exceeds its 16 MB budget.")
    if {name: compute_sha256(path) for name, path in files.items()} != snapshot[
        "sha256"
    ]:
        raise ValueError("Frozen baseline files differ from their recorded hashes.")
    shutil.copytree(source, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("output/pages-build"))
    parser.add_argument("--site-dir", type=Path, default=Path("output/pages-site"))
    parser.add_argument(
        "--revision", default=os.environ.get("GITHUB_SHA", "working-tree")
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9-]+", args.revision):
        raise ValueError("Revision must contain only letters, numbers and hyphens.")
    if args.output_dir.exists() or args.site_dir.exists():
        raise ValueError(
            "Choose new build and site directories; existing outputs are preserved."
        )
    args.output_dir.mkdir(parents=True)
    args.site_dir.mkdir(parents=True)
    for name in ("index.html", "style.css", "globe.js"):
        shutil.copyfile(Path("docs") / name, args.site_dir / name)
    index = args.site_dir / "index.html"
    html = index.read_text(encoding="utf-8")
    for name in ("style.css", "globe.js"):
        html = html.replace(f'"{name}"', f'"{name}?v={args.revision}"')
    index.write_text(html, encoding="utf-8")
    # One immutable, reduced preview snapshot. Never rebuild historical commits.
    copy_baseline(Path("docs/baseline"), args.site_dir / "baseline")
    versions = json.loads(Path("docs/versions.json").read_text(encoding="utf-8"))
    versions["versions"][0]["revision"] = args.revision
    (args.site_dir / "versions.json").write_text(
        json.dumps(versions, indent=2), encoding="utf-8"
    )

    source_cache = Path(load_config()["layout"]["source_cache_dir"])
    fetch_data_sources(source_cache, load_source_lock())
    reports = {}
    for preset in ("terrain", "ocean", "fog"):
        print(f"Building Pages variant {preset}", flush=True)
        config = load_config("config/globe-215mm-high-density.yaml")
        config["layout"]["exterior"] = preset
        root = args.output_dir / preset
        artifacts = build_artifacts(config, root)
        validate_output_directory(root)
        export_web_preview(
            artifacts["texture"],
            artifacts["gore_dir"],
            args.site_dir / "assets",
            config=config,
            preset_id=preset,
        )
        report = root / "build-report.json"
        destination = args.site_dir / "assets" / preset / "build-report.json"
        shutil.copyfile(report, destination)
        reports[preset] = str(destination.relative_to(args.site_dir).as_posix())

    # Hash every published asset for independent deployed-byte verification.
    files = {
        path.relative_to(args.site_dir).as_posix(): compute_sha256(path)
        for path in sorted(args.site_dir.rglob("*"))
        if path.is_file()
    }
    (args.site_dir / "build.json").write_text(
        json.dumps(
            {
                "revision": args.revision,
                "reports": reports,
                "sha256": files,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Validated Pages site: {args.site_dir}", flush=True)


if __name__ == "__main__":
    main()

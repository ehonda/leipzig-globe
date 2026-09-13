"""Build both Pages presets from current code; never publish stale tracked assets.

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

    source_cache = Path(load_config()["layout"]["source_cache_dir"])
    fetch_data_sources(source_cache, load_source_lock())
    reports = {}
    for preset, config_path in (
        ("default", None),
        ("globe-215mm-high-density", "config/globe-215mm-high-density.yaml"),
    ):
        print(f"Building Pages preset {preset}", flush=True)
        config = load_config(config_path)
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

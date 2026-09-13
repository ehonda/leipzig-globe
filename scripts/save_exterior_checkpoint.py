"""Validate cross-variant invariants and save a compact exterior comparison.

Run through uv with --build-dir pointing to a completed scripts/build_pages.py run.
"""

import argparse
import json
import shutil
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

from leipzig_globe.exterior import EXTERIORS
from leipzig_globe.fetcher import compute_sha256
from leipzig_globe.pipeline import validate_output_directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("demos/06-exterior-variants")
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    font_path = str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf")
    font = ImageFont.truetype(font_path, 22)
    small = ImageFont.truetype(font_path, 15)
    sheet = Image.new("RGB", (1280, 1130), (247, 247, 247))
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 12), "Outside Leipzig · 215 mm / 300 PPI", font=font, fill="#333333")
    evidence = {}
    shared = None
    for row, variant in enumerate(("terrain", "ocean", "fog")):
        root = args.build_dir / variant
        validation = validate_output_directory(root)
        report = json.loads((root / "build-report.json").read_text(encoding="utf-8"))
        metadata = json.loads((root / "leipzig-map.json").read_text(encoding="utf-8"))
        geometry = json.loads(
            (root / "gores/geometry-manifest.json").read_text(encoding="utf-8")
        )
        identity = {
            "city_data": compute_sha256(root / "municipal-map.geojson"),
            "city_raster": compute_sha256(root / "leipzig-map.png"),
            "municipal_mask": compute_sha256(root / "leipzig-map.boundary.png"),
            "map_metadata": metadata,
            "gore_geometry": geometry["gores"],
        }
        if shared is None:
            shared = identity
        assert (
            identity == shared
        ), f"{variant}: city placement, labels or gore geometry changed"
        with Image.open(root / "leipzig-texture.png") as texture:
            unrotated = ImageChops.offset(
                texture,
                -round(
                    report["config"]["globe"]["seam_offset_deg"] / 360 * texture.width
                ),
                0,
            )
            array = np.asarray(unrotated)
            np.testing.assert_array_equal(array[:, 0], array[:, -1])
            assert (
                np.unique(array[0], axis=0).shape[0] == 1
            ), f"{variant}: north pole is not uniform"
            assert (
                np.unique(array[-1], axis=0).shape[0] == 1
            ), f"{variant}: south pole is not uniform"
            with (
                Image.open(root / "leipzig-map.png") as city,
                Image.open(root / "leipzig-map.boundary.png") as mask,
            ):
                city = np.asarray(city.resize(texture.size, Image.Resampling.LANCZOS))
                inside = (
                    np.asarray(mask.resize(texture.size, Image.Resampling.LANCZOS))
                    == 255
                )
                np.testing.assert_array_equal(array[inside], city[inside])
            compact = texture.copy()
            compact.thumbnail((1600, 800), Image.Resampling.LANCZOS)
            compact.save(args.output / f"{variant}-texture.png")
        top = 50 + row * 350
        draw.text((18, top), EXTERIORS[variant][0], font=font, fill="#333333")
        for column, view in enumerate(("front", "back", "north", "south")):
            with Image.open(root / "preview" / f"{view}.png") as preview:
                sheet.paste(
                    preview.resize((300, 300), Image.Resampling.LANCZOS),
                    (column * 320 + 10, top + 28),
                )
            draw.text(
                (column * 320 + 20, top + 325), view.title(), font=small, fill="#333333"
            )
        shutil.copyfile(
            root / "build-report.json", args.output / f"{variant}-build-report.json"
        )
        evidence[variant] = {
            "validated_artifacts": len(validation["artifacts"]),
            "texture_sha256": compute_sha256(root / "leipzig-texture.png"),
            "physical": report["physical"],
        }
    draw.text(
        (18, 1105),
        "© OpenStreetMap contributors · Boundary: Stadt Leipzig · Physical fit test still pending",
        font=small,
        fill="#333333",
    )
    sheet.save(args.output / "comparison.jpg", quality=92)
    (args.output / "checkpoint.json").write_text(
        json.dumps(
            {
                "source_build": str(args.build_dir),
                "variants": evidence,
                "verified": [
                    "identical municipal data, raster, masks and labels",
                    "identical gore geometry",
                    "all city interior pixels preserved",
                    "exact wrap and pole continuity",
                    "full artifact validation",
                ],
                "physical_test": "Pending human printing, measurement and fit.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Validated exterior comparison: {args.output}", flush=True)


if __name__ == "__main__":
    main()

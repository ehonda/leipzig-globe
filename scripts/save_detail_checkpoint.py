"""Record detail/label evidence and an exact-scale A4 before/current comparison."""

import argparse
import json
from pathlib import Path

import geopandas as gpd
import matplotlib
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("demos/09-detail-labels"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    roots = [args.before, args.after]
    metadata = [
        json.loads((root / "leipzig-map.json").read_text(encoding="utf-8"))
        for root in roots
    ]
    reports = [
        json.loads((root / "build-report.json").read_text(encoding="utf-8"))
        for root in roots
    ]
    for key in ("center_metric", "bounds_metric", "span_metric", "sampling"):
        assert metadata[0][key] == metadata[1][key], f"City placement changed: {key}"
    frame = gpd.read_file(args.after / "municipal-map.geojson")
    transform = Transformer.from_crs(frame.crs, 4326, always_xy=True)
    landmarks = []
    selected = {item["label"]: item for item in metadata[1]["rendered_labels"]}
    for symbol in metadata[1]["landmark_symbols"]:
        feature = frame.loc[frame["id"] == symbol["source_id"]].iloc[0]
        from shapely.geometry import Point

        assert symbol["label"] in {feature.get("name"), feature.get("name:de")}
        assert feature.geometry.buffer(1e-6).covers(Point(symbol["anchor_metric"]))
        landmarks.append(
            {
                **symbol,
                "lon_lat": list(transform.transform(*symbol["anchor_metric"])),
                "label_placement": selected.get(symbol["label"]),
            }
        )
    assert {"Völkerschlachtdenkmal", "Red Bull Arena"} <= selected.keys()
    evidence = {
        "baseline_revision": "69567a2f7d4cbf5936f2608d8b36c286748d1b19",
        "before": {
            "build": str(args.before),
            "texture_sha256": reports[0]["artifact_sha256"]["leipzig-texture.png"],
            "visible_labels": len(metadata[0]["rendered_labels"]),
            "performance": reports[0]["performance"],
        },
        "current": {
            "build": str(args.after),
            "texture_sha256": reports[1]["artifact_sha256"]["leipzig-texture.png"],
            "visible_labels": len(selected),
            "performance": reports[1]["performance"],
        },
        "landmarks": landmarks,
        "omitted_labels": metadata[1]["omitted_labels"],
        "verified": [
            "unchanged city viewport and sampling",
            "landmark anchors inside identified OSM geometries",
            "Völkerschlachtdenkmal and stadium labels visible",
        ],
    }
    (args.output / "detail-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pdf = canvas.Canvas(
        str(args.output / "print-scale-comparison.pdf"),
        pagesize=(210 * 72 / 25.4, 297 * 72 / 25.4),
    )
    mm = 72 / 25.4
    pdf.setFont("Helvetica", 13)
    pdf.drawString(15 * mm, 280 * mm, "215 mm globe - before / current at print scale")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(
        15 * mm,
        270 * mm,
        "Print at 100%. Each artwork crop is 80 x 60 mm. Physical fit remains untested.",
    )
    pdf.rect(15 * mm, 254 * mm, 100 * mm, 10 * mm)
    pdf.drawString(120 * mm, 258 * mm, "100 mm calibration")
    sheet = Image.new("RGB", (1400, 1780), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(
        str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"), 22
    )
    draw.text((20, 10), "Before (69567a2)", fill="black", font=font)
    draw.text((720, 10), "Current", fill="black", font=font)
    textures = [Image.open(root / "leipzig-texture.png") for root in roots]
    cfg = reports[1]["config"]
    px_mm = cfg["globe"]["ppi"] / 25.4
    tw, th = textures[1].size
    sw, sh = metadata[1]["sampling"]["source_pixels"]
    anchors = {
        entry["label"]: entry["anchor_px"] for entry in metadata[1]["landmark_symbols"]
    }
    for row, name in enumerate(
        ("Red Bull Arena", "Thomaskirche", "Völkerschlachtdenkmal")
    ):
        x, y = anchors[name]
        cx, cy = (
            x / sw * tw + round(cfg["globe"]["seam_offset_deg"] / 360 * tw),
            y / sh * th,
        )
        region = (
            round(cx - 40 * px_mm),
            round(cy - 30 * px_mm),
            round(cx + 40 * px_mm),
            round(cy + 30 * px_mm),
        )
        draw.text((20, 50 + row * 565), name, fill="black", font=font)
        for column, texture in enumerate(textures):
            crop = texture.crop(region)
            pdf.drawImage(
                ImageReader(crop),
                (15 + column * 100) * mm,
                (180 - row * 75) * mm,
                width=80 * mm,
                height=60 * mm,
            )
            pdf.setFont("Helvetica", 9)
            pdf.drawString(
                (15 + column * 100) * mm,
                (242 - row * 75) * mm,
                f"{'Before' if column == 0 else 'Current'} - {name}",
            )
            sheet.paste(
                crop.resize((660, 495), Image.Resampling.LANCZOS),
                (20 + column * 700, 85 + row * 565),
            )
    pdf.setFont("Helvetica", 7)
    pdf.drawString(
        15 * mm,
        15 * mm,
        "Map data (c) OpenStreetMap contributors. Boundary: Stadt Leipzig, DL-DE/BY-2.0.",
    )
    pdf.save()
    sheet.save(args.output / "detail-comparison.jpg", quality=92)
    for texture in textures:
        texture.close()
    print(f"Detail and print-scale evidence: {args.output}")


if __name__ == "__main__":
    main()

"""Compare fixed regional crops and audit their mapped land-cover sources."""

import argparse
import json
from pathlib import Path

import geopandas as gpd
import matplotlib
import shapely
from PIL import Image, ImageDraw, ImageFont

from leipzig_globe.rendering import feature_kind

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--before", type=Path, required=True)
parser.add_argument("--after", type=Path, required=True)
parser.add_argument("--output", type=Path, default=Path("demos/10-landcover-lakes"))
args = parser.parse_args()
root = args.after
out = args.output
out.mkdir(exist_ok=True, parents=True)
frame = gpd.read_file(root / "municipal-map.geojson")
frame["render_kind"] = [feature_kind(row) for row in frame.to_dict("records")]
regions = {
    "South of Grünau / west of Großzschocher": (12.26, 51.285, 12.315, 51.314),
    "East of Engelsdorf": (12.47, 51.325, 12.525, 51.36),
    "Northern outskirts": (12.325, 51.402, 12.43, 51.435),
    "Böhlitz-Ehrenberg": (12.272, 51.352, 12.32, 51.377),
    "Dölitz-Dösen": (12.37, 51.274, 12.426, 51.299),
    "Kulkwitzer See": (12.226, 51.285, 12.273, 51.323),
    "Cospudener See": (12.323, 51.249, 12.367, 51.295),
}
meta = json.loads((root / "leipzig-map.json").read_text(encoding="utf-8"))
before_meta = json.loads((args.before / "leipzig-map.json").read_text(encoding="utf-8"))
for key in ("center_metric", "bounds_metric", "span_metric", "sampling"):
    assert meta[key] == before_meta[key], key
images = [
    Image.open(args.before / "leipzig-map.png"),
    Image.open(root / "leipzig-map.png"),
]
cx, cy = meta["center_metric"]
sx, sy = meta["span_metric"]
w, h = images[1].size
font = ImageFont.truetype(
    str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"), 24
)
sheet = Image.new("RGB", (1600, len(regions) * 480), "white")
draw = ImageDraw.Draw(sheet)
evidence = {}
boundary = shapely.union_all(frame[frame["kind"] == "district"].geometry)
for i, (name, bounds) in enumerate(regions.items()):
    geom = gpd.GeoSeries([shapely.box(*bounds)], crs=4326).to_crs(frame.crs).iloc[0]
    municipal_region = geom.intersection(boundary)
    selected = frame[frame.geometry.intersects(municipal_region)]
    covers = {}
    for kind, group in selected.groupby("render_kind"):
        if kind in {
            "farmland",
            "industrial",
            "disturbed",
            "orchard",
            "scrub",
            "park",
            "water",
        }:
            area = shapely.union_all(group.geometry).intersection(municipal_region).area
            covers[kind] = {
                "area_km2": round(area / 1e6, 3),
                "municipal_region_percent": round(
                    area / municipal_region.area * 100, 1
                ),
                "features": len(group),
            }
    evidence[name] = {
        "bounds_lon_lat": bounds,
        "mapped_cover": covers,
        "large_fields": [
            {
                "source_id": row["id"],
                "area_ha": round(row["geometry"].intersection(geom).area / 10000, 2),
            }
            for row in selected[selected["render_kind"] == "farmland"]
            .sort_values("id")
            .to_dict("records")
            if row["geometry"].intersection(geom).area > 50000
        ],
    }
    x0, y0, x1, y1 = geom.bounds
    crop = (
        round((x0 - cx) * w / sx + w / 2),
        round(h / 2 - (y1 - cy) * h / sy),
        round((x1 - cx) * w / sx + w / 2),
        round(h / 2 - (y0 - cy) * h / sy),
    )
    crop = (max(0, crop[0]), max(0, crop[1]), min(w, crop[2]), min(h, crop[3]))
    draw.text((15, i * 480 + 5), name, fill="black", font=font)
    for col, image in enumerate(images):
        panel = image.crop(crop)
        # Final map doubles x relative to y; retain the printed label proportions.
        ratio = min(770 / panel.width, 420 / (panel.height / 2))
        panel = panel.resize(
            (round(panel.width * ratio), round(panel.height * ratio / 2)),
            Image.Resampling.LANCZOS,
        )
        sheet.paste(panel, (15 + col * 800, i * 480 + 55))
        draw.text(
            (15 + col * 800, i * 480 + 30),
            "Before" if col == 0 else "Current",
            fill="black",
            font=font,
        )
sheet.save(out / "regional-comparison.jpg", quality=92)
evidence["landcover_totals"] = {
    kind: round(shapely.union_all(group.geometry).area / 1e6, 3)
    for kind, group in frame.groupby("render_kind")
    if kind in {"farmland", "industrial", "disturbed", "orchard", "scrub"}
}
evidence["visible_lakes"] = [
    item for item in meta["rendered_labels"] if item.get("is_lake")
]
for label in evidence["visible_lakes"]:
    source = frame.loc[frame["id"] == label["source_id"]].iloc[0]
    assert label["label"] in {source.get("name"), source.get("name:de")}
    assert source.geometry.covers(shapely.Point(label["anchor_metric"]))
    x0, y0, x1, y1 = label["bbox"]
    footprint = shapely.box(
        (x0 - w / 2) * sx / w + cx,
        cy - (y1 - h / 2) * sy / h,
        (x1 - w / 2) * sx / w + cx,
        cy - (y0 - h / 2) * sy / h,
    )
    assert source.geometry.covers(footprint), label["label"]
evidence["composite_omissions"] = [
    item for item in meta["omitted_labels"] if item["reason"] == "covered_by_composite"
]
visible_names = {item["label"] for item in meta["rendered_labels"]}
for omission in evidence["composite_omissions"]:
    assert omission["composite"] in visible_names
    assert omission["label"] not in visible_names
evidence["lake_omissions"] = [
    item for item in meta["omitted_labels"] if item.get("is_lake")
]
evidence["baseline_revision"] = "b273fff003c11adb719674db666585eff5eebc71"
evidence["source_snapshot"] = "sources-2026-09-01"
evidence["visible_labels"] = len(meta["rendered_labels"])
evidence["verified"] = [
    "unchanged viewport and sampling",
    "mapped OSM land-cover classes; no inferred fills",
    "lake source names and anchors verified; entire label footprints inside water",
    "every suppressed component has a visible composite",
]
(out / "source-evidence.json").write_text(
    json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("Mapped land-cover totals (km²):", evidence["landcover_totals"])
print("Visible lakes:", [item["label"] for item in evidence["visible_lakes"]])
print(
    "Lake omissions:",
    [(item["label"], item["reason"]) for item in evidence["lake_omissions"]],
)
print(
    "Composites:",
    [(item["label"], item["composite"]) for item in evidence["composite_omissions"]],
)

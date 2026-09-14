import json
import math
import runpy
import subprocess
from pathlib import Path

import geopandas as gpd
import matplotlib
import pytest
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Point, box, shape

from leipzig_globe.config import validate_config
from leipzig_globe.municipal_map import extract_osm_features
from leipzig_globe.rendering import feature_kind, render_clean_map


def test_real_osmium_preserves_paths_and_sports_areas(tmp_path):
    fixture = Path("tests/fixtures/leipzig.osm").read_text(encoding="utf-8")
    additions = """
      <way id="7"><nd ref="1"/><nd ref="3"/><tag k="highway" v="cycleway"/></way>
      <way id="8"><nd ref="5"/><nd ref="6"/><nd ref="7"/><nd ref="8"/><nd ref="5"/><tag k="leisure" v="pitch"/></way>
      <way id="9"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/><tag k="leisure" v="stadium"/><tag k="name" v="Red Bull Arena"/></way>
    """
    source = tmp_path / "detail.osm"
    source.write_text(fixture.replace("</osm>", additions + "</osm>"), encoding="utf-8")
    pbf = tmp_path / "detail.pbf"
    subprocess.run(["osmium", "cat", str(source), "-o", str(pbf)], check=True)
    result = extract_osm_features(pbf, tmp_path / "features.geojson")
    features = json.loads(result.read_text(encoding="utf-8"))["features"]
    selected = {item["id"]: item for item in features}
    assert selected["w7"]["geometry"]["type"] == "LineString"
    assert feature_kind(selected["w7"]["properties"]) == "path"
    assert shape(selected["a16"]["geometry"]).equals(
        box(12.365, 51.335, 12.370, 51.340)
    )
    assert feature_kind(selected["a16"]["properties"]) == "sport"
    assert selected["a18"]["properties"]["name"] == "Red Bull Arena"


@pytest.mark.parametrize("sx,sy", [(1, 1), (1.3, 0.8), (0.7, 1.3)])
def test_text_keeps_natural_final_aspect_and_landmark_identity(tmp_path, sx, sy):
    rows = [
        {"kind": "land", "geometry": box(0, 0, 100, 100)},
        {
            "id": "stadium",
            "name": "Red Bull Arena",
            "leisure": "stadium",
            "geometry": Point(50, 50),
        },
        {
            "id": "sign",
            "name": "Red Bull Arena",
            "tourism": "information",
            "geometry": Point(10, 10),
        },
    ]
    cfg = validate_config(
        {
            "globe": {"ppi": 100},
            "layout": {
                "world_layout_scale_x": sx,
                "world_layout_scale_y": sy,
                "curated_landmarks": ["Red Bull Arena"],
            },
        }
    )
    result = render_clean_map(
        cfg, tmp_path / "map.png", gpd.GeoDataFrame(rows, crs=32633)
    )
    label = result["layout"]["rendered_labels"][0]
    assert label["source_id"] == "stadium"
    assert label["anchor_metric"] == pytest.approx([50, 50])
    assert label["leader_px"][0] == pytest.approx(label["anchor_px"])
    assert label["is_landmark"]
    # The final glyph proportions must not inherit the geography's x/y stretch.
    x0, y0, x1, y1 = label["texture_bbox_unwrapped"]
    font = ImageFont.truetype(
        str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"), 100
    )
    bounds = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox(
        (0, 0), "Red Bull Arena", font=font, stroke_width=10
    )
    assert (x1 - x0) / (y1 - y0) == pytest.approx(
        (bounds[2] - bounds[0]) / (bounds[3] - bounds[1]), rel=0.09
    )
    tw, th = result["layout"]["sampling"]["texture_pixels"]
    margin = 10 * 100 / 25.4
    assert math.floor((x0 - margin) / (tw / 12)) == math.floor(
        (x1 + margin) / (tw / 12)
    )
    assert y0 >= 20 * 100 / 25.4 and y1 <= th - 20 * 100 / 25.4


def test_fixed_baseline_is_complete_bounded_and_tamper_checked(tmp_path):
    copy_baseline = runpy.run_path("scripts/build_pages.py")["copy_baseline"]
    copy_baseline(Path("docs/baseline"), tmp_path / "baseline")
    root = tmp_path / "baseline"
    presets = json.loads((root / "assets/presets.json").read_text())["presets"]
    assert len(presets) == 3
    for preset in presets:
        path = root / "assets" / preset["manifest"]
        manifest = json.loads(path.read_text())
        assert manifest["diameter_mm"] == 215
        assert (path.parent / manifest["texture"]).is_file()
        assert len(manifest["gores"]) == 12
        assert all(
            (path.parent / gore["texture"]).is_file() for gore in manifest["gores"]
        )
    (root / "assets/terrain/texture.webp").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hashes"):
        copy_baseline(root, tmp_path / "invalid")


def test_unplaceable_label_keeps_identity_and_all_rejection_evidence(tmp_path):
    rows = [
        {"kind": "land", "geometry": box(0, 0, 100, 100)},
        {"natural": "water", "geometry": box(0, 0, 100, 100)},
        {"id": "city", "name": "Leipzig", "place": "city", "geometry": Point(50, 50)},
    ]
    result = render_clean_map(
        {"globe": {"ppi": 60}, "layout": {"curated_landmarks": ["Leipzig"]}},
        tmp_path / "map.png",
        gpd.GeoDataFrame(rows, crs=32633),
    )
    assert not result["rendered_labels"]
    omission = result["omitted_labels"][0]
    assert omission["source_id"] == "city"
    assert omission["anchor_metric"] == pytest.approx([50, 50])
    assert omission["rejected_positions"]["feature_collision"] > 0
    assert sum(omission["rejected_positions"].values()) == 2 * 33 * 33
    assert omission["reason"] == max(
        omission["rejected_positions"], key=omission["rejected_positions"].get
    )

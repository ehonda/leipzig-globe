import json
import subprocess
from pathlib import Path

import geopandas as gpd
import pytest
import shapely
from PIL import Image

from leipzig_globe.municipal_map import extract_osm_features
from leipzig_globe.rendering import feature_kind, render_clean_map


def render(tmp_path, rows):
    return render_clean_map(
        {"globe": {"ppi": 60}, "layout": {"curated_landmarks": []}},
        tmp_path / "map.png",
        gpd.GeoDataFrame(
            [{"kind": "land", "geometry": shapely.box(0, 0, 10000, 10000)}, *rows],
            crs=32633,
        ),
    )


@pytest.mark.parametrize("composite", ["Dölitz-Dösen", "Böhlitz-Ehrenberg"])
def test_composite_replaces_nearby_components(tmp_path, composite):
    names = [composite, *composite.split("-")]
    rows = [
        {
            "name": name,
            "place": "suburb",
            "geometry": shapely.Point(4900 + i * 100, 5000),
        }
        for i, name in enumerate(names)
    ]
    result = render(tmp_path, rows)
    assert composite in result["rendered_labels"]
    assert not set(names[1:]) & set(result["rendered_labels"])
    assert {
        item["label"]
        for item in result["omitted_labels"]
        if item["reason"] == "covered_by_composite"
    } == set(names[1:])


def test_components_survive_when_composite_cannot_fit(tmp_path):
    rows = [
        {"name": name, "place": "suburb", "geometry": shapely.Point(x, y)}
        for name, x, y in [
            ("Dölitz-Dösen", 5000, 9900),
            ("Dölitz", 4000, 5200),
            ("Dösen", 6000, 5200),
        ]
    ]
    result = render(tmp_path, rows)
    assert "Dölitz-Dösen" not in result["rendered_labels"]
    assert {"Dölitz", "Dösen"} <= set(result["rendered_labels"])


def test_distant_component_is_not_removed(tmp_path):
    rows = [
        {"name": name, "place": "suburb", "geometry": shapely.Point(x, y)}
        for name, x, y in [
            ("Dölitz-Dösen", 2000, 2500),
            ("Dölitz", 2500, 2500),
            ("Dösen", 8000, 7500),
        ]
    ]
    result = render(tmp_path, rows)
    assert not any(
        item["reason"] == "covered_by_composite" for item in result["omitted_labels"]
    )


def test_lake_label_stays_in_water_and_off_roads(tmp_path):
    lake = shapely.box(1500, 2000, 8500, 8000).difference(
        shapely.box(4200, 4300, 5300, 5600)
    )
    road = shapely.LineString([(5500, 0), (5500, 10000)])
    result = render(
        tmp_path,
        [
            {
                "id": "lake",
                "natural": "water",
                "water": "lake",
                "name": "Testsee",
                "geometry": lake,
            },
            {"highway": "primary", "geometry": road},
            {
                "natural": "water",
                "water": "pond",
                "name": "Tiny",
                "geometry": shapely.box(100, 100, 200, 200),
            },
            {
                "natural": "water",
                "water": "river",
                "name": "River",
                "geometry": shapely.box(100, 2000, 500, 8000),
            },
        ],
    )
    assert result["rendered_labels"] == ["Testsee"]
    meta = result["layout"]
    label = meta["rendered_labels"][0]
    width, height = meta["sampling"]["source_pixels"]
    cx, cy = meta["center_metric"]
    sx, sy = meta["span_metric"]
    x0, y0, x1, y1 = label["bbox"]
    footprint = shapely.box(
        (x0 - width / 2) * sx / width + cx,
        cy - (y1 - height / 2) * sy / height,
        (x1 - width / 2) * sx / width + cx,
        cy - (y0 - height / 2) * sy / height,
    )
    assert lake.covers(footprint)
    assert not road.intersects(footprint)
    assert label["source_id"] == "lake" and label["is_lake"]
    assert lake.covers(shapely.Point(label["anchor_metric"]))


def test_real_extract_retains_landcover_and_water_classification(tmp_path):
    fixture = Path("tests/fixtures/leipzig.osm").read_text(encoding="utf-8")
    classes = [
        ("landuse", "farmland"),
        ("landuse", "industrial"),
        ("natural", "scrub"),
        ("landuse", "orchard"),
        ("landuse", "brownfield"),
        ("natural", "water"),
    ]
    additions = "".join(
        f'<way id="{i}"><nd ref="5"/><nd ref="6"/><nd ref="7"/><nd ref="8"/><nd ref="5"/><tag k="{key}" v="{value}"/><tag k="water" v="lake"/></way>'
        for i, (key, value) in enumerate(classes, 20)
    )
    source = tmp_path / "landcover.osm"
    source.write_text(fixture.replace("</osm>", additions + "</osm>"), encoding="utf-8")
    pbf = tmp_path / "landcover.pbf"
    subprocess.run(["osmium", "cat", str(source), "-o", str(pbf)], check=True)
    path = extract_osm_features(pbf, tmp_path / "features.geojson")
    selected = {
        item["id"]: item
        for item in json.loads(path.read_text(encoding="utf-8"))["features"]
    }
    for i, expected in enumerate(
        ["farmland", "industrial", "scrub", "orchard", "disturbed", "water"], 20
    ):
        assert feature_kind(selected[f"a{i*2}"]["properties"]) == expected
        assert shapely.geometry.shape(selected[f"a{i*2}"]["geometry"]).equals(
            shapely.box(12.365, 51.335, 12.370, 51.340)
        )
    assert selected["a50"]["properties"]["water"] == "lake"


def test_narrow_lake_uses_vertical_name_with_natural_aspect(tmp_path):
    result = render(
        tmp_path,
        [
            {
                "natural": "water",
                "water": "lake",
                "name": "Kulkwitzer See",
                "geometry": shapely.box(2500, 1500, 3000, 8500),
            }
        ],
    )
    assert result["rendered_labels"] == ["Kulkwitzer See"]
    label = result["layout"]["rendered_labels"][0]
    assert label["rotation_deg"] == 90
    x0, y0, x1, y1 = label["texture_bbox_unwrapped"]
    assert (y1 - y0) / (x1 - x0) > 4


def test_farmland_has_fill_and_preserves_holes(tmp_path):
    field = shapely.box(1000, 1000, 9000, 9000).difference(
        shapely.box(4000, 4000, 6000, 6000)
    )
    result = render(tmp_path, [{"landuse": "farmland", "geometry": field}])
    with Image.open(result["image_path"]) as image:
        assert image.getpixel((image.width // 4, image.height // 2)) == (226, 226, 193)
        assert image.getpixel((image.width // 2, image.height // 2)) == (247, 244, 238)

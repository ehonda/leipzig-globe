import math

import geopandas as gpd
import pytest
from PIL import Image
from shapely.geometry import Point, box

from leipzig_globe.config import validate_config
from leipzig_globe.rendering import (
    generate_globe_texture,
    render_clean_map,
    scaled_texture_dimensions,
    source_map_dimensions,
    texture_dimensions,
)


@pytest.mark.parametrize("ratio", [0.5, 0.9868, 1, 2])
@pytest.mark.parametrize("sx,sy", [(1, 1), (1.25, 0.7), (0.4, 1.5)])
def test_source_sampling_meets_both_axes_after_world_scaling(ratio, sx, sy):
    cfg = validate_config(
        {
            "globe": {"ppi": 40},
            "layout": {
                "world_layout_scale_x": sx,
                "world_layout_scale_y": sy,
            },
        }
    )
    width, height = source_map_dimensions(cfg, ratio)
    scaled_width, scaled_height = scaled_texture_dimensions(cfg)
    assert width >= scaled_width
    assert height >= scaled_height
    assert width / height == pytest.approx(ratio, abs=1 / height)
    assert width * height <= 100_000_000


@pytest.mark.parametrize("diameter,minimum", [(215, (5320, 2660)), (300, (7422, 3711))])
def test_reference_and_legacy_source_are_not_half_resolution(diameter, minimum):
    cfg = validate_config({"globe": {"diameter_mm": diameter}})
    width, height = source_map_dimensions(cfg, 3662 / 3711)
    assert width >= minimum[0]
    assert height >= minimum[1]
    assert width * height <= 100_000_000


def test_extreme_physical_size_has_actionable_budget_error():
    with pytest.raises(ValueError, match="texture budget"):
        validate_config({"globe": {"diameter_mm": 1e200}})


@pytest.mark.parametrize("sx,sy", [(1e300, 1), (100, 100), (1e200, 1e-200)])
def test_unbounded_scaled_raster_fails_configuration(sx, sy):
    with pytest.raises(ValueError, match="raster budget"):
        validate_config(
            {"layout": {"world_layout_scale_x": sx, "world_layout_scale_y": sy}}
        )


def test_source_budget_fails_before_image_allocation(tmp_path, monkeypatch):
    data = gpd.GeoDataFrame(
        {"kind": ["land"]}, geometry=[box(0, 0, 100, 200)], crs=32633
    )

    def no_allocation(*args, **kwargs):
        pytest.fail("Oversized source raster reached image allocation")

    monkeypatch.setattr("leipzig_globe.rendering.Image.new", no_allocation)
    with pytest.raises(ValueError, match="source-map budget"):
        render_clean_map({"globe": {"diameter_mm": 300}}, tmp_path / "map.png", data)


def test_texture_rejects_undersized_map(tmp_path):
    path = tmp_path / "map.png"
    Image.new("RGB", (100, 100)).save(path)
    with pytest.raises(ValueError, match="insufficient resolution"):
        generate_globe_texture(
            {"globe": {"ppi": 20}}, tmp_path / "texture.png", source_map=path
        )
    assert not (tmp_path / "texture.png").exists()


def test_scaled_texture_resamples_once_without_enlargement(tmp_path, monkeypatch):
    cfg = validate_config(
        {
            "globe": {"ppi": 20},
            "layout": {
                "world_layout_scale_x": 1.3,
                "world_layout_scale_y": 0.7,
            },
        }
    )
    size = source_map_dimensions(cfg, 1)
    path = tmp_path / "map.png"
    Image.new("RGB", size, (20, 40, 60)).save(path)
    original = Image.Image.resize
    calls = []

    def resize(image, target, *args, **kwargs):
        calls.append((image.size, target))
        assert image.width >= target[0] and image.height >= target[1]
        return original(image, target, *args, **kwargs)

    monkeypatch.setattr(Image.Image, "resize", resize)
    texture = generate_globe_texture(cfg, tmp_path / "texture.png", source_map=path)
    assert calls == [(size, scaled_texture_dimensions(cfg))]
    with Image.open(texture) as image:
        assert image.size == texture_dimensions(cfg)
        assert image.getpixel((image.width // 2, image.height // 2)) == (20, 40, 60)
        assert image.getpixel((image.width // 2, 0)) == tuple(
            cfg["style"]["background"]
        )


def mixed_names():
    rows = [
        {"id": "land", "kind": "land", "geometry": box(0, 0, 100, 100)},
        {"id": "city", "name": "Leipzig", "place": "city", "geometry": Point(50, 50)},
        {
            "id": "city-sign",
            "name": "Leipzig",
            "tourism": "information",
            "geometry": Point(10, 90),
        },
        {
            "id": "city-attraction",
            "name": "Leipzig",
            "tourism": "attraction",
            "geometry": Point(90, 90),
        },
        {
            "id": "monument",
            "name": "Testdenkmal",
            "historic": "monument",
            "geometry": Point(65, 65),
        },
        {
            "id": "monument-sign",
            "name": "Testdenkmal",
            "tourism": "information",
            "geometry": Point(30, 30),
        },
        {
            "id": "monument-stop",
            "name": "Testdenkmal",
            "highway": "bus_stop",
            "geometry": Point(70, 20),
        },
    ]
    return gpd.GeoDataFrame(rows, crs=32633)


@pytest.mark.parametrize("reverse", [False, True])
def test_places_and_landmarks_beat_same_named_signs_and_stops(tmp_path, reverse):
    data = mixed_names()
    if reverse:
        data = data.iloc[::-1]
    cfg = {
        "globe": {"ppi": 40},
        "layout": {"curated_landmarks": ["Leipzig", "Testdenkmal"]},
    }
    result = render_clean_map(cfg, tmp_path / "map.png", data)
    selected = {
        item["label"]: item
        for item in result["layout"]["rendered_labels"] + result["omitted_labels"]
    }
    assert selected["Leipzig"]["source_id"] == "city"
    assert selected["Leipzig"]["source_tags"]["place"] == "city"
    assert selected["Leipzig"]["anchor_px"] == pytest.approx(
        result["layout"]["center_pixel"]
    )
    assert selected["Testdenkmal"]["source_id"] == "monument"
    assert selected["Testdenkmal"]["source_tags"]["historic"] == "monument"


@pytest.mark.parametrize("sx,sy", [(1, 1), (1.3, 0.8), (0.7, 1.3)])
def test_supersampling_preserves_physical_label_size_and_final_safety(tmp_path, sx, sy):
    cfg = validate_config(
        {
            "globe": {"ppi": 60},
            "layout": {
                "curated_landmarks": ["Leipzig", "Testdenkmal"],
                "world_layout_scale_x": sx,
                "world_layout_scale_y": sy,
            },
        }
    )
    result = render_clean_map(cfg, tmp_path / "map.png", mixed_names())
    metadata = result["layout"]
    sampling = metadata["sampling"]
    assert min(sampling["source_effective_ppi"]) >= cfg["globe"]["ppi"]
    tw, th = texture_dimensions(cfg)
    sw, sh = scaled_texture_dimensions(cfg)
    width, height = sampling["source_pixels"]
    labels = metadata["rendered_labels"]
    assert labels
    for label in labels:
        x0, y0, x1, y1 = label["bbox"]
        assert 0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height
        transformed = [
            x0 / width * sw + (tw - sw) // 2 + round(15 / 360 * tw),
            y0 / height * sh + (th - sh) // 2,
            x1 / width * sw + (tw - sw) // 2 + round(15 / 360 * tw),
            y1 / height * sh + (th - sh) // 2,
        ]
        assert label["texture_bbox_unwrapped"] == pytest.approx(transformed)
        # Font bounding-box height remains roughly 2–4 mm in unscaled source
        # layout coordinates, independent of the extra sampling resolution.
        assert 1.5 < (y1 - y0) / (height / th) / (60 / 25.4) < 4
        seam = cfg["layout"]["gore_seam_margin_mm"] * 60 / 25.4
        pole = cfg["layout"]["pole_safety_zone_mm"] * 60 / 25.4
        assert transformed[1] >= pole and transformed[3] <= th - pole
        assert math.floor((transformed[0] - seam) / (tw / 12)) == math.floor(
            (transformed[2] + seam) / (tw / 12)
        )


def test_scaled_out_label_is_reported_as_omitted(tmp_path):
    data = gpd.GeoDataFrame(
        [
            {"kind": "land", "geometry": box(0, 0, 100, 100)},
            {
                "id": "city",
                "name": "Leipzig",
                "place": "city",
                "geometry": Point(50, 50),
            },
            {"id": "edge", "name": "Rand", "place": "suburb", "geometry": Point(1, 50)},
        ],
        crs=32633,
    )
    result = render_clean_map(
        {
            "globe": {"ppi": 40},
            "layout": {
                "world_layout_scale_x": 1.8,
                "gore_seam_margin_mm": 0,
                "curated_landmarks": ["Leipzig", "Rand"],
            },
        },
        tmp_path / "map.png",
        data,
    )
    assert "Rand" not in result["rendered_labels"]
    omission = next(
        item for item in result["omitted_labels"] if item["label"] == "Rand"
    )
    assert omission["reason"] == "world_layout_crop"
    assert omission["source_id"] == "edge"

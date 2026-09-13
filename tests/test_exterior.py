"""Check real placement invariants, city preservation, poles and the texture wrap."""

import json

import geopandas as gpd
import numpy as np
import pytest
from PIL import Image, ImageChops
from shapely.geometry import Polygon, box

from leipzig_globe.config import validate_config
from leipzig_globe.exterior import render_context_map, spherical_background
from leipzig_globe.rendering import generate_globe_texture, render_clean_map


@pytest.mark.parametrize("kind", ["terrain", "ocean", "fog"])
def test_exterior_preserves_city_holes_and_joins_at_wrap_and_poles(tmp_path, kind):
    # A concave municipality plus a detached outlier, with a hole outside the city.
    boundary = Polygon(
        [(0, 0), (100, 0), (100, 50), (60, 50), (60, 100), (0, 100)],
        holes=[[(15, 15), (25, 15), (25, 25), (15, 25)]],
    )
    frame = gpd.GeoDataFrame(
        {"kind": ["district", "district", "water"], "name": [None] * 3},
        geometry=[boundary, box(85, 85, 90, 90), box(30, 30, 45, 45)],
        crs=32633,
    )
    config = validate_config(
        {
            "globe": {"ppi": 20, "seam_offset_deg": 0},
            "layout": {"exterior": kind, "curated_landmarks": []},
        }
    )
    source = tmp_path / "map.png"
    render_clean_map(config, source, frame)
    if kind == "terrain":
        # Known water feature outside the city, but inside the same viewport.
        context = tmp_path / "context.geojson"
        gpd.GeoDataFrame(
            {"natural": ["water", "water"]},
            geometry=[box(70, 60, 80, 70), box(15, 15, 25, 25)],
            crs=32633,
        ).to_file(context)
        render_context_map(context, source, config)
    output = generate_globe_texture(config, tmp_path / "variant.png", source_map=source)
    config["layout"]["exterior"] = "blank"
    baseline = generate_globe_texture(config, tmp_path / "blank.png", source_map=source)
    with (
        Image.open(output) as image,
        Image.open(baseline) as original,
        Image.open(source.with_suffix(".boundary.png")) as mask,
    ):
        mask = mask.resize(image.size, Image.Resampling.LANCZOS)
        pixels, before, inside = (
            np.array(image),
            np.array(original),
            np.array(mask) == 255,
        )
        np.testing.assert_array_equal(pixels[inside], before[inside])
        np.testing.assert_array_equal(pixels[:, 0], pixels[:, -1])
        assert np.unique(pixels[0], axis=0).shape[0] == 1
        assert np.unique(pixels[-1], axis=0).shape[0] == 1
        assert np.any(pixels[~inside] != before[~inside])
        metadata = json.loads(source.with_suffix(".json").read_text())
        cx, cy = metadata["center_metric"]
        sx, sy = metadata["span_metric"]

        def at(x, y):
            return image.getpixel(
                (
                    round((x - cx) / sx * image.width + image.width / 2),
                    round(image.height / 2 - (y - cy) / sy * image.height),
                )
            )

        assert at(20, 20) != tuple(
            config["style"]["land"]
        ), "Municipal holes must be exterior"
        assert at(87, 87) == tuple(
            config["style"]["land"]
        ), "Detached city areas must survive"
        if kind == "terrain":
            assert at(75, 65) == tuple(
                config["style"]["water"]
            ), "Context must retain its actual coordinates"
    config["layout"]["exterior"] = kind
    config["globe"]["seam_offset_deg"] = config["layout"]["seam_offset_deg"] = 90
    rotated = generate_globe_texture(
        config, tmp_path / "rotated.png", source_map=source
    )
    with Image.open(output) as original, Image.open(rotated) as image:
        assert (
            ImageChops.difference(
                image, ImageChops.offset(original, round(image.width / 4), 0)
            ).getbbox()
            is None
        )


def test_fog_is_deterministic_and_nonuniform():
    a = np.array(spherical_background((512, 256), "fog"))
    np.testing.assert_array_equal(a, np.array(spherical_background((512, 256), "fog")))
    assert a[40:-40, :, 0].std() > 5


@pytest.mark.parametrize("water", [[132, 178, 198], [110, 160, 180]])
def test_ocean_shore_opens_at_boundary_water_and_preserves_inland_lake(tmp_path, water):
    frame = gpd.GeoDataFrame(
        {"kind": ["district", "water", "water"]},
        geometry=[
            Polygon(
                [
                    (0, 0),
                    (100, 0),
                    (100, 20),
                    (70, 20),
                    (70, 80),
                    (100, 80),
                    (100, 100),
                    (0, 100),
                ]
            ),
            box(50, 40, 70, 60),
            box(30, 30, 45, 45),
        ],
        crs=32633,
    )
    config = validate_config(
        {
            "globe": {"ppi": 60, "seam_offset_deg": 0},
            "style": {"water": water},
            "layout": {"exterior": "ocean", "curated_landmarks": []},
        }
    )
    source = tmp_path / "map.png"
    render_clean_map(config, source, frame)
    output = generate_globe_texture(config, tmp_path / "ocean.png", source_map=source)
    metadata = json.loads(source.with_suffix(".json").read_text())
    cx, cy = metadata["center_metric"]
    sx, sy = metadata["span_metric"]
    with Image.open(output) as image:

        def at(x, y):
            return np.array(
                image.getpixel(
                    (
                        round((x - cx) / sx * image.width + image.width / 2),
                        round(image.height / 2 - (y - cy) / sy * image.height),
                    )
                )
            )

        np.testing.assert_array_equal(at(37, 37), water)
        np.testing.assert_array_equal(at(60, 50), water)
        # Immediately beyond the boundary, lake water must meet blue shallows,
        # while land receives the pale shore. No beach across the lake mouth.
        mouth = at(70.1, 50)
        shore = at(70.1, 30)
        assert np.linalg.norm(mouth - water) < 25
        assert shore.mean() > mouth.mean() + 20


def test_reject_unknown_exterior():
    with pytest.raises(ValueError, match="layout.exterior"):
        validate_config({"layout": {"exterior": "dragons-typo"}})


def test_exterior_rejects_missing_context_and_cropped_municipality(tmp_path):
    frame = gpd.GeoDataFrame(
        {"kind": ["district"]}, geometry=[box(0, 0, 100, 100)], crs=32633
    )
    config = validate_config({"globe": {"ppi": 20}, "layout": {"exterior": "terrain"}})
    source = tmp_path / "map.png"
    render_clean_map(config, source, frame)
    with pytest.raises(FileNotFoundError):
        generate_globe_texture(config, tmp_path / "missing.png", source_map=source)
    config["layout"].update(exterior="ocean", world_layout_scale_y=1.1)
    render_clean_map(config, source, frame)
    with pytest.raises(ValueError, match="entire municipality"):
        generate_globe_texture(config, tmp_path / "cropped.png", source_map=source)

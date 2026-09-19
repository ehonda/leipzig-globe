from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
from PIL import Image, ImageChops
from pypdf import PdfReader, PdfWriter
from pypdf.generic import FloatObject
from reportlab.pdfbase.pdfmetrics import getAscentDescent, stringWidth
from shapely.geometry import Point, Polygon, box

from leipzig_globe.config import load_config, validate_config
from leipzig_globe.fetcher import (
    SourceManifest,
    compute_sha256,
    persist_source_manifest,
)
from leipzig_globe.pipeline import build_artifacts, validate_output_directory
from leipzig_globe.preview import generate_preview_set
from leipzig_globe.printing import (
    build_gore_set,
    build_pdf,
    gore_outline_points,
    page_tiles,
)
from leipzig_globe.rendering import (
    generate_globe_texture,
    render_clean_map,
    texture_dimensions,
)
from leipzig_globe.web_preview import export_web_preview


@pytest.mark.parametrize("diameter,ppi", [(300, 200), (250, 150), (180, 80), (301, 27)])
def test_texture_ppi_uses_circumference_and_even_width(diameter, ppi):
    width, height = texture_dimensions({"globe": {"diameter_mm": diameter, "ppi": ppi}})
    assert width == height * 2
    assert (
        math.pi * diameter * ppi / 25.4 <= width < math.pi * diameter * ppi / 25.4 + 2
    )


def test_sinusoidal_gore_tapers_symmetrically_and_covers_circumference():
    circumference = math.pi * 300
    points = np.asarray(gore_outline_points(0, 12, circumference, circumference / 2))
    left, right = points[:361], points[361:][::-1]
    widths = right[:, 0] - left[:, 0]
    np.testing.assert_allclose(
        widths, circumference / 12 * np.sin(np.linspace(0, math.pi, 361)), atol=1e-10
    )
    assert widths[180] * 12 == pytest.approx(circumference)
    assert widths[0] == pytest.approx(0)
    assert widths[-1] == pytest.approx(0)


def test_texture_rotation_is_pixel_exact_and_source_is_untouched(tmp_path):
    source = tmp_path / "source.png"
    width, height = texture_dimensions({"globe": {"ppi": 20}})
    array = np.zeros((height, width, 3), dtype=np.uint8)
    array[:, :40] = [200, 10, 20]
    array[10:30, 70:100] = [5, 220, 60]
    Image.fromarray(array).save(source)
    before = compute_sha256(source)
    config = {"globe": {"ppi": 20, "seam_offset_deg": 0}}
    first = generate_globe_texture(config, tmp_path / "first.png", source_map=source)
    config["globe"]["seam_offset_deg"] = 90
    second = generate_globe_texture(config, tmp_path / "second.png", source_map=source)
    with Image.open(first) as a, Image.open(second) as b:
        expected = ImageChops.offset(a, round(a.width / 4), 0)
        assert ImageChops.difference(expected, b).getbbox() is None
    assert compute_sha256(source) == before
    with pytest.raises(FileNotFoundError):
        generate_globe_texture(
            config, tmp_path / "missing.png", source_map=tmp_path / "absent.png"
        )


def test_layers_ignore_input_order_and_preserve_water_island(tmp_path):
    water = Polygon(
        [(10, 10), (90, 10), (90, 90), (10, 90)],
        holes=[[(40, 40), (60, 40), (60, 60), (40, 60)]],
    )
    data = gpd.GeoDataFrame(
        {"kind": ["water", "land"], "name": [None, None]},
        geometry=[water, box(0, 0, 100, 100)],
        crs=32633,
    )
    config = {"globe": {"ppi": 20}, "style": {"land": [245, 240, 230]}}
    path = tmp_path / "map.png"
    render_clean_map(config, path, data)
    with Image.open(path) as image:
        assert image.getpixel((image.width // 2, image.height // 2)) == (245, 240, 230)
        assert image.getpixel((image.width // 4, image.height // 4)) == (132, 178, 198)


def test_labels_come_from_source_points_and_zentrum_is_at_equator(tmp_path):
    data = gpd.GeoDataFrame(
        {
            "kind": ["land", None, None],
            "name": [None, "Leipzig", "Positionstest"],
            "place": [None, "city", "suburb"],
        },
        geometry=[box(0, 0, 100, 100), Point(40, 30), Point(80, 70)],
        crs=32633,
    )
    result = render_clean_map(
        {
            "globe": {"ppi": 80},
            "layout": {
                "curated_landmarks": ["Positionstest"],
                "gore_seam_margin_mm": 0,
            },
        },
        tmp_path / "map.png",
        data,
    )
    metadata = result["layout"]
    assert metadata["center_metric"] == [40, 30]
    assert metadata["center_pixel"][1] == result["height_px"] / 2
    entry = next(
        label
        for label in metadata["rendered_labels"]
        if label["label"] == "Positionstest"
    )
    assert entry["anchor_px"][0] > metadata["center_pixel"][0]
    assert entry["anchor_px"][1] < metadata["center_pixel"][1]
    assert "Mitte" not in result["rendered_labels"]


@pytest.fixture
def printed_fixture(tmp_path):
    # Preserve the original 300 mm / 10 mm overlap regression explicitly.
    config = validate_config(
        {
            "globe": {"diameter_mm": 300, "ppi": 20},
            "layout": {"tile_overlap_mm": 10},
        }
    )
    width, height = texture_dimensions(config)
    yy, xx = np.indices((height, width))
    texture = np.stack(
        (xx * 255 // width, yy * 255 // height, np.full_like(xx, 100)), axis=2
    ).astype(np.uint8)
    path = tmp_path / "texture.png"
    Image.fromarray(texture).save(path)
    gores = build_gore_set(path, tmp_path / "gores", config)
    pdf = build_pdf(gores, tmp_path / "print.pdf", config)
    return config, texture, gores, pdf


def test_gore_overlap_samples_neighbor_and_svg_has_physical_size(printed_fixture):
    _, _, gores, _ = printed_fixture
    import xml.etree.ElementTree as ET

    for index in (0, 11):
        path = gores[index]
        root = ET.parse(path).getroot()
        assert root.attrib["width"].endswith("mm")
        info = json.loads(path.with_suffix(".json").read_text())
        assert info["pole_to_pole_mm"] == pytest.approx(math.pi * 300 / 2)
        assert info["equator_width_mm"] == pytest.approx(math.pi * 300 / 12)
        with Image.open(path.with_suffix(".png")) as image:
            row = np.array(image)[image.height // 2]
            inside = np.flatnonzero(row[:, 3])
            # Rightmost overlap must use longitudes beyond the nominal edge;
            # for the last gore this wraps around to the first texture columns.
            x = (
                (inside[-1] + 0.5) * info["width_mm"] / image.width
                - info["inset_mm"]
                - info["equator_width_mm"] / 2
            )
            longitude = ((index + 0.5) / 12 + x / (math.pi * 300)) % 1
            assert row[inside[-1], 0] == pytest.approx(longitude * 255, abs=2)


def test_pdf_is_exact_a4_with_real_content_and_100mm_calibration(printed_fixture):
    _, _, gores, pdf = printed_fixture
    reader = PdfReader(pdf)
    assert len(reader.pages) == 13
    assert reader.trailer["/Root"]["/ViewerPreferences"]["/PrintScaling"] == "/None"
    for index, page in enumerate(reader.pages):
        assert float(page.mediabox.width) == pytest.approx(210 * 72 / 25.4, abs=0.001)
        assert float(page.mediabox.height) == pytest.approx(297 * 72 / 25.4, abs=0.001)
        text = page.extract_text()
        assert "OpenStreetMap" in text
        if index == 0:
            assert not page.images
            assert "100 mm horizontal" in text and "100 mm vertical" in text
            # Inspect physical drawing operators, not just the printed label.
            rectangles = [
                [float(v) * 25.4 / 72 for v in args]
                for args, op in page.get_contents().operations
                if op == b"re"
            ]
            assert len(rectangles) == 1
            assert rectangles[0] == pytest.approx([55, 98.5, 100, 100], abs=0.001)
        else:
            assert len(page.images) == 2
            assert "100 mm" not in text and "PRINT 100%" in text
    manifest = json.loads(pdf.with_suffix(".tiles.json").read_text())
    assert manifest["calibration_page"] == 1
    assert manifest["calibration_square_mm"] == [100, 100]
    tiles = manifest["tiles"]
    assert [tile["page"] for tile in tiles] == list(range(2, 14))
    for index in range(len(gores)):
        portions = sorted(
            (tile["y_mm"], tile["y_mm"] + tile["height_mm"])
            for tile in tiles
            if index in tile["gores"]
        )
        assert portions[0][0] == 0
        assert portions[-1][1] >= math.pi * 300 / 2 + 6
        assert portions[0][1] - portions[1][0] == 10


@pytest.mark.parametrize(
    "diameter,count,margin,mode",
    [
        (150, 12, 8, "automatic"),
        (215, 12, 10, "equator"),
        (450, 12, 10, "automatic"),
        (300, 4, 40, "automatic"),
    ],
)
def test_every_gore_tile_has_unclipped_identifiers_and_safe_guides(
    tmp_path, diameter, count, margin, mode
):
    config = validate_config(
        {
            "globe": {"diameter_mm": diameter, "gore_count": count, "ppi": 20},
            "layout": {"print_margin_mm": margin, "vertical_tile_mode": mode},
        }
    )
    texture = tmp_path / "texture.png"
    Image.new("RGB", (200, 100), "white").save(texture)
    gores = build_gore_set(texture, tmp_path / "gores", config)
    pdf = build_pdf(gores, tmp_path / "print.pdf", config)
    reader = PdfReader(pdf)
    tiles = json.loads(pdf.with_suffix(".tiles.json").read_text())["tiles"]
    for tile in tiles:
        page = reader.pages[tile["page"] - 1]
        labels = []
        boxes = []

        def inspect_text(text, cm, tm, font, size, *, boxes=boxes, labels=labels):
            text = text.strip()
            if not text:
                return
            assert cm == [1, 0, 0, 1, 0, 0]
            ascent, descent = getAscentDescent("Helvetica", size)
            x, y = tm[4], tm[5]
            bounds = [
                x,
                y + descent,
                x + stringWidth(text, "Helvetica", size),
                y + ascent,
            ]
            left, bottom, right, top = [v * 25.4 / 72 for v in bounds]
            assert 4.2 < left < right < 210 - 4.2
            assert 4.2 < bottom < top < 297 - 4.2
            boxes.append((left, bottom, right, top))
            if text.startswith("Gore "):
                labels.append(text)
                assert bottom > 297 - margin  # above the artwork, including lower tiles

        page.extract_text(visitor_text=inspect_text)
        assert labels == [f"Gore {index+1:02d}" for index in tile["gores"]]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1 :]:
                assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]
        # Text extraction alone ignores clipping: check graphics-state scope too.
        clipped, stack = False, []
        for args, op in page.get_contents().operations:
            if op == b"q":
                stack.append(clipped)
            elif op == b"Q":
                clipped = stack.pop()
            elif op in (b"W", b"W*"):
                clipped = True
            elif op == b"Tj":
                assert not clipped
            elif op in (b"m", b"l") and not clipped:
                x, y = [float(v) * 25.4 / 72 for v in args]
                assert 4.3 <= x <= 210 - 4.3
                assert 4.3 <= y <= 297 - 4.3


@pytest.mark.parametrize("diameter,count", [(150, 12), (250, 12), (450, 12), (300, 4)])
def test_page_coverage_recalculates_for_other_globes(diameter, count):
    height = math.pi * diameter / 2 + 6
    width = math.pi * diameter / count + 8
    tiles = page_tiles(count, width, height, 10, 10)
    for index in range(count):
        pieces = [tile for tile in tiles if index in tile["gores"]]
        assert min(tile["y_mm"] for tile in pieces) == 0
        assert max(tile["y_mm"] + tile["height_mm"] for tile in pieces) >= height
        assert max(tile["x_mm"] + tile["width_mm"] for tile in pieces) >= width


def test_equator_tile_mode_splits_symmetrically_with_configured_overlap():
    gore_height = 296.0004
    tiles = page_tiles(12, 56.3334, gore_height, 10, 10, "equator")
    pieces = [tile for tile in tiles if 0 in tile["gores"]]

    assert len(pieces) == 2
    assert pieces[0]["y_mm"] == 0
    assert pieces[0]["y_mm"] + pieces[0]["height_mm"] == pytest.approx(
        gore_height / 2 + 5
    )
    assert pieces[1]["y_mm"] == pytest.approx(gore_height / 2 - 5)
    assert pieces[1]["y_mm"] + pieces[1]["height_mm"] == pytest.approx(gore_height)
    assert pieces[0]["y_mm"] + pieces[0]["height_mm"] - pieces[1][
        "y_mm"
    ] == pytest.approx(10)


def test_equator_tile_mode_keeps_fitting_gore_on_one_page():
    tiles = page_tiles(1, 60, 200, 10, 10, "equator")

    assert [(tile["y_mm"], tile["height_mm"]) for tile in tiles] == [(0, 200)]


@pytest.mark.parametrize(
    "preset,page_count",
    [("test-print-184-62mm-high-density", 9), ("production-215mm-ocean", 13)],
)
def test_print_halves_meet_at_equator_in_pdf(preset, page_count, tmp_path):
    config = load_config(f"config/{preset}.yaml")
    # Low raster density keeps this physical PDF geometry check inexpensive.
    config["globe"]["ppi"] = 10
    texture = tmp_path / "texture.png"
    Image.new("RGB", texture_dimensions(config), "skyblue").save(texture)
    gores = build_gore_set(texture, tmp_path / "gores", config)
    pdf = build_pdf(gores, tmp_path / "print.pdf", config)
    manifest = json.loads(pdf.with_suffix(".tiles.json").read_text())
    reader = PdfReader(pdf)
    assert len(reader.pages) == page_count
    height = manifest["gore_height_mm"]
    for gore in range(12):
        halves = [t for t in manifest["tiles"] if gore in t["gores"]]
        north, south = halves
        assert north["y_mm"] == 0
        assert north["height_mm"] == pytest.approx(height / 2)
        assert south["y_mm"] == pytest.approx(height / 2)
        assert south["height_mm"] == pytest.approx(height / 2)
        # Inspect actual artwork clipping and placement, beyond the manifest.
        for tile in halves:
            operations = reader.pages[tile["page"] - 1].get_contents().operations
            clip = next(args for args, op in operations if op == b"re")
            assert float(clip[3]) * 25.4 / 72 == pytest.approx(height / 2, abs=1e-4)
            images = [
                args for args, op in operations if op == b"cm" and float(args[3]) > 100
            ]
            assert len(images) == len(tile["gores"])
            for matrix in images:
                top = (float(matrix[5]) + float(matrix[3])) * 25.4 / 72
                assert top == pytest.approx(287 + tile["y_mm"], abs=1e-4)


def test_equator_tile_mode_rejects_gore_halves_too_tall_for_a4():
    with pytest.raises(ValueError, match="Equator split does not fit"):
        page_tiles(1, 60, 550, 10, 10, "equator")


def test_pdf_uses_configured_equator_tile_mode(printed_fixture, tmp_path):
    config, _, gores, _ = printed_fixture
    config["layout"]["vertical_tile_mode"] = "equator"

    pdf = build_pdf(gores, tmp_path / "equator-print.pdf", config)
    manifest = json.loads(pdf.with_suffix(".tiles.json").read_text())
    pieces = [tile for tile in manifest["tiles"] if 0 in tile["gores"]]

    assert manifest["vertical_tile_mode"] == "equator"
    assert len(pieces) == 2
    assert pieces[0]["y_mm"] == 0
    assert pieces[1]["y_mm"] == pytest.approx(
        manifest["gore_height_mm"] / 2 - config["layout"]["tile_overlap_mm"] / 2
    )


def test_six_previews_are_different_spherical_views(printed_fixture, tmp_path):
    _, _, gores, _ = printed_fixture
    texture = gores[0].parent.parent / "texture.png"
    paths = generate_preview_set(texture, tmp_path / "preview", size=128)
    assert len({compute_sha256(path) for path in paths}) == 6
    with Image.open(paths[0]) as image:
        assert image.getpixel((0, 0)) == (247, 247, 247)
        assert image.getpixel((64, 64)) != (247, 247, 247)


def test_web_preview_export_uses_printed_gore_geometry(printed_fixture, tmp_path):
    config, _texture, gores, _ = printed_fixture
    manifest_path = export_web_preview(
        gores[0].parent.parent / "texture.png",
        gores[0].parent,
        tmp_path / "site-assets",
        config=config,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert (
        manifest_path == tmp_path / "site-assets" / "default" / "preview-manifest.json"
    )
    assert manifest["preset_id"] == "default"
    assert manifest["gore_count"] == 12
    assert manifest["pole_safety_zone_mm"] == config["layout"]["pole_safety_zone_mm"]
    assert (manifest_path.parent / manifest["texture"]).is_file()
    assert len(manifest["gores"]) == len(gores)
    first = manifest["gores"][0]
    assert first["id"] == "Gore 01"
    assert (manifest_path.parent / first["texture"]).is_file()
    stride = len(first["mesh"]["positions"]) // (121 * 3)
    assert stride > 2
    midpoint = stride * (120 // 2) * 3
    left_equator = first["mesh"]["positions"][midpoint : midpoint + 3]
    assert left_equator == pytest.approx([0, 0, 1], abs=1e-8)
    seam_midpoint = (120 // 2) * 3
    nominal_seam = first["nominal_seam"][seam_midpoint : seam_midpoint + 3]
    assert nominal_seam == pytest.approx([0.5, 0, math.sqrt(3) / 2], abs=1e-8)

    alternate_config = validate_config(
        {
            "globe": {"diameter_mm": 215, "ppi": 20},
            "layout": {"label_density": "high"},
        }
    )
    alternate_gores = build_gore_set(
        gores[0].parent.parent / "texture.png",
        tmp_path / "alternate-gores",
        alternate_config,
    )
    alternate_manifest = export_web_preview(
        gores[0].parent.parent / "texture.png",
        alternate_gores[0].parent,
        tmp_path / "site-assets",
        config=alternate_config,
        preset_id="globe-215mm-high-density",
    )
    presets = json.loads(
        (tmp_path / "site-assets" / "presets.json").read_text(encoding="utf-8")
    )
    assert alternate_manifest.is_file()
    assert presets["presets"] == [
        {
            "id": "default",
            "label": "300 mm - medium labels",
            "exterior": "blank",
            "description": "The municipal map on its original paper background.",
            "ppi": config["globe"]["ppi"],
            "manifest": "default/preview-manifest.json",
            "diameter_mm": 300.0,
            "gore_count": 12,
            "label_density": "medium",
        },
        {
            "id": "globe-215mm-high-density",
            "label": "215 mm - high labels",
            "exterior": "blank",
            "description": "The municipal map on its original paper background.",
            "ppi": 20,
            "manifest": "globe-215mm-high-density/preview-manifest.json",
            "diameter_mm": 215.0,
            "gore_count": 12,
            "label_density": "high",
        },
    ]


@pytest.mark.parametrize("exterior", ["blank", "terrain", "ocean", "fog"])
def test_real_offline_fixture_build_and_validation(tmp_path, monkeypatch, exterior):
    if shutil.which("osmium") is None:
        pytest.skip("osmium-tool required; CI installs it")
    cache = tmp_path / "cache"
    cache.mkdir()
    source = Path(__file__).parent / "fixtures/leipzig.osm"
    pbf = cache / "sachsen-latest.osm.pbf"
    subprocess.run(["osmium", "cat", str(source), "-o", str(pbf)], check=True)
    boundary = cache / "leipzig-municipal-boundary.geojson"
    gpd.GeoDataFrame(
        {"Name": ["West", "Ost"]},
        geometry=[
            box(12.355, 51.325, 12.375, 51.355),
            box(12.375, 51.325, 12.395, 51.355),
        ],
        crs=4326,
    ).to_crs(25833).to_file(boundary)
    for path in (pbf, boundary):
        persist_source_manifest(
            cache,
            SourceManifest(
                path.stem,
                "https://example.com/offline-fixture",
                path.name,
                sha256=compute_sha256(path),
                metadata={"license": "test fixture"},
            ),
        )

    def no_network(*args, **kwargs):
        pytest.fail("Offline build attempted network access")

    monkeypatch.setattr("requests.sessions.Session.request", no_network)
    config = {
        "globe": {"ppi": 20},
        "layout": {
            "source_cache_dir": str(cache),
            "curated_landmarks": ["Testdenkmal ÄÖÜ"],
            "exterior": exterior,
        },
    }
    output = tmp_path / "output"
    artifacts = build_artifacts(config, output)
    assert validate_output_directory(output)["status"] == "valid"
    nested = output / "another-preset"
    nested.mkdir()
    shutil.copyfile(artifacts["report"], nested / "build-report.json")
    assert validate_output_directory(output)["status"] == "valid"
    municipal = gpd.read_file(artifacts["municipal_map"])
    assert len(municipal[municipal["kind"] == "district"]) == 2
    assert "Testdenkmal ÄÖÜ" in set(municipal["name"])
    report = json.loads(artifacts["report"].read_text(encoding="utf-8"))
    assert report["physical"]["tile_count"] == 12
    assert report["physical"]["pdf_page_count"] == 13
    if exterior == "blank":
        # Matching text and checksums must not mask an incorrectly sized square.
        original_pdf = artifacts["pdf"].read_bytes()
        writer = PdfWriter(clone_from=artifacts["pdf"])
        content = writer.pages[0].get_contents()
        for args, op in content.operations:
            if op == b"re":
                args[2] = FloatObject(96 * 72 / 25.4)
        writer.pages[0].replace_contents(content)
        writer.write(artifacts["pdf"])
        report["artifact_sha256"][report["artifacts"]["pdf"]] = compute_sha256(
            artifacts["pdf"]
        )
        artifacts["report"].write_text(json.dumps(report), encoding="utf-8")
        with pytest.raises(ValueError, match="calibration square"):
            validate_output_directory(output)
        artifacts["pdf"].write_bytes(original_pdf)
        report["artifact_sha256"][report["artifacts"]["pdf"]] = compute_sha256(
            artifacts["pdf"]
        )
        artifacts["report"].write_text(json.dumps(report), encoding="utf-8")
    if exterior != "blank":
        assert artifacts["municipal_mask"].name in report["artifact_sha256"]
    if exterior == "terrain":
        assert artifacts["context_map"].name in report["artifact_sha256"]
        assert report["performance"]["context"]["feature_count"] > 0
    assert min(report["physical"]["map_sampling"]["source_effective_ppi"]) >= 20
    unchanged_report = artifacts["report"].read_text(encoding="utf-8")
    report["physical"]["map_sampling"]["source_pixels"][0] -= 1
    artifacts["report"].write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="sampling metadata"):
        validate_output_directory(output)
    artifacts["report"].write_text(unchanged_report, encoding="utf-8")
    assert report["source_provenance"]["manifests"]["osm_pbf"][
        "sha256"
    ] == compute_sha256(pbf)
    artifacts["preview"][0].unlink()
    with pytest.raises(FileNotFoundError, match="front.png"):
        validate_output_directory(output)
    pbf.write_bytes(b"corrupt source")
    with pytest.raises(ValueError, match="checksum mismatch"):
        build_artifacts(config, tmp_path / "bad")

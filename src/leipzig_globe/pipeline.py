from __future__ import annotations

import base64
import json
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib
from shapely.ops import transform

matplotlib.use("Agg")
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from leipzig_globe.config import DEFAULT_CONFIG, validate_config
from leipzig_globe.municipal_map import derive_municipal_map_from_sources

A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297
LABEL_DENSITY_SETTINGS = {
    "low": {"font_scale": 0.8, "max_labels": 6},
    "medium": {"font_scale": 1.0, "max_labels": 9},
    "high": {"font_scale": 1.2, "max_labels": 12},
}


def ensure_osmium_available() -> None:
    if shutil.which("osmium") is None:
        raise RuntimeError(
            "Osmium is required for map extraction. Install the `osmium-tool` binary and ensure it is on your PATH."
        )


def texture_dimensions(config: dict[str, Any]) -> tuple[int, int]:
    cfg = validate_config(config)
    globe = cfg["globe"]
    px_per_mm = globe["ppi"] / 25.4
    width_px = max(2, round(globe["diameter_mm"] * px_per_mm))
    height_px = max(1, round(width_px / 2))
    return width_px, height_px


def gore_outline_points(
    gore_index: int, gore_count: int, width: int, height: int
) -> list[tuple[float, float]]:
    if gore_count <= 0:
        raise ValueError("gore_count must be positive")
    if not 0 <= gore_index < gore_count:
        raise ValueError("gore_index is outside the valid gore range")

    left_fraction = gore_index / gore_count
    right_fraction = (gore_index + 1) / gore_count
    left_x0 = left_fraction * width
    left_x1 = left_fraction * width + width * 0.06
    right_x0 = right_fraction * width
    right_x1 = right_fraction * width - width * 0.06

    return [
        (left_x0, 0),
        (right_x0, 0),
        (right_x1, height),
        (left_x1, height),
    ]


def _gore_seam_positions(cfg: dict[str, Any], width: int) -> list[float]:
    gore_count = cfg["globe"]["gore_count"]
    seam_offset_deg = float(
        cfg["globe"].get("seam_offset_deg", cfg["layout"].get("seam_offset_deg", 0))
    )
    step = width / gore_count
    return [
        (seam_offset_deg / 360.0 * width + (index * step)) % width
        for index in range(gore_count)
    ]


def _municipal_feature_kind(row: Any) -> str:
    value = row.get("kind") if hasattr(row, "get") else None
    if value is None:
        value = row.get("type") if hasattr(row, "get") else None
    if value is None:
        value = row.get("feature_type") if hasattr(row, "get") else None
    if value is None:
        return "land"
    text = str(value).lower()
    if any(token in text for token in ("water", "river", "lake", "canal")):
        return "water"
    if any(token in text for token in ("park", "green", "wood")):
        return "park"
    if any(token in text for token in ("rail", "tram")):
        return "rail"
    if any(
        token in text
        for token in ("motorway", "trunk", "primary", "major", "road", "highway")
    ):
        return "major_road"
    if any(
        token in text for token in ("secondary", "street", "service", "residential")
    ):
        return "secondary_road"
    if any(token in text for token in ("boundary", "district", "administrative")):
        return "land"
    return "land"


def _draw_geometry(
    draw: ImageDraw.ImageDraw,
    geometry: Any,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int] | None = None,
    stroke_width: int = 1,
) -> None:
    if geometry is None or geometry.is_empty:
        return
    if geometry.geom_type == "Polygon":
        coords = [(round(x), round(y)) for x, y in geometry.exterior.coords]
        draw.polygon(coords, fill=fill, outline=outline or fill)
        return
    if geometry.geom_type == "MultiPolygon":
        for part in geometry.geoms:
            _draw_geometry(draw, part, fill, outline, stroke_width)
        return
    if geometry.geom_type == "LineString":
        coords = [(round(x), round(y)) for x, y in geometry.coords]
        draw.line(coords, fill=outline or fill, width=max(1, stroke_width))
        return
    if geometry.geom_type == "MultiLineString":
        for part in geometry.geoms:
            _draw_geometry(draw, part, fill, outline, stroke_width)
        return


def _project_geometry(
    geometry: Any, width: int, height: int, bounds: tuple[float, float, float, float]
) -> Any:
    min_x, min_y, max_x, max_y = bounds
    pad_x = max((max_x - min_x) * 0.05, 1.0)
    pad_y = max((max_y - min_y) * 0.05, 1.0)
    min_x -= pad_x
    max_x += pad_x
    min_y -= pad_y
    max_y += pad_y
    x_span = max(max_x - min_x, 1e-9)
    y_span = max(max_y - min_y, 1e-9)
    return transform(
        lambda x, y, z=None: (
            (x - min_x) * width / x_span,
            height - ((y - min_y) * height / y_span),
        ),
        geometry,
    )


def _render_municipal_map_layers(
    image: Image.Image,
    municipal_map: gpd.GeoDataFrame | str | Path,
    cfg: dict[str, Any],
    width: int,
    height: int,
) -> None:
    draw = ImageDraw.Draw(image)
    if isinstance(municipal_map, (str, Path)):
        frame = gpd.read_file(municipal_map)
    else:
        frame = municipal_map.copy()

    if frame.empty:
        return
    if frame.crs is None:
        raise ValueError("Municipal map data is missing a CRS.")
    if frame.crs.is_geographic or frame.crs.to_string() != "EPSG:32633":
        frame = frame.to_crs("EPSG:32633")

    bounds = frame.total_bounds
    if bounds.size == 0:
        return

    palette = {key: tuple(value) for key, value in cfg["style"].items()}
    for _, row in frame.iterrows():
        geometry = row.geometry
        if geometry is None or geometry.is_empty:
            continue
        kind = _municipal_feature_kind(row)
        if kind == "water":
            fill = palette["water"]
            outline = palette["water"]
            stroke = 1
        elif kind == "park":
            fill = palette["park"]
            outline = palette["park"]
            stroke = 1
        elif kind == "rail":
            fill = palette["rail"]
            outline = palette["rail"]
            stroke = max(1, int(width / 240))
        elif kind == "major_road":
            fill = palette["major_road"]
            outline = palette["major_road"]
            stroke = max(2, int(width / 220))
        elif kind == "secondary_road":
            fill = palette["secondary_road"]
            outline = palette["secondary_road"]
            stroke = max(1, int(width / 300))
        else:
            fill = palette["land"]
            outline = palette["land"]
            stroke = 1

        projected = _project_geometry(geometry, width, height, tuple(bounds))
        _draw_geometry(draw, projected, fill, outline, stroke)


def render_clean_map(
    config: dict[str, Any],
    output_path: str | Path,
    municipal_map: gpd.GeoDataFrame | str | Path | None = None,
) -> dict[str, Any]:
    cfg = validate_config(config)
    width, height = texture_dimensions(cfg)
    path = Path(output_path)
    pole_margin = max(
        24,
        int((cfg["layout"]["pole_safety_zone_mm"] / 25.4) * cfg["globe"]["ppi"]),
    )
    seam_margin = max(
        12,
        int((cfg["layout"]["gore_seam_margin_mm"] / 25.4) * cfg["globe"]["ppi"]),
    )
    seam_positions = _gore_seam_positions(cfg, width)
    density = LABEL_DENSITY_SETTINGS.get(
        str(cfg["layout"].get("label_density", "medium")).lower(),
        LABEL_DENSITY_SETTINGS["medium"],
    )
    palette = {key: tuple(value) for key, value in cfg["style"].items()}

    image = Image.new("RGB", (width, height), color=palette["background"])
    draw = ImageDraw.Draw(image)

    if municipal_map is not None:
        _render_municipal_map_layers(image, municipal_map, cfg, width, height)
    else:
        land_polygon = [
            (width * 0.12, height * 0.22),
            (width * 0.62, height * 0.12),
            (width * 0.84, height * 0.28),
            (width * 0.9, height * 0.66),
            (width * 0.66, height * 0.9),
            (width * 0.26, height * 0.84),
            (width * 0.12, height * 0.56),
        ]
        draw.polygon(land_polygon, fill=palette["land"])

        water = [
            (0.0, 0.18),
            (0.2, 0.14),
            (0.34, 0.22),
            (0.2, 0.52),
            (0.3, 0.78),
            (0.08, 0.88),
            (0.0, 0.72),
        ]
        draw.polygon(
            [(int(x * width), int(y * height)) for x, y in water],
            fill=palette["water"],
        )

        for road_index in range(6):
            y = int(height * (0.18 + road_index * 0.11))
            draw.line(
                [(0, y), (width, y + int(height * 0.03))],
                fill=palette["major_road"],
                width=max(2, int(width / 200)),
            )

        draw.line(
            [(0, int(height * 0.53)), (width, int(height * 0.63))],
            fill=palette["secondary_road"],
            width=max(3, int(width / 120)),
        )

    labels = [
        {"label": "Leipzig", "x": 0.30, "y": 0.32},
        {"label": "Mitte", "x": 0.44, "y": 0.46},
        {"label": "Connewitz", "x": 0.58, "y": 0.52},
        {"label": "Schönefeld", "x": 0.57, "y": 0.68},
        {"label": "Plagwitz", "x": 0.22, "y": 0.78},
        {"label": "Leipzig Nord", "x": 0.46, "y": 0.08},
        {"label": "Leipzig Süd", "x": 0.46, "y": 0.92},
    ]
    curated_landmarks = [
        str(name).strip()
        for name in cfg["layout"].get("curated_landmarks", [])
        if str(name).strip()
    ]
    if curated_landmarks:
        for name in curated_landmarks:
            if not any(entry["label"] == name for entry in labels):
                labels.append({"label": name, "x": 0.5, "y": 0.5})

    visible_labels: list[dict[str, Any]] = []
    omitted_labels: list[dict[str, str]] = []
    font_size_base = max(12, int(width / 120))

    for entry in labels[: max(2, density["max_labels"])]:
        if (
            entry["y"] * height <= pole_margin
            or entry["y"] * height >= height - pole_margin
        ):
            omitted_labels.append(
                {"label": entry["label"], "reason": "pole_safety_zone"}
            )
            continue

        font_size = max(12, int(font_size_base * density["font_scale"]))
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        x_px = int(entry["x"] * width)
        y_px = int(entry["y"] * height)
        label_width = (
            font.getbbox(entry["label"])[2]
            if hasattr(font, "getbbox")
            else len(entry["label"]) * font_size * 0.6
        )
        label_height = (
            font.getbbox(entry["label"])[3]
            if hasattr(font, "getbbox")
            else font_size * 1.2
        )
        bbox = (
            x_px - label_width / 2,
            y_px - label_height / 2,
            x_px + label_width / 2,
            y_px + label_height / 2,
        )

        center_x = (bbox[0] + bbox[2]) / 2
        if any(
            min(
                abs(center_x - seam_x),
                abs(center_x - seam_x + width),
                abs(center_x - seam_x - width),
            )
            <= seam_margin
            for seam_x in seam_positions
        ):
            omitted_labels.append({"label": entry["label"], "reason": "gore_seam"})
            continue

        if any(
            not (
                bbox[2] < prior["bbox"][0]
                or bbox[0] > prior["bbox"][2]
                or bbox[3] < prior["bbox"][1]
                or bbox[1] > prior["bbox"][3]
            )
            for prior in visible_labels
        ):
            omitted_labels.append(
                {"label": entry["label"], "reason": "label_collision"}
            )
            continue

        draw.text(
            (x_px, y_px),
            entry["label"],
            fill=palette["label"],
            font=font,
            anchor="mm",
        )
        visible_labels.append({"label": entry["label"], "bbox": bbox})

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return {
        "image_path": path,
        "omitted_labels": omitted_labels,
        "rendered_labels": [entry["label"] for entry in visible_labels],
        "width_px": width,
        "height_px": height,
    }


def generate_globe_texture(
    config: dict[str, Any],
    output_path: str | Path,
    *,
    source_map: str | Path | None = None,
) -> Path:
    cfg = validate_config(config)
    path = Path(output_path)
    width, height = texture_dimensions(cfg)
    background = tuple(cfg["style"]["background"])
    texture = Image.new("RGB", (width, height), color=background)

    source_path = Path(source_map) if source_map is not None else None
    if source_path is None:
        candidate = cfg["paths"].get("map_file")
        if candidate:
            source_path = Path(candidate)
            if not source_path.is_absolute():
                source_path = Path.cwd() / source_path
        if not source_path or not source_path.exists():
            source_path = path.parent / cfg["paths"].get("map_file", "leipzig-map.png")
    if source_path is not None and source_path.exists():
        source_image = Image.open(source_path).convert("RGB")
        scale_x = float(cfg["layout"]["world_layout_scale_x"])
        scale_y = float(cfg["layout"]["world_layout_scale_y"])
        scaled_size = (
            max(1, round(source_image.width * scale_x)),
            max(1, round(source_image.height * scale_y)),
        )
        mapped = source_image.resize(scaled_size, Image.Resampling.BICUBIC)
        seam_offset_deg = float(
            cfg["globe"].get("seam_offset_deg", cfg["layout"].get("seam_offset_deg", 0))
        )
        seam_offset_px = round((seam_offset_deg / 360.0) * width)
        y_anchor = (height - mapped.height) // 2
        x_anchor = (width - mapped.width) // 2
        positions = [
            x_anchor + seam_offset_px,
            x_anchor + seam_offset_px - width,
            x_anchor + seam_offset_px + width,
        ]
        for position in positions:
            if position >= width or position + mapped.width <= 0:
                continue
            src_x0 = max(0, -position)
            src_x1 = min(mapped.width, width - position)
            if src_x1 <= src_x0:
                continue
            dst_x0 = max(0, position)
            dst_x1 = min(width, position + mapped.width)
            if dst_x1 <= dst_x0:
                continue
            crop = mapped.crop((src_x0, 0, src_x1, mapped.height))
            texture.paste(crop, (dst_x0, y_anchor))
    else:
        draw = ImageDraw.Draw(texture)
        polygon = [
            (width * 0.18, height * 0.22),
            (width * 0.68, height * 0.12),
            (width * 0.82, height * 0.33),
            (width * 0.88, height * 0.68),
            (width * 0.72, height * 0.88),
            (width * 0.28, height * 0.82),
            (width * 0.14, height * 0.56),
        ]
        draw.polygon(polygon, fill=(214, 228, 220))

        water = [
            (0.0, 0.16),
            (0.2, 0.15),
            (0.32, 0.25),
            (0.18, 0.5),
            (0.26, 0.76),
            (0.12, 0.88),
            (0.0, 0.74),
        ]
        water_pts = [(int(x * width), int(y * height)) for x, y in water]
        draw.polygon(water_pts, fill=(135, 176, 196))

        for road in range(7):
            y = int(height * (0.18 + road * 0.11))
            start = (0, y)
            end = (width, y + int(height * 0.03))
            draw.line([start, end], fill=(92, 100, 105), width=max(2, int(width / 200)))

        road_band = [(0, int(height * 0.52)), (width, int(height * 0.62))]
        draw.line(road_band, fill=(72, 76, 81), width=max(3, int(width / 120)))

        for idx, label in enumerate(
            ["Leipzig", "Zentrum", "Mitte", "Connewitz", "Schönefeld", "Plagwitz"]
        ):
            position = (
                int(width * (0.12 + (idx + 1) * 0.08)),
                int(height * (0.15 + (idx % 6) * 0.11)),
            )
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", max(12, int(width / 70)))
            except OSError:
                font = ImageFont.load_default()
            draw.text(position, label, fill=(70, 71, 73), font=font)

    path.parent.mkdir(parents=True, exist_ok=True)
    texture.save(path)
    return path


def generate_gore_svg(
    texture_path: str | Path,
    output_path: str | Path,
    gore_index: int,
    gore_count: int,
    config: dict[str, Any],
) -> Path:
    texture_file = Path(texture_path)
    out_file = Path(output_path)
    width, height = texture_dimensions(config)
    polygon = gore_outline_points(gore_index, gore_count, width, height)
    polygon_svg = " ".join(f"{x:.2f},{y:.2f}" for x, y in polygon)
    with texture_file.open("rb") as handle:
        encoded = base64.b64encode(handle.read()).decode("ascii")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <clipPath id="clip-{gore_index}">
      <polygon points="{polygon_svg}" />
    </clipPath>
  </defs>
  <rect width="100%" height="100%" fill="white"/>
  <image href="data:image/png;base64,{encoded}" width="{width}" height="{height}" clip-path="url(#clip-{gore_index})" preserveAspectRatio="none"/>
  <polygon points="{polygon_svg}" fill="none" stroke="black" stroke-width="2"/>
  <line x1="{(polygon[0][0]+polygon[1][0])/2}" y1="{polygon[0][1]}" x2="{(polygon[3][0]+polygon[2][0])/2}" y2="{polygon[3][1]}" stroke="gray" stroke-width="1"/>
  <text x="{((polygon[0][0]+polygon[1][0])/2)}" y="{height * 0.08}" font-size="28" text-anchor="middle">Gore {gore_index + 1:02d}</text>
</svg>"""
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(svg, encoding="utf-8")
    return out_file


def build_gore_set(
    texture_path: str | Path, output_dir: str | Path, config: dict[str, Any]
) -> list[Path]:
    cfg = validate_config(config)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    gores: list[Path] = []
    for gore_index in range(cfg["globe"]["gore_count"]):
        out = output_root / f"gore-{gore_index + 1:02d}.svg"
        generate_gore_svg(
            texture_path, out, gore_index, cfg["globe"]["gore_count"], cfg
        )
        gores.append(out)
    return gores


def build_pdf(gore_files: Iterable[str | Path], output_path: str | Path) -> Path:
    pdf_path = Path(output_path)
    files = [Path(value) for value in gore_files]
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width_mm, height_mm = A4
    x_positions = [20, 120]

    for index in range(len(files)):
        page_index = index // 2
        if index % 2 == 0:
            c.showPage()
            # reset page default at start of each tile block
        c.setPageSize(A4)
        x = x_positions[index % 2]
        y = 20 + (page_index % 2) * 150
        c.drawString(20, height_mm - 20, f"Page {page_index + 1} / Tile {index + 1}")
        c.rect(10, 10, width_mm - 20, height_mm - 20)
        c.line(10, 10, width_mm - 10, 10)
        c.line(10, 10, 10, height_mm - 10)
        c.drawString(x, y, "Calibration line 100mm")
        c.line(x, y, x + 100, y)
        c.drawString(x, y + 10, "100 mm")

        gore_name = files[index].stem
        c.drawString(20, 40, gore_name)
        c.drawInlineImage(str(files[index]), x, y + 20, width=70, height=80)

    c.save()
    return pdf_path


def generate_preview_set(
    texture_path: str | Path, output_dir: str | Path
) -> list[Path]:
    texture_file = Path(texture_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    images: list[Path] = []
    viewpoints = ["front", "back", "left", "right", "north", "south"]
    img = Image.open(texture_file).convert("RGB")
    for name in viewpoints:
        preview = img.copy()
        overlay = Image.new("RGBA", preview.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle(
            (0, 0, preview.width, preview.height), outline=(120, 120, 120, 180), width=6
        )
        draw.text((20, 20), f"{name.title()} View", fill=(30, 30, 30, 220))
        preview = Image.alpha_composite(preview.convert("RGBA"), overlay).convert("RGB")
        output = out_dir / f"{name}.png"
        preview.save(output)
        images.append(output)
    return images


def write_build_report(
    config: dict[str, Any],
    output_dir: str | Path,
    artifact_paths: dict[str, Any],
    *,
    omitted_labels: list[dict[str, str]] | None = None,
    source_provenance: dict[str, str] | None = None,
) -> Path:
    report_path = Path(output_dir) / "build-report.json"
    payload = {
        "city": config.get("city", "Leipzig"),
        "config": config,
        "source_provenance": source_provenance or {},
        "artifacts": artifact_paths,
        "omitted_labels": omitted_labels or [],
        "generated_at_utc": __import__("datetime")
        .datetime.now(__import__("datetime").timezone.utc)
        .isoformat(),
    }
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return report_path


def _cached_source_paths(config: dict[str, Any]) -> dict[str, Path]:
    cfg = validate_config(config)
    cache_dir = Path(cfg["layout"].get("source_cache_dir", ".cache"))
    if not cache_dir.is_absolute():
        cache_dir = Path.cwd() / cache_dir

    source_paths = {
        "osm_pbf": cache_dir / "sachsen-latest.osm.pbf",
        "municipal_boundary": cache_dir / "leipzig-municipal-boundary.geojson",
    }
    missing = [str(path) for path in source_paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required cached sources: " + ", ".join(missing)
        )
    return source_paths


def build_artifacts(
    config: dict[str, Any] | None = None, output_dir: str | Path = "output"
) -> dict[str, Any]:
    cfg = validate_config(config or DEFAULT_CONFIG)
    work_dir = Path(output_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    cached_sources = _cached_source_paths(cfg)
    municipal_map_path = work_dir / "municipal-map.geojson"
    municipal_map_result = derive_municipal_map_from_sources(
        cached_sources["municipal_boundary"],
        cached_sources["osm_pbf"],
        municipal_map_path,
    )
    municipal_map_path = Path(municipal_map_result.get("output_path", municipal_map_path))

    map_path = work_dir / cfg["paths"].get("map_file", "leipzig-map.png")
    map_render = render_clean_map(cfg, map_path, municipal_map=municipal_map_path)

    texture_path = work_dir / cfg["paths"]["texture_file"]
    generate_globe_texture(cfg, texture_path, source_map=map_path)

    gore_dir = work_dir / cfg["paths"]["gore_dir"]
    gore_files = build_gore_set(texture_path, gore_dir, cfg)

    pdf_path = work_dir / cfg["paths"]["pdf_file"]
    build_pdf(gore_files, pdf_path)

    preview_dir = work_dir / cfg["paths"]["preview_dir"]
    preview_files = generate_preview_set(texture_path, preview_dir)

    source_provenance = {
        "osm_pbf": str(cached_sources["osm_pbf"]),
        "municipal_boundary": str(cached_sources["municipal_boundary"]),
        "municipal_map": str(municipal_map_path),
    }

    report_path = write_build_report(
        cfg,
        work_dir,
        {
            "municipal_map": str(municipal_map_path),
            "map": str(map_path),
            "texture": str(texture_path),
            "gore_dir": str(gore_dir),
            "gore_files": [str(path) for path in gore_files],
            "pdf": str(pdf_path),
            "preview": [str(path) for path in preview_files],
            "report": str(work_dir / cfg["paths"]["report_file"]),
        },
        omitted_labels=map_render["omitted_labels"],
        source_provenance=source_provenance,
    )

    return {
        "municipal_map": municipal_map_path,
        "map": map_path,
        "texture": texture_path,
        "gores": gore_files,
        "pdf": pdf_path,
        "preview": preview_files,
        "report": report_path,
        "omitted_labels": map_render["omitted_labels"],
    }


def validate_output_directory(output_dir: str | Path) -> dict[str, Any]:
    output_root = Path(output_dir)
    if not output_root.exists():
        raise FileNotFoundError(f"Output directory not found: {output_root}")

    required = [
        output_root / "municipal-map.geojson",
        output_root / "leipzig-map.png",
        output_root / "leipzig-texture.png",
        output_root / "leipzig-globe-print.pdf",
        output_root / "build-report.json",
        output_root / "preview",
        output_root / "gores",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required artifacts: {', '.join(missing)}")

    return {
        "output_dir": str(output_root),
        "artifacts": [str(path) for path in required],
        "status": "valid",
    }

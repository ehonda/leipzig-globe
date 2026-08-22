from __future__ import annotations

import base64
import json
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from leipzig_globe.config import DEFAULT_CONFIG, validate_config

A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297


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


def generate_globe_texture(config: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    width, height = texture_dimensions(config)
    image = Image.new("RGB", (width, height), color=(248, 245, 239))
    draw = ImageDraw.Draw(image)

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

    for label in ["Leipzig", "Zentrum", "Mitte", "Connewitz", "Schönefeld", "Plagwitz"]:
        position = (
            int(width * (0.12 + len(label) * 0.02)),
            int(height * (0.15 + (abs(hash(label)) % 6) * 0.11)),
        )
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", max(12, int(width / 70)))
        except OSError:
            font = ImageFont.load_default()
        draw.text(position, label, fill=(70, 71, 73), font=font)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
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
    config: dict[str, Any], output_dir: str | Path, artifact_paths: dict[str, Any]
) -> Path:
    report_path = Path(output_dir) / "build-report.json"
    payload = {
        "city": config.get("city", "Leipzig"),
        "config": config,
        "artifacts": artifact_paths,
        "generated_at_utc": __import__("datetime")
        .datetime.now(__import__("datetime").timezone.utc)
        .isoformat(),
    }
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return report_path


def build_artifacts(
    config: dict[str, Any] | None = None, output_dir: str | Path = "output"
) -> dict[str, Any]:
    cfg = validate_config(config or DEFAULT_CONFIG)
    work_dir = Path(output_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    texture_path = work_dir / cfg["paths"]["texture_file"]
    generate_globe_texture(cfg, texture_path)

    gore_dir = work_dir / cfg["paths"]["gore_dir"]
    gore_files = build_gore_set(texture_path, gore_dir, cfg)

    pdf_path = work_dir / cfg["paths"]["pdf_file"]
    build_pdf(gore_files, pdf_path)

    preview_dir = work_dir / cfg["paths"]["preview_dir"]
    preview_files = generate_preview_set(texture_path, preview_dir)

    report_path = write_build_report(
        cfg,
        work_dir,
        {
            "texture": str(texture_path),
            "gore_dir": str(gore_dir),
            "gore_files": [str(path) for path in gore_files],
            "pdf": str(pdf_path),
            "preview": [str(path) for path in preview_files],
            "report": str(work_dir / cfg["paths"]["report_file"]),
        },
    )

    return {
        "texture": texture_path,
        "gores": gore_files,
        "pdf": pdf_path,
        "preview": preview_files,
        "report": report_path,
    }


def validate_output_directory(output_dir: str | Path) -> dict[str, Any]:
    output_root = Path(output_dir)
    if not output_root.exists():
        raise FileNotFoundError(f"Output directory not found: {output_root}")

    required = [
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

"""Sinusoidal gores and physical, unscaled A4 page tiles."""

from __future__ import annotations

import base64
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .config import validate_config

ATTRIBUTION = "© OpenStreetMap contributors | openstreetmap.org/copyright"


def gore_outline_points(gore_index, gore_count, width, height):
    if gore_count <= 0 or not 0 <= gore_index < gore_count:
        raise ValueError("Invalid gore index or gore_count")
    half_width = width / gore_count / 2
    left, right = [], []
    for y in np.linspace(0, height, 361):
        extent = half_width * math.sin(math.pi * y / height)
        left.append((half_width - extent, float(y)))
        right.append((half_width + extent, float(y)))
    return left + right[::-1]


def _outline(equator_width, height, overlap, inset=3):
    left, right, seam = [], [], []
    center = inset + equator_width / 2
    for y in np.linspace(0, height, 721):
        taper = math.sin(math.pi * y / height)
        # Nominal overlap is measured at the equator and tapers at the poles.
        left.append([center - equator_width / 2 * taper, inset + float(y)])
        seam.append([center + equator_width / 2 * taper, inset + float(y)])
        right.append([center + (equator_width / 2 + overlap) * taper, inset + float(y)])
    return left + right[::-1], seam


def generate_gore_svg(texture_path, output_path, gore_index, gore_count, config):
    cfg = validate_config(config)
    globe = cfg["globe"]
    circumference = math.pi * globe["diameter_mm"]
    equator_width, height = circumference / gore_count, circumference / 2
    overlap = globe["assembly_overlap_mm"]
    inset = 3
    canvas_width, canvas_height = (
        equator_width + overlap + 2 * inset,
        height + 2 * inset,
    )
    ppi = globe["ppi"]
    width_px = math.ceil(canvas_width * ppi / 25.4)
    height_px = math.ceil(canvas_height * ppi / 25.4)
    with Image.open(texture_path) as image:
        texture = np.asarray(image.convert("RGB"))
    # Pixel centres map directly to physical paper coordinates. Work one row
    # at a time so print-size textures do not create giant float arrays.
    output = np.zeros((height_px, width_px, 4), dtype=np.uint8)
    x_mm = (
        (np.arange(width_px) + 0.5) * canvas_width / width_px
        - inset
        - equator_width / 2
    )
    slot = (
        gore_index
        if cfg["layout"]["gore_order"] == "clockwise"
        else gore_count - 1 - gore_index
    )
    for row in range(height_px):
        y_mm = (row + 0.5) * canvas_height / height_px - inset
        if not 0 <= y_mm < height:
            continue
        taper = math.sin(math.pi * y_mm / height)
        inside = (x_mm >= -equator_width / 2 * taper) & (
            x_mm <= (equator_width / 2 + overlap) * taper
        )
        # The right-hand overlap samples the next gore's actual content.
        longitude = (slot + 0.5) / gore_count + x_mm / (circumference * taper)
        sample = (longitude * texture.shape[1] - 0.5) % texture.shape[1]
        lo = np.floor(sample).astype(int)
        fraction = sample - lo
        ty = min(texture.shape[0] - 1, int(y_mm / height * texture.shape[0]))
        colors = (
            texture[ty, lo] * (1 - fraction[:, None])
            + texture[ty, (lo + 1) % texture.shape[1]] * fraction[:, None]
        )
        output[row, inside, :3] = np.rint(colors[inside]).astype(np.uint8)
        output[row, inside, 3] = 255
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    png = path.with_suffix(".png")
    Image.fromarray(output).save(png, dpi=(ppi, ppi))
    outline, seam = _outline(equator_width, height, overlap, inset)
    alignment = []
    for fraction in (0.25, 0.5, 0.75):
        extent = equator_width / 2 * math.sin(math.pi * fraction)
        for sign in (-1, 1):
            alignment.append(
                [inset + equator_width / 2 + sign * extent, inset + height * fraction]
            )
    marks = "".join(
        f'<path d="M {x-.6} {y} h 1.2 M {x} {y-.6} v 1.2" stroke="#555" stroke-width="0.1"/>'
        for x, y in alignment
    )
    points = lambda coords: " ".join(f"{x:.5f},{y:.5f}" for x, y in coords)
    encoded = base64.b64encode(png.read_bytes()).decode("ascii")
    centerline = (
        f'<line x1="{inset+equator_width/2}" x2="{inset+equator_width/2}" y1="{inset}" y2="{height+inset}" stroke="#aaa" stroke-width="0.1" stroke-dasharray="1 2"/>'
        if cfg["layout"].get("gore_centerlines", False)
        else ""
    )
    number = (
        f'<text x="{canvas_width/2}" y="2.3" font-size="2" text-anchor="middle">Gore {gore_index+1:02d}</text>'
        if cfg["layout"].get("gore_numbering", True)
        else ""
    )
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_width}mm" height="{canvas_height}mm" viewBox="0 0 {canvas_width} {canvas_height}">
<image href="data:image/png;base64,{encoded}" width="{canvas_width}" height="{canvas_height}"/>
<polygon points="{points(outline)}" fill="none" stroke="#444" stroke-width="0.15"/>
<polyline points="{points(seam)}" fill="none" stroke="#777" stroke-width="0.1" stroke-dasharray="1 1"/>
{centerline}{number}{marks}
</svg>""",
        encoding="utf-8",
    )
    metadata = {
        "index": gore_index,
        "longitude_slot": slot,
        "svg": path.name,
        "png": png.name,
        "width_mm": canvas_width,
        "height_mm": canvas_height,
        "inset_mm": inset,
        "equator_width_mm": equator_width,
        "pole_to_pole_mm": height,
        "overlap_equator_mm": overlap,
        "outline_mm": outline,
        "seam_mm": seam,
        "alignment_mm": alignment,
    }
    path.with_suffix(".json").write_text(json.dumps(metadata), encoding="utf-8")
    return path


def build_gore_set(texture_path, output_dir, config):
    cfg = validate_config(config)
    root = Path(output_dir)
    files = [
        generate_gore_svg(
            texture_path,
            root / f"gore-{index+1:02d}.svg",
            index,
            cfg["globe"]["gore_count"],
            cfg,
        )
        for index in range(cfg["globe"]["gore_count"])
    ]
    manifest = {
        "config": cfg,
        "texture": str(texture_path),
        "gores": [json.loads(path.with_suffix(".json").read_text()) for path in files],
    }
    (root / "geometry-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return files


def page_tiles(gore_count, gore_width, gore_height, margin, overlap):
    usable_width, usable_height = 210 - 2 * margin, 297 - 2 * margin
    gap = 4
    across = math.floor((usable_width + gap) / (gore_width + gap))
    if across < 1:
        # A wide gore is tiled horizontally too, at the same physical scale.
        columns = (
            math.ceil(max(0, gore_width - usable_width) / (usable_width - overlap)) + 1
        )
        groups = [
            (index, column) for index in range(gore_count) for column in range(columns)
        ]
    else:
        groups = [(index, 0) for index in range(0, gore_count, across)]
    rows = (
        math.ceil(max(0, gore_height - usable_height) / (usable_height - overlap)) + 1
    )
    tiles = []
    for first, column in groups:
        for row in range(rows):
            tiles.append(
                {
                    "page": len(tiles) + 1,
                    "row": row,
                    "column": column,
                    "y_mm": row * (usable_height - overlap),
                    "x_mm": column * (usable_width - overlap),
                    "width_mm": usable_width,
                    "height_mm": usable_height,
                    "gores": list(
                        range(first, min(gore_count, first + max(1, across)))
                    ),
                }
            )
    return tiles


def build_pdf(gore_files, output_path, config=None):
    files = [Path(path) for path in gore_files]
    cfg = validate_config(config)
    info = [json.loads(path.with_suffix(".json").read_text()) for path in files]
    width, height = info[0]["width_mm"], info[0]["height_mm"]
    margin, overlap = cfg["layout"]["print_margin_mm"], cfg["layout"]["tile_overlap_mm"]
    tiles = page_tiles(len(files), width, height, margin, overlap)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4, pageCompression=1, invariant=1)
    c.setTitle("Planet Leipzig — print at 100% / actual size")
    c.setAuthor("Leipzig Globe; map data © OpenStreetMap contributors")
    c.setViewerPreference("PrintScaling", "None")

    def polyline(points, close=False):
        drawing = c.beginPath()
        drawing.moveTo(*points[0])
        for point in points[1:]:
            drawing.lineTo(*point)
        if close:
            drawing.close()
        c.drawPath(drawing)

    for tile in tiles:
        c.saveState()
        clip = c.beginPath()
        clip.rect(
            margin * mm, margin * mm, tile["width_mm"] * mm, tile["height_mm"] * mm
        )
        c.clipPath(clip, stroke=0)
        for position, index in enumerate(tile["gores"]):
            x = margin + position * (width + 4) - tile["x_mm"]
            top = 297 - margin + tile["y_mm"]
            c.drawImage(
                str(files[index].with_suffix(".png")),
                x * mm,
                (top - height) * mm,
                width=width * mm,
                height=height * mm,
                mask="auto",
            )
            c.setStrokeColorRGB(0.25, 0.25, 0.25)
            c.setLineWidth(0.15 * mm)
            polyline(
                [
                    ((x + px) * mm, (top - py) * mm)
                    for px, py in info[index]["outline_mm"]
                ],
                close=True,
            )
            c.setLineWidth(0.1 * mm)
            c.setDash(1 * mm, 1 * mm)
            polyline(
                [((x + px) * mm, (top - py) * mm) for px, py in info[index]["seam_mm"]]
            )
            c.setDash()
            for px, py in info[index].get("alignment_mm", []):
                c.line(
                    (x + px - 0.6) * mm,
                    (top - py) * mm,
                    (x + px + 0.6) * mm,
                    (top - py) * mm,
                )
                c.line(
                    (x + px) * mm,
                    (top - py - 0.6) * mm,
                    (x + px) * mm,
                    (top - py + 0.6) * mm,
                )
            if cfg["layout"].get("gore_numbering", True):
                c.setFont("Helvetica", 6)
                c.drawCentredString(
                    (x + width / 2) * mm, (top - 2.3) * mm, f"Gore {index+1:02d}"
                )
            if cfg["layout"].get("gore_centerlines", False):
                center = (
                    x + info[index]["inset_mm"] + info[index]["equator_width_mm"] / 2
                )
                c.line(
                    center * mm,
                    (top - info[index]["inset_mm"]) * mm,
                    center * mm,
                    (top - height + info[index]["inset_mm"]) * mm,
                )
        c.restoreState()
        c.setFont("Helvetica", 7)
        names = ", ".join(f"{index+1:02d}" for index in tile["gores"])
        c.drawString(
            margin * mm,
            (297 - margin / 2) * mm,
            f"Page {tile['page']}/{len(tiles)} | Gores {names} | row {tile['row']+1}, column {tile['column']+1} | PRINT 100%",
        )
        c.setFont("Helvetica", 5)
        c.drawString(margin * mm, 2 * mm, ATTRIBUTION)
        # 100 millimetres in PDF points, with measurable perpendicular ends.
        ruler_y = margin / 2
        c.setLineWidth(0.2 * mm)
        c.line(margin * mm, ruler_y * mm, (margin + 100) * mm, ruler_y * mm)
        for tick in range(0, 101, 10):
            c.line(
                (margin + tick) * mm,
                (ruler_y - 0.6) * mm,
                (margin + tick) * mm,
                (ruler_y + 0.6) * mm,
            )
        c.drawString(
            (margin + 102) * mm, ruler_y * mm, "100 mm — measure before assembly"
        )
        # Shared world y coordinates appear in both overlapping page tiles.
        # Place registration crosses in side margins at overlap centres.
        for world_y in (
            tile["y_mm"] + overlap / 2,
            tile["y_mm"] + tile["height_mm"] - overlap / 2,
        ):
            page_y = 297 - margin - (world_y - tile["y_mm"])
            for page_x in (margin / 2, 210 - margin / 2):
                c.line((page_x - 1) * mm, page_y * mm, (page_x + 1) * mm, page_y * mm)
                c.line(page_x * mm, (page_y - 1) * mm, page_x * mm, (page_y + 1) * mm)
        if width > tile["width_mm"]:
            for world_x in (
                tile["x_mm"] + overlap / 2,
                tile["x_mm"] + tile["width_mm"] - overlap / 2,
            ):
                page_x = margin + world_x - tile["x_mm"]
                for page_y in (margin / 2, 297 - margin / 2):
                    c.line(
                        (page_x - 1) * mm, page_y * mm, (page_x + 1) * mm, page_y * mm
                    )
                    c.line(
                        page_x * mm, (page_y - 1) * mm, page_x * mm, (page_y + 1) * mm
                    )
        c.showPage()
    c.save()
    path.with_suffix(".tiles.json").write_text(
        json.dumps(
            {
                "paper_mm": [210, 297],
                "tiles": tiles,
                "gore_width_mm": width,
                "gore_height_mm": height,
                "print_scale": 1.0,
                "calibration_mm": 100,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path

"""Save compact, attributed visual evidence from an already validated build.

Run: uv run --with pymupdf scripts/save_checkpoint.py 02-real-globe
"""

import argparse
import json
import shutil
from pathlib import Path

import matplotlib
import pymupdf
from PIL import Image, ImageDraw, ImageFont

from leipzig_globe.pipeline import validate_output_directory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()
    if Path(args.name).name != args.name or args.name in {".", ".."}:
        raise ValueError("Checkpoint name must be a single directory name.")
    validate_output_directory(args.output)
    root = Path("demos") / args.name
    root.mkdir(parents=True, exist_ok=True)
    font_path = str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf")
    font = ImageFont.truetype(font_path, 22)
    small = ImageFont.truetype(font_path, 16)
    sheet = Image.new("RGB", (1500, 1100), (247, 247, 247))
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (25, 12),
        "Planet Leipzig · six views of the printable texture",
        font=font,
        fill="#333333",
    )
    for index, name in enumerate(("front", "back", "left", "right", "north", "south")):
        with Image.open(args.output / "preview" / f"{name}.png") as image:
            image = image.resize((490, 490), Image.Resampling.LANCZOS)
        x, y = index % 3 * 500 + 5, index // 3 * 510 + 45
        sheet.paste(image, (x, y))
        draw.text((x + 10, y + 470), name.title(), font=small, fill="#333333")
    draw.text(
        (20, 1075),
        "© OpenStreetMap contributors · openstreetmap.org/copyright · Boundary: Stadt Leipzig",
        font=small,
        fill="#333333",
    )
    sheet.save(root / "globe-views.jpg", quality=92)
    for name in ("leipzig-map.png", "leipzig-texture.png"):
        with Image.open(args.output / name) as image:
            image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
            image.save(root / name)
    shutil.copyfile(args.output / "build-report.json", root / "build-report.json")
    document = pymupdf.open(args.output / "leipzig-globe-print.pdf")
    page = document[min(6, len(document) - 1)]
    page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(root / "print-page.png")
    # A small two-page sample contains the adjacent central gores at exact size.
    sample = pymupdf.open()
    first = min(6, len(document) - 2)
    sample.insert_pdf(document, from_page=first, to_page=first + 1)
    sample.xref_set_key(
        sample.pdf_catalog(), "ViewerPreferences", "<< /PrintScaling /None >>"
    )
    sample.save(root / "test-print-two-gores.pdf")
    description = {
        "source_output": str(args.output),
        "checkpoint": args.name,
        "images_are_downsampled": True,
        "sample_pdf_pages": [first + 1, first + 2],
        "sample_pdf_print_at": "100% / actual size",
        "full_build_report": "build-report.json",
        "physical_test": "Awaiting human printing, measurement and assembly.",
    }
    (root / "checkpoint.json").write_text(
        json.dumps(description, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

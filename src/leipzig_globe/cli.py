from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Annotated

import requests
import typer

from leipzig_globe.config import load_config
from leipzig_globe.fetcher import (
    DEFAULT_CACHE_DIR,
    DEFAULT_SOURCE_LOCK,
    fetch_data_sources,
    load_source_lock,
)
from leipzig_globe.pipeline import build_artifacts, validate_output_directory
from leipzig_globe.web_preview import export_web_preview

app = typer.Typer(help="Leipzig Globe build and validation CLI")


@app.command("fetch-data")
def fetch_data(
    cache_dir: Annotated[
        Path, typer.Option(help="Directory for cached OpenStreetMap and boundary data.")
    ] = Path(DEFAULT_CACHE_DIR),
    source_lock: Annotated[
        Path,
        typer.Option(
            help="Versioned source lock with URLs, expected checksums and attribution."
        ),
    ] = DEFAULT_SOURCE_LOCK,
) -> None:
    try:
        downloaded = fetch_data_sources(cache_dir, load_source_lock(source_lock))
    except (ValueError, OSError, requests.RequestException) as exc:
        typer.echo(f"Source acquisition failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    for source_name, data_file in downloaded.items():
        typer.echo(f"{source_name}: {data_file}")


@app.command("build")
def build(
    output_dir: Annotated[
        Path, typer.Option(help="Directory for generated outputs.")
    ] = Path("output"),
    config_path: Annotated[
        Path | None, typer.Option(help="Optional YAML config file.")
    ] = None,
) -> None:
    try:
        config = load_config(config_path)
        artifacts = build_artifacts(config, output_dir)
    except (
        ValueError,
        TypeError,
        OSError,
        RuntimeError,
        subprocess.CalledProcessError,
    ) as exc:
        typer.echo(f"Build failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Build complete. Texture: {artifacts['texture']}")
    typer.echo(f"PDF: {artifacts['pdf']}")


@app.command("validate")
def validate(
    output_dir: Annotated[Path, typer.Option(help="Directory to validate.")] = Path(
        "output"
    ),
) -> None:
    try:
        result = validate_output_directory(output_dir)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        typer.echo(f"Validation failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Validation status: {result['status']}")
    typer.echo(f"Checked {len(result['artifacts'])} artifacts.")


@app.command("export-web-preview")
def export_web_preview_assets(
    build_dir: Annotated[
        Path, typer.Option(help="Validated build output containing texture and gores.")
    ] = Path("output"),
    site_dir: Annotated[
        Path, typer.Option(help="Static-site asset directory to populate.")
    ] = Path("docs/assets"),
    preset_id: Annotated[
        str,
        typer.Option(
            help="Stable preset ID used by the viewer, for example 'globe-215mm-high-density'."
        ),
    ] = "default",
) -> None:
    try:
        report = (build_dir / "build-report.json")
        if not report.is_file():
            raise FileNotFoundError(f"Build Report not found: {report}")
        build = json.loads(report.read_text(encoding="utf-8"))
        artifacts = build["artifacts"]
        manifest = export_web_preview(
            build_dir / artifacts["texture"],
            build_dir / artifacts["gore_dir"],
            site_dir,
            config=build["config"],
            preset_id=preset_id,
        )
    except (KeyError, ValueError, OSError) as exc:
        typer.echo(f"Web preview export failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Web preview assets: {manifest}")


def main() -> None:
    app()

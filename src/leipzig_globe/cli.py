from __future__ import annotations

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


def main() -> None:
    app()

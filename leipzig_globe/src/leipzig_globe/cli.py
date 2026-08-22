from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from leipzig_globe.config import DEFAULT_CONFIG, load_config, validate_config
from leipzig_globe.fetcher import (
    DEFAULT_LEIPZIG_BOUNDARY_URL,
    DEFAULT_OSM_PBF_URL,
    SourceManifest,
    fetch_data_sources,
)
from leipzig_globe.pipeline import build_artifacts, validate_output_directory

app = typer.Typer(help="Leipzig Globe build and validation CLI")


@app.command("fetch-data")
def fetch_data(
    cache_dir: Annotated[
        Path, typer.Option(help="Directory for cached OpenStreetMap and boundary data.")
    ] = Path(".cache"),
    pbf_url: Annotated[
        str,
        typer.Option(help="URL to the Geofabrik Saxony OSM PBF extract."),
    ] = DEFAULT_OSM_PBF_URL,
    boundary_url: Annotated[
        str,
        typer.Option(help="URL to the official Leipzig municipal boundary source."),
    ] = DEFAULT_LEIPZIG_BOUNDARY_URL,
) -> None:
    manifests = (
        SourceManifest(
            source_name="sachsen-latest",
            url=pbf_url,
            file_name="sachsen-latest.osm.pbf",
            metadata={
                "license": "OpenStreetMap © Contributors",
                "source_type": "osm.pbf",
                "source_version": "sachsen-latest",
            },
        ),
        SourceManifest(
            source_name="leipzig-municipal-boundary",
            url=boundary_url,
            file_name="leipzig-municipal-boundary.geojson",
            metadata={
                "license": "Leipzig Open Data",
                "source_type": "geojson",
                "source_version": "official",
            },
        ),
    )

    downloaded = fetch_data_sources(cache_dir, manifests)
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
    config = load_config(config_path) if config_path else DEFAULT_CONFIG
    validate_config(config)
    artifacts = build_artifacts(config, output_dir)
    typer.echo(f"Build complete. Texture: {artifacts['texture']}")
    typer.echo(f"PDF: {artifacts['pdf']}")


@app.command("validate")
def validate(
    output_dir: Annotated[Path, typer.Option(help="Directory to validate.")] = Path(
        "output"
    ),
) -> None:
    result = validate_output_directory(output_dir)
    typer.echo(f"Validation status: {result['status']}")
    for artifact in result["artifacts"]:
        typer.echo(f"- {artifact}")


def main() -> None:
    app()

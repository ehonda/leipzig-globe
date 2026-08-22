from __future__ import annotations

from pathlib import Path

import typer

from leipzig_globe.config import DEFAULT_CONFIG, load_config, validate_config
from leipzig_globe.fetcher import SourceManifest, fetch_data_cache
from leipzig_globe.pipeline import build_artifacts, ensure_osmium_available, validate_output_directory

app = typer.Typer(help="Leipzig Globe build and validation CLI")


@app.command("fetch-data")
def fetch_data(
    cache_dir: Path = typer.Option(Path(".cache"), "--cache-dir", help="Directory for cached OpenStreetMap and boundary data."),
    url: str = typer.Option(
        "https://download.geofabrik.de/europe/germany/sachsen-latest.osm.pbf",
        "--url",
        help="URL to the source OSM extract.",
    ),
) -> None:
    ensure_osmium_available()
    manifest = SourceManifest(
        source_name="sachsen-latest",
        url=url,
        file_name="sachsen-latest.osm.pbf",
        sha256="66a521f00dca61ea08a3a7afd2a4a0ce6f1ef3caeb4df4d5020c9ad4a1f79117",
        metadata={"license": "OpenStreetMap © Contributors"},
    )
    data_file = fetch_data_cache(cache_dir, manifest)
    typer.echo(f"Fetched source data to {data_file}")


@app.command("build")
def build(
    output_dir: Path = typer.Option(Path("output"), "--output-dir", help="Directory for generated outputs."),
    config_path: Path | None = typer.Option(None, "--config", help="Optional YAML config file."),
) -> None:
    config = load_config(config_path) if config_path else DEFAULT_CONFIG
    validate_config(config)
    artifacts = build_artifacts(config, output_dir)
    typer.echo(f"Build complete. Texture: {artifacts['texture']}")
    typer.echo(f"PDF: {artifacts['pdf']}")


@app.command("validate")
def validate(
    output_dir: Path = typer.Option(Path("output"), "--output-dir", help="Directory to validate."),
) -> None:
    result = validate_output_directory(output_dir)
    typer.echo(f"Validation status: {result['status']}")
    for artifact in result["artifacts"]:
        typer.echo(f"- {artifact}")


def main() -> None:
    app()

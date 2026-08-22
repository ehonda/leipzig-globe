from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

DEFAULT_OSM_PBF_URL = (
    "https://download.geofabrik.de/europe/germany/sachsen-latest.osm.pbf"
)
DEFAULT_LEIPZIG_BOUNDARY_URL = "https://static.leipzig.de/fileadmin/mediendatenbank/leipzig-de/Stadt/02.1_Dez1_Allgemeine_Verwaltung/12_Statistik_und_Wahlen/Geodaten/Stadtbezirke_Leipzig_UTM33N.json"


@dataclass
class SourceManifest:
    source_name: str
    url: str
    file_name: str
    checksum: str | None = None
    sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def expected_digest(self) -> str | None:
        return self.sha256 or self.checksum

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "source_name": self.source_name,
            "url": self.url,
            "file_name": self.file_name,
            "checksum": self.checksum,
            "sha256": self.sha256,
            "metadata": self.metadata,
        }
        if self.metadata.get("source_version") is not None:
            payload["source_version"] = self.metadata["source_version"]
        return payload


DEFAULT_SOURCE_MANIFESTS: tuple[SourceManifest, ...] = (
    SourceManifest(
        source_name="sachsen-latest",
        url=DEFAULT_OSM_PBF_URL,
        file_name="sachsen-latest.osm.pbf",
        checksum=None,
        sha256=None,
        metadata={
            "license": "OpenStreetMap © Contributors",
            "source_type": "osm.pbf",
            "source_version": "sachsen-latest",
        },
    ),
    SourceManifest(
        source_name="leipzig-municipal-boundary",
        url=DEFAULT_LEIPZIG_BOUNDARY_URL,
        file_name="leipzig-municipal-boundary.geojson",
        checksum=None,
        sha256=None,
        metadata={
            "license": "Leipzig Open Data",
            "source_type": "geojson",
            "source_version": "official",
        },
    ),
)


def compute_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest(manifest: SourceManifest, file_path: str | Path) -> str:
    expected = (manifest.expected_digest or "").lower()
    if not expected:
        return ""

    actual = compute_sha256(file_path).lower()
    if actual != expected:
        raise ValueError(
            f"checksum mismatch for {Path(file_path).name}: expected {expected}, got {actual}"
        )
    return actual


def fetch_remote_file(
    url: str, destination: str | Path, *, expected_sha256: str | None = None
) -> Path:
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    destination_path.write_bytes(response.content)

    if expected_sha256:
        actual = compute_sha256(destination_path).lower()
        if actual != expected_sha256.lower():
            raise ValueError(
                f"checksum mismatch for {destination_path.name}: expected {expected_sha256}, got {actual}"
            )
    return destination_path


def load_source_manifests(cache_dir: str | Path) -> dict[str, SourceManifest]:
    manifest_path = Path(cache_dir) / "source-manifest.json"
    if not manifest_path.exists():
        return {}

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    if not isinstance(payload, dict):
        return {}

    if "source_name" in payload:
        entry = SourceManifest(
            source_name=str(payload.get("source_name", "unknown")),
            url=str(payload.get("url", "")),
            file_name=str(payload.get("file_name", "")),
            checksum=payload.get("checksum"),
            sha256=payload.get("sha256"),
            metadata=dict(payload.get("metadata") or {}),
        )
        return {entry.file_name: entry} if entry.file_name else {}

    sources: dict[str, SourceManifest] = {}
    for item in payload.get("sources", []):
        if not isinstance(item, dict):
            continue
        entry = SourceManifest(
            source_name=str(item.get("source_name", "unknown")),
            url=str(item.get("url", "")),
            file_name=str(item.get("file_name", "")),
            checksum=item.get("checksum"),
            sha256=item.get("sha256"),
            metadata=dict(item.get("metadata") or {}),
        )
        if entry.file_name:
            sources[entry.file_name] = entry
    return sources


def persist_source_manifest(cache_dir: str | Path, manifest: SourceManifest) -> Path:
    cache_root = Path(cache_dir)
    cache_root.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_root / "source-manifest.json"

    existing = load_source_manifests(cache_root)
    existing[manifest.file_name] = manifest
    entries = [entry.as_dict() for entry in existing.values()]

    payload: dict[str, Any] | list[dict[str, Any]]
    if len(entries) == 1:
        payload = entries[0]
    else:
        payload = {"sources": entries}

    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest_path


def fetch_data_cache(cache_dir: str | Path, manifest: SourceManifest) -> Path:
    cache_root = Path(cache_dir)
    cache_root.mkdir(parents=True, exist_ok=True)
    file_path = cache_root / manifest.file_name
    cached_manifest = load_source_manifests(cache_root).get(manifest.file_name)
    if cached_manifest is not None:
        if manifest.checksum is None and cached_manifest.checksum is not None:
            manifest.checksum = cached_manifest.checksum
        if manifest.sha256 is None and cached_manifest.sha256 is not None:
            manifest.sha256 = cached_manifest.sha256
        if manifest.metadata:
            cached_metadata = dict(cached_manifest.metadata)
            cached_metadata.update(manifest.metadata)
            manifest.metadata = cached_metadata
        elif cached_manifest.metadata:
            manifest.metadata = dict(cached_manifest.metadata)

    if file_path.exists():
        if manifest.expected_digest:
            verify_manifest(manifest, file_path)
        else:
            manifest.sha256 = compute_sha256(file_path)
    else:
        fetch_remote_file(
            manifest.url,
            file_path,
            expected_sha256=manifest.expected_digest,
        )
        manifest.sha256 = compute_sha256(file_path)
        if (
            manifest.expected_digest
            and manifest.sha256.lower() != manifest.expected_digest.lower()
        ):
            raise ValueError(
                f"checksum mismatch for {file_path.name}: expected {manifest.expected_digest}, got {manifest.sha256}"
            )

    manifest.sha256 = compute_sha256(file_path)
    manifest.metadata["source_version"] = manifest.metadata.get(
        "source_version", "unknown"
    )
    persist_source_manifest(cache_root, manifest)
    return file_path


def fetch_data_sources(
    cache_dir: str | Path, manifests: Iterable[SourceManifest]
) -> dict[str, Path]:
    downloaded: dict[str, Path] = {}
    for manifest in manifests:
        downloaded[manifest.source_name] = fetch_data_cache(cache_dir, manifest)
    return downloaded

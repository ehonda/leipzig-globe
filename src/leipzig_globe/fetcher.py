from __future__ import annotations

import hashlib
import json
import re
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import requests

DEFAULT_OSM_PBF_URL = (
    "https://download.geofabrik.de/europe/germany/sachsen-260901.osm.pbf"
)
DEFAULT_LEIPZIG_BOUNDARY_URL = "https://static.leipzig.de/fileadmin/mediendatenbank/leipzig-de/Stadt/02.1_Dez1_Allgemeine_Verwaltung/12_Statistik_und_Wahlen/Geodaten/Stadtbezirke_Leipzig_UTM33N.json"
DEFAULT_SOURCE_LOCK = Path(__file__).resolve().parents[2] / "config/source-lock.json"
DEFAULT_CACHE_DIR = ".cache/sources-2026-09-01"
MAX_DOWNLOAD_BYTES = 400_000_000


class ManifestError(ValueError):
    """External JSON fails the source-manifest schema (not a caller type error)."""


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


def _validate_manifest(manifest: SourceManifest) -> None:
    for key in ("source_name", "url", "file_name"):
        value = getattr(manifest, key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Invalid source manifest: {key} must be a nonempty string."
            )
    if manifest.file_name in {".", ".."} or any(
        char in manifest.file_name for char in "/\\:"
    ):
        raise ValueError(
            "Invalid source manifest: file_name must be a single local filename."
        )
    digest = manifest.expected_digest
    if not isinstance(digest, str) or not re.fullmatch("[0-9a-fA-F]{64}", digest):
        raise ValueError(
            f"Invalid SHA-256 checksum for {manifest.file_name}; expected a pinned 64-digit digest."
        )
    if (
        manifest.sha256 is not None
        and manifest.checksum is not None
        and (
            not isinstance(manifest.sha256, str)
            or not isinstance(manifest.checksum, str)
            or manifest.sha256.lower() != manifest.checksum.lower()
        )
    ):
        raise ManifestError("Invalid source manifest: conflicting SHA-256 checksums.")
    if not isinstance(manifest.metadata, dict):
        raise ManifestError("Invalid source manifest: metadata must be an object.")


def compute_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest(manifest: SourceManifest, file_path: str | Path) -> str:
    _validate_manifest(manifest)
    actual = compute_sha256(file_path)
    if actual != manifest.expected_digest.lower():
        raise ValueError(
            f"checksum mismatch for {Path(file_path).name}: expected {manifest.expected_digest}, got {actual}"
        )
    return actual


def _read_manifests(path: Path) -> dict[str, SourceManifest]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError(f"Malformed source manifest: {path}") from exc
    if not isinstance(payload, dict):
        raise ManifestError(
            f"Malformed source manifest: {path} must contain an object."
        )
    entries = [payload] if "source_name" in payload else payload.get("sources")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"Malformed source manifest: {path} has no source entries.")
    manifests = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ManifestError(f"Malformed source entry in {path}")
        try:
            manifest = SourceManifest(
                source_name=entry["source_name"],
                url=entry["url"],
                file_name=entry["file_name"],
                checksum=entry.get("checksum"),
                sha256=entry.get("sha256"),
                metadata=entry.get("metadata", {}),
            )
        except KeyError as exc:
            raise ValueError(f"Missing source manifest field in {path}: {exc}") from exc
        _validate_manifest(manifest)
        if manifest.file_name in manifests:
            raise ValueError(
                f"Duplicate source filename in {path}: {manifest.file_name}"
            )
        manifests[manifest.file_name] = manifest
    return manifests


def load_source_lock(
    path: str | Path = DEFAULT_SOURCE_LOCK,
) -> tuple[SourceManifest, ...]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("Source lock must have version 1.")
    manifests = _read_manifests(source)
    if set(manifests) != {
        "sachsen-latest.osm.pbf",
        "leipzig-municipal-boundary.geojson",
    }:
        raise ValueError(
            "Source lock must contain the Saxony PBF and official Leipzig boundary."
        )
    for manifest in manifests.values():
        for key in ("source_version", "license", "license_url", "attribution"):
            if (
                not isinstance(manifest.metadata.get(key), str)
                or not manifest.metadata[key].strip()
            ):
                raise ValueError(f"Source lock entry {manifest.file_name} lacks {key}.")
    return tuple(manifests.values())


def load_source_manifests(cache_dir: str | Path) -> dict[str, SourceManifest]:
    path = Path(cache_dir) / "source-manifest.json"
    return _read_manifests(path) if path.exists() else {}


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".part", delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def persist_source_manifest(cache_dir: str | Path, manifest: SourceManifest) -> Path:
    _validate_manifest(manifest)
    root = Path(cache_dir)
    existing = load_source_manifests(root)
    existing[manifest.file_name] = manifest
    entries = [existing[key].as_dict() for key in sorted(existing)]
    path = root / "source-manifest.json"
    _atomic_json(path, entries[0] if len(entries) == 1 else {"sources": entries})
    return path


def fetch_remote_file(
    url: str, destination: str | Path, *, expected_sha256: str | None = None
) -> Path:
    if not isinstance(expected_sha256, str) or not re.fullmatch(
        "[0-9a-fA-F]{64}", expected_sha256
    ):
        raise ValueError("A pinned SHA-256 checksum is required before downloading.")
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        digest = hashlib.sha256()
        with requests.get(url, stream=True, timeout=(15, 60)) as response:
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=path.parent, suffix=".part", delete=False
            ) as handle:
                temporary = Path(handle.name)
                for chunk in response.iter_content(1024 * 1024):
                    if handle.tell() + len(chunk) > MAX_DOWNLOAD_BYTES:
                        raise ValueError(
                            f"Download exceeds the {MAX_DOWNLOAD_BYTES} byte limit: {url}"
                        )
                    handle.write(chunk)
                    digest.update(chunk)
        if digest.hexdigest() != expected_sha256.lower():
            raise ValueError(
                f"checksum mismatch for {path.name}: expected {expected_sha256}, got {digest.hexdigest()}"
            )
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    return path


def _check_cached_identity(
    manifest: SourceManifest, cached: SourceManifest | None
) -> None:
    _validate_manifest(manifest)
    if cached and (
        cached.url != manifest.url
        or cached.source_name != manifest.source_name
        or cached.expected_digest.lower() != manifest.expected_digest.lower()
        or cached.metadata.get("source_version")
        != manifest.metadata.get("source_version")
    ):
        raise ValueError(
            f"Cached source identity differs for {manifest.file_name}; select a new --cache-dir to preserve the existing inputs."
        )


def fetch_data_cache(cache_dir: str | Path, manifest: SourceManifest) -> Path:
    root = Path(cache_dir)
    _check_cached_identity(
        manifest, load_source_manifests(root).get(manifest.file_name)
    )
    root.mkdir(parents=True, exist_ok=True)
    path = root / manifest.file_name
    if path.exists():
        verify_manifest(manifest, path)
    else:
        fetch_remote_file(manifest.url, path, expected_sha256=manifest.expected_digest)
        verify_manifest(manifest, path)
    persist_source_manifest(
        root, replace(manifest, sha256=manifest.expected_digest.lower())
    )
    return path


def fetch_data_sources(
    cache_dir: str | Path, manifests: Iterable[SourceManifest]
) -> dict[str, Path]:
    entries = tuple(manifests)
    if len({entry.file_name for entry in entries}) != len(entries):
        raise ValueError("Duplicate source filenames in acquisition request.")
    cached = load_source_manifests(cache_dir)
    for entry in entries:
        _check_cached_identity(entry, cached.get(entry.file_name))
    return {entry.source_name: fetch_data_cache(cache_dir, entry) for entry in entries}

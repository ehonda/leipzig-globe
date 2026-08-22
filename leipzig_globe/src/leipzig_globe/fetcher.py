from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


@dataclass
class SourceManifest:
    source_name: str
    url: str
    file_name: str
    checksum: str | None = None
    sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "url": self.url,
            "file_name": self.file_name,
            "checksum": self.checksum,
            "sha256": self.sha256,
            "metadata": self.metadata,
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        }


def compute_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: Path(path).read_bytes() if False else None, None):
        pass
    data = Path(path).read_bytes()
    digest.update(data)
    return digest.hexdigest()


def verify_manifest(manifest: SourceManifest, file_path: str | Path) -> str:
    expected = manifest.sha256 or manifest.checksum
    if not expected:
        return ""

    actual = compute_sha256(file_path)
    if actual != expected.lower():
        raise ValueError(
            f"checksum mismatch for {Path(file_path).name}: expected {expected}, got {actual}"
        )
    return actual


def fetch_remote_file(url: str, destination: str | Path, *, expected_sha256: str | None = None) -> Path:
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    destination_path.write_bytes(response.content)

    if expected_sha256:
        actual = compute_sha256(destination_path)
        if actual != expected_sha256.lower():
            raise ValueError(
                f"checksum mismatch for {destination_path.name}: expected {expected_sha256}, got {actual}"
            )
    return destination_path


def fetch_data_cache(cache_dir: str | Path, manifest: SourceManifest) -> Path:
    cache_root = Path(cache_dir)
    cache_root.mkdir(parents=True, exist_ok=True)
    file_path = cache_root / manifest.file_name
    if not file_path.exists():
        fetch_remote_file(manifest.url, file_path, expected_sha256=manifest.sha256 or manifest.checksum)
    verify_manifest(manifest, file_path)
    manifest_path = cache_root / "source-manifest.json"
    manifest_path.write_text(json.dumps(manifest.as_dict(), indent=2), encoding="utf-8")
    return file_path

from __future__ import annotations

import json
from pathlib import Path

import pytest

from leipzig_globe.config import DEFAULT_CONFIG, load_config, validate_config
from leipzig_globe.fetcher import SourceManifest, verify_manifest


def test_default_config_sets_expected_mvp_values():
    config = load_config()

    assert config["globe"]["diameter_mm"] == 300
    assert config["globe"]["gore_count"] == 12
    assert config["globe"]["assembly_overlap_mm"] == 2
    assert config["layout"]["seam_offset_deg"] == 0


def test_invalid_configuration_raises_actionable_error():
    bad_config = {
        "globe": {
            "diameter_mm": 0,
            "gore_count": 0,
            "assembly_overlap_mm": -1,
        },
        "layout": {"seam_offset_deg": 180},
    }

    with pytest.raises(ValueError, match="diameter_mm|gore_count|assembly_overlap_mm"):
        validate_config(bad_config)


def test_source_manifest_checksum_verification(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    data_file = source_dir / "sample.osm.pbf"
    data_file.write_bytes(b"example-data")

    manifest = SourceManifest(
        source_name="sample",
        url="https://example.com/sample.osm.pbf",
        checksum="3d5a90e1a2b3e32bafc47f1f4f7d8a61d4f5e9b90d9e6b8d6c1b2c4d5ae0c8b",
        sha256="0f2b27f9f7d7d8f7d307f4e0b5fc72957f62d363fef6a6f33a0f1fa1b8890eed",
        file_name="sample.osm.pbf",
        metadata={"license": "example"},
    )

    with pytest.raises(ValueError, match="checksum"):
        verify_manifest(manifest, data_file)


def test_build_manifest_is_serializable(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "globe": {"diameter_mm": 300},
        "source": {"kind": "fixture"},
        "artifacts": {"texture": "texture.png"},
    }
    manifest_path.write_text(json.dumps(manifest))

    payload = json.loads(manifest_path.read_text())
    assert payload["globe"]["diameter_mm"] == 300
    assert payload["artifacts"]["texture"].endswith("texture.png")

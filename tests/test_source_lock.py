import hashlib
import json
from dataclasses import replace

import pytest
import requests

from leipzig_globe.fetcher import (
    SourceManifest,
    fetch_data_cache,
    fetch_data_sources,
    fetch_remote_file,
    load_source_lock,
    load_source_manifests,
)


def entry(name="data.bin", content=b"fixture"):
    return SourceManifest(
        name,
        "https://example.com/" + name,
        name,
        sha256=hashlib.sha256(content).hexdigest(),
        metadata={
            "source_version": "2026-09-01",
            "license": "fixture",
            "license_url": "https://example.com/license",
            "attribution": "fixture authors",
        },
    )


class Response:
    def __init__(self, data, interrupted=False):
        self.data = data
        self.interrupted = interrupted

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def raise_for_status(self):
        pass

    def iter_content(self, size):
        assert size <= 1024 * 1024
        yield self.data[:3]
        if self.interrupted:
            raise requests.ConnectionError("interrupted download")
        yield self.data[3:]


def test_two_clean_acquisitions_are_identical(tmp_path, monkeypatch):
    calls = []

    def get(url, *, stream, timeout):
        assert stream is True
        calls.append(url)
        return Response(b"fixture")

    monkeypatch.setattr("leipzig_globe.fetcher.requests.get", get)
    sources = [entry("a.bin"), entry("b.bin")]
    for cache in (tmp_path / "first", tmp_path / "second"):
        fetch_data_sources(cache, sources)
        assert (cache / "a.bin").read_bytes() == b"fixture"
        assert not list(cache.glob("*.part"))
    assert len(calls) == 4
    assert (tmp_path / "first/source-manifest.json").read_bytes() == (
        tmp_path / "second/source-manifest.json"
    ).read_bytes()
    fetch_data_sources(tmp_path / "first", sources)
    assert len(calls) == 4  # verified cached reuse is offline


@pytest.mark.parametrize("interrupted", [False, True])
def test_failed_download_preserves_existing_file_and_removes_partial(
    tmp_path, monkeypatch, interrupted
):
    target = tmp_path / "source.bin"
    target.write_bytes(b"existing-good-data")
    monkeypatch.setattr(
        "leipzig_globe.fetcher.requests.get",
        lambda *args, **kwargs: Response(b"changed-upstream-bytes", interrupted),
    )
    with pytest.raises(
        (ValueError, requests.ConnectionError), match="checksum mismatch|interrupted"
    ):
        fetch_remote_file(
            "https://example.com/source", target, expected_sha256=entry().sha256
        )
    assert target.read_bytes() == b"existing-good-data"
    assert not list(tmp_path.glob("*.part"))


def test_download_disk_budget_is_enforced_while_streaming(tmp_path, monkeypatch):
    monkeypatch.setattr("leipzig_globe.fetcher.MAX_DOWNLOAD_BYTES", 4)
    monkeypatch.setattr(
        "leipzig_globe.fetcher.requests.get",
        lambda *args, **kwargs: Response(b"fixture"),
    )
    with pytest.raises(ValueError, match="byte limit"):
        fetch_remote_file(
            "https://example.com/source",
            tmp_path / "new.bin",
            expected_sha256=entry().sha256,
        )
    assert list(tmp_path.iterdir()) == []


def test_changed_url_or_version_never_relabels_cached_bytes(tmp_path):
    manifest = entry()
    (tmp_path / manifest.file_name).write_bytes(b"fixture")
    fetch_data_cache(tmp_path, manifest)
    before = (tmp_path / "source-manifest.json").read_bytes()
    for changed in (
        replace(manifest, url="https://other.example.com/data.bin"),
        replace(
            manifest, metadata={**manifest.metadata, "source_version": "2099-01-01"}
        ),
    ):
        with pytest.raises(ValueError, match="identity differs"):
            fetch_data_cache(tmp_path, changed)
    assert (tmp_path / "source-manifest.json").read_bytes() == before
    assert (tmp_path / manifest.file_name).read_bytes() == b"fixture"


@pytest.mark.parametrize(
    "payload", ["{", "[]", "{}", '{"sources":[]}', '{"sources":[42]}']
)
def test_malformed_cache_manifests_fail_without_being_replaced(tmp_path, payload):
    path = tmp_path / "source-manifest.json"
    path.write_text(payload)
    with pytest.raises(ValueError, match="[Mm]alformed"):
        load_source_manifests(tmp_path)
    assert path.read_text() == payload


@pytest.mark.parametrize(
    "change",
    [
        {"file_name": "../escape"},
        {"file_name": "..\\escape"},
        {"sha256": "bad"},
        {"url": None},
        {"metadata": []},
        {"checksum": "0" * 64},
    ],
)
def test_invalid_manifest_fields_are_rejected(tmp_path, change):
    payload = {**entry().as_dict(), **change}
    (tmp_path / "source-manifest.json").write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="Invalid"):
        load_source_manifests(tmp_path)


def test_duplicate_source_entries_fail(tmp_path):
    (tmp_path / "source-manifest.json").write_text(
        json.dumps({"sources": [entry().as_dict()] * 2})
    )
    with pytest.raises(ValueError, match="Duplicate"):
        load_source_manifests(tmp_path)


def test_tracked_lock_contains_two_pinned_attributed_sources():
    sources = load_source_lock()
    assert len(sources) == 2
    osm = next(source for source in sources if source.file_name.endswith(".pbf"))
    assert "sachsen-260901.osm.pbf" in osm.url
    for source in sources:
        assert len(source.sha256) == 64
        assert source.metadata["source_version"]
        assert source.metadata["license_url"].startswith("https://")


def test_invalid_source_lock_metadata_fails(tmp_path):
    sources = [source.as_dict() for source in load_source_lock()]
    sources[0]["metadata"].pop("license_url")
    path = tmp_path / "lock.json"
    path.write_text(json.dumps({"version": 1, "sources": sources}))
    with pytest.raises(ValueError, match="lacks license_url"):
        load_source_lock(path)


def test_default_cache_agrees_with_build_config():
    from leipzig_globe.config import load_config
    from leipzig_globe.fetcher import DEFAULT_CACHE_DIR

    assert load_config()["layout"]["source_cache_dir"] == DEFAULT_CACHE_DIR

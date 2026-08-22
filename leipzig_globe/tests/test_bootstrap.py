import tomllib
from pathlib import Path

import pytest

import leipzig_globe

ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_contract_is_configured():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    project = data["project"]
    assert project["name"] == "leipzig-globe"
    assert "leipzig-globe" in project["scripts"]

    dev_dependencies = data["dependency-groups"]["dev"]
    assert any("pytest" in dep for dep in dev_dependencies)
    assert any("ruff" in dep for dep in dev_dependencies)
    assert any("black" in dep for dep in dev_dependencies)

    pytest_config = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    assert pytest_config.get("testpaths") == ["tests"]


def test_system_dependency_check_reports_missing_tool(monkeypatch):
    monkeypatch.setattr(leipzig_globe.shutil, "which", lambda name: None)

    with pytest.raises(RuntimeError, match="osmium"):
        leipzig_globe.require_system_dependencies("osmium")


def test_system_dependency_check_passes_when_present(monkeypatch):
    monkeypatch.setattr(leipzig_globe.shutil, "which", lambda name: f"/usr/bin/{name}")

    leipzig_globe.require_system_dependencies("osmium")

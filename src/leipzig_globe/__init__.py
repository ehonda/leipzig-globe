from __future__ import annotations

import shutil

from leipzig_globe.cli import main
from leipzig_globe.municipal_map import WORKING_CRS, derive_municipal_map

__version__ = "0.1.0"

REQUIRED_SYSTEM_TOOLS = {
    "osmium": "Install the Osmium toolchain before running data acquisition or build stages.",
}


def require_system_dependencies(*tool_names: str) -> None:
    missing = [name for name in tool_names if shutil.which(name) is None]
    if missing:
        details = ", ".join(
            f"{name} ({REQUIRED_SYSTEM_TOOLS.get(name, 'required system tool')})"
            for name in missing
        )
        raise RuntimeError(f"Missing required system tools: {details}")


__all__ = [
    "REQUIRED_SYSTEM_TOOLS",
    "WORKING_CRS",
    "__version__",
    "derive_municipal_map",
    "main",
    "require_system_dependencies",
]

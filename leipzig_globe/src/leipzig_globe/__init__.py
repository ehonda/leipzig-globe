from __future__ import annotations

import argparse
import shutil
import sys

REQUIRED_SYSTEM_TOOLS = {
    "osmium": "Install the Osmium toolchain before running data acquisition or build stages.",
}


def require_system_dependencies(*tool_names: str) -> None:
    missing = [name for name in tool_names if shutil.which(name) is None]
    if missing:
        details = ", ".join(f"{name} ({REQUIRED_SYSTEM_TOOLS.get(name, 'required system tool')})" for name in missing)
        raise RuntimeError(f"Missing required system tools: {details}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Leipzig Globe project bootstrap CLI.")
    parser.add_argument(
        "--check-system",
        action="store_true",
        help="Verify required system dependencies are available before data processing.",
    )
    args = parser.parse_args(argv)

    if args.check_system:
        try:
            require_system_dependencies(*REQUIRED_SYSTEM_TOOLS)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        print("System dependency check passed: osmium")
        return

    print("Hello from leipzig-globe!")

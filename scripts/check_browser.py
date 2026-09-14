"""Inspect a freshly built static site in headless Edge when in-app access fails.

Run: uv run --with playwright scripts/check_browser.py --site output/pages-site
Uses the installed Edge browser, an isolated profile, and a loopback-only server.
"""

import argparse
import functools
import hashlib
import io
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

from PIL import Image
from playwright.sync_api import expect, sync_playwright


class QuietHandler(SimpleHTTPRequestHandler):
    # Windows registry maps .js to text/plain on this machine; module scripts
    # require a JavaScript MIME type. Do not inherit that registry association.
    extensions_map: ClassVar[dict[str, str]] = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
    }

    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("output/browser-check"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(QuietHandler, directory=str(args.site.resolve()))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    errors = []
    console = []
    checks = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: console.append(message.text))
            page.on(
                "requestfailed",
                lambda request: errors.append(f"{request.url}: {request.failure}"),
            )
            page.goto(f"http://127.0.0.1:{server.server_port}/")
            try:
                expect(page.locator("#status")).to_be_hidden(timeout=30000)
            except AssertionError:
                print(json.dumps({"errors": errors, "console": console}), flush=True)
                page.screenshot(path=str(args.output / "load-failure.png"))
                raise
            canvas = page.locator("#globe-canvas")

            def frame():
                # OrbitControls damping and WebGL drawing settle asynchronously.
                page.wait_for_timeout(600)
                return hashlib.sha256(canvas.screenshot()).hexdigest()

            variant_frames = []
            for preset in ("terrain", "ocean", "fog"):
                page.get_by_label("Outside Leipzig", exact=True).select_option(preset)
                expect(page.locator("#status")).to_be_hidden(timeout=60000)
                expect(canvas).to_have_attribute("data-variant", preset)
                page.get_by_role("button", name="Finished globe", exact=True).click()
                finished = frame()
                variant_frames.append(finished)
                page.screenshot(path=str(args.output / f"{preset}-finished.png"))
                page.get_by_role("button", name="Gore assembly", exact=True).click()
                expect(
                    page.get_by_role("button", name="Gore assembly")
                ).to_have_attribute("aria-pressed", "true")
                assembled = frame()
                assert assembled != finished, "Mode did not change canvas"
                page.screenshot(path=str(args.output / f"{preset}-gores.png"))
                for label in (
                    "Nominal seams",
                    "Cut edges",
                    "Overlap",
                    "Equator",
                    "Pole zones",
                ):
                    if label == "Pole zones":
                        page.get_by_role("button", name="North", exact=True).click()
                    before = frame()
                    page.get_by_label(label, exact=True).check()
                    assert frame() != before, f"{label} did not change canvas"
                page.screenshot(path=str(args.output / f"{preset}-overlays.png"))
                for label in (
                    "Nominal seams",
                    "Cut edges",
                    "Overlap",
                    "Equator",
                    "Pole zones",
                ):
                    page.get_by_label(label, exact=True).uncheck()
                views = []
                for name in ("Front", "Back", "North", "South"):
                    page.get_by_role("button", name=name, exact=True).click()
                    views.append(frame())
                assert (
                    len(set(views)) == 4
                ), "Camera shortcuts must yield different views"
                page.get_by_role("button", name="Reset", exact=True).click()
                before = frame()
                assert before == assembled, "Reset did not restore the original camera"
                box = canvas.bounding_box()
                x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                page.mouse.move(x, y)
                page.mouse.down()
                page.mouse.move(x + 150, y + 50, steps=10)
                page.mouse.up()
                assert frame() != before, "Drag did not rotate canvas"
                before = frame()
                page.mouse.wheel(0, -200)
                assert frame() != before, "Wheel did not zoom canvas"
                page.get_by_label("Auto rotate", exact=True).check()
                before = frame()
                assert frame() != before, "Auto rotation did not change canvas"
                page.get_by_label("Auto rotate", exact=True).uncheck()
                page.get_by_role("button", name="Reset", exact=True).click()
                checks.append(preset)
            assert (
                len(set(variant_frames)) == 3
            ), "Exterior variants must change the visible globe"
            # Keep the current view/mode while comparing styles, including rapid changes.
            page.get_by_role("button", name="Back", exact=True).click()
            page.get_by_role("button", name="Gore assembly", exact=True).click()
            before_switching = frame()
            for preset in ("ocean", "terrain", "fog"):
                page.get_by_label("Outside Leipzig", exact=True).select_option(preset)
            expect(page.locator("#status")).to_be_hidden(timeout=60000)
            expect(canvas).to_have_attribute("data-variant", "fog")
            assert frame() == before_switching, "Switching variants moved the camera"
            expect(page.get_by_role("button", name="Gore assembly")).to_have_attribute(
                "aria-pressed", "true"
            )
            page.screenshot(path=str(args.output / "fog-back.png"))
            # Versions must switch artwork without moving a settled custom pose.
            for preset in ("terrain", "ocean", "fog"):
                page.get_by_label("Outside Leipzig", exact=True).select_option(preset)
                expect(page.locator("#status")).to_be_hidden(timeout=60000)
                page.get_by_role("button", name="Front", exact=True).click()
                for mode in ("Finished globe", "Gore assembly"):
                    page.get_by_role("button", name=mode, exact=True).click()
                    page.get_by_label("Equator", exact=True).check()
                    current = frame()
                    page.get_by_label("Version", exact=True).select_option("before")
                    expect(canvas).to_have_attribute(
                        "data-version", "before", timeout=60000
                    )
                    expect(page.locator("#status")).to_be_hidden()
                    assert frame() != current, "Before/current artwork did not change"
                    expect(
                        page.get_by_label("Outside Leipzig", exact=True)
                    ).to_have_value(preset)
                    expect(
                        page.get_by_role("button", name=mode, exact=True)
                    ).to_have_attribute("aria-pressed", "true")
                    expect(page.get_by_label("Equator", exact=True)).to_be_checked()
                    if mode == "Finished globe":
                        page.screenshot(path=str(args.output / f"{preset}-before.png"))
                    for version in ("current", "before", "current"):
                        page.get_by_label("Version", exact=True).select_option(version)
                    expect(canvas).to_have_attribute(
                        "data-version", "current", timeout=60000
                    )
                    expect(page.locator("#status")).to_be_hidden()
                    assert (
                        frame() == current
                    ), "Version switching moved the camera or lost overlays"
                    page.get_by_label("Equator", exact=True).uncheck()

            # A failed historical fetch must leave the visible version truthful,
            # retain the old canvas and allow a successful retry.
            def artwork_frame():
                # The error toast intentionally overlays the bottom of the stage.
                # Compare artwork above it and assert the toast separately.
                page.wait_for_timeout(600)
                with Image.open(io.BytesIO(canvas.screenshot())) as capture:
                    return hashlib.sha256(
                        capture.crop(
                            (0, 0, capture.width, capture.height - 60)
                        ).tobytes()
                    ).hexdigest()

            unchanged = artwork_frame()
            page.route(
                "**/baseline/assets/presets.json*",
                lambda route: route.fulfill(status=503, body="unavailable"),
            )
            page.get_by_label("Version", exact=True).select_option("before")
            expect(page.locator("#status")).to_have_text(
                "Preview presets are unavailable."
            )
            expect(canvas).to_have_attribute("data-version", "current")
            assert (
                artwork_frame() == unchanged
            ), "Failed load changed the previous artwork"
            page.unroute("**/baseline/assets/presets.json*")
            page.get_by_label("Version", exact=True).select_option("current")
            expect(page.locator("#status")).to_be_hidden(timeout=60000)
            page.close()
            page = browser.new_page(
                viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True
            )
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/")
            expect(page.locator("#status")).to_be_hidden(timeout=60000)
            page.get_by_label("Outside Leipzig", exact=True).select_option("ocean")
            expect(page.locator("#status")).to_be_hidden(timeout=60000)
            canvas = page.locator("#globe-canvas")
            box = canvas.bounding_box()
            x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            touch = page.context.new_cdp_session(page)
            before = frame()
            touch.send(
                "Input.dispatchTouchEvent",
                {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]},
            )
            for step in range(1, 11):
                touch.send(
                    "Input.dispatchTouchEvent",
                    {"type": "touchMove", "touchPoints": [{"x": x + step * 5, "y": y}]},
                )
            touch.send(
                "Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}
            )
            assert frame() != before, "Touch drag did not rotate canvas"
            before = frame()
            touch.send(
                "Input.dispatchTouchEvent",
                {
                    "type": "touchStart",
                    "touchPoints": [{"x": x - 30, "y": y}, {"x": x + 30, "y": y}],
                },
            )
            for step in range(1, 11):
                touch.send(
                    "Input.dispatchTouchEvent",
                    {
                        "type": "touchMove",
                        "touchPoints": [
                            {"x": x - 30 - step * 3, "y": y},
                            {"x": x + 30 + step * 3, "y": y},
                        ],
                    },
                )
            touch.send(
                "Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}
            )
            assert frame() != before, "Pinch did not zoom canvas"
            frame()
            page.screenshot(path=str(args.output / "mobile.png"), full_page=True)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.get_by_label("Version", exact=True).select_option("before")
            expect(canvas).to_have_attribute("data-version", "before", timeout=60000)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            browser.close()
        assert not errors, errors
        (args.output / "browser-check.json").write_text(
            json.dumps(
                {
                    "browser": "Installed Edge, headless",
                    "presets": checks,
                    "checks": [
                        "three distinct exterior variants",
                        "rapid switching preserves camera and mode",
                        "before/current changes all styles in both modes and preserves camera and overlays",
                        "failed baseline request preserves current preview and can be retried",
                        "mobile version selection",
                        "both modes",
                        "five overlays",
                        "four camera views",
                        "reset",
                        "drag",
                        "wheel zoom",
                        "auto rotation",
                        "mobile layout",
                        "touch drag",
                        "pinch zoom",
                    ],
                    "errors": errors,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("Browser checks passed for all three exterior variants.")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()

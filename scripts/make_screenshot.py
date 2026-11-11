"""Render the example HTML plan to a PNG (device scale factor 2) and report the printed page count.

Needs Playwright with Chromium, which is not a dependency of the tool itself:
    python scripts/make_screenshot.py
"""

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "examples" / "output"
IMAGES = ROOT / "docs" / "images"


def main() -> int:
    IMAGES.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 794, "height": 1123}, device_scale_factor=2, color_scheme="light")
        page = ctx.new_page()
        for name, target in (("plan-monday", "day-plan-monday.png"), ("week-overview", "week-overview.png")):
            page.goto((OUT / f"{name}.html").as_uri())
            page.screenshot(path=str(IMAGES / target), full_page=True)
            pdf = page.pdf(prefer_css_page_size=True, print_background=True)
            pages = max(int(m) for m in re.findall(rb"/Count (\d+)", pdf))
            print(f"{name}: printed pages on A4 = {pages}")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

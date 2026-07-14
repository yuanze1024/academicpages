from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service


BASE_URL = os.environ.get("SITE_PREVIEW_URL", "http://127.0.0.1:4000")
ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
VIEWPORTS = {
    "mobile": {"width": 390, "height": 844},
    "tablet": {"width": 768, "height": 1024},
    "desktop": {"width": 1440, "height": 1000},
}


def main() -> None:
    ARTIFACTS.mkdir(exist_ok=True)
    os.environ.pop("BROWSER", None)
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    os.environ["no_proxy"] = "localhost,127.0.0.1"
    for screenshot in ARTIFACTS.glob("*.png"):
        screenshot.unlink()

    options = Options()
    options.add_argument("-headless")
    geckodriver = shutil.which("geckodriver")
    if not geckodriver:
        raise SystemExit("Visual checks require geckodriver on PATH")
    print("Starting headless Firefox...", flush=True)
    browser = webdriver.Firefox(
        options=options,
        service=Service(
            geckodriver,
            log_output=str(ARTIFACTS / "geckodriver.log"),
        ),
    )
    try:
        for name, viewport in VIEWPORTS.items():
            print(f"Checking {name} viewport...", flush=True)
            browser.set_window_size(viewport["width"], viewport["height"])
            browser.get(BASE_URL)
            browser.execute_script(
                "document.documentElement.style.scrollBehavior = 'auto'"
            )

            overflow = browser.execute_script(
                "return document.documentElement.scrollWidth - "
                "document.documentElement.clientWidth"
            )
            if overflow > 1:
                raise AssertionError(f"{name}: horizontal overflow is {overflow}px")

            for selector in (".site-header", "#page-title", "#publications", "#contact"):
                if not browser.find_element(By.CSS_SELECTOR, selector).is_displayed():
                    raise AssertionError(f"{name}: {selector} is not visible")

            browser.execute_script("window.scrollTo(0, 0)")
            top_screenshot = browser.get_screenshot_as_png()
            if not top_screenshot:
                raise AssertionError(f"{name}: Firefox returned an empty screenshot")
            (ARTIFACTS / f"homepage-{name}.png").write_bytes(top_screenshot)

            browser.find_element(
                By.CSS_SELECTOR, '.site-nav a[href="#publications"]'
            ).click()
            time.sleep(0.15)
            publications = browser.find_element(By.ID, "publications")
            section_top = publications.rect["y"] - browser.execute_script(
                "return window.scrollY"
            )
            header_bottom = browser.find_element(By.CSS_SELECTOR, ".site-header").rect[
                "height"
            ]
            print(
                f"{name}: publications top={section_top:.1f}, "
                f"header={header_bottom:.1f}",
                flush=True,
            )
            if section_top < header_bottom or section_top > header_bottom + 40:
                raise AssertionError(
                    f"{name}: publications anchor is not aligned below the header"
                )
            publication_screenshot = browser.get_screenshot_as_png()
            (ARTIFACTS / f"publications-{name}.png").write_bytes(
                publication_screenshot
            )
            print(f"Saved {name} screenshots.", flush=True)
    finally:
        browser.quit()


if __name__ == "__main__":
    main()

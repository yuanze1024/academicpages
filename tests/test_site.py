from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]


def build_site(output: Path) -> BeautifulSoup:
    subprocess.run(
        [sys.executable, str(ROOT / "site.py"), "build", "--output", str(output)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return BeautifulSoup((output / "index.html").read_text(encoding="utf-8"), "html.parser")


def test_build_renders_single_page_content(tmp_path: Path) -> None:
    output = tmp_path / "dist"
    soup = build_site(output)

    assert soup.select_one("h1").get_text(" ", strip=True) == "Yuan Ze (袁泽)"
    assert [section.get("id") for section in soup.select("main > section")] == [
        "top",
        "research",
        "publications",
        "background",
        "contact",
    ]
    assert [item.get("id") for item in soup.select("article.publication")] == [
        "publication-shaderagent",
        "publication-seqtex",
        "publication-texgen",
        "publication-vrdistill",
    ]
    assert "yz-_-1998" in soup.get_text(" ", strip=True)
    assert soup.select_one(".colorful-word").get("aria-label") == "colorful"
    assert soup.select_one(".bio a[href='https://xjqi.github.io/']")
    assert soup.select_one(".bio a[href='https://scse.buaa.edu.cn/info/1387/10322.htm']")
    # PDFs must be hosted elsewhere, not committed into this repo.
    assert not soup.select(
        'a[href$=".pdf"]:not([href*="arxiv"]):not([href*="github.com"][href*="/releases/"])'
    )


def test_generated_assets_and_internal_links_exist(tmp_path: Path) -> None:
    output = tmp_path / "dist"
    soup = build_site(output)

    for element in soup.select("[src], link[href], script[src]"):
        reference = element.get("src") or element.get("href")
        if not reference or not reference.startswith("/"):
            continue
        assert (output / reference.lstrip("/")).is_file(), reference

    ids = {element.get("id") for element in soup.select("[id]")}
    for anchor in soup.select('a[href^="#"]'):
        assert anchor["href"][1:] in ids


def test_output_has_no_legacy_routes(tmp_path: Path) -> None:
    output = tmp_path / "dist"
    build_site(output)

    assert not (output / "cv").exists()
    assert not (output / "publications").exists()
    assert not (output / "publication").exists()
    assert (output / "CNAME").read_text(encoding="utf-8").strip() == "yuanze.me"


def test_build_removes_stale_output(tmp_path: Path) -> None:
    output = tmp_path / "dist"
    stale = output / "cv" / "index.html"
    stale.parent.mkdir(parents=True)
    stale.write_text("legacy", encoding="utf-8")

    build_site(output)

    assert not stale.exists()

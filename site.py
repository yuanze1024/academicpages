#!/usr/bin/env python3
"""Build and preview the config-driven static website."""

from __future__ import annotations

import argparse
import shutil
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Literal

import yaml
import markdown as markdown_lib
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
TEMPLATE_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
DEFAULT_OUTPUT = ROOT / "dist"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Link(StrictModel):
    label: str = Field(min_length=1)
    url: HttpUrl


class Portrait(StrictModel):
    source: str
    alt: str = Field(min_length=1)


class Person(StrictModel):
    name: str
    native_name: str
    role: str
    affiliation: str
    affiliation_short: str
    location: str
    email: str
    wechat: str
    portrait: Portrait
    links: list[Link]


class SiteMetadata(StrictModel):
    title: str
    url: HttpUrl
    language: str
    description: str


class Intro(StrictModel):
    tagline_before: str
    tagline_colorful: str
    tagline_after: str
    bio: list[str] = Field(min_length=1)


class Research(StrictModel):
    current_title: str
    current: str
    previous_title: str
    previous: str
    thread: str


class Advisor(StrictModel):
    name: str
    url: HttpUrl


class Education(StrictModel):
    period: str
    sort_year: int = Field(ge=1900, le=2100)
    degree: str
    institution: str
    advisor: Advisor | None = None


class Experience(StrictModel):
    period: str
    sort_year: int = Field(ge=1900, le=2100)
    role: str
    organization: str
    detail: str


class Profile(StrictModel):
    site: SiteMetadata
    person: Person
    intro: Intro
    research: Research
    education: list[Education]
    experience: list[Experience]
    personal: str
    cv_pdf: str | None = None


class Author(StrictModel):
    name: str
    self: bool = False


class Highlight(StrictModel):
    label: str
    tone: Literal["blue", "green", "gold", "award"]


class Publication(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    date: date
    title: str
    cover_label: str
    cover_tone: Literal["blue", "green", "gold"]
    authors: list[Author] = Field(min_length=1)
    venue: str
    track: str
    highlights: list[Highlight] = Field(default_factory=list)
    summary: str
    image: str | None = None
    image_alt: str | None = None
    preview_image: str | None = None
    links: list[Link] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_image_alt(self) -> "Publication":
        if bool(self.image) != bool(self.image_alt):
            raise ValueError("image and image_alt must be provided together")
        return self


class PublicationData(StrictModel):
    publications: list[Publication]

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "PublicationData":
        ids = [publication.id for publication in self.publications]
        if len(ids) != len(set(ids)):
            raise ValueError("publication ids must be unique")
        return self


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return value


def safe_source_path(relative_path: str) -> Path:
    path = PurePosixPath(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe media path: {relative_path}")
    source = STATIC_DIR.joinpath(*path.parts)
    if not source.is_file():
        raise FileNotFoundError(f"Media file does not exist: {relative_path}")
    return source


def responsive_image(
    source_path: str,
    output_dir: Path,
    stem: str,
    widths: tuple[int, ...],
) -> dict:
    source = safe_source_path(source_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    variants: list[dict] = []

    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        original_width, original_height = image.size
        target_widths = sorted({min(width, original_width) for width in widths})

        for width in target_widths:
            height = round(original_height * width / original_width)
            resized = image if width == original_width else image.resize(
                (width, height), Image.Resampling.LANCZOS
            )
            filename = f"{stem}-{width}.webp"
            resized.save(output_dir / filename, "WEBP", quality=84, method=6)
            variants.append(
                {
                    "url": f"/assets/media/{filename}",
                    "width": width,
                    "height": height,
                }
            )

    largest = variants[-1]
    return {
        "src": largest["url"],
        "srcset": ", ".join(f'{item["url"]} {item["width"]}w' for item in variants),
        "width": largest["width"],
        "height": largest["height"],
    }


def build(output: Path = DEFAULT_OUTPUT) -> Path:
    profile = Profile.model_validate(load_yaml(DATA_DIR / "profile.yaml"))
    publication_data = PublicationData.model_validate(
        load_yaml(DATA_DIR / "publications.yaml")
    )

    if output.exists():
        shutil.rmtree(output)
    (output / "assets").mkdir(parents=True)

    shutil.copy2(STATIC_DIR / "site.css", output / "assets" / "site.css")
    shutil.copy2(STATIC_DIR / "site.js", output / "assets" / "site.js")
    shutil.copy2(STATIC_DIR / "favicon.svg", output / "favicon.svg")

    portrait = responsive_image(
        profile.person.portrait.source,
        output / "assets" / "media",
        "profile",
        (256, 512),
    )

    publications: list[dict] = []
    for publication in sorted(
        publication_data.publications, key=lambda item: item.date, reverse=True
    ):
        item = publication.model_dump(mode="json")
        item["year"] = publication.date.year
        item["primary_url"] = str(publication.links[0].url)
        item["project_url"] = next(
            (
                str(link.url)
                for link in publication.links
                if link.label.lower() == "project"
            ),
            item["primary_url"],
        )
        if publication.image:
            item["image_asset"] = responsive_image(
                publication.image,
                output / "assets" / "media",
                publication.id,
                (640, 960),
            )
        else:
            item["image_asset"] = None
        if publication.preview_image:
            preview_source = safe_source_path(publication.preview_image)
            preview_name = f"{publication.id}-preview{preview_source.suffix.lower()}"
            shutil.copy2(preview_source, output / "assets" / "media" / preview_name)
            item["preview_url"] = f"/assets/media/{preview_name}"
        else:
            item["preview_url"] = None
        publications.append(item)

    cv_url = None
    if profile.cv_pdf:
        cv_source = safe_source_path(profile.cv_pdf)
        cv_dir = output / "assets" / "files"
        cv_dir.mkdir(parents=True, exist_ok=True)
        cv_name = "yuan-ze-cv.pdf"
        shutil.copy2(cv_source, cv_dir / cv_name)
        cv_url = f"/assets/files/{cv_name}"

    profile_data = profile.model_dump(mode="json")
    profile_data["site"]["url"] = str(profile.site.url).rstrip("/")
    profile_data["person"]["links"] = [
        {"label": link.label, "url": str(link.url)} for link in profile.person.links
    ]
    profile_data["portrait_asset"] = portrait
    profile_data["cv_url"] = cv_url
    profile_data["current_year"] = date.today().year
    profile_data["intro"]["bio_html"] = [
        markdown_lib.markdown(paragraph) for paragraph in profile.intro.bio
    ]
    background = []
    for item in profile.education:
        background.append({"kind": "education", **item.model_dump(mode="json")})
    for item in profile.experience:
        background.append({"kind": "experience", **item.model_dump(mode="json")})
    profile_data["background"] = sorted(
        background, key=lambda item: item["sort_year"], reverse=True
    )

    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.get_template("index.html.j2")
    html = template.render(profile=profile_data, publications=publications)
    (output / "index.html").write_text(html, encoding="utf-8")

    site_url = profile_data["site"]["url"]
    (output / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n",
        encoding="utf-8",
    )
    (output / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{site_url}/</loc></url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )
    shutil.copy2(ROOT / "CNAME", output / "CNAME")
    return output


def serve(output: Path, host: str, port: int) -> None:
    try:
        from livereload import Server
    except ImportError as exc:
        raise SystemExit(
            "Local preview requires development dependencies: "
            "pip install -r requirements-dev.txt"
        ) from exc

    def rebuild() -> None:
        build(output)

    rebuild()
    server = Server()
    server.watch(str(DATA_DIR / "*.yaml"), rebuild)
    server.watch(str(TEMPLATE_DIR / "*.j2"), rebuild)
    server.watch(str(STATIC_DIR / "*"), rebuild)
    server.watch(str(STATIC_DIR / "**" / "*"), rebuild)
    print(f"Preview: http://localhost:{port}")
    server.serve(root=str(output), host=host, port=port, open_url_delay=None)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build the static site")
    build_parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)

    serve_parser = subparsers.add_parser("serve", help="Build and preview the site")
    serve_parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=4000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "build":
        output = build(args.output.resolve())
        print(f"Built site in {output}")
    else:
        serve(args.output.resolve(), args.host, args.port)


if __name__ == "__main__":
    main()

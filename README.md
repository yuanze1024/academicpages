# Yuan Ze — Academic Website

A single-page academic website generated from YAML with Python. The published
site is static HTML and does not run a Python server in production.

## Update content

- Edit `data/profile.yaml` for the bio, research interests, background, and contact details.
- Edit `data/publications.yaml` for publications and their links.
- Put future portraits, paper images, or the CV under `static/media/`, then reference the file from YAML.

Publication images are optional. When present, the build creates responsive
WebP files automatically; when absent, the page uses a typographic cover.

## Local preview

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python site.py serve
```

Open <http://localhost:4000>. Changes to YAML, templates, and styles rebuild
the preview automatically.

## Build and test

```bash
.venv/bin/python -m pytest
.venv/bin/python site.py build
```

The production-ready static site is written to `dist/`. GitHub Actions uses
the same commands and deploys that directory to GitHub Pages.

With the preview server running, optional Firefox screenshots and responsive
layout checks can be generated with `python tests/visual_check.py`. This command
requires Firefox and `geckodriver` on `PATH`.

#!/usr/bin/env python3
"""Generate robots.txt and sitemap.xml from application config."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ui.seo import write_static_seo_files


def main() -> None:
    write_static_seo_files()
    print("Wrote static/robots.txt and static/sitemap.xml")


if __name__ == "__main__":
    main()

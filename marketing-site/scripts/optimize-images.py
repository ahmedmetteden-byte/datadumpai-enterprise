#!/usr/bin/env python3
"""Optimize marketing-site public images for production (run from repo root)."""

from __future__ import annotations

import io
import shutil
from pathlib import Path

from PIL import Image

PUBLIC = Path(__file__).resolve().parents[1] / "public"
BACKUP = PUBLIC / ".optimize-backup"


def backup(path: Path) -> None:
    BACKUP.mkdir(exist_ok=True)
    dest = BACKUP / path.name
    if path.exists() and not dest.exists():
        shutil.copy2(path, dest)


def save_webp(im: Image.Image, path: Path, quality: int = 92, max_width: int | None = None) -> int:
    image = im.copy()
    if max_width and image.width > max_width:
        height = max(1, round(image.height * max_width / image.width))
        image = image.resize((max_width, height), Image.Resampling.LANCZOS)
    image.save(path, format="WEBP", quality=quality, method=6)
    return path.stat().st_size


def save_png(im: Image.Image, path: Path, max_width: int | None = None) -> int:
    image = im.copy()
    if image.mode not in ("RGBA", "RGB"):
        image = image.convert("RGBA")
    if max_width and image.width > max_width:
        height = max(1, round(image.height * max_width / image.width))
        image = image.resize((max_width, height), Image.Resampling.LANCZOS)
    image.save(path, format="PNG", optimize=True, compress_level=9)
    return path.stat().st_size


def optimize_logo_assets() -> None:
    for name in ("logo.png", "datadump-hero-logo.png"):
        src = PUBLIC / name
        backup_src = BACKUP / name
        if not backup_src.exists() and src.exists():
            backup(src)
        source = backup_src if backup_src.exists() else src
        if not source.exists():
            continue
        im = Image.open(source)
        webp_name = name.replace(".png", ".webp")
        webp_size = save_webp(im, PUBLIC / webp_name, quality=92, max_width=400)
        png_size = save_png(im, src, max_width=320)
        print(f"{name}: png={png_size // 1024}KB webp={webp_size // 1024}KB ({webp_name})")


def optimize_og_image() -> None:
    src = PUBLIC / "og-image.png"
    backup_src = BACKUP / "og-image.png"
    if not backup_src.exists() and src.exists():
        backup(src)
    source = backup_src if backup_src.exists() else src
    if not source.exists():
        return
    im = Image.open(source).convert("RGB")
    webp_size = save_webp(im, PUBLIC / "og-image.webp", quality=88)
    png_size = save_png(im, src)
    print(f"og-image: png={png_size // 1024}KB webp={webp_size // 1024}KB")


def optimize_favicon() -> None:
    src = PUBLIC / "favicon.png"
    if not src.exists():
        return
    backup(src)
    im = Image.open(src)
    # Keep crisp edges at native 32x32.
    size = save_png(im, src)
    print(f"favicon.png: {size // 1024}KB")


def main() -> None:
    optimize_logo_assets()
    optimize_og_image()
    optimize_favicon()
    print("Image optimization complete.")


if __name__ == "__main__":
    main()

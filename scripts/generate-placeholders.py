#!/usr/bin/env python3
"""Generates placeholder artwork for Jupiter distribution assets."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "packaging/jupiter-branding/files/plymouth/jupiter/logo.png"
SIZE = 512


def main() -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Gradient-ish disc: two concentric circles.
    draw.ellipse((16, 16, SIZE - 16, SIZE - 16), fill=(88, 102, 230, 255))
    draw.ellipse((48, 48, SIZE - 48, SIZE - 48), fill=(42, 47, 107, 255))
    try:
        font = ImageFont.load_default(size=220)
    except TypeError:  # Pillow < 10.1 has no sized default font
        font = ImageFont.load_default()
    text = "J"
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    x = (SIZE - (right - left)) / 2 - left
    y = (SIZE - (bottom - top)) / 2 - top
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, format="PNG")
    print(f"wrote {OUT.relative_to(ROOT)} ({SIZE}x{SIZE})")


if __name__ == "__main__":
    main()

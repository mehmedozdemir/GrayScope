"""Generate assets/grayscope.ico from scratch using Pillow.

Run once before building the installer:
    python scripts/generate_icon.py

Produces a multi-resolution ICO file (16, 32, 48, 64, 128, 256 px).
The design: dark-navy rounded square, white magnifying-glass, teal accent ring.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

# Brand colours (match ui/theme.py dark palette)
BG       = (15,  17,  23, 255)   # #0F1117
SURFACE  = (26,  29,  39, 255)   # #1A1D27
ACCENT   = (91, 138, 240, 255)   # #5B8AF0
WHITE    = (240, 242, 255, 255)  # #F0F2FF
TEAL     = (76, 175, 128, 255)   # #4CAF80


def _rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill) -> None:
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size

    # Background rounded square
    pad = max(1, s // 16)
    radius = max(4, s // 5)
    _rounded_rect(d, [pad, pad, s - pad - 1, s - pad - 1], radius, SURFACE)

    # Accent border (thin ring)
    bw = max(1, s // 32)
    _rounded_rect(d, [pad, pad, s - pad - 1, s - pad - 1], radius, ACCENT)
    _rounded_rect(d, [pad + bw, pad + bw, s - pad - bw - 1, s - pad - bw - 1],
                  radius - bw, SURFACE)

    # Magnifying glass
    cx = int(s * 0.42)
    cy = int(s * 0.42)
    r_outer = int(s * 0.26)
    lw = max(2, s // 14)

    # Circle (draw as filled then inner cutout)
    d.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], fill=WHITE)
    inner_r = r_outer - lw
    d.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=SURFACE)

    # Handle (45° lower-right)
    angle = math.radians(45)
    hx0 = int(cx + r_outer * math.cos(angle))
    hy0 = int(cy + r_outer * math.sin(angle))
    handle_len = int(s * 0.24)
    hx1 = int(hx0 + handle_len * math.cos(angle))
    hy1 = int(hy0 + handle_len * math.sin(angle))
    d.line([hx0, hy0, hx1, hy1], fill=WHITE, width=lw)

    # Small accent dot inside the lens (symbolises a log entry)
    dot_r = max(1, s // 14)
    d.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=ACCENT)

    return img


def main() -> None:
    out = Path(__file__).parent.parent / "assets" / "grayscope.ico"
    out.parent.mkdir(parents=True, exist_ok=True)

    sizes = [16, 32, 48, 64, 128, 256]
    frames = [draw_icon(s).convert("RGBA") for s in sizes]

    # Save as multi-resolution ICO
    frames[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"Icon written: {out}  ({len(sizes)} resolutions)")


if __name__ == "__main__":
    main()

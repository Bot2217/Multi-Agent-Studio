"""Draw the Улей mark: a charcoal tile and a small honeycomb."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "icons" / "ulei-1024.png"

# Graphite tile, lime and honey cells. Same colors as the app palettes.
TILE = (13, 14, 18, 255)
LIME = (194, 242, 78, 255)
HONEY = (224, 161, 90, 255)
MINT = (155, 224, 184, 255)
PAPER = (238, 240, 244, 255)


def axial(cx: float, cy: float, radius: float, q: int, row: int) -> tuple[float, float]:
    x = cx + radius * math.sqrt(3) * (q + row / 2)
    y = cy + radius * 1.5 * row
    return x, y


def hexagon(cx: float, cy: float, radius: float) -> list[tuple[float, float]]:
    return [
        (
            cx + radius * math.cos(math.radians(60 * i - 90)),
            cy + radius * math.sin(math.radians(60 * i - 90)),
        )
        for i in range(6)
    ]


def draw(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)
    margin = size * 0.06
    pen.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=size * 0.22,
        fill=TILE,
    )
    radius = size * 0.115
    cells = [
        (0, 0, LIME),
        (1, 0, HONEY),
        (-1, 0, MINT),
        (0, -1, PAPER),
        (1, -1, LIME),
        (-1, 1, HONEY),
        (0, 1, PAPER),
    ]
    for q, row, color in cells:
        cx, cy = axial(size / 2, size / 2, radius, q, row)
        pen.polygon(hexagon(cx, cy, radius * 0.9), fill=color)
    return image


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    master = draw(1024)
    master.save(OUT)
    for size in (16, 32, 128, 256, 512):
        master.resize((size, size), Image.Resampling.LANCZOS).save(
            OUT.with_name(f"ulei-{size}.png")
        )


if __name__ == "__main__":
    main()

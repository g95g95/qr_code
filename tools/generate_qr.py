#!/usr/bin/env python3
"""Genera il QR code (SVG + PNG) che punta alla landing page del menu.

Uso:
    python3 tools/generate_qr.py [--url URL] [--out-dir assets]

Note sulla leggibilita':
  * correzione errore H (30%): il codice resta leggibile anche stampato male,
    piegato o sporco di sugo;
  * i moduli sono arrotondati ma **contigui** (nessun gap): l'arrotondamento
    estremo "a pois" fa fallire i decoder piu' severi;
  * gli occhi (finder pattern) hanno un raggio massimo di 1 modulo. Oltre
    ~1.2 moduli i decoder non riconoscono piu' il pattern di ricerca.
  * tools/test_qr.py verifica il decode a varie scale/sfocature.
"""

from __future__ import annotations

import argparse
import os

import segno
from PIL import Image, ImageDraw

DEFAULT_URL = "https://g95g95.github.io/qr_code/"

# Palette festa: bordeaux profondo -> rosso caldo -> oro
DARK_TOP = (92, 21, 51)
DARK_BOTTOM = (176, 58, 46)
GOLD = (224, 160, 51)
LIGHT = (255, 251, 242)

MODULE_RADIUS = 0.35  # frazione del modulo
EYE_RADIUS = 1.0  # in moduli (max sicuro ~1.2)


def matrix_of(url: str) -> list[list[int]]:
    qr = segno.make(url, error="h", boost_error=False)
    return [[int(bit) for bit in row] for row in qr.matrix]


def is_finder(row: int, col: int, size: int) -> bool:
    """True se il modulo appartiene a uno dei tre occhi 7x7."""
    for base_r, base_c in ((0, 0), (0, size - 7), (size - 7, 0)):
        if base_r <= row < base_r + 7 and base_c <= col < base_c + 7:
            return True
    return False


def eye_origins(size: int) -> tuple:
    return ((0, 0), (0, size - 7), (size - 7, 0))


def vertical_gradient(size: int) -> Image.Image:
    """Gradiente verticale bordeaux -> rosso -> oro."""
    stops = ((0.0, DARK_TOP), (0.6, DARK_BOTTOM), (1.0, GOLD))
    grad = Image.new("RGB", (1, size))
    px = grad.load()
    for y in range(size):
        t = y / max(size - 1, 1)
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                k = (t - t0) / (t1 - t0)
                px[0, y] = tuple(round(c0[j] + (c1[j] - c0[j]) * k) for j in range(3))
                break
    return grad.resize((size, size), Image.BICUBIC)


def render_png(matrix, path: str, module_px: int = 20, quiet: int = 4) -> None:
    size = len(matrix)
    canvas_px = (size + quiet * 2) * module_px
    mask = Image.new("L", (canvas_px, canvas_px), 0)
    md = ImageDraw.Draw(mask)
    mod_r = int(module_px * MODULE_RADIUS)
    eye_r = module_px * EYE_RADIUS

    for r, row in enumerate(matrix):
        for c, bit in enumerate(row):
            if not bit or is_finder(r, c, size):
                continue
            x0 = (c + quiet) * module_px
            y0 = (r + quiet) * module_px
            md.rounded_rectangle(
                (x0, y0, x0 + module_px - 1, y0 + module_px - 1),
                radius=mod_r,
                fill=255,
            )

    for base_r, base_c in eye_origins(size):
        x0 = (base_c + quiet) * module_px
        y0 = (base_r + quiet) * module_px
        outer = 7 * module_px
        md.rounded_rectangle(
            (x0, y0, x0 + outer - 1, y0 + outer - 1), radius=int(eye_r), fill=255
        )
        md.rounded_rectangle(
            (
                x0 + module_px,
                y0 + module_px,
                x0 + outer - module_px - 1,
                y0 + outer - module_px - 1,
            ),
            radius=int(eye_r * 0.7),
            fill=0,
        )
        md.rounded_rectangle(
            (
                x0 + 2 * module_px,
                y0 + 2 * module_px,
                x0 + 5 * module_px - 1,
                y0 + 5 * module_px - 1,
            ),
            radius=int(eye_r * 0.45),
            fill=255,
        )

    base = Image.new("RGB", (canvas_px, canvas_px), LIGHT)
    base.paste(vertical_gradient(canvas_px), (0, 0), mask)
    base.save(path, format="PNG", optimize=True)


def render_svg(matrix, path: str, module: int = 12, quiet: int = 4) -> None:
    size = len(matrix)
    total = (size + quiet * 2) * module
    mod_r = module * MODULE_RADIUS
    eye_r = module * EYE_RADIUS
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" '
        f'width="{total}" height="{total}" role="img" '
        f'aria-label="QR code che apre il menu del pranzo">',
        "<defs>"
        '<linearGradient id="festa" x1="0" y1="0" x2="0.3" y2="1">'
        f'<stop offset="0" stop-color="rgb{DARK_TOP}"/>'
        f'<stop offset="0.6" stop-color="rgb{DARK_BOTTOM}"/>'
        f'<stop offset="1" stop-color="rgb{GOLD}"/>'
        "</linearGradient></defs>",
        f'<rect width="{total}" height="{total}" fill="rgb{LIGHT}"/>',
        '<g fill="url(#festa)">',
    ]

    for row_i, row in enumerate(matrix):
        for col_i, bit in enumerate(row):
            if not bit or is_finder(row_i, col_i, size):
                continue
            x = (col_i + quiet) * module
            y = (row_i + quiet) * module
            parts.append(
                f'<rect x="{x}" y="{y}" width="{module}" height="{module}" '
                f'rx="{mod_r:.2f}"/>'
            )

    for base_r, base_c in eye_origins(size):
        x = (base_c + quiet) * module
        y = (base_r + quiet) * module
        outer = 7 * module
        parts.append(
            f'<rect x="{x}" y="{y}" width="{outer}" height="{outer}" '
            f'rx="{eye_r:.2f}"/>'
        )
        parts.append(
            f'<rect x="{x + module}" y="{y + module}" width="{outer - 2 * module}" '
            f'height="{outer - 2 * module}" rx="{eye_r * 0.7:.2f}" fill="rgb{LIGHT}"/>'
        )
        parts.append(
            f'<rect x="{x + 2 * module}" y="{y + 2 * module}" width="{3 * module}" '
            f'height="{3 * module}" rx="{eye_r * 0.45:.2f}"/>'
        )

    parts.append("</g></svg>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--out-dir", default="assets")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    matrix = matrix_of(args.url)

    png_path = os.path.join(args.out_dir, "qr-menu.png")
    svg_path = os.path.join(args.out_dir, "qr-menu.svg")
    render_png(matrix, png_path)
    render_svg(matrix, svg_path)

    print(f"URL      : {args.url}")
    print(f"Matrice  : {len(matrix)}x{len(matrix)} moduli (ECC H)")
    print(f"PNG      : {png_path}")
    print(f"SVG      : {svg_path}")


if __name__ == "__main__":
    main()

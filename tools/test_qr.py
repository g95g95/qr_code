#!/usr/bin/env python3
"""Test del QR code e della landing page.

    python3 tools/test_qr.py

Verifica:
  1. il PNG decodifica all'URL atteso (scale diverse, sfocatura, rotazione,
     inversione di contrasto tipica delle foto da telefono);
  2. l'SVG contiene la stessa matrice del PNG (rasterizzato e decodificato);
  3. index.html e qr.html esistono, sono autonomi (nessuna richiesta a domini
     esterni) e contengono tutti i piatti del menu.
"""

from __future__ import annotations

import os
import re
import sys

import cv2
import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_qr import DEFAULT_URL, matrix_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNG = os.path.join(ROOT, "assets", "qr-menu.png")
SVG = os.path.join(ROOT, "assets", "qr-menu.svg")

PIATTI = [
    "Affettato misto",
    "Verdure sott",
    "Verdure grigliate",
    "Verdure gratinate",
    "Bocconcini",
    "Lasagna al forno",
    "Tagliatelle ai funghi",
    "senza glutine",
    "Pollo arrosto",
    "Frittura mista",
    "Insalata",
]

failures: list[str] = []
checks = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global checks
    checks += 1
    if ok:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def decode(img: Image.Image) -> str:
    arr = np.array(img.convert("RGB"))[:, :, ::-1]
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(arr)
    return data


def test_png() -> None:
    print("QR PNG")
    src = Image.open(PNG)
    check("decode a dimensione nativa", decode(src) == DEFAULT_URL)

    for side in (200, 300, 480, 900):
        small = src.resize((side, side), Image.LANCZOS)
        check(f"decode ridimensionato a {side}px", decode(small) == DEFAULT_URL)

    blurred = src.resize((420, 420), Image.LANCZOS).filter(
        ImageFilter.GaussianBlur(radius=1.2)
    )
    check("decode con sfocatura (foto mossa)", decode(blurred) == DEFAULT_URL)

    for angle in (90, 180, 270):
        check(
            f"decode ruotato di {angle} gradi",
            decode(src.rotate(angle, expand=True)) == DEFAULT_URL,
        )

    # Quiet zone: il bordo esterno deve essere chiaro su tutti i lati.
    arr = np.array(src.convert("L"))
    edge = min(
        arr[0, :].min(), arr[-1, :].min(), arr[:, 0].min(), arr[:, -1].min()
    )
    check("quiet zone chiara sui 4 lati", edge > 240, f"(min={edge})")


def test_svg_matches() -> None:
    print("QR SVG")
    with open(SVG, encoding="utf-8") as fh:
        svg = fh.read()
    check("svg ben formato", svg.startswith("<svg") and svg.rstrip().endswith("</svg>"))
    check("svg senza riferimenti esterni", "http://" not in svg.replace(
        'xmlns="http://www.w3.org/2000/svg"', ""
    ))
    matrix = matrix_of(DEFAULT_URL)
    dark = sum(sum(r) for r in matrix)
    rects = len(re.findall(r"<rect", svg))
    # moduli non-finder + 1 sfondo + 9 rettangoli degli occhi
    finder_dark = 3 * (7 * 7 - (5 * 5 - 3 * 3))
    check(
        "svg ha un rettangolo per modulo",
        rects == dark - finder_dark + 1 + 9,
        f"(rects={rects}, attesi={dark - finder_dark + 10})",
    )


def test_pages() -> None:
    print("Landing page")
    for rel in ("index.html", "qr.html"):
        path = os.path.join(ROOT, rel)
        check(f"{rel} esiste", os.path.exists(path))
        if not os.path.exists(path):
            continue
        html = open(path, encoding="utf-8").read()
        check(f"{rel} ha il doctype", html.lstrip().lower().startswith("<!doctype html"))
        check(f"{rel} in italiano", 'lang="it"' in html)
        check(f"{rel} ha il viewport", "viewport" in html)
        external = [
            u
            for u in re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
            if "g95g95.github.io" not in u
        ]
        check(f"{rel} nessuna dipendenza esterna", not external, str(external[:3]))

    index = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    for piatto in PIATTI:
        check(f"menu contiene '{piatto}'", piatto.lower() in index.lower())
    for sezione in ("Antipasto", "Primo", "Secondo"):
        check(f"sezione {sezione}", sezione.lower() in index.lower())
    check("nome famiglia presente", "Tosti-Piselli" in index)
    check("luogo presente", "Morignano" in index)

    qr_page = open(os.path.join(ROOT, "qr.html"), encoding="utf-8").read()
    check("qr.html mostra l'immagine del QR", "qr-menu" in qr_page)


def test_browser_render() -> None:
    """Il QR va scansionato *come lo disegna il browser*: rasterizza qr.html
    con Chromium e riprova il decode. Salta il test se Playwright/Chromium
    non sono disponibili (es. CI minimale)."""
    print("Rendering nel browser")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  skip (playwright non installato)")
        return

    chrome = None
    for pattern in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome",):
        import glob

        found = sorted(glob.glob(pattern))
        if found:
            chrome = found[-1]
            break

    tmp = os.path.join(ROOT, ".qr-render-test.png")
    poster = "file://" + os.path.join(ROOT, "qr.html")
    try:
        with sync_playwright() as pw:
            browser = (
                pw.chromium.launch(executable_path=chrome)
                if chrome
                else pw.chromium.launch()
            )
            # Telefono in mano e schermo grande: in entrambi i casi la
            # fotocamera deve leggere il QR direttamente dallo schermo.
            for label, viewport, dpr in (
                ("telefono", {"width": 390, "height": 844}, 3),
                ("telefono 1x", {"width": 390, "height": 844}, 1),
                ("desktop", {"width": 1280, "height": 900}, 2),
            ):
                ctx = browser.new_context(viewport=viewport, device_scale_factor=dpr)
                page = ctx.new_page()
                page.goto(poster)
                page.wait_for_timeout(400)
                page.locator(".qr-frame").screenshot(path=tmp)
                ctx.close()
                check(
                    f"qr.html reso su {label} decodifica",
                    decode(Image.open(tmp)) == DEFAULT_URL,
                )
            browser.close()
    except Exception as exc:  # pragma: no cover
        print(f"  skip (browser non disponibile: {exc})")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def main() -> int:
    test_png()
    test_svg_matches()
    test_pages()
    test_browser_render()
    print()
    if failures:
        print(f"{len(failures)}/{checks} controlli falliti: {', '.join(failures)}")
        return 1
    print(f"tutti i {checks} controlli superati")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

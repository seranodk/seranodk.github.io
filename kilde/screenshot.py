#!/usr/bin/env python3
"""Tager et ingame-skærmbillede af et spil og gemmer det som et kvadratisk ikon.

Fremgangsmåde: åbn spillet som på en mobil, tryk på den første knap der ligner
"Start"/"Spil"/"Hurtig kamp", lad spillet køre et par sekunder, og klip det
største <canvas> ud (det er normalt selve spillebanen).

Brug: python3 kilde/screenshot.py <url> <ud.webp>
"""
import io
import re
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

START = re.compile(r"start|spil|hurtig|play|kamp|begynd|^go$|new game|nyt spil", re.I)
SKIP = re.compile(r"indstil|setting|lyd|sound|fuld|menu|pause|tilbage|back|hjælp|help|styring|control|regler|om\b|tema|theme", re.I)
SIZE = 480


def _click_start(page):
    for b in page.query_selector_all("button, [role=button], a.btn, .btn, .tile"):
        try:
            if not b.is_visible():
                continue
            label = " ".join(filter(None, [b.inner_text(), b.get_attribute("id"), b.get_attribute("aria-label")]))
        except Exception:
            continue
        if START.search(label) and not SKIP.search(label):
            try:
                b.click(timeout=2000)
                return True
            except Exception:
                continue
    return False


def _largest_canvas(page):
    best = None
    for c in page.query_selector_all("canvas"):
        box = c.bounding_box()
        if box and box["width"] > 50 and box["height"] > 50:
            if not best or box["width"] * box["height"] > best["width"] * best["height"]:
                best = box
    return best


def take(url, out, wait_ms=2500):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                                is_mobile=True, has_touch=True)
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1000)
        for _ in range(3):  # menuer kan have et par trin før selve kampen
            if not _click_start(page):
                break
            page.wait_for_timeout(800)
        box = _largest_canvas(page)
        page.keyboard.press("Space")  # sender kuglen afsted o.l.
        if box:
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] * 0.85)
        page.wait_for_timeout(wait_ms)
        box = _largest_canvas(page) or box
        png = page.screenshot()
        browser.close()

    im = Image.open(io.BytesIO(png)).convert("RGB")
    if box:
        im = im.crop(tuple(int(v * 2) for v in (box["x"], box["y"], box["x"] + box["width"], box["y"] + box["height"])))
    w, h = im.size
    ratio = w / h
    if 0.7 <= ratio <= 1.4:  # næsten kvadratisk: læg en kant om, så hele banen ses
        side = max(w, h)
        sq = Image.new("RGB", (side, side), im.getpixel((2, 2)))
        sq.paste(im, ((side - w) // 2, (side - h) // 2))
        im = sq
    else:  # aflang: klip et kvadrat ud af midten
        side = min(w, h)
        left, top = (w - side) // 2, (h - side) // 2
        im = im.crop((left, top, left + side, top + side))
    im.resize((SIZE, SIZE), Image.LANCZOS).save(out, "WEBP", quality=82)


if __name__ == "__main__":
    take(sys.argv[1], sys.argv[2])

#!/usr/bin/env python3
"""Tager et ingame-skærmbillede af et spil og gemmer det som et kvadratisk ikon.

Fremgangsmåde: åbn spillet som på en mobil, tryk dig gennem menuen med de knapper
der ligner "Start"/"Hurtig kamp"/"Opvisning", lad spillet køre et par sekunder,
og klip det største <canvas> ud (det er normalt selve spillebanen).

Brug: python3 kilde/screenshot.py <url> <ud.webp>
"""
import io
import re
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

STRONG = re.compile(r"\bstart|\bplay\b|begynd|opvisning|hurtig kamp|quick match|nyt spil|new game|^go$", re.I)
WEAK = re.compile(r"spil|kamp|hurtig", re.I)
SKIP = re.compile(r"indstil|setting|lyd|sound|fuld|menu|pause|tilbage|back|hjælp|help|styring|control|regler|om\b|tema|theme|omkamp|fortsæt|resume|turnering|tournament", re.I)
SIZE = 480


def _click_start(page):
    """Klik på den knap, der mest ligner "start": tydelige start-ord først
    (helst på den fremhævede knap), så den fremhævede knap, så svagere ord."""
    ranked = []
    for b in page.query_selector_all("button, [role=button], a.btn, .btn, .tile"):
        try:
            if not b.is_visible():
                continue
            label = " ".join(" ".join(filter(None, [b.inner_text(), b.get_attribute("aria-label")])).split())
            ident = b.get_attribute("id") or ""
            cls = b.get_attribute("class") or ""
        except Exception:
            continue
        if SKIP.search(label):
            continue
        primary = bool(re.search(r"primary|main|cta", cls, re.I))
        if STRONG.search(label):
            rank = 0 if primary else 1
        elif primary:
            rank = 2
        elif WEAK.search(label) or re.search(r"start|play|hur", ident, re.I):
            rank = 3
        else:
            continue
        ranked.append((rank, len(ranked), b))
    for _, _, b in sorted(ranked, key=lambda t: t[:2]):
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
        for _ in range(4):  # menuer kan have et par trin før selve kampen
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
    if 0.7 <= w / h <= 1.4:  # næsten kvadratisk: læg en kant om, så hele banen ses
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

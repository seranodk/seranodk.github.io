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
    """Spillebanen: det største <canvas> eller den største "bræt"-agtige blok
    (fx et gitter af kort i et vendespil). Gennemsigtige overlays tæller ikke."""
    return page.evaluate("""() => {
      const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
        return r.width > 50 && r.height > 50 && s.visibility !== 'hidden' && s.display !== 'none' ? r : null; };
      const cand = [...document.querySelectorAll('canvas')];
      document.querySelectorAll('[id*=board],[class*=board],[id*=grid],[class*=grid]').forEach(e => cand.push(e));
      document.querySelectorAll('body *').forEach(e => {
        const k = e.children; if (k.length >= 8 && [...k].every(c => c.tagName === k[0].tagName)) cand.push(e); });
      let best = null;
      for (const e of cand) { const r = vis(e); if (!r) continue;
        if (e.tagName === 'CANVAS' && getComputedStyle(e).position === 'fixed' && r.height < innerHeight * 0.5) continue;
        const a = r.width * r.height; if (!best || a > best.a) best = {x: r.x, y: r.y, width: r.width, height: r.height, a}; }
      return best; }""")


def take(url, out, wait_ms=2500, opts=None):
    """opts (fra "skaermbilleder" i spil.json) kan styre et bestemt spil:
       klik:     liste af CSS-selektorer, der trykkes på i rækkefølge (i stedet for at gætte)
       taster:   taster, der holdes nede under spillet, fx ["ArrowUp"] for at give gas
       ventetid: millisekunder spillet kører, før billedet tages
       udsnit:   0 = top, 0.5 = midten, 1 = bund, når billedet skal klippes til et kvadrat
       knapper:  true = lad knapper og tekst over spillet blive stående
       liggende: true = tag billedet med telefonen på tværs (844×390)"""
    opts = opts or {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        vp = {"width": 844, "height": 390} if opts.get("liggende") else {"width": 390, "height": 844}
        page = browser.new_page(viewport=vp, device_scale_factor=2, is_mobile=True, has_touch=True)
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1000)
        if opts.get("klik"):
            for sel in opts["klik"]:
                try:
                    page.click(sel, timeout=3000)
                except Exception as e:
                    print("  kunne ikke trykke på", sel, "-", str(e)[:60])
                page.wait_for_timeout(800)
        else:
            for _ in range(4):  # menuer kan have et par trin før selve kampen
                if not _click_start(page):
                    break
                page.wait_for_timeout(800)
        box = _largest_canvas(page)
        if opts.get("taster"):
            for k in opts["taster"]:
                page.keyboard.down(k)
        elif not opts.get("klik"):
            page.keyboard.press("Space")  # sender kuglen afsted o.l.
            if box:
                page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] * 0.85)
        page.wait_for_timeout(opts.get("ventetid", wait_ms))
        box = _largest_canvas(page) or box
        if box and not opts.get("knapper") and page.evaluate("""() => {
              const c = [...document.querySelectorAll('canvas')].sort((a, b) =>
                b.getBoundingClientRect().width * b.getBoundingClientRect().height -
                a.getBoundingClientRect().width * a.getBoundingClientRect().height)[0];
              return !!c && c.getBoundingClientRect().width * c.getBoundingClientRect().height >= innerWidth * innerHeight * 0.5; }"""):
            # spillet tegnes på et canvas: skjul knapper, joystick og tekst ovenpå
            page.add_style_tag(content="*{visibility:hidden!important} canvas{visibility:visible!important}")
            page.wait_for_timeout(100)
        png = page.screenshot()
        vw, vh = page.viewport_size["width"], page.viewport_size["height"]
        browser.close()

    im = Image.open(io.BytesIO(png)).convert("RGB")
    if box:  # kun den del af banen, der faktisk er på skærmen
        x0, y0 = max(0, box["x"]), max(0, box["y"])
        x1, y1 = min(vw, box["x"] + box["width"]), min(vh, box["y"] + box["height"])
        im = im.crop(tuple(int(v * 2) for v in (x0, y0, x1, y1)))
    w, h = im.size
    pos = opts.get("udsnit", 0.5)
    if 0.7 <= w / h <= 1.4:  # næsten kvadratisk: læg en kant om, så hele banen ses
        side = max(w, h)
        sq = Image.new("RGB", (side, side), im.getpixel((2, 2)))
        sq.paste(im, ((side - w) // 2, (side - h) // 2))
        im = sq
    else:  # aflang: klip et kvadrat ud
        side = min(w, h)
        left, top = int((w - side) * pos), int((h - side) * pos)
        im = im.crop((left, top, left + side, top + side))
    im.resize((SIZE, SIZE), Image.LANCZOS).save(out, "WEBP", quality=82)


if __name__ == "__main__":
    take(sys.argv[1], sys.argv[2])

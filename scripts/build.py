#!/usr/bin/env python3
"""Twilight Garden profile builder.

Fetches the GitHub contribution calendar + public repos for USER and renders
self-contained SVGs (banner, wisteria tree, dividers, repo cards) into ./assets,
then refreshes the repo list inside README.md (between the REPOS markers).
Standard library only.
"""
import html, json, math, os, random, re, textwrap, urllib.request
from datetime import datetime
from pathlib import Path

USER = os.environ.get("GH_USER", "Zhymalineir")
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
TOKEN = os.environ.get("GITHUB_TOKEN")
SERIF = "Georgia, 'Palatino Linotype', 'Times New Roman', serif"
MONO = "'Cascadia Mono', Consolas, 'SF Mono', Menlo, monospace"

CSS = """
.tw{animation:tw 4s ease-in-out infinite}
@keyframes tw{0%,100%{opacity:.2}50%{opacity:1}}
.sw{animation:sw 7s ease-in-out infinite}
@keyframes sw{0%,100%{transform:rotate(-1.5deg)}50%{transform:rotate(1.5deg)}}
.gl{animation:gl 3.6s ease-in-out infinite}
@keyframes gl{0%,100%{opacity:.55}50%{opacity:1}}
.fl{animation:fl 14s linear infinite;opacity:0}
@keyframes fl{0%{opacity:0;transform:translate(0,0) rotate(0)}10%{opacity:.9}85%{opacity:.8}
100%{opacity:0;transform:translate(-70px,330px) rotate(200deg)}}
.rp{animation:rp 6s ease-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes rp{0%{transform:scale(.3);opacity:.7}100%{transform:scale(1.6);opacity:0}}
.bk{animation:bk 1.1s steps(1) infinite}
@keyframes bk{50%{opacity:0}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


# ---------------------------------------------------------------- helpers
def get(url, api=False):
    h = {"User-Agent": "twilight-garden-readme"}
    if api:
        h["Accept"] = "application/vnd.github+json"
        if TOKEN:
            h["Authorization"] = f"Bearer {TOKEN}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
        return r.read().decode("utf-8")


def lerp_hex(a, b, t):
    a = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def petal(r):
    """Teardrop petal hanging downward, centred on (0,0)."""
    return (f"M0,{-r:.1f}C{r*.9:.1f},{-r*.9:.1f} {r*.8:.1f},{r*.8:.1f} 0,{r*1.7:.1f}"
            f"C{-r*.8:.1f},{r*.8:.1f} {-r*.9:.1f},{-r*.9:.1f} 0,{-r:.1f}Z")


def stars(rng, w, h, n):
    out = []
    for _ in range(n):
        x, y = rng.uniform(8, w - 8), rng.uniform(6, h)
        r = rng.choice([.7, .9, 1.1, 1.5])
        out.append(f'<circle class="tw" style="animation-delay:-{rng.uniform(0,4):.1f}s;'
                   f'animation-duration:{rng.uniform(2.8,6):.1f}s" cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#efe6ff"/>')
    return "".join(out)


def sprig(x, y, length, rng, n=8, r=4.6):
    """A little hanging wisteria raceme (decorative)."""
    pts, parts = [], []
    for k in range(n):
        t = (k + .5) / n
        py = y + t * length
        px = x + 3 * math.sin(k * 1.3 + x)
        pts.append((px, py))
        rr = r * (1 - .55 * t)
        col = lerp_hex("#6f52c8", "#c9a6ff", t)
        parts.append(f'<path d="{petal(rr)}" transform="translate({px:.1f},{py:.1f})" fill="{col}" opacity=".9"/>')
        parts.append(f'<path d="{petal(rr*.6)}" transform="translate({px+rng.uniform(-4,4):.1f},{py+length/n/2:.1f})" fill="{col}" opacity=".45"/>')
    line = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in [(x, y)] + pts)
    return (f'<g class="sw" style="transform-origin:{x:.0f}px {y:.0f}px;animation-delay:-{rng.uniform(0,7):.1f}s">'
            f'<path d="{line}" stroke="#3f2d73" stroke-width="1" fill="none"/>{"".join(parts)}</g>')


def svg_open(w, h, extra_defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<style>{CSS}</style><defs>{extra_defs}</defs>')


SKY = ('<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
       '<stop offset="0" stop-color="#0c0824"/><stop offset=".45" stop-color="#241250"/>'
       '<stop offset=".8" stop-color="#5a2a7c"/><stop offset="1" stop-color="#b24f8f"/></linearGradient>')

# ---------------------------------------------------------------- banner
FONT = {  # name font: (first_row, rows) on a 9-row grid, 5 px wide
    "Z": (0, ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"]),
    "h": (0, ["#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"]),
    "y": (2, ["#...#", "#...#", "#...#", "#...#", ".####", "....#", ".###."]),
    "m": (2, ["##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"]),
    "a": (2, [".###.", "....#", ".####", "#...#", ".####"]),
    "l": (0, [".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."]),
    "i": (0, ["..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."]),
    "n": (2, ["####.", "#...#", "#...#", "#...#", "#...#"]),
    "e": (2, [".###.", "#...#", "#####", "#....", ".####"]),
    "r": (2, ["#.##.", "##..#", "#....", "#....", "#...."]),
}


def ascii_name(name):
    grid = [""] * 9
    for ch in name:
        top, rows = FONT[ch]
        for r in range(9):
            row = rows[r - top] if top <= r < top + len(rows) else "....."
            grid[r] += "".join("##" if c == "#" else "  " for c in row) + "  "
    return [g.rstrip() for g in grid]


def banner(bio, bg=True):
    W, H = 960, 372
    cw, lh, fs = 6.2, 13.2, 11
    art = ascii_name("Zhymalineir")
    art_w = max(len(a) for a in art)
    cols = art_w + 14
    x0 = (W - cols * cw) / 2
    y0 = 104
    rng = random.Random(3)

    def ty(line):
        return y0 + line * lh + fs

    out = [svg_open(
        W, H,
        SKY + f'<linearGradient id="ag" gradientUnits="userSpaceOnUse" x1="{x0+7*cw:.0f}" y1="0" x2="{x0+(art_w+7)*cw:.0f}" y2="0">'
        '<stop offset="0" stop-color="#ffc2ee"/><stop offset=".5" stop-color="#c39bff"/>'
        '<stop offset="1" stop-color="#8a7cff"/></linearGradient>'
        '<filter id="bl" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="5"/></filter>'
        '<mask id="mm"><rect width="960" height="372" fill="#fff"/><circle cx="873" cy="42" r="17" fill="#000"/></mask>'),
        (f'<rect width="{W}" height="{H}" rx="16" fill="url(#sky)"/>' if bg else ''),
        stars(rng, W, 120, 60),
        '<circle cx="860" cy="48" r="20" fill="#fff0cf" mask="url(#mm)"/>',
        f'<rect x="{x0-14:.0f}" y="{y0-34}" width="{cols*cw+28:.0f}" height="{lh*18+46:.0f}" rx="12" fill="#0b0720" fill-opacity=".72" stroke="#7d5bd0" stroke-opacity=".5"/>',
        f'<circle cx="{x0+6:.0f}" cy="{y0-17}" r="4.5" fill="#ff8fb8"/><circle cx="{x0+22:.0f}" cy="{y0-17}" r="4.5" fill="#ffd28f"/><circle cx="{x0+38:.0f}" cy="{y0-17}" r="4.5" fill="#b794ff"/>',
        f'<text x="{W/2}" y="{y0-13}" text-anchor="middle" font-family="{MONO}" font-size="11" fill="#9a86d6">{USER.lower()}@twilight-garden: ~</text>',
        f'<g font-family="{MONO}" font-size="{fs}">']

    bc = "#7d5bd0"
    border = "#" * cols
    for line in (0, 17):
        out.append(f'<text x="{x0:.1f}" y="{ty(line):.1f}" textLength="{cols*cw:.1f}" lengthAdjust="spacingAndGlyphs" fill="{bc}">{border}</text>')
    for i in range(1, 17):
        out.append(f'<text x="{x0:.1f}" y="{ty(i):.1f}" fill="{bc}">#</text>'
                   f'<text x="{x0+(cols-1)*cw:.1f}" y="{ty(i):.1f}" fill="{bc}">#</text>')
    inner = x0 + 4 * cw
    out.append(f'<text x="{inner:.1f}" y="{ty(2):.1f}" fill="#ff9ad5">$</text>'
               f'<text x="{inner+2*cw:.1f}" y="{ty(2):.1f}" fill="#d7c6ff">whoami</text>')

    ax = x0 + 7 * cw
    runs = []
    for r, line in enumerate(art):
        for m in re.finditer(r"#+", line):
            runs.append(f'<text x="{ax+m.start()*cw:.1f}" y="{ty(4+r):.1f}" textLength="{(m.end()-m.start())*cw:.1f}" '
                        f'lengthAdjust="spacingAndGlyphs">{m.group()}</text>')
    out.append(f'<g id="art" fill="url(#ag)" font-weight="bold">{"".join(runs)}</g>')
    out.append('<use href="#art" filter="url(#bl)" opacity=".75"/>')

    out.append(f'<text x="{inner:.1f}" y="{ty(14):.1f}" fill="#ff9ad5">$</text>'
               f'<text x="{inner+2*cw:.1f}" y="{ty(14):.1f}" fill="#d7c6ff">cat bio.txt</text>')
    out.append(f'<text x="{inner:.1f}" y="{ty(15):.1f}" fill="#f1e6ff" font-family="{SERIF}" font-style="italic" font-size="13">{html.escape(bio)}</text>')
    out.append(f'<rect class="bk" x="{inner + len(bio)*6.0 + 6:.1f}" y="{ty(15)-11:.1f}" width="7" height="13" fill="#c39bff"/>')
    out.append('</g>')
    for sx in (30, 60, 90, 120, W - 30, W - 60, W - 90):
        out.append(sprig(sx, 0, rng.uniform(34, 56), rng, n=6))
    out.append('</svg>')
    return "".join(out)


# ---------------------------------------------------------------- divider
def divider(text, seed, bg=True):
    W, H = 960, 84
    rng = random.Random(seed)
    parts = [svg_open(W, H, '<linearGradient id="dv" x1="0" x2="1"><stop offset="0" stop-color="#1a0f3c"/>'
                      '<stop offset=".5" stop-color="#2d1560"/><stop offset="1" stop-color="#1a0f3c"/></linearGradient>'
                      '<linearGradient id="ln" x1="0" x2="1"><stop offset="0" stop-color="#b794ff" stop-opacity="0"/>'
                      '<stop offset="1" stop-color="#b794ff"/></linearGradient>'
                      '<linearGradient id="lr" x1="0" x2="1"><stop offset="0" stop-color="#b794ff"/>'
                      '<stop offset="1" stop-color="#b794ff" stop-opacity="0"/></linearGradient>'),
             (f'<rect width="{W}" height="{H}" rx="14" fill="url(#dv)"/>' if bg else ''), stars(rng, W, H, 22)]
    tw = len(text) * 15.5 + 50
    lx, rx = W / 2 - tw / 2, W / 2 + tw / 2
    parts.append(f'<path d="M40,44 C140,30 220,58 {lx-16:.0f},44" stroke="url(#ln)" stroke-width="1.6" fill="none"/>')
    parts.append(f'<path d="M{rx+16:.0f},44 C{rx+120:.0f},58 {W-140},30 {W-40},44" stroke="url(#lr)" stroke-width="1.6" fill="none"/>')
    for k in range(9):
        x = 70 + k * (lx - 140) / 8
        parts.append(sprig(x, 40 + 4 * math.sin(k), rng.uniform(16, 30), rng, n=4, r=3.4))
        x2 = rx + 70 + k * (W - rx - 140) / 8
        parts.append(sprig(x2, 40 + 4 * math.sin(k + 2), rng.uniform(16, 30), rng, n=4, r=3.4))
    parts.append(f'<text x="{W/2}" y="52" text-anchor="middle" font-family="{SERIF}" font-size="21" font-style="italic" '
                 f'letter-spacing="5" fill="#eadcff">{html.escape(text)}</text>')
    parts.append('</svg>')
    return "".join(parts)


# ---------------------------------------------------------------- contributions
def fetch_contributions():
    page = get(f"https://github.com/users/{USER}/contributions")
    cells = sorted(set(re.findall(r'data-date="(\d{4}-\d\d-\d\d)"[^>]*?data-level="(\d)"', page)))
    m = re.search(r"([\d,]+)\s+contributions?\s+in the last year", page)
    total = int(m.group(1).replace(",", "")) if m else 0
    return [int(l) for _, l in cells], total


LV = {0: ("#6a50b8", .82, 5.4), 1: ("#a88cf2", .92, 6.3), 2: ("#bd92ff", .95, 7.7),
      3: ("#dbaaff", 1, 9.2), 4: ("#f7d8ff", 1, 10.8)}


def tree(levels, total):
    W, H, WATER, CX = 960, 640, 520, 480
    rng = random.Random(11)
    n = len(levels)
    ns = math.ceil(n / 7)

    def top(x):
        return 250 - 190 * math.sqrt(max(0, 1 - ((x - CX) / 430) ** 2))

    # ---- branches + trunk
    limbs = [("M470 345 C440 300 360 240 320 105", 17), ("M395 255 C340 235 280 195 210 118", 11),
             ("M350 195 C330 160 315 130 300 95", 8),
             ("M462 425 C400 405 320 372 250 300 C200 250 160 220 125 165", 15),
             ("M292 332 C262 300 238 250 228 150", 9), ("M205 262 C170 250 140 235 100 200", 7)]
    side = "".join(
        f'<path d="{d}" stroke="#3a2658" stroke-width="{w}" stroke-linecap="round" fill="none"/>'
        f'<path d="{d}" transform="translate(-{w*.18:.1f} -{w*.1:.1f})" stroke="#6a4a95" stroke-opacity=".45" '
        f'stroke-width="{w*.3:.1f}" stroke-linecap="round" fill="none"/>' for d, w in limbs)
    centre = [("M481 345 C484 260 476 160 481 70", 16), ("M480 215 C450 180 420 130 405 75", 9),
              ("M482 190 C510 160 540 120 552 80", 8)]
    mid = "".join(
        f'<path d="{d}" stroke="#3a2658" stroke-width="{w}" stroke-linecap="round" fill="none"/>'
        f'<path d="{d}" transform="translate(-{w*.18:.1f} -{w*.1:.1f})" stroke="#6a4a95" stroke-opacity=".45" '
        f'stroke-width="{w*.3:.1f}" stroke-linecap="round" fill="none"/>' for d, w in centre)
    extra = ('<path d="M515 410 C580 372 655 350 745 292 C800 258 835 222 852 190" stroke="#3a2658" stroke-width="13" '
             'stroke-linecap="round" fill="none"/>')
    branches = [f'<circle cx="481" cy="320" r="30" fill="#3a2658"/>', mid, side,
                f'<g transform="translate(962 0) scale(-.992 1)">{side}</g>', extra]
    trunk = (
        '<path d="M410 548 C446 524 452 492 446 455 C440 410 452 360 456 300 L506 300 C510 360 524 410 516 455 '
        'C510 492 518 524 556 548 Z" fill="url(#bark)"/>'
        '<path d="M440 530 C410 534 380 538 340 552 M520 532 C560 534 590 540 630 552 M470 536 C470 548 462 556 450 566" '
        'stroke="#2a1a45" stroke-width="11" stroke-linecap="round" fill="none"/>'
        '<path d="M466 304 C462 360 472 420 462 500" stroke="#7a5aa0" stroke-opacity=".4" stroke-width="3" fill="none"/>'
        '<path d="M500 310 C504 380 507 430 502 500" stroke="#150a28" stroke-opacity=".55" stroke-width="4" fill="none"/>'
        '<path d="M480 340 C484 380 478 420 484 470" stroke="#150a28" stroke-opacity=".4" stroke-width="2" fill="none"/>')

    # ---- canopy: one strand per week, one big petal per day
    strands = []
    for i in range(ns):
        x = 90 + (780 * i / max(1, ns - 1)) + rng.uniform(-3, 3)
        t0 = top(x)
        u = abs(x - CX) / 390
        L = (160 + 110 * u * u) * rng.uniform(.9, 1.12)
        pts, body, glow = [], [], []
        for k in range(7):
            idx = i * 7 + k
            if idx >= n:
                break
            t = (k + .5) / 7
            y = t0 + 12 + t * (L - 12)
            px = x + 5 * math.sin(y / 37 + i * .9)
            pts.append((px, y))
            lvl = levels[idx]
            col, op, r = LV[lvl]
            if lvl == 0:
                col = lerp_hex("#5a44a8", "#9a7be4", t)
            shape = (f'<path d="{petal(r)}" transform="translate({px:.1f},{y:.1f}) rotate({rng.uniform(-14,14):.0f})" '
                     f'fill="{col}" opacity="{op}"/>')
            (glow if lvl >= 3 else body).append(shape)
            # airy filler between the real petals (decoration only)
            for _ in range(4):
                fy = y + rng.uniform(4, L / 7 - 4)
                fx = px + rng.uniform(-5, 5) + 2 * math.sin(fy / 37)
                body.insert(0, f'<path d="{petal(rng.uniform(2.6,4.0))}" transform="translate({fx:.1f},{fy:.1f})" '
                               f'fill="{lerp_hex("#5a44a8", "#b394f5", rng.uniform(.1, .9))}" opacity=".42"/>')
        if not pts:
            continue
        line = f"M{x:.1f},{t0:.1f} L" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        strands.append(
            f'<g class="sw" style="transform-origin:{x:.0f}px {t0:.0f}px;animation-delay:-{rng.uniform(0,7):.1f}s;'
            f'animation-duration:{rng.uniform(6,9):.1f}s"><path d="{line}" stroke="#3a2a6e" stroke-width="1" fill="none" opacity=".7"/>'
            f'{"".join(body)}<g class="gl" filter="url(#glow)">{"".join(glow)}</g></g>')

    plant = f'<g>{trunk}{"".join(branches)}{"".join(strands)}</g>'

    # ---- scenery
    mts = ('<path d="M0 520 L0 430 L60 395 L120 440 L190 380 L260 450 L330 420 L400 470 L470 440 L540 480 L620 410 '
           'L700 455 L780 385 L850 440 L910 400 L960 430 L960 520Z" fill="#2b1659" opacity=".85"/>'
           '<path d="M0 520 L0 470 L90 440 L170 480 L260 455 L360 490 L470 465 L580 495 L690 460 L800 490 L890 455 L960 480 L960 520Z" '
           'fill="#3a1d6b" opacity=".9"/>')
    island = ('<path d="M140 548 C230 520 340 516 480 516 C620 516 730 520 820 548 C740 574 600 580 480 580 C360 580 220 574 140 548Z" '
              'fill="url(#land)"/><path d="M160 543 C260 523 360 520 480 520 C600 520 700 523 800 543" stroke="#7fc0a0" '
              'stroke-opacity=".35" stroke-width="2" fill="none"/>')
    grass = "".join(
        f'<path d="M{gx:.0f},{gy:.0f} q{rng.uniform(-3,3):.1f},-8 {rng.uniform(-5,5):.1f},-{rng.uniform(8,15):.0f}" '
        f'stroke="#5a9a86" stroke-opacity=".7" stroke-width="1.2" fill="none"/>'
        for gx, gy in ((rng.uniform(190, 770), rng.uniform(534, 566)) for _ in range(70)))
    rocks = ('<ellipse cx="690" cy="552" rx="30" ry="16" fill="#3b2c63"/><ellipse cx="710" cy="546" rx="18" ry="11" fill="#4b3a7a"/>'
             '<ellipse cx="250" cy="556" rx="26" ry="13" fill="#3b2c63"/>')
    carpet = "".join(
        f'<path d="{petal(rng.uniform(2.5,4))}" transform="translate({px:.0f},{py:.0f}) rotate({rng.uniform(0,360):.0f})" '
        f'fill="{lerp_hex("#8e70e0", "#e3c5ff", rng.random())}" opacity="{rng.uniform(.4,.9):.2f}"/>'
        for px, py in ((rng.uniform(200, 770), rng.uniform(530, 570)) for _ in range(90)))

    def lantern(x, y, s=1.0):
        return (f'<g transform="translate({x},{y}) scale({s})"><circle class="gl" cy="-16" r="26" fill="url(#lamp)"/>'
                '<rect x="-8" y="-3" width="16" height="3" fill="#33264f"/><rect x="-3" y="-12" width="6" height="9" fill="#2a1d44"/>'
                '<rect x="-7" y="-26" width="14" height="14" fill="#ffd9a0"/>'
                '<path d="M-11 -26 L0 -35 L11 -26Z" fill="#33264f"/></g>')
    lanterns = lantern(335, 540) + lantern(625, 546, 1.1) + lantern(556, 556, .8) + lantern(720, 538, .9)

    falling = "".join(
        f'<g class="fl" style="animation-delay:-{rng.uniform(0,14):.1f}s;animation-duration:{rng.uniform(11,18):.0f}s">'
        f'<path d="{petal(4.5)}" transform="translate({fx:.0f},{fy:.0f})" fill="#e6c8ff"/></g>'
        for fx, fy in ((rng.uniform(250, 720), rng.uniform(180, 300)) for _ in range(12)))
    ripples = "".join(
        f'<ellipse class="rp" style="animation-delay:-{rng.uniform(0,6):.1f}s" cx="{rx:.0f}" cy="{ry:.0f}" rx="34" ry="5" '
        f'fill="none" stroke="#e0c4ff" stroke-opacity=".6"/>'
        for rx, ry in ((rng.uniform(80, 880), rng.uniform(592, 628)) for _ in range(7)))

    legend = ""
    for k in range(5):
        col, op, r = LV[k]
        legend += f'<path d="{petal(r*.8)}" transform="translate({96+k*20},606)" fill="{col}" opacity="{op}"/>'
    legend = (f'<text x="40" y="611" font-family="{SERIF}" font-style="italic" font-size="13" fill="#cdb8ff">less</text>{legend}'
              f'<text x="204" y="611" font-family="{SERIF}" font-style="italic" font-size="13" fill="#cdb8ff">more</text>'
              f'<text x="{W-40}" y="611" text-anchor="end" font-family="{SERIF}" font-style="italic" font-size="14" fill="#eadcff">'
              f'{total} petals gathered in the last year</text>')

    defs = (SKY +
            '<linearGradient id="water" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8a4a96"/>'
            '<stop offset=".25" stop-color="#4a2a7c"/><stop offset="1" stop-color="#150b32"/></linearGradient>'
            '<linearGradient id="bark" x1="0" x2="1"><stop offset="0" stop-color="#2a1a47"/><stop offset=".45" stop-color="#4d3470"/>'
            '<stop offset="1" stop-color="#22143c"/></linearGradient>'
            '<linearGradient id="land" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#34507a"/>'
            '<stop offset=".35" stop-color="#2a2552"/><stop offset="1" stop-color="#150d30"/></linearGradient>'
            '<radialGradient id="horizon" cx=".5" cy="1" r=".6"><stop offset="0" stop-color="#ffa6c8" stop-opacity=".75"/>'
            '<stop offset="1" stop-color="#ffa6c8" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="lamp"><stop offset="0" stop-color="#ffd9a0" stop-opacity=".9"/>'
            '<stop offset="1" stop-color="#ffd9a0" stop-opacity="0"/></radialGradient>'
            '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/>'
            '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
            '<filter id="soft"><feGaussianBlur stdDeviation="1.6"/></filter>'
            f'<clipPath id="wc"><rect x="0" y="{WATER}" width="{W}" height="{H-WATER}"/></clipPath>'
            '<mask id="mm"><rect width="960" height="640" fill="#fff"/><circle cx="903" cy="62" r="19" fill="#000"/></mask>')

    return "".join([
        svg_open(W, H, defs),
        f'<rect width="{W}" height="{H}" fill="url(#sky)"/>',
        stars(rng, W, 330, 90),
        '<circle cx="890" cy="68" r="22" fill="#fff0cf" mask="url(#mm)"/>',
        mts,
        f'<rect y="{WATER-120}" width="{W}" height="120" fill="url(#horizon)"/>',
        f'<rect y="{WATER}" width="{W}" height="{H-WATER}" fill="url(#water)"/>',
        f'<g clip-path="url(#wc)" opacity=".34" filter="url(#soft)"><g transform="translate(0 {2*WATER}) scale(1 -1)">{plant}</g></g>',
        ripples, island, grass, rocks, carpet,
        plant, lanterns, falling, legend, '</svg>'])


# ---------------------------------------------------------------- repo cards
LANG = {"Python": "#7aa7ff", "JavaScript": "#ffe08a", "TypeScript": "#7fb4ff", "HTML": "#ff9a7a", "CSS": "#b794ff",
        "Java": "#ffb27a", "C": "#9fb0d0", "C++": "#ff8fb8", "C#": "#8fd68f", "PHP": "#a9a0ff", "Rust": "#ffb38f",
        "Go": "#7fe0e8", "Kotlin": "#d19cff", "Shell": "#a5e8a0", "Lua": "#7f9cff", "Dart": "#7fe0e8"}


def repo_card(r, idx):
    W, H = 470, 176
    rng = random.Random(idx + 40)
    name = html.escape(r["name"] if len(r["name"]) <= 24 else r["name"][:23] + "…")
    desc = (r.get("description") or "").strip()
    wrapped = textwrap.wrap(desc, 46) if desc else ["a quiet corner of the garden, still growing"]
    lines = wrapped[:2]
    if len(wrapped) > 2:
        lines[1] = lines[1][:43] + "…"
    style = "" if desc else ' font-style="italic"'
    lang = r.get("language")
    lcol = LANG.get(lang, "#c39bff")
    try:
        when = datetime.strptime(r["pushed_at"][:10], "%Y-%m-%d").strftime("%b %Y")
    except Exception:
        when = ""
    meta = f'<g font-family="{SERIF}" font-size="13" fill="#bfaef0">'
    mx = 28
    if lang:
        meta += f'<circle cx="{mx+4}" cy="147" r="5" fill="{lcol}"/><text x="{mx+14}" y="152">{html.escape(lang)}</text>'
        mx += 24 + len(lang) * 7.4
    meta += f'<text x="{mx}" y="152">★ {r.get("stargazers_count", 0)}</text>'
    mx += 44
    meta += (f'<g transform="translate({mx},141)" stroke="#bfaef0" stroke-width="1.4" fill="none"><circle cx="2" cy="2" r="2"/>'
             f'<circle cx="10" cy="2" r="2"/><circle cx="6" cy="12" r="2"/><path d="M2 4 V6 H10 V4 M6 6 V10"/></g>'
             f'<text x="{mx+18}" y="152">{r.get("forks_count", 0)}</text>')
    if when:
        meta += f'<text x="{W-28}" y="152" text-anchor="end" font-style="italic" fill="#9a86d6">tended {when}</text>'
    meta += '</g>'
    desc_svg = "".join(f'<text x="28" y="{88+i*21}" font-family="{SERIF}" font-size="14" fill="#cfc0f5"{style}>{html.escape(l)}</text>'
                       for i, l in enumerate(lines))
    return "".join([
        svg_open(W, H, '<linearGradient id="cb" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1c1046"/>'
                       '<stop offset="1" stop-color="#341866"/></linearGradient>'
                       '<linearGradient id="cs" x1="0" x2="1"><stop offset="0" stop-color="#ff9ad5"/><stop offset="1" stop-color="#8a7cff"/></linearGradient>'
                       '<radialGradient id="lamp"><stop offset="0" stop-color="#ffd9a0" stop-opacity=".95"/><stop offset="1" stop-color="#ffd9a0" stop-opacity="0"/></radialGradient>'),
        f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="16" fill="url(#cb)" stroke="url(#cs)" stroke-opacity=".55" stroke-width="1.5"/>',
        stars(rng, W, 70, 9),
        '<circle class="gl" cx="42" cy="50" r="24" fill="url(#lamp)"/><rect x="35" y="41" width="14" height="14" fill="#ffd9a0"/>'
        '<path d="M31 41 L42 32 L53 41Z" fill="#6a4fb5"/><rect x="39" y="55" width="6" height="7" fill="#4b3a7a"/>',
        f'<text x="72" y="56" font-family="{SERIF}" font-size="22" font-weight="bold" fill="#f1e8ff">{name}</text>',
        desc_svg, meta,
        sprig(W - 40, 1, 56, rng, n=6, r=4), sprig(W - 66, 1, 36, rng, n=4, r=3.6), sprig(W - 92, 1, 24, rng, n=3, r=3.2),
        '</svg>'])


def empty_card():
    W, H = 960, 150
    rng = random.Random(5)
    return "".join([
        svg_open(W, H, '<linearGradient id="cb" x1="0" x2="1"><stop offset="0" stop-color="#1c1046"/><stop offset="1" stop-color="#341866"/></linearGradient>'),
        f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="16" fill="url(#cb)" stroke="#7d5bd0" stroke-opacity=".5"/>',
        stars(rng, W, H, 24),
        '<g transform="translate(480,92)"><path d="M0 30 C0 10 0 0 0 -14" stroke="#7fc0a0" stroke-width="3" fill="none"/>'
        '<path d="M0 -6 C-18 -8 -24 -22 -22 -28 C-8 -28 0 -18 0 -6Z" fill="#5ea58a"/>'
        '<path d="M0 -14 C16 -16 24 -30 22 -36 C8 -36 0 -26 0 -14Z" fill="#7fc0a0"/></g>',
        f'<text x="{W/2}" y="48" text-anchor="middle" font-family="{SERIF}" font-size="21" font-style="italic" fill="#eadcff">the garden is still sprouting</text>',
        f'<text x="{W/2}" y="136" text-anchor="middle" font-family="{SERIF}" font-size="13" fill="#9a86d6">new repositories will bloom here on their own</text>',
        '</svg>'])


def fetch_repos():
    data = json.loads(get(f"https://api.github.com/users/{USER}/repos?per_page=100&sort=pushed", api=True))
    repos = [r for r in data if not r["fork"] and r["name"].lower() != USER.lower()]
    repos.sort(key=lambda r: r["pushed_at"], reverse=True)
    return repos[:6]


def embed(svg, x, y, n, scale=1):
    inner = re.sub(r"^<svg[^>]*>", "", svg).rsplit("</svg>", 1)[0]
    for i in set(re.findall(r'id="([^"]+)"', inner)):
        p = f"g{n}_{i}"
        inner = (inner.replace(f'id="{i}"', f'id="{p}"').replace(f"url(#{i})", f"url(#{p})")
                 .replace(f'href="#{i}"', f'href="#{p}"'))
    return f'<g transform="translate({x},{y}) scale({scale})">{inner}</g>'


def garden(bio, levels, total, repos):
    W = 960
    pieces, y, n = [], 0, 0

    def add(svg, h, x=0, scale=1):
        nonlocal y, n
        pieces.append(embed(svg, x, y, n, scale))
        n += 1
        return h

    y += add(banner(bio, bg=False), 372)
    y += add(divider("✦  CONTRIBUTIONS  ✦", 1, bg=False), 84)
    tree_end = y + 640
    y += add(tree(levels, total), 640)
    y += 14
    y += add(divider("✦  REPOSITORIES  ✦", 2, bg=False), 84)
    if repos:
        row_y = y
        for i, r in enumerate(repos):
            col, row = i % 2, i // 2
            pieces.append(embed(repo_card(r, i), 10 + col * 470, row_y + row * 190, n))
            n += 1
        y = row_y + math.ceil(len(repos) / 2) * 190
    else:
        pieces.append(embed(empty_card(), 30, y, n, .9375))
        n += 1
        y += 150
    y += 10
    y += add(divider("the garden blooms for those who wait", 3, bg=False), 84)
    H = y + 6
    bg = (f'<linearGradient id="gbg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{H}">'
          f'<stop offset="0" stop-color="#0c0824"/><stop offset="{tree_end/H:.3f}" stop-color="#150b32"/>'
          f'<stop offset="1" stop-color="#0a0620"/></linearGradient><clipPath id="gclip"><rect width="{W}" height="{H}" rx="18"/></clipPath>')
    return (svg_open(W, H, bg) + f'<g clip-path="url(#gclip)"><rect width="{W}" height="{H}" fill="url(#gbg)"/>'
            + "".join(pieces) + '</g></svg>')


# ---------------------------------------------------------------- main
def main():
    ASSETS.mkdir(exist_ok=True)
    try:
        bio = (json.loads(get(f"https://api.github.com/users/{USER}", api=True)).get("bio") or "").strip()
    except Exception:
        bio = ""
    bio = bio or "growing quietly in the twilight garden"
    levels, total = fetch_contributions()
    for old in ASSETS.glob("*.svg"):
        old.unlink()
    (ASSETS / "garden.svg").write_text(garden(bio, levels, total, fetch_repos()), encoding="utf-8")
    print(f"ok: {len(levels)} days, {total} contributions")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate P1, an osu!stable skin styled after pax.moe.

Every element is drawn at SS x the @2x size, then downsampled to @2x and @1x.
Sizes below are in @1x ("logical") pixels. Everything visual is drawn here.
Sounds can optionally come from skins you already have:
    gen.py OUT [--assets SKIN] [--hitsounds SKIN]
"""

import math
import re
import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SS = 4                      # supersample factor on top of @2x
K = 2 * SS                  # canvas pixels per logical pixel

GRN = (0, 255, 0)
GRN2 = (0, 204, 0)          # hyprland gradient end
DARK = (0, 34, 0)           # hyprland inactive border
RED = (255, 85, 85)         # quickshell bar warning
WHITE = (255, 255, 255)



def find_font(pattern="Terminess Nerd Font Mono:style=Bold"):
    """Resolve the font file through fontconfig, so any distro's install works."""
    out = subprocess.run(["fc-match", "-f", "%{file}", pattern], capture_output=True, text=True)
    path = out.stdout.strip()
    if "Terminess" not in Path(path).name:
        sys.exit(f"Terminess Nerd Font not found (fc-match gave {path or 'nothing'}); install it first")
    return path


FONT = find_font()

OUT: Path


def rgba(c, a=1.0):
    return (*c, round(255 * a))


class C:
    """A canvas in logical pixels."""

    def __init__(self, w, h, bg=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (round(w * K), round(h * K)), bg)
        self.d = ImageDraw.Draw(self.im)

    def p(self, v):
        return v * K

    def ring(self, cx, cy, r, width, col):
        r, w = self.p(r), self.p(width)
        cx, cy = self.p(cx), self.p(cy)
        self.d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col, width=max(1, round(w)))

    def disc(self, cx, cy, r, col):
        r, cx, cy = self.p(r), self.p(cx), self.p(cy)
        self.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=1):
        self.d.rectangle((self.p(x0), self.p(y0), self.p(x1), self.p(y1)),
                         fill=fill, outline=outline, width=max(1, round(self.p(width))))

    def line(self, pts, col, width=1):
        self.d.line([(self.p(x), self.p(y)) for x, y in pts], fill=col,
                    width=max(1, round(self.p(width))), joint="curve")

    def brackets(self, x0, y0, x1, y1, arm, col, width=1, all4=False):
        """pax.moe corner brackets: top left and bottom right L shapes."""
        self.line([(x0, y0 + arm), (x0, y0), (x0 + arm, y0)], col, width)
        self.line([(x1, y1 - arm), (x1, y1), (x1 - arm, y1)], col, width)
        if all4:
            self.line([(x1 - arm, y0), (x1, y0), (x1, y0 + arm)], col, width)
            self.line([(x0 + arm, y1), (x0, y1), (x0, y1 - arm)], col, width)

    def text(self, s, cx, cy, size, col, font=FONT, anchor="mm"):
        f = ImageFont.truetype(font, round(self.p(size)))
        self.d.text((self.p(cx), self.p(cy)), s, font=f, fill=col, anchor=anchor)

    def glow(self, radius, strength=1.0):
        """Blur a copy of the current layer underneath it, like text-shadow."""
        blur = self.im.filter(ImageFilter.GaussianBlur(self.p(radius)))
        if strength != 1.0:
            a = blur.getchannel("A").point(lambda v: min(255, round(v * strength)))
            blur.putalpha(a)
        blur.alpha_composite(self.im)
        self.im = blur
        self.d = ImageDraw.Draw(self.im)

    def save(self, name, hd_only=False, jpg=False):
        for scale, suffix in ((2, "@2x"), (1, "")):
            if hd_only and scale == 1:
                continue
            size = (max(1, round(self.w * scale)), max(1, round(self.h * scale)))
            out = self.im.resize(size, Image.LANCZOS)
            if jpg:
                out.convert("RGB").save(OUT / f"{name}{suffix}.jpg", quality=92)
            else:
                out.save(OUT / f"{name}{suffix}.png")


def blank(name):
    """A 1x1 transparent image hides an element the game would otherwise draw."""
    Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(OUT / f"{name}.png")


def text_img(name, s, size, col, pad=8, glow=3, font=FONT):
    """Text sized to its own bounding box."""
    f = ImageFont.truetype(font, round(size * K))
    l, t, r, b = f.getbbox(s)
    w, h = (r - l) / K + 2 * pad, (b - t) / K + 2 * pad
    c = C(w, h)
    c.d.text((pad * K - l, pad * K - t), s, font=f, fill=col)
    if glow:
        c.glow(glow, 1.4)
    c.save(name)


# ---------------------------------------------------------------- gameplay

def hitcircles():
    # Tinted by the combo colour: drawn white so the tint shows through.
    c = C(128, 128)
    # Ring spans 58 to 63 so at slider heads it covers the body's border.
    c.disc(64, 64, 60, rgba(WHITE, 0.16))
    c.ring(64, 64, 63, 5, rgba(WHITE))
    c.ring(64, 64, 50, 1, rgba(WHITE, 0.35))
    c.save("hitcircle")

    blank("hitcircleoverlay")

    a = C(126, 126)
    a.ring(63, 63, 59, 6, rgba(WHITE))   # thick rim reads at small sizes
    a.save("approachcircle")

    for n in range(10):
        f = ImageFont.truetype(FONT, 54 * K)
        l, t, r, b = f.getbbox(str(n))
        d = C((r - l) / K + 8, (b - t) / K + 8)
        d.d.text((4 * K - l, 4 * K - t), str(n), font=f, fill=rgba((210, 255, 210)))
        d.glow(2, 1.2)
        d.save(f"default-{n}")


def sliders():
    s = C(256, 256)
    s.ring(128, 128, 118, 2, rgba(GRN, 0.85))
    s.glow(3, 1.5)
    s.save("sliderfollowcircle")

    b = C(118, 118)
    b.ring(59, 59, 38, 4, rgba(WHITE))
    b.disc(59, 59, 9, rgba(WHITE))
    b.save("sliderb")
    blank("sliderb-nd")
    blank("sliderendcircle")          # no circle at the slider tail; without this
    blank("sliderendcircleoverlay")   # stable falls back to the hit circle
    blank("sliderb-spec")

    r = C(128, 128)
    r.text(">", 64, 62, 72, rgba(WHITE))   # Terminess, like the numbers; points right, the game rotates it
    r.save("reversearrow")

    p = C(16, 16)
    p.rect(5, 5, 11, 11, fill=rgba(GRN))
    p.glow(1.5, 1.5)
    p.save("sliderscorepoint")

    f = C(24, 8)
    f.rect(4, 3, 20, 5, fill=rgba(WHITE, 0.8))
    f.save("followpoint")

    for name in ("lighting", "particle50", "particle100", "particle300"):
        blank(name)


def judgements():
    for name in ("hit300", "hit300g", "hit300k"):
        blank(name)
    text_img("hit100", "100", 34, rgba(GRN, 0.8))
    text_img("hit100k", "100", 34, rgba(GRN, 0.8))
    text_img("hit50", "50", 34, rgba(GRN, 0.45))
    text_img("hit0", "x", 54, rgba(RED), glow=4)
    blank("comboburst")


def cursor(src=None):
    """A solid dot: white core, phosphor green band, short glow. The trail comes
    from --assets when that skin has one (recoloured green: blue := red keeps
    white white; no @2x is written so none can override it), otherwise none."""
    trail = src / "cursortrail.png" if src else None
    if trail and trail.exists():
        r, g, _, a = Image.open(trail).convert("RGBA").split()
        Image.merge("RGBA", (r, g, r, a)).save(OUT / "cursortrail.png")
    else:
        blank("cursortrail")
    c = C(56, 56)
    c.disc(28, 28, 16, rgba(GRN))
    c.glow(3, 1.6)
    c.disc(28, 28, 10, rgba(WHITE))
    c.save("cursor")


def spinner():
    size = 480
    m = size / 2
    b = C(size, size)
    for i in range(72):
        a = 2 * math.pi * i / 72
        r0, r1 = (206, 222) if i % 6 else (196, 226)
        b.line([(m + r0 * math.cos(a), m + r0 * math.sin(a)),
                (m + r1 * math.cos(a), m + r1 * math.sin(a))],
               rgba(GRN, 0.66 if i % 6 else 1.0), 2)
    b.glow(2, 1.2)
    b.save("spinner-bottom")

    t = C(size, size)
    t.ring(m, m, 180, 1, rgba(GRN, 0.34))
    t.save("spinner-top")

    mid = C(160, 160)
    mid.ring(80, 80, 60, 3, rgba(WHITE))
    mid.save("spinner-middle")

    mid2 = C(40, 40)
    mid2.rect(14, 14, 26, 26, fill=rgba(GRN))
    mid2.glow(2, 1.5)
    mid2.save("spinner-middle2")

    g = C(size, size)
    g.ring(m, m, 214, 10, rgba(WHITE, 0.6))
    g.glow(10, 1.0)
    g.save("spinner-glow")

    a = C(384, 384)
    a.ring(192, 192, 188, 3, rgba(GRN))
    a.save("spinner-approachcircle")

    r = C(280, 56)
    r.rect(1, 1, 279, 55, fill=rgba((0, 0, 0), 0.85), outline=rgba(GRN, 0.34))
    r.brackets(1, 1, 279, 55, 10, rgba(GRN), 2)
    r.text("rpm", 24, 28, 22, rgba(GRN, 0.66), anchor="lm")
    r.save("spinner-rpm")

    text_img("spinner-clear", "clear", 64, rgba(GRN))
    text_img("spinner-spin", "spin", 48, rgba(GRN, 0.8))


# ---------------------------------------------------------------- hud

def scorebar():
    bg = C(640, 36)
    bg.rect(8, 9, 616, 23, outline=rgba(GRN, 0.34))
    bg.brackets(8, 9, 616, 23, 6, rgba(GRN), 1)
    bg.save("scorebar-bg")

    # With a marker the colour sits at (12,12) and is multiply tinted.
    col = C(600, 8)
    col.rect(0, 0, 600, 8, fill=rgba(WHITE))
    col.save("scorebar-colour")

    mk = C(24, 24)
    mk.rect(8, 6, 16, 18, fill=rgba(GRN))
    mk.glow(3, 1.6)
    mk.save("scorebar-marker")


def score_fonts():
    glyphs = {str(n): str(n) for n in range(10)}
    glyphs.update({"comma": ",", "dot": ".", "percent": "%", "x": "x"})
    for key, ch in glyphs.items():
        f = ImageFont.truetype(FONT, 44 * K)
        l, t, r, b = f.getbbox("0")       # fixed cell keeps digits aligned
        w = (r - l) / K + 6
        if key in ("comma", "dot"):
            w = 14
        c = C(w, (b - t) / K + 10)
        c.d.text((c.w * K / 2, c.h * K / 2), ch, font=f, fill=rgba(WHITE), anchor="mm")
        c.glow(2, 0.8)
        c.save(f"score-{key}")

        f2 = ImageFont.truetype(FONT, 14 * K)
        e = C(11 if key not in ("comma", "dot") else 5, 14)
        e.d.text((e.w * K / 2, e.h * K / 2), ch, font=f2, fill=rgba((170, 255, 170)), anchor="mm")
        e.save(f"scoreentry-{key}")


def input_overlay():
    bg = C(193, 55)
    bg.rect(1, 1, 192, 54, fill=rgba((0, 0, 0), 0.85), outline=rgba(GRN, 0.34))
    bg.save("inputoverlay-background")

    k = C(43, 46)
    k.rect(4, 5, 39, 41, fill=rgba((0, 0, 0), 0.8), outline=rgba(WHITE), width=2)
    k.save("inputoverlay-key")


def playfield():
    s = C(200, 60)
    s.rect(1, 1, 199, 59, fill=rgba((0, 0, 0), 0.85), outline=rgba(GRN, 0.34))
    s.brackets(1, 1, 199, 59, 10, rgba(GRN), 2)
    s.text("skip >>", 100, 30, 26, rgba(GRN))
    s.save("play-skip")

    for name, col in (("arrow-warning", RED), ("arrow-pause", GRN), ("arrow-generic", GRN)):
        a = C(64, 64)
        a.line([(20, 12), (44, 32), (20, 52)], rgba(col), 6)
        a.glow(3, 1.5)
        a.save(name)
    shutil.copy(OUT / "arrow-warning.png", OUT / "play-warningarrow.png")
    shutil.copy(OUT / "arrow-warning@2x.png", OUT / "play-warningarrow@2x.png")

    text_img("play-unranked", "unranked", 22, rgba(GRN, 0.5), glow=0)
    text_img("section-pass", "+", 160, rgba(GRN), glow=8)
    text_img("section-fail", "x", 160, rgba(RED), glow=8)
    text_img("ready", "ready?", 70, rgba(GRN))
    text_img("go", "go", 110, rgba(GRN), glow=6)
    for n in (1, 2, 3):
        text_img(f"count{n}", str(n), 140, rgba(GRN), glow=6)

    t = C(4, 24)
    t.rect(1, 0, 3, 24, fill=rgba(WHITE))
    t.save("options-offset-tick")


def pause_screens():
    """Plain: a dark overlay and text buttons, nothing else."""
    for name in ("pause-overlay", "fail-background"):
        C(1366, 768, rgba((0, 0, 0), 0.78)).save(name)

    for name, label in (("pause-continue", "continue"), ("pause-retry", "retry"),
                        ("pause-back", "back to menu"), ("pause-replay", "replay")):
        text_img(name, label, 40, rgba(GRN), pad=16, glow=2)


# ---------------------------------------------------------------- ranking

GRADES = {
    "XH": ("SS", (235, 255, 235)), "X": ("SS", GRN),
    "SH": ("S", (235, 255, 235)), "S": ("S", GRN),
    "A": ("A", GRN2), "B": ("B", (0, 170, 0)), "C": ("C", (0, 130, 0)), "D": ("D", RED),
}


def ranking():
    for key, (letters, col) in GRADES.items():
        big = C(320, 320)
        big.brackets(20, 20, 300, 300, 40, rgba(col, 0.66), 3)
        big.text(letters, 160, 168, 230 if len(letters) == 1 else 170, rgba(col))
        big.glow(6, 1.4)
        big.save(f"ranking-{key}")

        sm = C(34, 40)
        sm.text(letters, 17, 21, 30 if len(letters) == 1 else 22, rgba(col))
        sm.glow(1.5, 1.2)
        sm.save(f"ranking-{key}-small")

    p = C(620, 520)
    p.rect(1, 1, 619, 519, fill=rgba((0, 0, 0), 0.82), outline=rgba(GRN, 0.12))
    p.brackets(1, 1, 619, 519, 24, rgba(GRN, 0.66), 2)
    p.save("ranking-panel")

    g = C(320, 160)
    g.rect(1, 1, 319, 159, fill=rgba((0, 0, 0), 0.85), outline=rgba(GRN, 0.34))
    g.brackets(1, 1, 319, 159, 12, rgba(GRN), 2)
    for x in range(40, 320, 40):
        g.line([(x, 4), (x, 156)], rgba(GRN, 0.08), 1)
    g.line([(4, 80), (316, 80)], rgba(GRN, 0.12), 1)
    g.save("ranking-graph")

    text_img("ranking-title", "results_", 64, rgba(GRN))
    text_img("ranking-accuracy", "accuracy", 26, rgba(GRN, 0.66), glow=0)
    text_img("ranking-maxcombo", "max combo", 26, rgba(GRN, 0.66), glow=0)
    text_img("ranking-perfect", "perfect", 40, rgba(GRN))
    for name, label in (("ranking-retry", "retry"), ("ranking-replay", "replay")):
        b = C(300, 60)
        b.rect(1, 1, 299, 59, fill=rgba((0, 0, 0), 0.9), outline=rgba(GRN, 0.34))
        b.brackets(1, 1, 299, 59, 10, rgba(GRN), 2)
        b.text(f"[ {label} ]", 150, 30, 28, rgba(GRN))
        b.save(name)


# ---------------------------------------------------------------- menus

def menu_background():
    W, H = 1366, 768
    c = C(W, H, rgba((0, 0, 0)))
    # oscilloscope graticule: 10 x 8 divisions with minor ticks on the axes
    x0, y0, x1, y1 = 183, 64, 1183, 704
    dx, dy = (x1 - x0) / 10, (y1 - y0) / 8
    for i in range(11):
        c.line([(x0 + i * dx, y0), (x0 + i * dx, y1)], rgba(GRN, 0.07), 1)
    for j in range(9):
        c.line([(x0, y0 + j * dy), (x1, y0 + j * dy)], rgba(GRN, 0.07), 1)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for i in range(51):
        x = x0 + i * dx / 5
        c.line([(x, cy - 5), (x, cy + 5)], rgba(GRN, 0.14), 1)
    for j in range(41):
        y = y0 + j * dy / 5
        c.line([(cx - 5, y), (cx + 5, y)], rgba(GRN, 0.14), 1)
    # phosphor trace: a 3:2 Lissajous figure
    # pi/2 phase; pi/4 degenerates into an open curve traced twice
    pts = [(cx + 380 * math.sin(3 * t + math.pi / 2), cy + 250 * math.sin(2 * t))
           for t in (2 * math.pi * k / 4000 for k in range(4001))]
    c.line(pts, rgba(GRN, 0.9), 2.5)
    c.glow(6, 1.8)
    c.brackets(24, 24, W - 24, H - 24, 36, rgba(GRN, 0.34), 1)
    c.text("pax.moe", W - 48, H - 44, 20, rgba(GRN, 0.34), anchor="rm")
    c.save("menu-background", jpg=True)

    text_img("welcome_text", "welcome_", 80, rgba(GRN))
    blank("menu-snow")


def song_select():
    b = C(200, 64)
    b.rect(1, 1, 199, 63, fill=rgba((0, 0, 0), 0.85), outline=rgba(GRN, 0.34))
    b.brackets(1, 1, 199, 63, 10, rgba(GRN), 2)
    b.text("< back", 100, 32, 28, rgba(GRN))
    b.save("menu-back")

    # Tinted by the game per state, so grey scale with a hairline frame.
    m = C(690, 85)
    m.rect(1, 1, 689, 84, fill=rgba(WHITE, 0.10), outline=rgba(WHITE, 0.45))
    m.save("menu-button-background")

    t = C(142, 24)
    t.rect(1, 1, 141, 24, fill=rgba(WHITE, 0.12), outline=rgba(WHITE, 0.5))
    t.save("selection-tab")

    for name, label, w in (("selection-mode", "mode", 92), ("selection-mods", "mods", 77),
                           ("selection-random", "rand", 77), ("selection-options", "opts", 77)):
        for over in (False, True):
            c = C(w, 87)
            if over:
                c.rect(4, 8, w - 4, 82, fill=rgba(GRN, 0.12))
                c.brackets(4, 8, w - 4, 82, 10, rgba(GRN), 2)
            c.text(label, w / 2, 50, 24, rgba(GRN, 1.0 if over else 0.66))
            if over:
                c.glow(2, 1.2)
            c.save(name + ("-over" if over else ""))

    top = C(1366, 96)
    top.rect(0, 0, 1366, 95, fill=rgba((0, 0, 0), 0.82))
    top.line([(0, 95), (1366, 95)], rgba(GRN, 0.34), 1)
    top.save("songselect-top")
    bot = C(1366, 90)
    bot.rect(0, 0, 1366, 90, fill=rgba((0, 0, 0), 0.82))
    bot.line([(0, 0), (1366, 0)], rgba(GRN, 0.34), 1)
    bot.save("songselect-bottom")

    s = C(50, 50)
    s.rect(17, 17, 33, 33, fill=rgba(WHITE))
    s.save("star")
    blank("star2")   # kiai side fountains, combo burst, cursor and song select particles

    for side in ("left", "middle", "right"):
        bt = C(16 if side != "middle" else 4, 52)
        bt.rect(0, 0, bt.w, 52, fill=rgba(WHITE, 0.14))
        bt.line([(0, 1), (bt.w, 1)], rgba(WHITE, 0.6), 1)
        bt.line([(0, 51), (bt.w, 51)], rgba(WHITE, 0.6), 1)
        if side == "left":
            bt.line([(1, 1), (1, 51)], rgba(WHITE, 0.6), 1)
        if side == "right":
            bt.line([(15, 1), (15, 51)], rgba(WHITE, 0.6), 1)
        bt.save(f"button-{side}")


def mode_icon(c, mode, s, col, wid):
    m = s / 2
    if mode == "osu":
        c.ring(m, m, s * 0.36, wid, col)
        c.disc(m, m, s * 0.09, col)
    elif mode == "taiko":
        c.ring(m, m, s * 0.36, wid, col)
        c.ring(m, m, s * 0.18, wid, col)
    elif mode == "fruits":
        c.ring(m, m, s * 0.36, wid, col)
        c.line([(m - s * 0.2, m + s * 0.2), (m + s * 0.2, m - s * 0.2)], col, wid)
    else:
        for i in range(4):
            x = m - s * 0.27 + i * s * 0.18
            c.rect(x - s * 0.04, m - s * 0.3, x + s * 0.04, m + s * 0.3, fill=col)


def modes():
    for mode in ("osu", "taiko", "fruits", "mania"):
        for suffix, s, wid in (("", 256, 8), ("-med", 128, 5), ("-small", 32, 2)):
            c = C(s, s)
            mode_icon(c, mode, s, rgba(GRN), wid)
            c.glow(s / 40, 1.3)
            c.save(f"mode-{mode}{suffix}")


MODS = {
    # reduction: dim; increase: bright; other: white green
    "easy": ("EZ", 0.55), "nofail": ("NF", 0.55), "halftime": ("HT", 0.55), "spunout": ("SO", 0.55),
    "hardrock": ("HR", 1.0), "suddendeath": ("SD", 1.0), "perfect": ("PF", 1.0), "doubletime": ("DT", 1.0),
    "nightcore": ("NC", 1.0), "hidden": ("HD", 1.0), "flashlight": ("FL", 1.0), "fadein": ("FI", 1.0),
    "mirror": ("MR", 1.0), "random": ("RD", 1.0),
    "relax": ("RX", "w"), "relax2": ("AP", "w"), "autoplay": ("AT", "w"), "cinema": ("CN", "w"),
    "scorev2": ("V2", "w"), "target": ("TP", "w"), "touchdevice": ("TD", "w"),
    "freemodallowed": ("FM", "w"), "keycoop": ("CO", "w"),
}
MODS.update({f"key{n}": (f"{n}K", 1.0) for n in range(1, 10)})


def mod_icons():
    for name, (code, tier) in MODS.items():
        col = rgba((220, 255, 220)) if tier == "w" else rgba(GRN, tier)
        c = C(64, 64)
        c.rect(6, 6, 58, 58, fill=rgba((0, 0, 0), 0.9), outline=rgba(GRN, 0.34))
        c.brackets(6, 6, 58, 58, 10, col, 2)
        c.text(code, 32, 33, 26, col)
        c.glow(1.5, 1.1)
        c.save(f"selection-mod-{name}")


def extras():
    """Remaining elements from the wiki list that would fall back to default."""
    sel = C(128, 128)
    sel.ring(64, 64, 60, 3, rgba(WHITE))
    sel.save("hitcircleselect")

    blank("cursor-ripple")

    text_img("multi-skipped", "skip", 18, rgba(WHITE, 0.8), pad=4, glow=0)
    text_img("score-pp", "pp", 40, rgba(WHITE), pad=4, glow=2)
    text_img("ranking-winner", "winner", 48, rgba(GRN))

    rf = C(25, 25)
    rf.rect(4, 4, 21, 21, outline=rgba(GRN), width=2)
    rf.save("rank-forum")


# ---------------------------------------------------------------- skin.ini

SKIN_INI = """[General]
Name: P1
Author: pax
Version: 2.7
AnimationFramerate: -1
AllowSliderBallTint: 1
ComboBurstRandom: 0
CursorCentre: 1
CursorExpand: 0
CursorRotate: 0
CursorTrailRotate: 0
HitCircleOverlayAboveNumber: 0
LayeredHitSounds: 1
SliderBallFlip: 0
SpinnerFadePlayfield: 1
SpinnerFrequencyModulate: 0
SpinnerNoBlink: 1

[Colours]
Combo1: 0,255,0
Combo2: 0,165,0
Combo3: 0,95,0
InputOverlayText: 0,255,0
MenuGlow: 0,255,0
SliderBorder: 26,26,26
SliderTrackOverride: 14,14,14
SongSelectActiveText: 0,255,0
SongSelectInactiveText: 0,170,0
SpinnerBackground: 0,0,0
StarBreakAdditive: 0,255,0

[Fonts]
HitCirclePrefix: default
HitCircleOverlap: 4
ScorePrefix: score
ScoreOverlap: 4
ComboPrefix: score
ComboOverlap: 4
"""


def main():
    global OUT
    ap = argparse.ArgumentParser(description="Render the P1 osu!stable skin.")
    ap.add_argument("out", type=Path, help="output skin folder")
    ap.add_argument("--assets", type=Path, help="existing skin to take all sounds and the cursor trail from")
    ap.add_argument("--hitsounds", type=Path, help="existing skin whose gameplay sounds replace --assets' ones")
    ap.add_argument("--osk", type=Path, help="also pack the finished skin into this .osk file")
    args = ap.parse_args()
    OUT = args.out
    OUT.mkdir(parents=True, exist_ok=True)
    cursor(args.assets)
    for f in (hitcircles, sliders, judgements, spinner, scorebar, score_fonts,
              input_overlay, playfield, pause_screens, ranking, menu_background,
              song_select, modes, mod_icons, extras):
        f()
    (OUT / "skin.ini").write_text(SKIN_INI)
    if args.assets:
        for snd in args.assets.iterdir():
            if snd.suffix.lower() in (".wav", ".ogg", ".mp3"):
                shutil.copy2(snd, OUT / snd.name)
    if args.hitsounds:
        # Gameplay sounds from --hitsounds replace the --assets ones entirely: same
        # names in another extension, or numbered variants, would mix sets.
        hit = re.compile(r"^((normal|soft|drum)-(hit|slider)|nightcore-|combobreak)", re.I)
        for f in OUT.iterdir():
            if f.suffix.lower() in (".wav", ".ogg", ".mp3") and hit.match(f.name):
                f.unlink()
        for snd in args.hitsounds.rglob("*"):
            if snd.suffix.lower() in (".wav", ".ogg", ".mp3") and hit.match(snd.name):
                shutil.copy2(snd, OUT / snd.name)
    print(f"{sum(1 for _ in OUT.iterdir())} files in {OUT}")
    if args.osk:
        # An .osk is a zip of the skin folder's files; osu! imports it on open.
        with zipfile.ZipFile(args.osk, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(OUT.iterdir()):
                z.write(f, f.name)
        print(f"packed {args.osk}")


if __name__ == "__main__":
    main()

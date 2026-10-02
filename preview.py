#!/usr/bin/env python3
"""Render an asset sheet of a built skin.

Usage: preview.py SKIN_DIR OUT_PNG

Lays the skin's own @2x images out in labelled groups on black. Elements the
game tints are multiplied by the combo colours, the way osu! draws them.
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W = 1600
PAD = 48
COMBOS = [(0, 255, 0), (255, 40, 170), (170, 60, 255)]
LABEL = (0, 170, 0)
DIM = (0, 90, 0)


def font(size):
    path = subprocess.run(["fc-match", "-f", "%{file}", "Terminess Nerd Font Mono"],
                          capture_output=True, text=True).stdout.strip()
    return ImageFont.truetype(path, size)


def load(skin, name, height=None):
    path = skin / f"{name}@2x.png"
    im = Image.open(path if path.exists() else skin / f"{name}.png").convert("RGBA")
    if height:
        im = im.resize((max(1, im.width * height // im.height), height), Image.LANCZOS)
    return im


def tint(im, c):
    r, g, b, a = im.split()
    return Image.merge("RGBA", tuple(ch.point(lambda v, k=k: v * k // 255) for ch, k in zip((r, g, b), c)) + (a,))


class Sheet:
    def __init__(self):
        self.items = []          # (title, [(image, caption)])

    def group(self, title, entries):
        self.items.append((title, entries))

    def render(self, out):
        f_title, f_cap, f_head = font(26), font(17), font(64)
        rows = []                # (title, [lines of (im, cap)]) with wrapping
        for title, entries in self.items:
            lines, line, x = [], [], PAD
            for im, cap in entries:
                w = max(im.width, int(f_cap.getlength(cap)))
                if line and x + w > W - PAD:
                    lines.append(line); line, x = [], PAD
                line.append((im, cap)); x += w + 36
            lines.append(line)
            rows.append((title, lines))
        height = 170 + sum(56 + sum(max(im.height for im, _ in ln) + 44 for ln in lines) for _, lines in rows)
        sheet = Image.new("RGBA", (W, height), (0, 0, 0, 255))
        d = ImageDraw.Draw(sheet)
        d.text((PAD, 40), "P1", font=f_head, fill=(0, 255, 0))
        d.text((PAD + 110, 64), "osu!stable skin rendered from code", font=f_title, fill=LABEL)
        y = 150
        for title, lines in rows:
            d.text((PAD, y), title, font=f_title, fill=LABEL)
            d.line([(PAD + f_title.getlength(title) + 16, y + 16), (W - PAD, y + 16)], fill=DIM, width=1)
            y += 56
            for ln in lines:
                h = max(im.height for im, _ in ln)
                x = PAD
                for im, cap in ln:
                    w = max(im.width, int(f_cap.getlength(cap)))
                    sheet.alpha_composite(im, (x + (w - im.width) // 2, y + (h - im.height) // 2))
                    d.text((x + w // 2, y + h + 8), cap, font=f_cap, fill=LABEL, anchor="mt")
                    x += w + 36
                y += h + 44
        sheet.convert("RGB").save(out, optimize=True)
        print(f"wrote {out} ({W}x{height})")


def main():
    skin, out = Path(sys.argv[1]), Path(sys.argv[2])
    s = Sheet()

    hit = load(skin, "hitcircle", 140)
    circles = []
    for i, c in enumerate(COMBOS):
        im = tint(hit, c)
        num = load(skin, f"default-{i + 1}", 60)
        im.alpha_composite(num, ((im.width - num.width) // 2, (im.height - num.height) // 2))
        circles.append((im, f"combo {i + 1}"))
    s.group("hit circles", circles + [
        (tint(load(skin, "approachcircle", 140), COMBOS[0]), "approach"),
        (tint(load(skin, "sliderb", 120), COMBOS[0]), "slider ball"),
        (load(skin, "sliderfollowcircle", 170), "follow circle"),
        (load(skin, "reversearrow", 120), "reverse"),
        (load(skin, "cursor", 90), "cursor"),
        (load(skin, "cursortrail", 55), "trail"),
        (load(skin, "cursor-smoke", 40), "smoke"),
    ])
    # Assembled the way osu! layers the new style spinner (wiki order, bottom to
    # top): glow (tinted cyan, additive), bottom, top, middle2, middle (tinted
    # white at the start, red as time runs out), then the approach circle.
    size = 260
    full = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow = tint(load(skin, "spinner-glow", size), (0, 255, 255))
    full = Image.alpha_composite(full, glow)
    for name, h in (("spinner-bottom", size), ("spinner-top", size), ("spinner-middle2", 22), ("spinner-middle", 86)):
        im = load(skin, name, h)
        full.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    ap = load(skin, "spinner-approachcircle", 200)
    full.alpha_composite(ap, ((size - ap.width) // 2, (size - ap.height) // 2))
    s.group("spinner", [
        (full, "assembled"),
        (tint(load(skin, "spinner-glow", 150), (0, 255, 255)), "glow (tinted)"),
        (load(skin, "spinner-bottom", 150), "bottom"),
        (load(skin, "spinner-top", 150), "top"),
        (load(skin, "spinner-middle", 70), "middle"),
        (tint(load(skin, "spinner-middle", 70), (255, 70, 70)), "middle (late)"),
        (load(skin, "spinner-middle2", 40), "middle2"),
        (load(skin, "spinner-approachcircle", 150), "approach"),
        (load(skin, "spinner-circle", 150), "circle (taiko)"),
        (load(skin, "spinner-rpm", 56), "rpm"),
        (load(skin, "spinner-clear", 70), "clear"),
        (load(skin, "spinner-spin", 56), "spin"),
    ])
    s.group("judgements", [
        (load(skin, "hit100", 64), "100"),
        (load(skin, "hit50", 64), "50"),
        (load(skin, "hit0", 80), "miss"),
        (load(skin, "section-pass", 100), "pass"),
        (load(skin, "section-fail", 100), "fail"),
    ])

    digits = Image.new("RGBA", (1, 1))
    glyphs = [load(skin, f"score-{k}", 60) for k in "0123456789"] + [load(skin, "score-dot", 60), load(skin, "score-percent", 60), load(skin, "score-x", 60)]
    digits = Image.new("RGBA", (sum(g.width - 4 for g in glyphs), 60))
    x = 0
    for g in glyphs:
        digits.alpha_composite(g, (x, 0)); x += g.width - 4
    bar = load(skin, "scorebar-bg", 40)
    fill = load(skin, "scorebar-colour", 12)
    bar.alpha_composite(fill.crop((0, 0, int(bar.width * 0.62), fill.height)), (int(bar.width * 0.015), (bar.height - fill.height) // 2))
    s.group("hud", [
        (bar, "health"),
        (digits, "score font"),
        (tint(load(skin, "inputoverlay-key", 60), (255, 255, 255)), "key"),
        (tint(load(skin, "inputoverlay-key", 60), (255, 220, 0)), "key pressed"),
    ])
    s.group("grades", [(load(skin, f"ranking-{g}", 150), lbl) for g, lbl in
                       (("XH", "SS silver"), ("X", "SS"), ("SH", "S silver"), ("S", "S"), ("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"))])
    s.group("mods", [(load(skin, f"selection-mod-{m}", 80), m) for m in
                     ("easy", "nofail", "halftime", "hardrock", "suddendeath", "doubletime", "hidden", "flashlight", "relax", "autoplay")])
    s.group("menus", [
        (load(skin, "menu-back", 70), "back"),
        (load(skin, "play-skip", 70), "skip"),
        (load(skin, "pause-continue", 56), "pause"),
        (load(skin, "mode-osu", 90), "mode"),
        (load(skin, "ranking-retry", 56), "retry"),
    ])
    s.render(out)


if __name__ == "__main__":
    main()

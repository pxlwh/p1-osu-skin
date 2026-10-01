#!/usr/bin/env python3
"""Render a gameplay-style preview of a built skin.

Usage: preview.py SKIN_DIR OUT_PNG

Composes one frame from the skin's own @2x images: a stream into a repeating
slider, approach circles, follow points, the HUD, and a few mod icons. Tinted
elements are multiplied by a combo colour the way osu! does it.
"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 1600, 900
CIRCLE = 150                       # on-screen hit circle size in this frame
COMBOS = [(0, 255, 0), (0, 165, 0), (0, 95, 0)]
TRACK, BORDER = (14, 14, 14), (26, 26, 26)   # skin.ini SliderTrackOverride / SliderBorder


def load(skin, name, size=None):
    im = Image.open(skin / f"{name}@2x.png").convert("RGBA")
    return im.resize(size, Image.LANCZOS) if size else im


def tint(im, c):
    r, g, b, a = im.split()
    return Image.merge("RGBA", tuple(ch.point(lambda v, k=k: v * k // 255) for ch, k in zip((r, g, b), c)) + (a,))


def paste(dst, im, x, y):
    dst.alpha_composite(im, (round(x - im.width / 2), round(y - im.height / 2)))


def bezier(p0, p1, p2, n=200):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


def slider_body(dst, pts, radius, border):
    """Stamp discs along the path: border colour first, track on top."""
    d = ImageDraw.Draw(dst)
    for col, r in ((BORDER, radius), (TRACK, radius - border)):
        for x, y in pts:
            d.ellipse((x - r, y - r, x + r, y + r), fill=col)


def main():
    skin, out = Path(sys.argv[1]), Path(sys.argv[2])
    frame = Image.open(skin / "menu-background@2x.jpg").convert("RGBA").resize((W, H))
    frame.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 170)))

    hit = load(skin, "hitcircle", (CIRCLE, CIRCLE))
    approach = load(skin, "approachcircle")
    fp = Image.open(skin / "followpoint.png").convert("RGBA")   # @1x: in-game dash size at this scale

    # objects: three circles, then a repeating slider; combo colour steps every 2 objects
    circles = [(300, 600), (470, 470), (660, 430)]
    s0, s1, s2 = (860, 470), (1080, 330), (1290, 470)
    path = bezier(s0, s1, s2)
    objs = circles + [s0]

    # follow points between consecutive objects
    for (ax, ay), (bx, by) in zip(objs, objs[1:]):
        dist = math.hypot(bx - ax, by - ay)
        ang = math.degrees(math.atan2(-(by - ay), bx - ax))
        rot = fp.rotate(ang, expand=True, resample=Image.BICUBIC)
        edge = (CIRCLE / 2 + 12) / dist          # dashes run between circle edges only
        for k in range(1, int(dist // 34) + 1):
            t = k * 34 / dist
            if edge < t < 1 - edge:
                paste(frame, rot, ax + (bx - ax) * t, ay + (by - ay) * t)

    slider_body(frame, path, radius=CIRCLE * 0.47, border=CIRCLE * 0.05)

    # reverse arrow at the tail, pointing back along the path
    tx, ty = path[-1]
    bx, by = path[-12]
    ang = math.degrees(math.atan2(-(by - ty), bx - tx))
    paste(frame, load(skin, "reversearrow", (CIRCLE, CIRCLE)).rotate(ang, resample=Image.BICUBIC), tx, ty)

    for i, (x, y) in enumerate(objs):
        c = COMBOS[(i // 2) % len(COMBOS)]
        paste(frame, tint(hit, c), x, y)
        num = load(skin, f"default-{i + 1}")
        paste(frame, num.resize((num.width * CIRCLE // 256, num.height * CIRCLE // 256)), x, y)

    # the next object to hit gets its approach circle
    ax, ay = circles[0]
    paste(frame, tint(approach, COMBOS[0]).resize((CIRCLE + 70,) * 2), ax, ay)

    # slider ball partway along, with follow circle and the cursor on it
    bx, by = path[110]
    sc = COMBOS[(len(circles) // 2) % len(COMBOS)]
    paste(frame, tint(load(skin, "sliderb", (int(CIRCLE * 0.9),) * 2), sc), bx, by)
    paste(frame, load(skin, "sliderfollowcircle", (int(CIRCLE * 2),) * 2), bx, by)
    paste(frame, load(skin, "cursor"), bx, by)

    # judgements on earlier objects
    paste(frame, load(skin, "hit100"), 150, 470)
    paste(frame, load(skin, "hit0"), 130, 640)

    # HUD: health bar top left, score and accuracy top right, combo bottom left
    sb = load(skin, "scorebar-bg")
    frame.alpha_composite(sb.resize((sb.width * 3 // 4, sb.height * 3 // 4)), (10, 10))
    col = load(skin, "scorebar-colour").crop((0, 0, 820, 16))
    frame.alpha_composite(col.resize((615, 12)), (19, 19))

    def number(text, x, y, scale, right=True):
        glyphs = []
        for ch in text:
            key = {"%": "percent", ".": "dot", ",": "comma", "x": "x"}.get(ch, ch)
            g = load(skin, f"score-{key}")
            glyphs.append(g.resize((g.width * scale // 100, g.height * scale // 100)))
        width = sum(g.width - 4 for g in glyphs)
        cx = x - width if right else x
        for g in glyphs:
            frame.alpha_composite(g, (cx, y))
            cx += g.width - 4

    number("00428170", W - 20, 16, 66)
    number("98.42%", W - 20, 78, 40)
    number("127x", 24, H - 110, 75, right=False)

    for i, m in enumerate(("hidden", "hardrock", "doubletime")):
        frame.alpha_composite(load(skin, f"selection-mod-{m}", (84, 84)), (W - 300 + i * 94, 130))

    frame.convert("RGB").save(out, optimize=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

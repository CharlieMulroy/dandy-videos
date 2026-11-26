"""Video 17, The Thanksgiving Metaphor: Dandy explained with pilgrims. Vertical 1080x1920.

Usage:  python3 videos/17-thanksgiving/plymouth/render_plymouth.py [--preview] [--stills] [--final]

Charlie talks fast over a storybook Plymouth, 1621, cut on his words. The feast is your project and the pilgrims
are your AI agents: hard workers who wake up every morning having forgotten everything. Three pots of corn, no
turkey, the feast moved a day, and nobody told the guy with the pie. Dandy is the scroll nailed to the wall, the
only purple thing in the film: every dish, who is on it, what it needs, what is done. Pilgrims check it before
they cook and update it after; move the feast and they all know; run out of an ingredient and every dish that
depends on it is flagged. Same pilgrims, and the feast happens.

Metaphor video: its own look (cut paper, autumn colours), no Dandy Man, end card without him. The cast is the
pilgrims and one turkey. Built on render/stage.py for captions, sound, the finish pass and the render loop.
Scene times are cut to Charlie's recording (voiceover/plymouth.json holds the word times).
"""
import argparse
import functools
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(VIDEO, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "render"))
import stage as S  # noqa: E402
from stage import clamp, ease_out, smooth, lerp, mix  # noqa: E402

W, H = S.W, S.H
VO = os.path.join(VIDEO, "voiceover", "plymouth.json")
BITTER = "/usr/share/fonts/truetype/google-fonts/ofl/bitter/Bitter[wght].ttf"

# ---------------------------------------------------------------- palette (autumn paper; purple is Dandy's alone)
INK = (52, 34, 28)
CREAM = (255, 244, 222)
PAPER = (246, 228, 190)
WOOD, WOOD_D, WOOD_L = (146, 96, 58), (104, 64, 40), (176, 122, 76)
LEAF = [(214, 96, 40), (232, 150, 52), (190, 64, 38), (240, 188, 80)]
RED = (196, 52, 40)
BUCKLE = (236, 200, 96)
DANDY, DANDY_HI = S.PURPLE, S.PURPLE_HI
SKIES = {   # sky top, sky bottom, far hill, near hill, ground top, ground bottom, light tint, tint amount
    "day": ((252, 226, 176), (245, 184, 122), (204, 124, 64), (172, 94, 50), (182, 134, 70), (150, 104, 56), (255, 255, 255), 0.0),
    "dawn": ((116, 108, 156), (250, 176, 132), (170, 104, 84), (140, 80, 64), (160, 116, 76), (128, 90, 60), (255, 190, 150), 0.12),
    "eve": ((98, 72, 118), (242, 146, 92), (150, 84, 60), (120, 64, 48), (146, 100, 62), (112, 76, 50), (255, 170, 110), 0.14),
    "dusk": ((30, 36, 76), (98, 84, 128), (60, 56, 88), (48, 44, 72), (74, 66, 80), (54, 48, 64), (90, 100, 170), 0.42),
}


@functools.lru_cache(None)
def bitter(size, weight=800):
    f = ImageFont.truetype(BITTER, int(size))
    f.set_variation_by_axes([weight])
    return f


# ---------------------------------------------------------------- drawing at 3x, then shrunk, so paper edges are clean
class D:
    def __init__(self, im, k):
        self.im, self.d, self.k = im, ImageDraw.Draw(im, "RGBA"), k

    def _s(self, pts):
        return [v * self.k for p in pts for v in p]

    def ell(self, cx, cy, rx, ry=None, fill=None, outline=None, width=0):
        ry = rx if ry is None else ry
        self.d.ellipse(self._s([(cx - rx, cy - ry), (cx + rx, cy + ry)]), fill=fill, outline=outline, width=int(width * self.k))

    def rect(self, x0, y0, x1, y1, fill=None, r=0, outline=None, width=0):
        self.d.rounded_rectangle(self._s([(x0, y0), (x1, y1)]), radius=r * self.k, fill=fill, outline=outline, width=int(width * self.k))

    def poly(self, pts, fill):
        self.d.polygon(self._s(pts), fill=fill)

    def line(self, pts, fill, width):
        self.d.line(self._s(pts), fill=fill, width=int(width * self.k), joint="curve")
        for p in (pts[0], pts[-1]):
            self.ell(p[0], p[1], width / 2, fill=fill)

    def pie(self, cx, cy, r, a0, a1, fill):
        self.d.pieslice(self._s([(cx - r, cy - r), (cx + r, cy + r)]), a0, a1, fill=fill)

    def arc(self, cx, cy, rx, ry, a0, a1, fill, width):
        self.d.arc(self._s([(cx - rx, cy - ry), (cx + rx, cy + ry)]), a0, a1, fill=fill, width=int(width * self.k))

    def text(self, x, y, s, size, fill, weight=800, anchor="mm"):
        self.d.text((x * self.k, y * self.k), s, font=bitter(size * self.k, weight), fill=fill, anchor=anchor)


def sprite(w, h, fn, k=3):
    im = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    fn(D(im, k))
    return im.resize((w, h), Image.LANCZOS)


def put(img, spr, x, y, scale=1.0, flip=False, rot=0.0, alpha=1.0, anchor="feet"):
    """Paste a sprite with its feet (bottom centre) or its centre at (x, y)."""
    if alpha <= 0.01 or scale <= 0.01:
        return
    if flip:
        spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
    if abs(scale - 1) > 0.01:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if abs(rot) > 0.3:
        spr = spr.rotate(rot, Image.BILINEAR, expand=True)
    if alpha < 0.99:
        spr = spr.copy()
        spr.putalpha(spr.split()[3].point(lambda v: int(v * alpha)))
    ox = int(x - spr.width / 2)
    oy = int(y - spr.height) if anchor == "feet" else int(y - spr.height / 2)
    if ox >= img.width or oy >= img.height or ox + spr.width <= 0 or oy + spr.height <= 0:
        return
    img.alpha_composite(spr, (max(ox, 0), max(oy, 0)), (max(-ox, 0), max(-oy, 0)))


def shadow(img, x, y, rx, a=70):
    ImageDraw.Draw(img, "RGBA").ellipse((x - rx, y - rx * 0.18, x + rx, y + rx * 0.18), fill=(40, 24, 16, a))


# ---------------------------------------------------------------- the cast
KINDS = [  # coat, skin, headwear
    ((38, 34, 40), (240, 200, 160), "hat"),
    ((98, 62, 44), (200, 148, 106), "hat"),
    ((62, 76, 64), (234, 186, 150), "bonnet"),
    ((72, 72, 86), (146, 100, 72), "hat"),
]
PW, PH = 280, 400


def _q(a, step=10):
    return int(round(a / step) * step)


@functools.lru_cache(None)
def _pilgrim(kind, la, ra, step, face, hold):
    coat, skin, head = KINDS[kind]
    dress = head == "bonnet"

    def draw(d):
        cx = 140
        for i, lx in enumerate((cx - 20, cx + 20)):   # legs: the stepping one lifts
            up = 14 if (step == 1 and i == 0) or (step == 2 and i == 1) else 0
            d.rect(lx - 9, 312, lx + 9, 362 - up, fill=(236, 228, 212))
            d.ell(lx + 5, 366 - up, 19, 11, fill=(30, 24, 26))
            d.rect(lx + 2, 358 - up, lx + 14, 368 - up, fill=BUCKLE, r=2)
        if dress:
            d.poly([(cx - 40, 184), (cx + 40, 184), (cx + 70, 344), (cx - 70, 344)], fill=coat)
            d.poly([(cx - 26, 232), (cx + 26, 232), (cx + 36, 338), (cx - 36, 338)], fill=(244, 238, 226))
        else:
            d.poly([(cx - 40, 184), (cx + 40, 184), (cx + 54, 322), (cx - 54, 322)], fill=coat)
            d.rect(cx - 50, 262, cx + 50, 278, fill=mix(coat, (0, 0, 0), 0.45))
            d.rect(cx - 13, 257, cx + 13, 283, fill=BUCKLE, r=3)
            d.rect(cx - 6, 264, cx + 6, 276, fill=mix(coat, (0, 0, 0), 0.45))
        for side, ang in ((-1, la), (1, ra)):       # arms: 0 hangs down, 90 points out, 180 straight up
            sx, sy = cx + side * 38, 198
            r = math.radians(ang)
            ex, ey = sx + side * math.sin(r) * 78, sy + math.cos(r) * 78
            d.line([(sx, sy), (ex, ey)], fill=coat, width=28)
            d.ell(lerp(sx, ex, 0.86), lerp(sy, ey, 0.86), 16, fill=(244, 238, 226))
            d.ell(ex, ey, 14, fill=skin)
        d.rect(cx - 46, 170, cx + 46, 206, fill=(248, 244, 234), r=16)
        d.poly([(cx - 6, 170), (cx + 6, 170), (cx, 196)], fill=coat)
        d.ell(cx, 124, 50, fill=skin)
        d.ell(cx - 26, 136, 9, 6, fill=mix(skin, (230, 110, 90), 0.4))
        d.ell(cx + 26, 136, 9, 6, fill=mix(skin, (230, 110, 90), 0.4))
        ey = 120
        if face == "o":
            d.ell(cx - 17, ey, 8, fill=(255, 255, 255))
            d.ell(cx + 17, ey, 8, fill=(255, 255, 255))
            d.ell(cx - 17, ey, 4, fill=INK)
            d.ell(cx + 17, ey, 4, fill=INK)
            d.ell(cx, 148, 7, 9, fill=INK)
        else:
            d.ell(cx - 17, ey, 5.5, fill=INK)
            d.ell(cx + 17, ey, 5.5, fill=INK)
            if face == "smile":
                d.arc(cx, 138, 15, 12, 20, 160, fill=INK, width=4)
            elif face == "grin":
                d.pie(cx, 138, 15, 0, 180, fill=INK)
            else:
                d.line([(cx - 10, 148), (cx + 10, 148)], fill=INK, width=4)
        if head == "hat":
            d.ell(cx, 84, 68, 13, fill=(26, 22, 26))
            d.poly([(cx - 36, 84), (cx + 36, 84), (cx + 29, 8), (cx - 29, 8)], fill=(26, 22, 26))
            d.rect(cx - 35, 58, cx + 35, 76, fill=(70, 58, 52))
            d.rect(cx - 12, 54, cx + 12, 80, fill=BUCKLE, r=3)
            d.rect(cx - 5, 61, cx + 5, 73, fill=(70, 58, 52))
        else:
            d.pie(cx, 118, 58, 180, 360, fill=(248, 244, 234))
            d.rect(cx - 58, 110, cx + 58, 124, fill=(248, 244, 234), r=6)
        if hold:
            d.im.alpha_composite(item(hold, 3).resize((int(150 * d.k), int(150 * d.k)), Image.LANCZOS), (int((cx - 75) * d.k), int(196 * d.k)))
    return sprite(PW, PH, draw)


def pilgrim(kind=0, la=15, ra=15, step=0, face="smile", hold=None):
    if hold:
        la, ra = 40, 40
    return _pilgrim(kind, _q(la), _q(ra), step, face, hold)


@functools.lru_cache(None)
def turkey(step=0, peck=0):
    def draw(d):
        for i, a in enumerate(range(186, 354, 21)):
            d.pie(130, 170, 128, a, a + 21, fill=LEAF[i % 4])
        d.pie(130, 170, 86, 186, 354, fill=(120, 66, 40))
        for i, lx in enumerate((118, 150)):
            up = 12 if step == i + 1 else 0
            d.line([(lx, 236), (lx, 280 - up)], fill=(226, 150, 50), width=8)
            d.line([(lx - 12, 282 - up), (lx + 16, 282 - up)], fill=(226, 150, 50), width=7)
        d.ell(138, 190, 78, 62, fill=(122, 74, 44))
        d.ell(120, 196, 44, 34, fill=(150, 96, 56))
        hx, hy = (236, 196) if peck else (228, 92)
        d.line([(196, 160), (hx - 6, hy + 14)], fill=(122, 74, 44), width=30)
        d.ell(hx, hy, 26, fill=(176, 92, 72))
        d.poly([(hx + 20, hy - 8), (hx + 54, hy + 4), (hx + 20, hy + 12)], fill=(240, 190, 70))
        d.ell(hx + 16, hy + 26, 9, 17, fill=RED)
        d.ell(hx + 6, hy - 6, 7, fill=(255, 255, 255))
        d.ell(hx + 8, hy - 6, 3.5, fill=INK)
    return sprite(300, 300, draw)


@functools.lru_cache(None)
def item(name, k=3):
    def pot(d):
        d.ell(75, 62, 46, 16, fill=(240, 196, 70))
        for i in range(7):
            d.ell(42 + i * 11, 58 + (i % 2) * 5, 8, 6, fill=(250, 216, 96))
        d.pie(75, 62, 54, 0, 180, fill=(40, 38, 46))
        d.rect(17, 54, 133, 68, fill=(58, 56, 66), r=7)
        d.arc(75, 60, 60, 40, 200, 340, fill=(58, 56, 66), width=5)
        d.rect(48, 110, 58, 128, fill=(40, 38, 46))
        d.rect(92, 110, 102, 128, fill=(40, 38, 46))

    def platter(d):
        d.ell(75, 104, 70, 20, fill=(206, 206, 214))
        d.ell(75, 101, 58, 14, fill=(232, 232, 238))

    def roast(d):
        platter(d)
        d.ell(75, 78, 46, 32, fill=(168, 92, 44))
        d.ell(64, 68, 22, 12, fill=(198, 122, 62))
        for sx in (-1, 1):
            d.line([(75 + sx * 34, 86), (75 + sx * 58, 62)], fill=(168, 92, 44), width=20)
            d.ell(75 + sx * 62, 56, 7, fill=(248, 240, 226))

    def pie(d):
        d.poly([(22, 84), (128, 84), (112, 116), (38, 116)], fill=(170, 170, 180))
        d.ell(75, 82, 56, 18, fill=(214, 150, 76))
        d.ell(75, 80, 42, 11, fill=(196, 104, 44))
        for i in range(-2, 3):
            d.line([(75 + i * 16, 71), (75 + i * 16, 89)], fill=(226, 170, 96), width=5)

    def bread(d):
        d.rect(30, 70, 120, 116, fill=(236, 190, 84), r=10)
        d.rect(30, 70, 120, 84, fill=(206, 150, 56), r=8)

    def corn(d):
        d.poly([(26, 70), (124, 70), (110, 122), (40, 122)], fill=(150, 104, 60))
        for i in range(5):
            d.ell(40 + i * 18, 62 - (i % 2) * 12, 9, 24, fill=(246, 206, 80))
            d.ell(40 + i * 18, 76 - (i % 2) * 12, 11, 12, fill=(120, 150, 70))
        d.rect(24, 66, 126, 80, fill=(170, 122, 72), r=6)

    def basket(d):   # the corn basket, empty
        d.poly([(26, 70), (124, 70), (110, 122), (40, 122)], fill=(150, 104, 60))
        d.rect(24, 66, 126, 80, fill=(170, 122, 72), r=6)

    def fire(d):
        d.line([(30, 136), (120, 118)], fill=WOOD_D, width=14)
        d.line([(30, 118), (120, 136)], fill=WOOD, width=14)
        d.poly([(40, 124), (58, 60), (72, 96), (84, 40), (100, 92), (112, 66), (112, 124)], fill=(240, 120, 40))
        d.poly([(58, 124), (72, 86), (82, 104), (90, 76), (98, 124)], fill=(252, 206, 90))

    def hat(d):
        d.ell(75, 104, 60, 12, fill=(26, 22, 26))
        d.poly([(43, 104), (107, 104), (100, 36), (50, 36)], fill=(26, 22, 26))
        d.rect(44, 80, 106, 96, fill=(70, 58, 52))
        d.rect(64, 76, 86, 100, fill=BUCKLE, r=3)
        d.rect(70, 82, 80, 94, fill=(70, 58, 52))
    fn = dict(pot=pot, platter=platter, roast=roast, pie=pie, bread=bread, corn=corn, basket=basket, fire=fire, hat=hat)[name]
    return sprite(150, 150, fn, k)


@functools.lru_cache(None)
def ship():
    def draw(d):
        d.poly([(60, 300), (460, 300), (420, 380), (110, 380)], fill=WOOD_D)
        d.poly([(40, 262), (480, 262), (460, 306), (60, 306)], fill=WOOD)
        d.rect(380, 214, 470, 266, fill=WOOD, r=6)
        for mx, top in ((170, 40), (290, 20), (400, 90)):
            d.rect(mx - 6, top, mx + 6, 266, fill=WOOD_D)
        for mx, top, w in ((170, 60, 120), (290, 40, 150), (400, 110, 90)):
            d.poly([(mx - w / 2, top), (mx + w / 2, top), (mx + w / 2 + 12, top + 96), (mx - w / 2 - 12, top + 96)], fill=CREAM)
            d.poly([(mx - w / 2 + 10, top + 108), (mx + w / 2 - 10, top + 108), (mx + w / 2, top + 176), (mx - w / 2, top + 176)], fill=(244, 230, 204))
        d.poly([(290, 20), (290, 0), (336, 10)], fill=RED)
    return sprite(520, 400, draw, 2)


@functools.lru_cache(None)
def mark(ch, size, color):
    """A big ? or ! with a dark edge, so it reads on any backdrop."""
    f = bitter(size, 900)
    w = int(f.getlength(ch) + size * 0.5)
    im = Image.new("RGBA", (w, int(size * 1.4)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((w / 2, size * 0.7), ch, font=f, fill=color, anchor="mm", stroke_width=max(4, size // 14), stroke_fill=INK)
    return im


def pop(t, at, d=0.22):
    """0 before `at`, overshoots to about 1.15, settles at 1."""
    p = (t - at) / d
    if p <= 0:
        return 0.0
    if p >= 1.6:
        return 1.0
    return min(1.0, p) * (1 + 0.28 * math.sin(min(p, 1.6) / 1.6 * math.pi))


# ---------------------------------------------------------------- backdrops (drawn once each)
def _sky(c0, c1, y1=1000):
    arr = np.zeros((H, W, 3), np.float32)
    g = np.clip(np.arange(H) / y1, 0, 1)[:, None]
    for i in range(3):
        arr[:, :, i] = c0[i] + (c1[i] - c0[i]) * g
    return Image.fromarray(arr.astype(np.uint8)).convert("RGBA")


def _tree(d, x, y, s, rnd, dark=0.0):
    d.rect(x - 9 * s, y - 90 * s, x + 9 * s, y, fill=mix(WOOD_D, (20, 16, 30), dark))
    for dx, dy, r in ((0, -150, 62), (-44, -112, 50), (44, -116, 52), (0, -100, 56)):
        d.ell(x + dx * s, y + dy * s, r * s, fill=mix(rnd.choice(LEAF), (30, 26, 60), dark))


def _cabin(d, x, y, w, h, lit=False, dark=0.0):
    wall = mix(WOOD, (30, 26, 56), dark)
    d.poly([(x - 26, y - h), (x + w / 2, y - h - w * 0.36), (x + w + 26, y - h)], fill=mix((84, 50, 36), (20, 18, 40), dark))
    n = max(3, int(h // 36))
    for i in range(n):
        yy = y - h + i * h / n
        d.rect(x, yy + 2, x + w, yy + h / n - 2, fill=mix(wall, (0, 0, 0), 0.10 * (i % 2)), r=10)
    d.rect(x + w * 0.38, y - h * 0.62, x + w * 0.62, y, fill=mix((84, 50, 36), (20, 18, 40), dark), r=6)
    d.rect(x + w * 0.12, y - h * 0.62, x + w * 0.3, y - h * 0.3, fill=(255, 210, 120) if lit else mix((70, 86, 110), (20, 18, 40), dark), r=4)


@functools.lru_cache(None)
def backdrop(kind, mood="day"):
    c0, c1, hill_f, hill_n, g0, g1, tint, amt = SKIES[mood]
    dark = {"day": 0.0, "dawn": 0.15, "eve": 0.2, "dusk": 0.55}[mood]
    rnd = random.Random(hash(kind) % 1000 + 3)
    k = 2
    big = Image.new("RGBA", (W * k, H * k), (0, 0, 0, 0))
    d = D(big, k)
    base = _sky(c0, c1)
    hz = 900
    if kind == "wall":   # a log wall, close
        for i in range(18):
            d.rect(-20, i * 112, W + 20, i * 112 + 106, fill=mix(WOOD, (0, 0, 0), 0.07 * (i % 2)), r=40)
            d.line([(60 + (i * 197) % 700, i * 112 + 54), (260 + (i * 197) % 700, i * 112 + 56)], fill=mix(WOOD, (0, 0, 0), 0.2), width=4)
            d.ell(900 - (i * 263) % 800, i * 112 + 52, 16, 10, fill=mix(WOOD, (0, 0, 0), 0.22))
        base = Image.new("RGBA", (W, H), WOOD_D + (255,))
    else:
        if mood == "dusk":
            d.ell(820, 380, 60, fill=(244, 240, 220))
            d.ell(846, 366, 52, fill=c0)
            for _ in range(40):
                d.ell(rnd.uniform(0, W), rnd.uniform(0, 700), rnd.uniform(1.5, 3.5), fill=(240, 236, 220, 200))
        elif mood in ("dawn", "eve"):
            d.ell(250 if mood == "dawn" else 830, hz - 40, 120, fill=(255, 220, 150))
        else:
            d.ell(860, 420, 86, fill=(255, 240, 196))
        d.poly([(0, hz), (0, 800), (240, 740), (520, 810), (820, 730), (W, 790), (W, hz)], fill=hill_f)
        d.poly([(0, hz), (0, 850), (300, 820), (640, 870), (900, 830), (W, 860), (W, hz)], fill=hill_n)
        if kind == "harbor":
            d.rect(0, hz - 30, W, H, fill=mix((70, 120, 136), (20, 24, 60), dark))
            for i in range(26):
                yy = hz + 10 + i * 38
                d.line([(rnd.uniform(0, 500), yy), (rnd.uniform(600, W), yy)], fill=(255, 255, 255, 26), width=5)
            d.poly([(0, 1330), (300, 1290), (700, 1350), (W, 1300), (W, H), (0, H)], fill=g0)
        else:
            d.rect(0, hz, W, H, fill=g0)
            d.poly([(0, 1320), (W, 1260), (W, H), (0, H)], fill=g1)
            for _ in range(70):
                x, y = rnd.uniform(0, W), rnd.uniform(hz + 20, 1500)
                d.line([(x, y), (x + rnd.uniform(14, 40), y)], fill=mix(g0, (0, 0, 0), 0.12), width=4)
        if kind in ("village", "cabin"):
            for x, s in ((440, 0.8), (640, 0.9), (30, 1.0), (1050, 1.0)):
                _tree(d, x, hz + 6, s, rnd, dark)
        if kind == "village":
            _cabin(d, 70, hz + 30, 300, 230, lit=mood in ("eve", "dusk"), dark=dark)
            _cabin(d, 740, hz + 20, 270, 200, lit=mood in ("eve", "dusk"), dark=dark)
        if kind == "cabin":
            _cabin(d, 170, 1250, 740, 560, lit=False, dark=dark)
        if kind == "field":
            for x, s in ((90, 1.5), (1000, 1.7), (560, 0.8)):
                _tree(d, x, hz + 40, s, rnd, dark)
        if kind in ("village", "table"):   # the long table
            ty = 1130
            x0, x1 = (110, 970) if kind == "village" else (-40, W + 40)
            top = mix(WOOD_L, (30, 26, 60), dark)
            for lx in (x0 + 50, x1 - 70):
                d.rect(lx, ty + 30, lx + 22, ty + 150, fill=mix(WOOD_D, (20, 18, 40), dark))
            d.rect(x0, ty, x1, ty + 56, fill=top, r=10)
            d.rect(x0, ty + 40, x1, ty + 56, fill=mix(top, (0, 0, 0), 0.25), r=8)
    out = base
    out.alpha_composite(big.resize((W, H), Image.LANCZOS))
    if amt:
        out = Image.blend(out, Image.new("RGBA", (W, H), tint + (255,)), amt * 0.5)
    return out.convert("RGB")


def scene_bg(kind, mood="day"):
    return backdrop(kind, mood).convert("RGBA")


# ---------------------------------------------------------------- text
def headline(img, lines, y, size, alpha=1.0, color=CREAM, scale=1.0):
    if alpha <= 0.01:
        return
    d = ImageDraw.Draw(img, "RGBA")
    f = bitter(size * scale, 900)
    for i, line in enumerate(lines):
        yy = y + i * size * 1.12 + size * 0.56
        d.text((W / 2, yy), line, font=f, fill=color + (int(255 * alpha),), anchor="mm", stroke_width=int(size * 0.07), stroke_fill=INK + (int(255 * alpha),))


def headline_box(lines, y, size):
    f = bitter(size, 900)
    w = max(f.getlength(line) for line in lines) + size * 0.14
    return (W / 2 - w / 2, y, W / 2 + w / 2, y + len(lines) * size * 1.12)


def tag_box(cx, cy, text, size=46):
    w = bitter(size, 800).getlength(text)
    return (cx - w / 2 - 30, cy - size * 0.85, cx + w / 2 + 30, cy + size * 0.85)


def tag(img, cx, cy, text, a, up=True, size=46):
    """A paper label with a pointer: up=True points up at the thing above it."""
    if a <= 0.01:
        return
    d = ImageDraw.Draw(img, "RGBA")
    cy = cy + (1 - min(a, 1)) * (30 if up else -30)
    b = tag_box(cx, cy, text, size)
    al = int(255 * min(a, 1))
    py = b[1] if up else b[3]
    d.polygon([(cx - 22, py), (cx + 22, py), (cx, py + (-30 if up else 30))], fill=CREAM + (al,))
    d.rounded_rectangle(b, radius=16, fill=CREAM + (al,), outline=INK + (al,), width=4)
    d.text((cx, cy), text, font=bitter(size, 800), fill=INK + (al,), anchor="mm")


# ---------------------------------------------------------------- the scroll (Dandy): the only purple
ROWS = [("Turkey", "roast", 0, "fire"), ("Cornbread", "bread", 1, "corn"), ("Corn", "pot", 2, "corn"), ("Pie", "pie", 3, "fire")]
SCROLL = (150, 330, 930, 1130)
ROW_Y0, ROW_H = 560, 132


def scroll(img, t, unroll=1.0, names=1.0, who=1.0, needs=1.0, done=(0, 0, 0, 0), day=None, day_flip=None, gone=0.0, flags=(0, 0, 0, 0),
           hi=(0, 0, 0, 0), jig=0.0):
    x0, y0, x1, y1 = SCROLL
    y1 = lerp(y0 + 120, y1, unroll)
    x0 += jig
    x1 += jig
    S.put_sprite(img, S.GLOW_P, (x0 + x1) / 2, (y0 + y1) / 2, scale=2.6, alpha=0.95)
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((x0 - 10, y0 - 6, x1 + 10, y1 + 8), radius=22, fill=DANDY_HI)
    d.rounded_rectangle((x0, y0, x1, y1), radius=16, fill=PAPER)
    for yy in (y0, y1):   # the rolled ends
        d.rounded_rectangle((x0 - 26, yy - 26, x1 + 26, yy + 26), radius=26, fill=mix(PAPER, WOOD, 0.25), outline=DANDY_HI, width=6)
    d.ellipse((W / 2 - 16 + jig, y0 - 16, W / 2 + 16 + jig, y0 + 16), fill=(60, 58, 70))
    d.ellipse((W / 2 - 7 + jig, y0 - 9, W / 2 + 3 + jig, y0 + 1), fill=(150, 150, 164))
    if unroll < 0.6:
        return
    a = clamp((unroll - 0.6) / 0.4)
    d.text((x0 + 60, y0 + 108), "The Feast", font=bitter(72, 900), fill=INK + (int(255 * a),), anchor="lm")
    if day:
        bx = (x1 - 250, y0 + 66, x1 - 50, y0 + 150)
        fl = day_flip if day_flip is not None else 0.0
        S.put_sprite(img, S.GLOW_P, (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2, scale=0.8, alpha=fl)
        d.rounded_rectangle(bx, radius=18, fill=mix(CREAM, DANDY_HI, 0.25 + 0.5 * fl), outline=DANDY, width=5)
        d.text(((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2), day, font=bitter(54, 800), fill=INK, anchor="mm")
    d.line((x0 + 50, y0 + 176, x1 - 50, y0 + 176), fill=mix(PAPER, INK, 0.5), width=4)
    for i, (name, icon, who_k, need) in enumerate(ROWS):
        cy = ROW_Y0 + i * ROW_H
        if cy + 50 > y1:
            break
        ra = clamp(ease_out((names - i * 0.18) / 0.4))
        if hi[i] > 0:
            d.rounded_rectangle((x0 + 30, cy - 58, x1 - 30, cy + 58), radius=18, fill=mix(PAPER, DANDY_HI, 0.3) + (int(255 * hi[i]),))
        put(img, item(icon), x0 + 96, cy + 2, scale=0.62 * ra, anchor="mid", alpha=ra)
        d = ImageDraw.Draw(img, "RGBA")
        d.text((x0 + 164, cy), name, font=bitter(54, 700), fill=INK + (int(255 * ra),), anchor="lm")
        wa = clamp(ease_out((who - i * 0.12) / 0.3))
        put(img, item("hat"), x0 + 500, cy - 2, scale=0.5 * wa, anchor="mid", alpha=wa)
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse((x0 + 488, cy + 22, x0 + 512, cy + 46), fill=KINDS[who_k][1] + (int(255 * wa),))
        na = clamp(ease_out((needs - i * 0.12) / 0.3))
        is_corn = need == "corn"
        put(img, item("corn" if is_corn and gone < 0.5 else "basket" if is_corn else "fire"), x0 + 600, cy, scale=0.5 * na, anchor="mid", alpha=na)
        d = ImageDraw.Draw(img, "RGBA")
        if is_corn and gone > 0:
            g = clamp(gone)
            d.line((x0 + 572, cy - 28, x0 + 572 + 56 * g, cy - 28 + 56 * g), fill=RED, width=8)
            d.line((x0 + 628, cy - 28, x0 + 628 - 56 * g, cy - 28 + 56 * g), fill=RED, width=8)
        bx = x0 + 700
        d.rounded_rectangle((bx - 26, cy - 26, bx + 26, cy + 26), radius=8, outline=INK + (int(255 * na),), width=5)
        if done[i] > 0:
            p = clamp(done[i])
            pts = [(bx - 16, cy), (bx - 4, cy + 14), (bx + 22, cy - 22)]
            d.line(pts[:2] if p < 0.5 else pts, fill=DANDY, width=10, joint="curve")
        if flags[i] > 0:
            f = pop(flags[i], 0, 1.0)
            fx = x0 + 688
            d.line((fx, cy + 30, fx, cy + 30 - 96 * f), fill=INK, width=7)
            d.polygon([(fx + 3, cy - 66 * f), (fx + 66 * f, cy - 42 * f), (fx + 3, cy - 18 * f)], fill=DANDY)


def mini_scroll(img, x, y, pulse=0.0):
    S.put_sprite(img, S.GLOW_P, x, y, scale=0.7 + 0.5 * pulse, alpha=0.75 + 0.25 * pulse)
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((x - 50, y - 70, x + 50, y + 70), radius=8, fill=PAPER, outline=DANDY_HI, width=6)
    for i in range(4):
        d.line((x - 30, y - 36 + i * 24, x + 12, y - 36 + i * 24), fill=mix(PAPER, INK, 0.6), width=5)
        d.rectangle((x + 22, y - 42 + i * 24, x + 34, y - 30 + i * 24), outline=DANDY, width=3)
    d.ellipse((x - 7, y - 78, x + 7, y - 64), fill=(60, 58, 70))


# ---------------------------------------------------------------- timing: cut to Charlie's read (seconds in the recording)
CUTS = [("hook", 0.0), ("year", 7.45), ("dinner", 9.12), ("labels", 11.82), ("forget", 17.42), ("q_turkey", 21.05), ("q_corn", 22.2),
        ("q_pot", 22.86), ("pots", 24.45), ("platter", 26.45), ("moved", 27.4), ("pie", 29.25), ("scroll", 31.4), ("use", 36.28),
        ("change", 43.3), ("feast", 49.75), ("outro", 53.15), ("end", 57.5)]
TOTAL = 61.52
START = {sid: at for sid, at in CUTS}
DUR = {sid: round((CUTS[i + 1][1] if i + 1 < len(CUTS) else TOTAL) - at, 3) for i, (sid, at) in enumerate(CUTS)}


def L(sid, tg):
    """A moment in the recording, as time into scene sid."""
    return tg - START[sid]


SPOTS = [250, 540, 830]   # where the three pilgrims stand behind the table


def table_food(img, what, t=0.0):
    for name, x in what:
        put(img, item(name), x, 1146, scale=1.15)


def leaves(img, tg, n=14):
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(n):
        x = (i * 173 + 40 * math.sin(tg * 1.3 + i)) % W
        y = (i * 311 + tg * (90 + 17 * (i % 5))) % 1500
        r = 9 + i % 4 * 2
        d.ellipse((x - r, y - r * 0.6, x + r, y + r * 0.6), fill=LEAF[i % 4] + (230,))


# ---------------------------------------------------------------- scenes
def s_hook(t, dur, tg):
    img = scene_bg("village", "day")
    not_at, anyway = L("hook", 5.2), L("hook", 6.0)
    table_food(img, [])
    wave_ = 135 + 28 * math.sin(tg * 9)
    shrug = t >= anyway
    put(img, turkey(int(tg * 4) % 2 + 1 if t > 0.5 else 0, peck=int(tg * 1.6) % 2 if t > 0.5 else 0), 830, 1392, scale=0.8)
    shadow(img, 420, 1392, 110)
    put(img, pilgrim(0, 110 if shrug else 15, 110 if shrug else wave_, 0, "flat" if shrug else "smile"), 420, 1400, scale=1.45)
    headline(img, ["A Thanksgiving", "metaphor"], 290, 104)
    fall = max(0.0, t - L("hook", 6.45))
    a = pop(t, not_at, 0.16)
    if a > 0:
        st = stamp()
        put(img, st, 540, 760 + 1500 * fall * fall, scale=(2.2 - 1.2 * min(a, 1)) if a < 1 else 1.0, rot=-9 - 60 * fall, alpha=min(1, a * 1.5), anchor="mid")
    return img


@functools.lru_cache(None)
def stamp():
    im = Image.new("RGBA", (700, 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, 692, 182), radius=24, outline=RED + (240,), width=14, fill=(255, 244, 222, 60))
    d.text((350, 95), "NOT APPROVED", font=S.font("Inter-Black.otf", 78), fill=RED + (240,), anchor="mm")
    return im


def s_year(t, dur, tg):
    img = scene_bg("harbor", "day")
    put(img, ship(), 540 + 30 * math.sin(tg * 0.8), 1210 + 10 * math.sin(tg * 2.2), scale=1.5, rot=2.5 * math.sin(tg * 2.2))
    a = pop(t, L("year", 7.95), 0.2)
    headline(img, ["1621"], 300 - (1 - min(a, 1)) * 200, 250, alpha=min(1, a * 2), scale=max(a, 0.01))
    return img


def village_work(tl, tg, speed=0.0, zip_=0.0):
    """Three pilgrims behind the long table, making dinner. tl is seconds since they came in."""
    img = scene_bg("village", "day")
    for i, x in enumerate(SPOTS):
        come = smooth((tl - 0.15 * i) / 1.0)
        fromx = -200 if i == 0 else W + 200 if i == 2 else 540
        px = lerp(fromx, x, come) + zip_ * 70 * math.sin(tg * 21 + i * 2.1)
        py = 1210 + (1 - come) * (0 if i != 1 else -40)
        rate = 9 + 9 * speed
        chop = 60 + 50 * math.sin(tg * rate + i * 1.7)
        walking = come < 0.98
        bobv = 7 * abs(math.sin(tg * (rate if not walking else 10) + i))
        if zip_ > 0:
            d = ImageDraw.Draw(img, "RGBA")
            for k in range(4):
                d.line((px - 150 + k * 20, 900 + k * 46, px - 60 + k * 20, 900 + k * 46), fill=(255, 255, 255, int(120 * zip_)), width=6)
        put(img, pilgrim(i, 30 if i == 1 else chop, 140 - chop if i != 1 else chop, int(tg * 8) % 2 + 1 if walking else 0, "smile"), px, py - bobv, scale=1.15, flip=i == 2)
    img.alpha_composite(table_layer("day"))
    table_food(img, [("pot", 300)] if tl > 1.4 else [])
    if tl > 2.0:
        table_food(img, [("corn", 790)])
    return img


@functools.lru_cache(None)
def table_layer(mood):
    """The long table on its own, so pilgrims can stand behind it."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    src = backdrop("village", mood).convert("RGBA")
    box = (100, 1128, 980, 1290)
    im.paste(src.crop(box), box[:2])
    return im


def s_dinner(t, dur, tg):
    return village_work(t, tg)


def s_labels(t, dur, tg):
    hard, fast = L("labels", 15.3), L("labels", 16.48)
    img = village_work(t + DUR["dinner"], tg, speed=smooth((t - hard) / 0.5), zip_=smooth((t - fast) / 0.25))
    tag(img, 540, 1330, "your project", pop(t, L("labels", 12.3)), up=True)
    tag(img, 540, 660, "your AI agents", pop(t, L("labels", 14.0)), up=False)
    return img


def s_forget(t, dur, tg):
    wake = L("forget", 18.45)
    sun = smooth(t / max(wake, 0.1))
    img = Image.blend(scene_bg("cabin", "dusk"), scene_bg("cabin", "dawn"), sun)
    for i, x in enumerate((300, 540, 780)):
        out_at = wake + 0.3 * i
        p = smooth((t - out_at) / 0.35)
        if p <= 0:
            continue
        q_at = L("forget", 19.9) + 0.22 * i
        confused = t >= q_at
        stretch = 1 - smooth((t - out_at - 0.5) / 0.4)
        put(img, pilgrim(i, 15 + 150 * stretch, 15 + 150 * stretch, 0, "o" if confused else "flat"), lerp(540, x, p), 1400 - 10 * abs(math.sin(tg * 3 + i)), scale=0.75 + 0.35 * p)
        a = pop(t, q_at)
        put(img, mark("?", 170, CREAM), x + 10, 870 - 20 * math.sin(tg * 4 + i), scale=a, anchor="mid", rot=8 * math.sin(tg * 3 + i))
    return img


def q_scene(t, tg, kind):
    img = scene_bg("field", "day")
    a = pop(t, 0.12, 0.16)
    if kind == "turkey":
        x = lerp(-120, W + 160, t / DUR["q_turkey"])
        put(img, pilgrim(0, 15, 150, 0, "o"), 300, 1400, scale=1.1)
        shadow(img, x, 1392, 110)
        put(img, turkey(int(tg * 9) % 2 + 1), x, 1400 - 8 * abs(math.sin(tg * 18)), scale=1.25)
        put(img, mark("?", 190, CREAM), 330, 800, scale=a, anchor="mid")
    elif kind == "corn":
        put(img, item("corn"), 540, 1400, scale=3.3)
        put(img, pilgrim(2, 15, 150, 0, "o"), 880, 1400, scale=1.0, flip=True)
        put(img, mark("?", 190, CREAM), 520, 760, scale=a, anchor="mid")
    else:
        put(img, item("fire"), 540, 1420, scale=2.6)
        put(img, item("pot"), 540, 1270 + 5 * math.sin(tg * 16), scale=3.0)
        d = ImageDraw.Draw(img, "RGBA")
        for i in range(5):
            yy = 880 - ((tg * 120 + i * 60) % 260)
            d.ellipse((470 + i * 34 + 14 * math.sin(tg * 3 + i) - 18, yy - 18, 470 + i * 34 + 14 * math.sin(tg * 3 + i) + 18, yy + 18), fill=(255, 255, 255, 110))
        put(img, pilgrim(1, 150, 15, 0, "o"), 190, 1400, scale=1.0)
        put(img, mark("?", 190, CREAM), 800, 760, scale=a, anchor="mid")
    return img


def s_q_turkey(t, dur, tg):
    return q_scene(t, tg, "turkey")


def s_q_corn(t, dur, tg):
    return q_scene(t, tg, "corn")


def s_q_pot(t, dur, tg):
    return q_scene(t, tg, "pot")


POT_X = [230, 540, 850]


def s_pots(t, dur, tg):
    img = scene_bg("table", "day")
    for i, x in enumerate(POT_X):
        at = L("pots", 25.2) + 0.3 * i
        p = clamp((t - at) / 0.18)
        if p <= 0:
            continue
        squash = 1 + 0.18 * math.sin(clamp((t - at - 0.18) / 0.25) * math.pi)
        y = lerp(300, 1146, p * p)
        put(img, item("pot"), x, y, scale=2.3 * squash if p >= 1 else 2.3)
        a = pop(t, at + 0.16)
        put(img, mark(str(i + 1), 150, CREAM), x, 700, scale=a, anchor="mid")
    return img


def s_platter(t, dur, tg):
    img = scene_bg("table", "day")
    peek = smooth((t - L("platter", 26.95)) / 0.25)
    put(img, turkey(0), 1010 - 150 * peek, 1136, scale=1.3, flip=True)
    img.alpha_composite(big_table())
    put(img, item("platter"), 500, 1170, scale=3.6)
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(3):   # where the turkey should be: a dotted outline
        a = i * 2.1 + tg * 2
        d.ellipse((500 + 150 * math.cos(a) - 7, 960 + 50 * math.sin(a) - 7, 500 + 150 * math.cos(a) + 7, 960 + 50 * math.sin(a) + 7), fill=CREAM + (220,))
    put(img, mark("?", 200, CREAM), 500, 940, scale=pop(t, 0.1, 0.16), anchor="mid")
    return img


@functools.lru_cache(None)
def big_table():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    src = backdrop("table", "day").convert("RGBA")
    im.paste(src.crop((0, 1128, W, 1300)), (0, 1128))
    return im


@functools.lru_cache(None)
def plank(text, w=620, h=150):
    def draw(d):
        d.rect(4, 4, w - 4, h - 4, fill=WOOD_L, r=14, outline=WOOD_D, width=6)
        d.line([(30, 40), (w - 60, 44)], fill=mix(WOOD_L, WOOD_D, 0.35), width=3)
        d.line([(60, h - 36), (w - 30, h - 40)], fill=mix(WOOD_L, WOOD_D, 0.35), width=3)
        d.text(w / 2, h / 2, text, 84, INK, 900)
    return sprite(w, h, draw, 2)


SIGN_Y = (760, 960)


def s_moved(t, dur, tg):
    img = scene_bg("field", "day")
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((520, 700, 560, 1400), fill=WOOD_D)
    flip_at = L("moved", 27.9)
    put(img, plank("FEAST", 460), 540, SIGN_Y[0], anchor="mid")
    p = clamp((t - flip_at) / 0.3)
    sy = abs(math.cos(p * math.pi))
    bonk = 14 * math.sin(clamp((t - flip_at - 0.3) / 0.3) * math.pi)
    spr = plank("THURSDAY" if p < 0.5 else "WEDNESDAY")
    spr = spr.resize((spr.width, max(2, int(spr.height * max(sy, 0.03)))), Image.BILINEAR)
    put(img, spr, 540, SIGN_Y[1] - bonk, anchor="mid", rot=-3 if p >= 0.5 else 0)
    px = lerp(W + 200, 880, smooth(t / 0.4))
    hit = 150 if abs(t - flip_at) < 0.2 else 60
    put(img, pilgrim(3, 15, hit, int(tg * 8) % 2 + 1 if t < 0.4 else 0, "grin"), px, 1400, scale=1.05, flip=True)
    return img


def s_pie(t, dur, tg):
    img = scene_bg("village", "dusk")
    img.alpha_composite(table_layer("dusk"))
    d = ImageDraw.Draw(img, "RGBA")
    for x in (260, 420, 700, 860):   # crumbs and an empty plate or two: dinner is over
        d.ellipse((x - 40, 1118, x + 40, 1140), fill=(150, 150, 170))
    stop = L("pie", 30.3)
    px = lerp(W + 200, 620, smooth(t / max(stop, 0.2)))
    arrived = t >= stop
    shadow(img, px, 1396, 100, 90)
    put(img, pilgrim(1, 15, 15, 0 if arrived else int(tg * 8) % 2 + 1, "o" if arrived else "smile", hold="pie"), px, 1400, scale=1.2, flip=True)
    put(img, mark("?", 170, CREAM), 640, 820, scale=pop(t, stop + 0.1), anchor="mid", rot=6 * math.sin(tg * 3))
    for i in range(3):   # crickets
        if int(tg * 3 + i) % 3 == 0:
            d.ellipse((180 + i * 90, 1000 - i * 40, 190 + i * 90, 1010 - i * 40), fill=(200, 230, 160, 200))
    return img


def s_scroll(t, dur, tg):
    img = scene_bg("wall")
    un = ease_out((t - L("scroll", 31.5)) / 0.8)
    nail = L("scroll", 32.6)
    jig = 10 * math.sin((t - nail) * 50) * max(0.0, 1 - (t - nail) / 0.3) if t >= nail else 0
    scroll(img, t, unroll=un, names=max(0.0, t - L("scroll", 33.75)), who=max(0.0, t - L("scroll", 34.45)), needs=max(0.0, t - L("scroll", 34.9)),
           done=(clamp((t - L("scroll", 35.6)) / 0.25), 0, 0, 0), jig=jig)
    return img


MINI = (205, 780)


def s_use(t, dur, tg):
    img = scene_bg("village", "day")
    fin, upd = L("use", 41.3), L("use", 42.3)
    marks = []
    for i in (2, 1, 0):
        arrive = 0.7 + 0.95 * (2 - i) if i else 0.7 + 0.95 * 2
        arrive = 0.7 + 0.95 * [0, 1, 2][[2, 1, 0].index(i)]
        read_end = arrive + 0.75
        home = SPOTS[i]
        if t < arrive:
            px = lerp(W + 200 + 150 * [2, 1, 0].index(i), 330, smooth(t / arrive))
            pose = pilgrim(i, 15, 15, int(tg * 8) % 2 + 1, "flat")
            flip = True
        elif t < read_end:
            px = 330
            pose = pilgrim(i, 15, 120, 0, "o")
            flip = True
            marks.append((px + 20, pop(t, arrive + 0.2)))
        else:
            go = smooth((t - read_end) / 0.7)
            px = lerp(330, home, go)
            back = i == 0 and t >= fin + 0.2
            if back:
                gb = smooth((t - fin - 0.2) / 0.7)
                px = lerp(home, 330, gb)
                pose = pilgrim(i, 15, 130 if gb >= 1 else 15, int(tg * 8) % 2 + 1 if gb < 1 else 0, "smile")
                flip = True
            else:
                chop = 60 + 50 * math.sin(tg * 11 + i)
                pose = pilgrim(i, chop, 140 - chop, int(tg * 8) % 2 + 1 if go < 1 else 0, "smile")
                flip = False
        put(img, pose, px, 1210 - 6 * abs(math.sin(tg * 9 + i)), scale=1.15, flip=flip)
    img.alpha_composite(table_layer("day"))
    food = []
    if t > 3.6:
        food.append(("pot", 560))
    if t > 4.4:
        food.append(("bread", 800))
    if t >= fin:
        food.append(("roast", 310))
    table_food(img, food)
    pulse = max(0.0, 1 - abs(t - upd - 0.15) / 0.5)
    mini_scroll(img, *MINI, pulse=pulse)
    for x, a in marks:
        put(img, mark("!", 130, DANDY_HI), x, 720, scale=a, anchor="mid")
    if fin + 0.9 <= t:   # the check flies from the pilgrim into the scroll
        p = clamp((t - upd + 0.25) / 0.3)
        cx, cy = lerp(330, MINI[0] + 28, p), lerp(900, MINI[1] - 36, p)
        d = ImageDraw.Draw(img, "RGBA")
        d.line([(cx - 16, cy), (cx - 4, cy + 14), (cx + 22, cy - 22)], fill=DANDY_HI, width=10, joint="curve")
    return img


def s_change(t, dur, tg):
    img = scene_bg("wall")
    flip_at, aware, gone_at = L("change", 44.0), L("change", 44.9), L("change", 46.5)
    hi_at, flag_at = L("change", 47.75), L("change", 49.05)
    fl = max(0.0, 1 - abs(t - flip_at - 0.1) / 0.7)
    hi = (0, clamp((t - hi_at) / 0.3), clamp((t - hi_at - 0.3) / 0.3), 0)
    scroll(img, t, done=(1, 0, 0, 0), day="Thu" if t < flip_at else "Wed", day_flip=fl, gone=clamp((t - gone_at) / 0.3),
           flags=(0, max(0.0, (t - flag_at) / 0.25), max(0.0, (t - flag_at - 0.12) / 0.25), 0), hi=hi)
    for i, x in enumerate((300, 540, 780)):
        up = smooth((t - 0.2 - 0.1 * i) / 0.4)
        put(img, pilgrim(i, 15, 15, 0, "o" if t >= aware else "flat"), x, 1640 - 240 * up, scale=0.78)
        put(img, mark("!", 96, DANDY_HI), x + 70, 1180, scale=pop(t, aware + 0.12 * i), anchor="mid")
    return img


FEAST = [("corn", 215), ("bread", 375), ("roast", 540), ("pot", 705), ("pie", 865)]


def feast(tl, tg, wave_=0.0):
    img = scene_bg("village", "eve")
    for i, x in enumerate(SPOTS):
        up = 120 + 40 * math.sin(tg * 7 + i * 2)
        put(img, pilgrim(i, up, up if wave_ == 0 else 140 + 30 * math.sin(tg * 10 + i), 0, "grin"), x, 1210 - 16 * abs(math.sin(tg * 6 + i * 1.3)), scale=1.15)
    put(img, pilgrim(3, 150, 150, 0, "grin"), 95, 1380 - 14 * abs(math.sin(tg * 6.5)), scale=0.95)
    img.alpha_composite(table_layer("eve"))
    for i, (name, x) in enumerate(FEAST):
        a = pop(tl, 0.05 + 0.07 * i, 0.16)
        put(img, item(name), x, 1146, scale=1.2 * a)
    mini_scroll(img, *MINI, pulse=0.5 + 0.5 * math.sin(tg * 4))
    leaves(img, tg)
    return img


def s_feast(t, dur, tg):
    return feast(t, tg)


def s_outro(t, dur, tg):
    img = feast(t + DUR["feast"], tg, wave_=1.0 if t >= L("outro", 56.5) else 0.0)
    no_at, happy = L("outro", 54.7), L("outro", 55.35)
    if t < happy:
        headline(img, ["Perfect metaphor?"], 290, 92, alpha=pop(t, L("outro", 53.3), 0.15))
        a = pop(t, no_at, 0.14)
        headline(img, ["No."], 450, 150, alpha=min(1, a * 2), scale=max(a, 0.01))
    else:
        a = pop(t, happy, 0.2)
        headline(img, ["Happy", "Thanksgiving"], 290, 118, alpha=min(1, a * 2), scale=max(min(a, 1.08), 0.01), color=(255, 226, 150))
    _last["img"] = img
    return img


_last = {}


def s_end(t, dur, tg):
    """The shared end card, without Dandy Man: the feast blurs back and the hat, the name and the two lines come up."""
    last = _last.get("img") or feast(9, START["end"])
    p = ease_out(t / 0.8)
    bg = last.filter(ImageFilter.GaussianBlur(int(18 * p))).convert("RGBA")
    bg.alpha_composite(Image.new("RGBA", bg.size, S._hex("background") + (int(226 * p),)))
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W * 0.12, H * 0.28, W * 0.88, H * 0.72), fill=S._hex("primary") + (int(120 * p),))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(130)))
    d = ImageDraw.Draw(bg)
    sizes = S.CONTRACT["type"]["vertical"]
    a = ease_out((t - 0.35) / 0.5)
    if a > 0:
        hh = int(H * 0.11)
        hat = S.hat(hh).copy()
        hat.putalpha(hat.split()[3].point(lambda v: int(v * a)))
        bg.alpha_composite(hat, (int(W / 2 - hat.width / 2), int(H * 0.34 + (1 - a) * 40)))
        fh = S.font("Inter-Bold.otf", int(sizes["headline"] * 1.5))
        ty = H * 0.34 + hh + 40
        d.text((W / 2, ty), "Dandy", font=fh, fill=S._hex("text") + (int(255 * a),), anchor="ma")
        yy = ty + fh.size * 1.1 + 60
        for i, line in enumerate(S.CONTRACT["copy_rules"]["end_card_lines"]):
            b = ease_out((t - 0.7 - 0.2 * i) / 0.45)
            fl = S.font("Inter-Medium.otf", sizes["body" if i == 0 else "caption"])
            d.text((W / 2, yy), line, font=fl, fill=(S._hex("accent_gold") if i == 1 else S._hex("soft")) + (int(255 * b),), anchor="ma")
            yy += fl.size * 1.1 + 50
    return bg


FNS = dict(hook=s_hook, year=s_year, dinner=s_dinner, labels=s_labels, forget=s_forget, q_turkey=s_q_turkey, q_corn=s_q_corn, q_pot=s_q_pot,
           pots=s_pots, platter=s_platter, moved=s_moved, pie=s_pie, scroll=s_scroll, use=s_use, change=s_change, feast=s_feast, outro=s_outro, end=s_end)
SCENES = [(sid, DUR[sid], FNS[sid]) for sid, _ in CUTS]
CAPTIONS = []
if os.path.exists(VO):
    with open(VO) as _f:
        CAPTIONS = [tuple(c) for c in json.load(_f)["lines"]]
assert all(len(S.caption_lines(c[2])) == 1 for c in CAPTIONS), [c[2] for c in CAPTIONS if len(S.caption_lines(c[2])) > 1]


def qa_scenes(starts, durs, captions):
    el = S.text_el

    def caps(sid):
        return S.caption_els(captions, starts[sid], durs[sid])

    x0, y0, x1, y1 = SCROLL
    rows = [el(f"row {n}", n, (x0 + 164, ROW_Y0 + i * ROW_H - 34, x0 + 164 + bitter(54, 700).getlength(n), ROW_Y0 + i * ROW_H + 34)) for i, (n, *_) in enumerate(ROWS)]
    head = el("scroll title", "The Feast", (x0 + 60, y0 + 70, x0 + 60 + bitter(72, 900).getlength("The Feast"), y0 + 146), role="headline")
    out = []
    for sid, _ in CUTS:
        laid = []
        if sid == "hook":
            laid = [el("title", "A Thanksgiving metaphor", headline_box(["A Thanksgiving", "metaphor"], 290, 104), role="headline", lines=["A Thanksgiving", "metaphor"]),
                    el("stamp", "NOT APPROVED", (200, 670, 880, 850), enter_at=L("hook", 5.2), exit_at=L("hook", 6.9))]
        elif sid == "year":
            laid = [el("year", "1621", headline_box(["1621"], 300, 250), role="headline")]
        elif sid == "labels":
            laid = [el("tag project", "your project", tag_box(540, 1330, "your project")), el("tag agents", "your AI agents", tag_box(540, 660, "your AI agents"))]
        elif sid == "moved":
            laid = [el("sign", "FEAST", (310, SIGN_Y[0] - 75, 770, SIGN_Y[0] + 75), role="headline"),
                    el("sign day", "WEDNESDAY", (230, SIGN_Y[1] - 75, 850, SIGN_Y[1] + 75), role="headline")]
        elif sid == "scroll":
            laid = [head] + rows
        elif sid == "change":
            laid = [head, el("day", "Wed", (x1 - 250, y0 + 66, x1 - 50, y0 + 150))] + rows
        elif sid == "outro":
            hp = L("outro", 55.35)
            laid = [el("perfect", "Perfect metaphor?", headline_box(["Perfect metaphor?"], 290, 92), role="headline", exit_at=hp),
                    el("no", "No.", headline_box(["No."], 450, 150), role="headline", enter_at=L("outro", 54.7), exit_at=hp),
                    el("happy", "Happy Thanksgiving", headline_box(["Happy", "Thanksgiving"], 290, 118), role="headline", lines=["Happy", "Thanksgiving"], enter_at=hp)]
        if sid == "end":
            out.append(dict(id="end", type="end_card", duration=durs["end"], laid_out=[]))
        else:
            out.append(dict(id=sid, type="stage", duration=durs[sid], laid_out=laid + caps(sid)))
    return out


def events(starts, durs):
    """Light touches only: Charlie's own music is already in the recording."""
    ev = [(5.2, "pop", dict(gain=0.4, f=140), 0.0), (6.45, "whoosh", dict(gain=0.2, dur=0.5), 0.0), (7.95, "pop", dict(gain=0.34, f=220), 0.0),
          (12.3, "pop", dict(gain=0.22, f=620), 0.0), (14.0, "pop", dict(gain=0.22, f=700), 0.0), (16.48, "zip", dict(gain=0.16), 0.0)]
    ev += [(19.9 + 0.22 * i, "pop", dict(gain=0.24, f=420 - 40 * i), -0.5 + 0.5 * i) for i in range(3)]
    ev += [(at, "pop", dict(gain=0.22, f=380), 0.0) for at in (21.17, 22.32, 22.98)]
    ev += [(25.38 + 0.3 * i, "pop", dict(gain=0.36, f=150 + 20 * i), -0.6 + 0.6 * i) for i in range(3)]
    ev += [(26.95, "zip", dict(gain=0.14), 0.5), (27.9, "tick", dict(gain=0.3), 0.0), (28.2, "pop", dict(gain=0.34, f=160), 0.0), (30.4, "pop", dict(gain=0.22, f=360), 0.2),
           (31.5, "whoosh", dict(gain=0.26, dur=0.8), 0.0), (32.6, "tick", dict(gain=0.36), 0.0), (32.6, "pop", dict(gain=0.3, f=200), 0.0)]
    ev += [(33.75 + 0.18 * i, "tick", dict(gain=0.18), 0.0) for i in range(4)]
    ev += [(35.6, "chime", dict(gain=0.24, f0=988), 0.0)]
    ev += [(36.28 + 0.9 + 0.95 * i, "pop", dict(gain=0.22, f=660 + 80 * i), -0.4) for i in range(3)]
    ev += [(42.3, "chime", dict(gain=0.26, f0=1047), -0.4), (44.0, "pop", dict(gain=0.26, f=520), 0.3)]
    ev += [(44.9 + 0.12 * i, "pop", dict(gain=0.2, f=700 + 60 * i), -0.5 + 0.5 * i) for i in range(3)]
    ev += [(46.5, "tick", dict(gain=0.3), 0.0), (49.05, "pop", dict(gain=0.3, f=560), 0.3), (49.17, "pop", dict(gain=0.3, f=620), 0.3),
           (49.8, "chime", dict(gain=0.26, f0=784), 0.0), (54.7, "pop", dict(gain=0.36, f=150), 0.0), (55.35, "chime", dict(gain=0.3, f0=880), 0.0),
           (57.5, "whoosh", dict(gain=0.22, dur=0.8), 0.0)]
    return ev


SPEC = dict(video_dir=VIDEO, slug="17-thanksgiving", look_tag="plymouth", look="plymouth 1621", end_card="without Dandy Man", scenes=SCENES,
            captions=CAPTIONS, qa_scenes=qa_scenes, events=events, still_s=0.4, voiceover=VO)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if S.render_video(SPEC, a.preview, a.stills, a.final) else 1)

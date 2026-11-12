"""Renderer for video 09, Just the Diamonds: the context window as a glass column, drawn in code. Vertical 1080x1920.

Usage:  python3 videos/09-diamonds/vault/render_diamonds.py [--preview] [--stills] [--final] [--audio-only]

A tall glass column on a near-black ground is Claude Code's context window. Grey rubble pours in and settles; the fill
meter stops under half while the agent (a small cursor of light) slows to a drag. Push in: tags flick up on the junk
(old file reads, error logs, dead ends) and three diamonds glint, half buried; the cursor passes right over one. Hard
cut wide: the column shrinks to the left and a purple Dandy case slides in. The diamonds lift out of the pile into the
case, laid flat and joined as a map (decided, built, next). The cursor reads the case, does a beat of work in the
column and drops a new diamond in (kept current). Then the column again, holding only diamonds, the cursor fast. Soft
end card without Dandy Man. Purple appears only on the case and the end card.

Scene timings move to voiceover/diamonds.json ("durations", "file", "offset_s", "lines") once Charlie records;
captions are burned in from CAPTIONS until then.
"""
import argparse
import json
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "render"))
from finish import finish, spring  # noqa: E402
from checks import check_layout  # noqa: E402

with open(os.path.join(ROOT, "style", "contract.json")) as f:
    CONTRACT = json.load(f)
PAL = CONTRACT["palette"]
W, H = 1080, 1920
FPS = CONTRACT["motion"]["fps"]
FONT_DIR = "/usr/share/fonts/opentype/inter"
SAFE = (int(W * 0.08), CONTRACT["layout"]["vertical_safe_top_px"], W - int(W * 0.08), H - CONTRACT["layout"]["vertical_safe_bottom_px"])

# ---------------------------------------------------------------- look
GROUND, GROUND_LIFT = (8, 10, 15), (24, 30, 44)
GLASS_BACK = (16, 20, 30)
GLASS_EDGE = (170, 190, 220)
METER = (120, 205, 228)
TEXT = (243, 238, 255)
ROCK_COLS = [(74, 74, 78), (92, 86, 80), (64, 62, 66), (102, 92, 82), (58, 60, 66), (84, 80, 76)]
CHIP_COLS = [(96, 100, 110), (110, 104, 96), (82, 86, 96)]
CURSOR = (210, 245, 255)
PURPLE, PURPLE_HI, PURPLE_SOFT = (tuple(int(PAL[k][i:i + 2], 16) for i in (1, 3, 5)) for k in ("primary", "highlight", "soft"))
CASE_BODY, CASE_PANEL = (26, 15, 46), (36, 22, 64)

COL = (300, 430, 780, 1250)          # the glass column, world coords (= screen coords at identity)
INNER = (COL[0] + 12, COL[1] + 12, COL[2] - 12, COL[3] - 12)
CASE = (470, 540, 975, 1190)         # the Dandy case, screen coords
SHRINK = (0.58, -83.0, 373.0)        # column transform in s4: scale, offset x, offset y
NODES = [(600, 690), (860, 820), (620, 960), (850, 1085)]      # case map: decided, built, next, the new one
NODE_TAGS = ["what's decided", "what's built", "what's next"]
EDGES = [(0, 1, 2.95), (0, 2, 3.35), (1, 2, 3.45), (1, 3, 5.4), (2, 3, 5.5)]   # (a, b, draw start in s4)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(size))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def lerp(a, b, p):
    return a + (b - a) * p


def mix(c1, c2, p):
    return tuple(int(lerp(c1[i], c2[i], p)) for i in range(3))


# ---------------------------------------------------------------- the pile
class Piece:
    def __init__(self, x, y, r, kind, col, poly, row, drop):
        self.x, self.y, self.r, self.kind, self.col, self.poly, self.row, self.drop = x, y, r, kind, col, poly, row, drop


def _rock_poly(rnd, r):
    n = rnd.randint(7, 10)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.25, 0.25)
        rr = r * rnd.uniform(0.72, 1.0)
        pts.append((math.cos(a) * rr, math.sin(a) * rr * 0.82))
    return pts


def _chip_poly(rnd, r):
    w, h = r * 1.5, r * 0.95
    a = math.radians(rnd.uniform(-28, 28))
    corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    return [(x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)) for x, y in corners]


ROW_Y0, ROW_DY, ROWS, PER_ROW = INNER[3] - 30, 52, 6, 9
POUR_T0, POUR_SPAN = 0.15, 1.75
# the three buried diamonds: (x, y, row); they lift into the case as decided, built, next
GEMS = [(385, 996, 4), (672, 1048, 3), (470, 1152, 1)]
GEM_SIZE = 64


def build_pile():
    rnd = random.Random(9)
    pieces = []
    for r in range(ROWS):
        for k in range(PER_ROW):
            if r == ROWS - 1 and rnd.random() < 0.3:
                continue
            x = INNER[0] + (k + 0.5) * (INNER[2] - INNER[0]) / PER_ROW + rnd.uniform(-10, 10)
            y = ROW_Y0 - r * ROW_DY + rnd.uniform(-9, 9)
            rad = rnd.uniform(26, 37)
            chip = rnd.random() < 0.3
            poly = _chip_poly(rnd, rad) if chip else _rock_poly(rnd, rad)
            col = rnd.choice(CHIP_COLS if chip else ROCK_COLS)
            pieces.append(Piece(x, y, rad, "chip" if chip else "rock", col, poly, r, 0.0))
    # clear room above each gem so it shows half buried, and drop its own row's piece under it
    keep = []
    for p in pieces:
        hit = False
        for gx, gy, gr in GEMS:
            if abs(p.x - gx) < 46 and ((p.row > gr and gy - 90 < p.y < gy) or (p.row == gr and abs(p.y - gy) < 30)):
                hit = True
        if not hit:
            keep.append(p)
    pieces = keep
    # cover rocks drawn in front of each gem's lower half
    covers = []
    for i, (gx, gy, gr) in enumerate(GEMS):
        for dx, dy, rad in ((-30, 16, 27), (32, 18, 26), (2, 30, 24)):
            covers.append(Piece(gx + dx, gy + dy, rad, "rock", rnd.choice(ROCK_COLS), _rock_poly(rnd, rad), gr + 0.5, 0.0))
    order = sorted(pieces, key=lambda p: (p.row, rnd.random()))
    n = len(order) + len(covers) + len(GEMS)
    step = POUR_SPAN / n
    seq, t = [], POUR_T0
    gem_drop = {}
    for p in order:
        p.drop = t
        t += step
        seq.append(p)
        for i, (gx, gy, gr) in enumerate(GEMS):
            if i not in gem_drop and p.row > gr:
                gem_drop[i] = t
                t += step
                for c in covers[3 * i:3 * i + 3]:
                    c.drop = t
                    t += step
    for i in range(len(GEMS)):
        gem_drop.setdefault(i, t)
    return order, covers, gem_drop


PIECES, COVERS, GEM_DROP = build_pile()
LAST_DROP = max([p.drop for p in PIECES + COVERS] + list(GEM_DROP.values()))


def fall_y(t, drop, y_end, y_start=INNER[1] + 30):
    """Gravity drop from the top of the glass, then a small settle bounce. None before it drops."""
    if t < drop:
        return None
    dur = 0.22 + 0.28 * (y_end - y_start) / 800
    p = (t - drop) / dur
    if p < 1:
        return y_start + (y_end - y_start) * p * p
    q = (t - drop - dur) / 0.22
    return y_end - (9 * math.sin(math.pi * q) * (1 - q) if q < 1 else 0)


# ---------------------------------------------------------------- sprites
def _radial(size, color, power=2.0, alpha=255):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.sqrt((xx - size / 2) ** 2 + (yy - size / 2) ** 2) / (size / 2)
    a = np.clip(1 - r, 0, 1) ** power * alpha
    arr = np.zeros((size, size, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = a.astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


HALO = _radial(220, CURSOR, 2.2, 150)
CORE = _radial(34, (255, 255, 255), 1.2, 255)
GEM_HALO = _radial(200, (190, 235, 255), 2.4, 110)
PURPLE_GLOW = _radial(400, PURPLE_HI, 1.8, 170)


def put_sprite(img, spr, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    s = spr if scale == 1.0 else spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if alpha < 1:
        s = s.copy()
        s.putalpha(s.split()[3].point(lambda v: int(v * alpha)))
    img.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))


# ---------------------------------------------------------------- drawing
_ground = None


def ground():
    global _ground
    if _ground is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - 540) / 820) ** 2 + ((yy - 860) / 1050) ** 2)
        lift = np.clip(1 - r, 0, 1) ** 1.8
        arr = np.array(GROUND, np.float32) + lift[..., None] * (np.array(GROUND_LIFT, np.float32) - np.array(GROUND, np.float32))
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(im, "RGBA")
        rnd = random.Random(4)
        for _ in range(160):
            x, y = rnd.uniform(0, W), rnd.uniform(0, H)
            d.ellipse((x, y, x + 2, y + 2), fill=(150, 170, 200, rnd.randint(10, 40)))
        _ground = im
    return _ground.copy()


_glass = {}


def glass_layers():
    """Back wall (behind the pile) and front glass (over it), both full-canvas RGBA in world coords."""
    if not _glass:
        back = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(back)
        x0, y0, x1, y1 = COL
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((x0 + 6, y0 + 30, x1 + 6, y1 + 40), radius=30, fill=(0, 0, 0, 150))
        back.alpha_composite(sh.filter(ImageFilter.GaussianBlur(24)))
        d = ImageDraw.Draw(back)
        d.rounded_rectangle((x0, y0, x1, y1), radius=28, fill=GLASS_BACK + (255,))
        # faint depth gradient on the back wall
        grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        for i in range(24):
            yy = y0 + (y1 - y0) * i / 24
            gd.rectangle((x0 + 8, yy, x1 - 8, yy + (y1 - y0) / 24 + 1), fill=(60, 80, 120, int(26 * (1 - i / 24))))
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).rounded_rectangle((x0 + 4, y0 + 4, x1 - 4, y1 - 4), radius=24, fill=255)
        back.paste(Image.alpha_composite(back, grad), (0, 0), mask)
        # base plate
        d = ImageDraw.Draw(back)
        d.rounded_rectangle((x0 - 22, y1 - 6, x1 + 22, y1 + 18), radius=10, fill=(38, 44, 58, 255))
        d.line((x0 - 14, y1 - 4, x1 + 14, y1 - 4), fill=(80, 92, 118, 255), width=2)
        # meter track and half tick
        mx0, mx1 = x1 + 26, x1 + 38
        d.rounded_rectangle((mx0, y0 + 20, mx1, y1 - 20), radius=6, fill=(34, 40, 54, 255))
        my = (y0 + 20 + y1 - 20) / 2
        d.line((mx0 - 10, my, mx1 + 10, my), fill=(150, 165, 190, 170), width=3)
        front = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fd = ImageDraw.Draw(front)
        fd.rounded_rectangle((x0, y0, x1, y1), radius=28, outline=GLASS_EDGE + (110,), width=3)
        streak = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(streak).rounded_rectangle((x0 + 26, y0 + 40, x0 + 52, y1 - 60), radius=12, fill=(255, 255, 255, 34))
        ImageDraw.Draw(streak).rounded_rectangle((x1 - 40, y0 + 60, x1 - 30, y0 + 340), radius=5, fill=(255, 255, 255, 22))
        front.alpha_composite(streak.filter(ImageFilter.GaussianBlur(6)))
        fd = ImageDraw.Draw(front)
        fd.arc((x0 + 10, y0 - 10, x1 - 10, y0 + 30), 180, 360, fill=GLASS_EDGE + (90,), width=2)
        _glass["back"], _glass["front"] = back, front
    return _glass["back"], _glass["front"]


def draw_piece(d, p, y, dx=0.0, highlight=0.0):
    pts = [(p.x + dx + px, y + py) for px, py in p.poly]
    d.polygon([(p.x + dx + px * 1.18, y + py * 1.18 + 4) for px, py in p.poly], fill=(14, 14, 18, 200))
    col = mix(p.col, (120, 126, 140), highlight * 0.25)
    d.polygon(pts, fill=col + (255,))
    top = [(p.x + dx + px * 0.62 - p.r * 0.12, y + py * 0.55 - p.r * 0.2) for px, py in p.poly]
    d.polygon(top, fill=mix(col, (180, 180, 180), 0.22) + (150,))
    if p.kind == "chip":
        rnd = random.Random(int(p.x * 3 + p.y))
        for i in range(2):
            bw = p.r * rnd.uniform(0.5, 0.9)
            yy = y - p.r * 0.2 + i * p.r * 0.32
            d.line((p.x + dx - p.r * 0.45, yy, p.x + dx - p.r * 0.45 + bw, yy), fill=mix(col, (30, 30, 34), 0.5) + (200,), width=3)
    if highlight > 0:
                d.line(pts + [pts[0]], fill=(205, 214, 230, int(190 * highlight)), width=2)


def draw_gem(img, cx, cy, size, alpha=1.0, glint=0.0, flash=0.0):
    put_sprite(img, GEM_HALO, cx, cy, scale=size / 110 * (1 + 0.6 * flash), alpha=alpha * (0.45 + 0.55 * max(glint, flash)))
    d = ImageDraw.Draw(img, "RGBA")
    w, h = size, size * 0.86
    y0, y1, y2 = cy - h * 0.45, cy - h * 0.1, cy + h * 0.5
    tl, tr = (cx - w * 0.26, y0), (cx + w * 0.26, y0)
    gl, gr = (cx - w / 2, y1), (cx + w / 2, y1)
    cul = (cx, y2)
    a = int(255 * alpha)
    b = flash * 0.5
    d.polygon([gl, tl, tr, gr], fill=mix((222, 240, 252), (255, 255, 255), b) + (a,))
    d.polygon([gl, tl, (cx - w * 0.1, y1)], fill=mix((196, 226, 246), (255, 255, 255), b) + (a,))
    d.polygon([gr, tr, (cx + w * 0.1, y1)], fill=mix((240, 250, 255), (255, 255, 255), b) + (a,))
    d.polygon([gl, (cx, y1), cul], fill=mix((150, 205, 236), (255, 255, 255), b) + (a,))
    d.polygon([(cx, y1), gr, cul], fill=mix((205, 234, 250), (255, 255, 255), b) + (a,))
    ink = (120, 175, 210, int(200 * alpha))
    for seg in ((tl, (cx - w * 0.1, y1)), (tr, (cx + w * 0.1, y1)), ((cx - w * 0.1, y1), cul), ((cx + w * 0.1, y1), cul), (gl, gr)):
        d.line(seg, fill=ink, width=2)
    d.polygon([gl, tl, tr, gr, cul], outline=(255, 255, 255, a))
    if glint > 0.05:
        gx, gy = cx + w * 0.18, y0 + h * 0.06
        L = size * 0.42 * glint
        d.line((gx - L, gy, gx + L, gy), fill=(255, 255, 255, int(230 * glint * alpha)), width=3)
        d.line((gx, gy - L, gx, gy + L), fill=(255, 255, 255, int(230 * glint * alpha)), width=3)
        put_sprite(img, CORE, gx, gy, scale=0.9 * glint, alpha=alpha)


def world(t_pour, meter, gems_visible=(True, True, True), glint=(0, 0, 0), gem_flash=(0, 0, 0), highlights=None, pile=True):
    """The column and its contents in world coords. t_pour is time since the pour began (large = settled)."""
    back, front = glass_layers()
    img = back.copy()
    d = ImageDraw.Draw(img, "RGBA")
    x1 = COL[2]
    my0, my1 = COL[1] + 20, COL[3] - 20
    fy = my1 - (my1 - my0) * clamp(meter)
    if meter > 0.001:
        d.rounded_rectangle((x1 + 26, fy, x1 + 38, my1), radius=6, fill=METER + (235,))
    if pile:
        highlights = highlights or {}
        for i, p in enumerate(PIECES):
            y = fall_y(t_pour, p.drop, p.y)
            if y is not None:
                draw_piece(d, p, y, highlight=highlights.get(i, 0.0))
        for i, (gx, gy, gr) in enumerate(GEMS):
            if not gems_visible[i]:
                continue
            y = fall_y(t_pour, GEM_DROP[i], gy)
            if y is not None:
                draw_gem(img, gx, y, GEM_SIZE, glint=glint[i], flash=gem_flash[i])
        d = ImageDraw.Draw(img, "RGBA")
        for p in COVERS:
            y = fall_y(t_pour, p.drop, p.y)
            if y is not None:
                draw_piece(d, p, y)
    img.alpha_composite(front)
    return img


def place(layer, scale, ox, oy):
    """Composite a world layer onto the ground with world point p -> p * scale + (ox, oy)."""
    out = ground()
    if abs(scale - 1) < 1e-4 and abs(ox) < 0.5 and abs(oy) < 0.5:
        out.alpha_composite(layer)
        return out
    nw, nh = int(W * scale), int(H * scale)
    big = layer.resize((nw, nh), Image.BILINEAR)
    lx, ly = int(round(ox)), int(round(oy))
    sx0, sy0 = max(0, -lx), max(0, -ly)
    sx1, sy1 = min(nw, W - lx), min(nh, H - ly)
    if sx1 > sx0 and sy1 > sy0:
        out.alpha_composite(big.crop((sx0, sy0, sx1, sy1)), (lx + sx0, ly + sy0))
    return out


def xf(p, scale, ox, oy):
    return p[0] * scale + ox, p[1] * scale + oy


def zoom_about(c_world, c_screen, z):
    return z, c_screen[0] - c_world[0] * z, c_screen[1] - c_world[1] * z


def tag(img, x, y, text, alpha=1.0, color=TEXT, size=28, bg=(8, 10, 16)):
    if alpha <= 0:
        return
    f = font("Inter-Medium.otf", size)
    d = ImageDraw.Draw(img, "RGBA")
    tw = d.textlength(text, font=f)
    d.rounded_rectangle((x - tw / 2 - size * 0.6, y - size * 0.8, x + tw / 2 + size * 0.6, y + size * 0.9), radius=size * 0.4,
                        fill=bg + (int(200 * alpha),))
    d.text((x - tw / 2, y - size * 0.62), text, font=f, fill=color + (int(255 * alpha),))


def tag_box(x, y, text, size=28):
    f = font("Inter-Medium.otf", size)
    tw = f.getlength(text)
    return (x - tw / 2 - size * 0.6, y - size * 0.8, x + tw / 2 + size * 0.6, y + size * 0.9)


LABEL_Y, LABEL_SIZE = 322, 44


def label(img, text, alpha=1.0):
    tag(img, W / 2, LABEL_Y, text, alpha=alpha, size=LABEL_SIZE)


def labels(img, t, seq):
    for i, (lab, at) in enumerate(seq):
        end = seq[i + 1][1] if i + 1 < len(seq) else 1e9
        a = ease_out((t - at) / 0.35) * (1 - ease_out((t - end + 0.3) / 0.3))
        if a > 0:
            label(img, lab, alpha=a)


def cursor(img, pos_fn, t, alpha=1.0, trail=8, trail_dt=0.035, dim=0.0):
    for k in range(trail, 0, -1):
        px, py = pos_fn(t - k * trail_dt)
        put_sprite(img, HALO, px, py, scale=0.22 * (1 - k / (trail + 2)), alpha=alpha * 0.35 * (1 - k / (trail + 1)))
    x, y = pos_fn(t)
    put_sprite(img, HALO, x, y, scale=0.62 * (1 - 0.3 * dim), alpha=alpha * (1 - 0.45 * dim))
    put_sprite(img, CORE, x, y, scale=1.0, alpha=alpha * (1 - 0.35 * dim))


# ---------------------------------------------------------------- scenes
def quick_path(t):
    return 540 + 165 * math.sin(4.1 * t), 760 + 250 * math.sin(2.9 * t + 1.0)


def s1(t, dur):
    img = place(world(0, 0.0, pile=False), 1, 0, 0)
    cursor(img, quick_path, t + 0.3, alpha=ease_out(t / 0.4))
    labels(img, t, [("Claude Code's context window", 0.45)])
    return img


SLOW_AT = 1.75


def s2_phase(t):
    return t if t < SLOW_AT else SLOW_AT + (t - SLOW_AT) * 0.12


def s2_path(t):
    ph = s2_phase(t + 3.0)
    x = 540 + 165 * math.sin(4.1 * ph)
    y = lerp(760, 1010, smooth((t - 1.0) / 1.0)) + lerp(250, 70, smooth((t - 1.0) / 1.0)) * math.sin(2.9 * ph + 1.0)
    return x, y


def s2(t, dur):
    landed = sum(1 for p in PIECES if t >= p.drop + 0.3)
    meter = 0.42 * smooth(landed / len(PIECES))
    img = place(world(t, meter), 1, 0, 0)
    slow = smooth((t - SLOW_AT) / 0.6)
    cursor(img, s2_path, t, trail=int(lerp(8, 3, slow)), dim=slow)
    labels(img, t, [("not even half full", 1.85)])
    return img


Z_C, Z_S, Z_MAX = (540, 1060), (540, 860), 1.45
# anchors for the junk tags: target points, resolved to the nearest piece
_TAG_TARGETS = [("old file reads", (331, 941), 2.85), ("error logs", (725, 1000), 3.95), ("dead ends", (560, 1105), 4.95)]


def _nearest(pt):
    best, bi = 1e9, 0
    for i, p in enumerate(PIECES):
        dd = (p.x - pt[0]) ** 2 + (p.y - pt[1]) ** 2
        if dd < best and all(abs(p.x - gx) > 50 or abs(p.y - gy) > 50 for gx, gy, _ in GEMS):
            best, bi = dd, i
    return bi


JUNK_TAGS = [(txt, _nearest(pt), at) for txt, pt, at in _TAG_TARGETS]


def s3_xf(t):
    q = smooth(t / 1.6)
    z = lerp(1.0, Z_MAX, q)
    cs = (Z_C[0], lerp(Z_C[1], Z_S[1], q))
    return zoom_about(Z_C, cs, z)


def s3_cursor_world(t):
    gx, gy, _ = GEMS[1]
    x = lerp(330, 790, clamp(t / DUR['s3']))
    return x, gy - 6 + 26 * math.sin(t * 1.7) + (gx - x) * 0.02


def s3(t, dur):
    sc, ox, oy = s3_xf(t)
    glint = tuple(clamp((t - 0.8) / 0.5) * (0.55 + 0.45 * math.sin(t * 3.1 + i * 2.1)) for i in range(3))
    hl = {i: ease_out((t - at) / 0.25) for _, i, at in JUNK_TAGS}
    img = place(world(99, 0.42, glint=glint, highlights=hl), sc, ox, oy)
    cursor(img, lambda tt: xf(s3_cursor_world(tt), *s3_xf(tt)), t, trail=4, trail_dt=0.06, dim=0.7)
    for txt, i, at in JUNK_TAGS:
        a = ease_out((t - at) / 0.25)
        if a > 0:
            p = PIECES[i]
            x, y = xf((p.x, p.y), sc, ox, oy)
            tag(img, x, y - 62 - (1 - a) * 18, txt, alpha=a, size=30)
    return img


def s4_xf(t):
    q = smooth(t / 0.75)
    return lerp(1.0, SHRINK[0], q), lerp(0.0, SHRINK[1], q), lerp(0.0, SHRINK[2], q)


GEM_LIFT = [1.75, 2.2, 2.65]       # gems 0, 1, 2 lift into nodes 0, 1, 2
LIFT_DUR = 0.7
READ_T, WORK_T, CARRY_T, DROP_T = 3.6, 4.3, 4.85, 5.3
CURSOR_REST = (770, 612)


def _arc(a, b, p, h=140):
    return lerp(a[0], b[0], p), lerp(a[1], b[1], p) - h * math.sin(math.pi * p)


def s4_cursor(t):
    sc, ox, oy = s4_xf(t)
    pile_pt = xf((540, 975), sc, ox, oy)
    if t < 0.95:
        return pile_pt[0] + 30 * math.sin(t * 1.3), pile_pt[1] + 12 * math.sin(t * 1.9)
    if t < 1.65:
        return _arc(xf((540, 975), *s4_xf(0.95)), CURSOR_REST, ease_out((t - 0.95) / 0.7), h=220)
    if t < READ_T:
        return CURSOR_REST[0] + 10 * math.sin(t * 2), CURSOR_REST[1] + 6 * math.sin(t * 2.6)
    if t < WORK_T:
        p = (t - READ_T) / (WORK_T - READ_T)
        pts = [CURSOR_REST] + [(NODES[i][0], NODES[i][1] - 4) for i in range(3)]
        seg = min(2, int(p * 3))
        return _arc(pts[seg], pts[seg + 1], smooth(p * 3 - seg), h=26) if seg < 3 else pts[-1]
    work_pt = xf((540, 1000), *SHRINK)
    if t < WORK_T + 0.35:
        return _arc((NODES[2][0], NODES[2][1] - 4), work_pt, smooth((t - WORK_T) / 0.35), h=90)
    if t < CARRY_T:
        return work_pt[0] + 26 * math.sin((t - WORK_T) * 22), work_pt[1] + 10 * math.cos((t - WORK_T) * 17)
    if t < DROP_T:
        return _arc(work_pt, (NODES[3][0], NODES[3][1] - 70), smooth((t - CARRY_T) / (DROP_T - CARRY_T)), h=120)
    return NODES[3][0] + 8 * math.sin(t * 2), NODES[3][1] - 70 + 5 * math.sin(t * 2.4)


def draw_case(img, t):
    slide = spring(clamp((t - 0.25) / 0.75))
    if slide <= 0:
        return
    dx = (1 - slide) * 620
    x0, y0, x1, y1 = CASE[0] + dx, CASE[1], CASE[2] + dx, CASE[3]
    light = ease_out((t - 0.95) / 0.5)
    put_sprite(img, PURPLE_GLOW, (x0 + x1) / 2, (y0 + y1) / 2, scale=2.0, alpha=0.55 * light)
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((x0 + 8, y0 + 22, x1 + 8, y1 + 30), radius=26, fill=(0, 0, 0, 140))
    d.rounded_rectangle((x0, y0, x1, y1), radius=24, fill=CASE_BODY + (255,))
    d.rounded_rectangle((x0 + 14, y0 + 58, x1 - 14, y1 - 14), radius=16, fill=mix(CASE_BODY, CASE_PANEL, light) + (255,))
    for gx in range(int(x0 + 40), int(x1 - 20), 38):
        for gy in range(int(y0 + 84), int(y1 - 24), 38):
            d.ellipse((gx - 1.5, gy - 1.5, gx + 1.5, gy + 1.5), fill=PURPLE_SOFT + (int(40 * light),))
    d.rounded_rectangle((x0, y0, x1, y1), radius=24, outline=mix((70, 50, 110), PURPLE_HI, light) + (255,), width=4)
    hat = _hat()
    img.alpha_composite(hat, (int(x0 + 26), int(y0 + 14)))
    f = font("Inter-Bold.otf", 30)
    d.text((x0 + 26 + hat.width + 12, y0 + 16), "Dandy", font=f, fill=mix((120, 100, 160), TEXT, light) + (255,))
    return dx


_hat_img = None


def _hat():
    global _hat_img
    if _hat_img is None:
        h = Image.open(os.path.join(ROOT, "motifs", "logo-hat-light.png")).convert("RGBA")
        _hat_img = h.resize((int(h.width * 34 / h.height), 34), Image.LANCZOS)
    return _hat_img


def draw_edge(img, a, b, p):
    if p <= 0:
        return
    d = ImageDraw.Draw(img, "RGBA")
    ex, ey = lerp(a[0], b[0], p), lerp(a[1], b[1], p)
    d.line((a[0], a[1], ex, ey), fill=PURPLE_HI + (70,), width=10)
    d.line((a[0], a[1], ex, ey), fill=PURPLE_SOFT + (230,), width=3)


def s4(t, dur):
    sc, ox, oy = s4_xf(t)
    lifted = tuple(t >= GEM_LIFT[i] for i in range(3))
    img = place(world(99, 0.42, gems_visible=tuple(not v for v in lifted), glint=(0.4, 0.4, 0.4)), sc, ox, oy)
    draw_case(img, t)
    # edges between nodes that have landed
    for a, b, at in EDGES:
        draw_edge(img, NODES[a], NODES[b], ease_out((t - at) / 0.4))
    # gems flying from the pile into the case, then sitting as nodes
    for i in range(3):
        st = GEM_LIFT[i]
        if t < st:
            continue
        src = xf((GEMS[i][0], GEMS[i][1]), *SHRINK)
        p = clamp((t - st) / LIFT_DUR)
        if p < 1:
            x, y = _arc(src, NODES[i], ease_out(p), h=170)
            draw_gem(img, x, y, lerp(GEM_SIZE * SHRINK[0], 74, ease_out(p)), glint=0.6, flash=0.4 * (1 - p))
        else:
            cx, cy = s4_cursor(t)
            near = clamp(1 - math.hypot(cx - NODES[i][0], cy - NODES[i][1]) / 60) if READ_T <= t < WORK_T + 0.1 else 0
            settle = spring(clamp((t - st - LIFT_DUR) / 0.4))
            draw_gem(img, NODES[i][0], NODES[i][1], 74 * (0.85 + 0.15 * settle), glint=0.35 + 0.3 * math.sin(t * 2.4 + i), flash=near)
            a = ease_out((t - st - LIFT_DUR + 0.05) / 0.3)
            tag(img, NODES[i][0], NODES[i][1] + 66, NODE_TAGS[i], alpha=a, size=26, bg=(20, 11, 38))
    # the new diamond, carried from the column and dropped in
    if CARRY_T <= t < DROP_T:
        cx, cy = s4_cursor(t)
        draw_gem(img, cx, cy + 34, 44, glint=0.7, alpha=ease_out((t - CARRY_T) / 0.2))
    elif t >= DROP_T:
        p = clamp((t - DROP_T) / 0.3)
        y = lerp(NODES[3][1] - 36, NODES[3][1], p * p)
        draw_gem(img, NODES[3][0], y, lerp(44, 74, spring(clamp((t - DROP_T) / 0.45))), glint=0.6, flash=0.6 * (1 - clamp((t - DROP_T - 0.2) / 0.5)))
    cursor(img, s4_cursor, t, trail=7)
    labels(img, t, [("point it at Dandy", 0.3), ("a live map of your project", 2.1), ("kept current by your agent", 3.85)])
    return img


S5_GEMS = [(435, 1165, 0.15), (655, 1150, 0.3), (545, 1040, 0.45), (690, 985, 0.6)]
HOP_T0, HOP_GAP = 1.0, 0.38
HOP_SEQ = [0, 2, 1, 3, 2, 0, 3, 1]


HOP_TIMES = [1.0, 1.4, 1.8, 2.2, 2.6, 3.0]   # scene-relative arrivals; voiceover json "hops" sets them on the music's kicks


def s5_target(k):
    g = S5_GEMS[HOP_SEQ[k % len(HOP_SEQ)]]
    return g[0], g[1] - 6


def s5_cursor(t):
    T = HOP_TIMES
    if t < T[0]:
        return _arc((540, 760), s5_target(0), smooth(t / T[0]), h=0)
    k = max(i for i in range(len(T)) if T[i] <= t)
    if k + 1 < len(T) and t > T[k + 1] - 0.12:
        return _arc(s5_target(k), s5_target(k + 1), ease_out((t - (T[k + 1] - 0.12)) / 0.12), h=40)
    return s5_target(k)


def s5(t, dur):
    img = place(world(0, 0.08 * smooth(t / 0.9), pile=False), 1, 0, 0)
    cx, cy = s5_cursor(t)
    for gx, gy, at in S5_GEMS:
        y = fall_y(t, at, gy)
        if y is None:
            continue
        hit = max([h for h in HOP_TIMES if h <= t], default=None)
        near = clamp(1 - math.hypot(cx - gx, cy - gy) / 50) * (1 - clamp((t - hit) / 0.3)) if hit is not None else 0
        draw_gem(img, gx, y, 70, glint=0.5 + 0.4 * math.sin(t * 2.8 + gx), flash=near)
    cursor(img, s5_cursor, t, trail=5, trail_dt=0.025)
    labels(img, t, [("just the diamonds", 0.6)])
    return img


END_IN = (0.5, 1.0, 0.6, 0.9, 0.25, 0.5)   # logo at, bg fade, logo fade, lines at, line gap, line fade


def end_card(last, t):
    logo_at, bg_fade, logo_fade, lines_at, line_gap, line_fade = END_IN
    p = ease_out(t / bg_fade)
    bg = last.filter(ImageFilter.GaussianBlur(int(16 * p)))
    bg.alpha_composite(Image.new("RGBA", bg.size, PURPLE_BG + (int(222 * p),)))
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W * 0.12, H * 0.28, W * 0.88, H * 0.72), fill=PURPLE + (int(120 * p),))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(130)))
    d = ImageDraw.Draw(bg)
    sizes = CONTRACT["type"]["vertical"]
    a = ease_out((t - logo_at) / logo_fade) if t >= logo_at else 0
    if a > 0:
        hat = Image.open(os.path.join(ROOT, "motifs", "logo-hat-light.png")).convert("RGBA")
        hh = int(H * 0.11)
        hat = hat.resize((int(hat.width * hh / hat.height), hh), Image.LANCZOS)
        hat.putalpha(hat.split()[3].point(lambda v: int(v * a)))
        hy = H * 0.34
        bg.alpha_composite(hat, (int(W / 2 - hat.width / 2), int(hy)))
        fh = font("Inter-Bold.otf", int(sizes["headline"] * 1.5))
        tw = d.textlength("Dandy", font=fh)
        ty = hy + hh + 40
        d.text((W / 2 - tw / 2, ty), "Dandy", font=fh, fill=TEXT + (int(255 * a),))
        yy = ty + fh.size * 1.1 + 60
        gold = tuple(int(PAL["accent_gold"][i:i + 2], 16) for i in (1, 3, 5))
        for i, line in enumerate(CONTRACT["copy_rules"]["end_card_lines"]):
            b = ease_out((t - lines_at - line_gap * i) / line_fade)
            fl = font("Inter-Medium.otf", sizes["body" if i == 0 else "caption"])
            lw = d.textlength(line, font=fl)
            d.text((W / 2 - lw / 2, yy), line, font=fl, fill=(gold if i == 1 else PURPLE_SOFT) + (int(255 * b),))
            yy += fl.size * 1.1 + 50
    return bg


PURPLE_BG = tuple(int(PAL["background"][i:i + 2], 16) for i in (1, 3, 5))

SCENES = [("s1", 3.0, s1), ("s2", 4.0, s2), ("s3", 5.0, s3), ("s4", 7.0, s4), ("s5", 4.0, s5), ("end", 3.5, None)]
DUR = {sid: d for sid, d, _ in SCENES}
CAPTIONS = [
    (0.35, 2.8, "Claude Code has a huge context window."),
    (3.3, 6.7, "But it starts slipping long before it's full."),
    (7.2, 9.15, "Because most of what's in there is junk."),
    (9.25, 10.0, "Old file reads."), (10.05, 10.8, "Error logs."), (10.85, 11.8, "Dead ends."),
    (12.3, 13.9, "So point it at Dandy:"), (14.0, 16.0, "a live map of your project,"), (16.1, 18.6, "kept current by your agent."),
    (19.4, 22.2, "It holds just the diamonds."),
]
ON_SCREEN = ["Claude Code's context window", "not even half full", "old file reads", "error logs", "dead ends",
             "point it at Dandy", "a live map of your project", "kept current by your agent", "Dandy",
             "what's decided", "what's built", "what's next", "just the diamonds"]


def apply_timing():
    p = os.path.join(VIDEO, "voiceover", "diamonds.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        vo = json.load(f)
    global CAPTIONS
    for i, (sid, dur, fn) in enumerate(SCENES):
        if sid in vo.get("durations", {}):
            SCENES[i] = (sid, float(vo["durations"][sid]), fn)
            DUR[sid] = SCENES[i][1]
    global END_IN
    if "hops" in vo:
        HOP_TIMES[:] = vo["hops"]
    if "end_in" in vo:
        END_IN = tuple(vo["end_in"])
    if "lines" in vo:
        CAPTIONS = [(s - 0.05, e + 0.3, tx) for s, e, tx in vo["lines"]]
    return vo


CAP_SIZE = int(CONTRACT["type"]["vertical"]["body"] * 0.95)


def caption_lines(text, d=None):
    fnt = font("Inter-Bold.otf", CAP_SIZE)
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if fnt.getlength(trial) <= SAFE[2] - SAFE[0] - 40 or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    return lines


def caption_box(text):
    fnt = font("Inter-Bold.otf", CAP_SIZE)
    lines = caption_lines(text)
    lh, pad = fnt.size * 1.18, 20
    y = SAFE[3] - len(lines) * (lh + pad * 0.6) - 10
    w = max(fnt.getlength(l) for l in lines)
    return (W / 2 - w / 2 - pad, y - pad * 0.55, W / 2 + w / 2 + pad, y + (len(lines) - 1) * (lh + pad * 0.6) + lh + pad * 0.3)


def draw_caption(img, tg):
    cue = next((c for c in CAPTIONS if c[0] <= tg < c[1]), None)
    if cue is None:
        return
    a = min(1.0, (tg - cue[0]) / 0.25, (cue[1] - tg) / 0.2)
    fnt = font("Inter-Bold.otf", CAP_SIZE)
    d = ImageDraw.Draw(img)
    lines = caption_lines(cue[2])
    lh, pad = fnt.size * 1.18, 20
    y = SAFE[3] - len(lines) * (lh + pad * 0.6) - 10
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=fnt)
        x, yy = W / 2 - tw / 2, y + i * (lh + pad * 0.6)
        d.rounded_rectangle((x - pad, yy - pad * 0.55, x + tw + pad, yy + lh + pad * 0.3), radius=14, fill=(6, 8, 14, int(190 * a)))
        d.text((x, yy), line, font=fnt, fill=TEXT + (int(255 * a),))


# ---------------------------------------------------------------- QA
def copy_qa():
    rules = CONTRACT["copy_rules"]
    problems = []
    for tx in [c[2] for c in CAPTIONS] + ON_SCREEN:
        for ch in rules["banned_characters"]:
            if ch in tx:
                problems.append(f"banned character in {tx!r}")
        for ph in rules["banned_phrases"] + ["state layer"]:
            if ph in tx.lower():
                problems.append(f"banned phrase {ph!r} in {tx!r}")
        if len(tx.split()) > CONTRACT["type"]["max_words_on_screen"]:
            problems.append(f"too many words: {tx!r}")
    return problems


def layout_qa(starts):
    """Settled layout per scene for render/checks.check_layout: beat labels, junk tags, case, node tags, captions."""
    def lab(text):
        return tag_box(W / 2, LABEL_Y, text, LABEL_SIZE)

    def caps(sid, dur):
        out = []
        for i, (s, e, tx) in enumerate(CAPTIONS):
            t0, t1 = s - starts[sid], e - starts[sid]
            if t1 > 0 and t0 < dur:
                out.append(dict(name=f"caption {i}", bbox=caption_box(tx), enter_at=max(0, t0), exit_at=min(dur, t1)))
        return out

    col_box = (COL[0], COL[1], COL[2] + 50, COL[3] + 18)
    scenes = []
    sc = [dict(name="label", bbox=lab("Claude Code's context window")), dict(name="column", bbox=col_box)]
    scenes.append(dict(id="s1", duration=DUR["s1"], laid_out=sc + caps("s1", DUR["s1"])))
    sc = [dict(name="label", bbox=lab("not even half full"), enter_at=1.85), dict(name="column", bbox=col_box)]
    scenes.append(dict(id="s2", duration=DUR["s2"], laid_out=sc + caps("s2", DUR["s2"])))
    sc = []
    z = s3_xf(DUR['s3'])
    for txt, i, at in JUNK_TAGS:
        p = PIECES[i]
        x, y = xf((p.x, p.y), *z)
        sc.append(dict(name=f"tag {txt}", bbox=tag_box(x, y - 62, txt, 30), enter_at=at))
    scenes.append(dict(id="s3", duration=DUR["s3"], laid_out=sc + caps("s3", DUR["s3"])))
    sc0 = xf(COL[:2], *SHRINK) + xf((COL[2] + 50, COL[3] + 18), *SHRINK)
    sc = [dict(name="label", bbox=lab("a live map of your project")), dict(name="column", bbox=sc0),
          dict(name="case", bbox=(CASE[0], CASE[1], CASE[2], CASE[3] + 8))]
    scenes.append(dict(id="s4", duration=DUR["s4"], laid_out=sc + caps("s4", DUR["s4"])))
    # node tags sit inside the case: check them against each other only
    inner = [dict(name=f"node tag {NODE_TAGS[i]}", bbox=tag_box(NODES[i][0], NODES[i][1] + 66, NODE_TAGS[i], 26)) for i in range(3)]
    scenes.append(dict(id="s4-case", duration=DUR["s4"], laid_out=inner))
    sc = [dict(name="label", bbox=lab("just the diamonds")), dict(name="column", bbox=col_box)]
    scenes.append(dict(id="s5", duration=DUR["s5"], laid_out=sc + caps("s5", DUR["s5"])))
    return [f"{s}: {m}" for s, m in check_layout(scenes, CONTRACT["canvases"]["vertical"], CONTRACT)]


# ---------------------------------------------------------------- sound: glass, gravel and a cold room
SR = 48000
_rng = np.random.default_rng(19)


def _band(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x).astype(np.float32)


def _norm(x, gain):
    return (x / (np.abs(x).max() + 1e-9) * gain).astype(np.float32)


def snd_clack(gain=0.3):
    n = int(SR * 0.12)
    t = np.arange(n) / SR
    f = _rng.uniform(500, 1400)
    x = _band(_rng.normal(0, 1, n), 600, 4500) * np.exp(-t * 70) + np.sin(2 * np.pi * f * t) * np.exp(-t * 90) * 0.4
    return _norm(x, gain)


def snd_ting(gain=0.3, f0=1760):
    n = int(SR * 1.4)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f0 * m * t) * np.exp(-t * (3 + 2.5 * k)) / (k + 1) for k, m in enumerate((1.0, 2.76, 5.4)))
    return _norm(x, gain)


def snd_whoosh(gain=0.4, dur=0.6):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = _band(_rng.normal(0, 1, n), 300, 3500) * np.sin(np.pi * t / dur) ** 2
    return _norm(x, gain)


def snd_drone(gain=0.2, dur=2.0, f=55):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 1.5 * t)) * np.sin(np.pi * t / dur) ** 1.5
    return _norm(x, gain)


def snd_tick(gain=0.25):
    n = int(SR * 0.05)
    t = np.arange(n) / SR
    return _norm(_band(_rng.normal(0, 1, n), 2500, 9000) * np.exp(-t * 160), gain)


def snd_tone(gain=0.25):
    n = int(SR * 2.2)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * 440 * f * t + k) * np.exp(-t * (1.4 + 1.2 * k)) / (k + 1) for k, f in enumerate((1.0, 2.0, 3.01)))
    return _norm(x, gain)


def build_bed(path, total, starts):
    n = int(SR * total) + SR
    L = np.zeros(n, np.float32)
    R = np.zeros(n, np.float32)

    def put(x, at, pan=0.0):
        i = int(at * SR)
        if 0 <= i < n:
            x = x[:n - i]
            L[i:i + len(x)] += x * math.cos((pan + 1) * math.pi / 4) * 1.41
            R[i:i + len(x)] += x * math.sin((pan + 1) * math.pi / 4) * 1.41

    room = _band(_rng.normal(0, 1, n), 50, 400)
    room = _norm(room, 0.04)
    L += room
    R += np.roll(room, 2400)
    s2, s3, s4, s5 = (starts[k] for k in ("s2", "s3", "s4", "s5"))
    for p in PIECES + COVERS:
        land_t = s2 + p.drop + 0.22 + 0.28 * (p.y - INNER[1] - 30) / 800
        put(snd_clack(0.22), land_t, pan=(p.x - 540) / 400)
    for i, (gx, gy, _) in enumerate(GEMS):
        put(snd_ting(0.12, 1900 + 200 * i), s2 + GEM_DROP[i] + 0.5, pan=(gx - 540) / 400)
    put(snd_drone(0.16, 2.4, 49), s2 + SLOW_AT - 0.2)
    put(snd_drone(0.12, 4.6, 46), s3 + 0.2)
    for _, _, at in JUNK_TAGS:
        put(snd_tick(0.3), s3 + at)
    put(snd_ting(0.09, 2400), s3 + 0.9, pan=-0.3)
    put(snd_whoosh(0.45, 0.8), s4 + 0.1, pan=0.5)
    put(snd_ting(0.22, 880), s4 + 0.95)
    for i, st in enumerate(GEM_LIFT):
        put(snd_whoosh(0.18, 0.5), s4 + st, pan=0.2)
        put(snd_ting(0.26, 1568 + 196 * i), s4 + st + LIFT_DUR, pan=0.4)
    for k in range(3):
        put(snd_tick(0.25), s4 + READ_T + 0.33 * (k + 1))
    for k in range(3):
        put(snd_clack(0.14), s4 + WORK_T + 0.3 + k * 0.12, pan=-0.5)
    put(snd_ting(0.3, 2093), s4 + DROP_T + 0.25, pan=0.4)
    for gx, gy, at in S5_GEMS:
        put(snd_ting(0.16, 1760 + (gx - 400)), s5 + at + 0.35, pan=(gx - 540) / 400)
    for h in HOP_TIMES:
        if h < DUR['s5'] - 0.05:
            put(snd_tick(0.22), s5 + h)
    put(snd_tone(0.3), starts["end"] + END_IN[0])
    peak = max(np.abs(L).max(), np.abs(R).max(), 1e-6)
    st = np.stack([L, R], 1)[:int(SR * total)] / peak * 0.6
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- render
def render(preview=False, stills=False, final=False, audio_only=False):
    vo = apply_timing()
    out = os.path.join(VIDEO, "out")
    os.makedirs(out, exist_ok=True)
    starts, acc = {}, 0.0
    for sid, dur, _ in SCENES:
        starts[sid] = acc
        acc += dur
    total = acc
    problems = copy_qa()
    layout = layout_qa(starts)
    with open(os.path.join(out, "qa-diamonds-vertical.json"), "w") as f:
        json.dump(dict(canvas="vertical", look="vault", duration=total, copy_problems=problems, layout_problems=layout,
                       end_card="soft, without Dandy Man", gold_elements_max=1,
                       scenes=[dict(id=s, start=round(starts[s], 2), duration=d) for s, d, _ in SCENES]), f, indent=2)
    if problems or layout:
        print("QA FAILED:", problems + layout)
        return False
    mp4 = os.path.join(out, "09-diamonds-vertical.mp4")
    wav = os.path.join(out, "diamonds-bed.wav")
    step = 3 if preview else 1
    if not audio_only:
        tmp = tempfile.mkdtemp(prefix="dandy-diamonds-")
        n, last = 0, None
        for sid, dur, fn in SCENES:
            frames = int(round(dur * FPS))
            picks = {int(frames * 0.25), int(frames * 0.6), frames - 2}
            for i in range(frames):
                if i % step or (stills and i not in picks):
                    continue
                t = i / FPS
                tg = starts[sid] + t
                img = end_card(last, t) if fn is None else fn(t, dur)
                if fn is not None:
                    last = img
                fr = finish(img, t, tg, bloom=0.55, grain=2.4, vignette=0.36, drift=0.4, zoom=1.03)
                draw_caption(fr, tg)
                if stills:
                    fr.convert("RGB").save(os.path.join(out, f"still-{sid}-{t:04.1f}.png"))
                    continue
                fr.convert("RGB").save(os.path.join(tmp, f"f{n:06d}.png"), compress_level=1)
                n += 1
        if stills:
            print("stills in", out)
            return True
    build_bed(wav, total, starts)
    if audio_only:
        src = mp4 + ".video.mp4"
        shutil.copy(mp4, src)
        vid_in = ["-i", src]
    else:
        vid_in = ["-framerate", str(FPS // step), "-i", os.path.join(tmp, "f%06d.png")]
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + vid_in + ["-i", wav]
    if vo and vo.get("file") and not preview:
        cmd += ["-i", os.path.join(ROOT, vo["file"])]
        hp = "" if vo.get("mixed") else "highpass=f=70,"
        ff = vo.get("file_fade_out")
        tail = f"afade=t=out:st={ff[0]}:d={ff[1]}," if ff else ""
        fc = (f"[2:a]atrim=start={vo.get('offset_s', 0)},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
              f"{hp}{tail}volume={vo.get('voice_db', 7.5)}dB,apad=whole_dur={total},asplit=2[v][vk];[1:a]volume={vo.get('bed_db', 0)}dB[b];"
              f"[b][vk]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350[bd];"
              f"[v][bd]amix=inputs=2:normalize=0:duration=longest,atrim=0:{total},afade=t=out:st={total - 1.2}:d=1.2,alimiter=limit=0.89:level=0[a]")
        cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += (["-c:v", "copy"] if audio_only else ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18" if final else "20", "-preset", "slow" if final else "medium"])
    cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4]
    subprocess.run(cmd, check=True)
    if audio_only:
        os.remove(src)
    else:
        shutil.rmtree(tmp)
    print(f"rendered {mp4} ({total:.1f} s)")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--audio-only", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if render(a.preview, a.stills, a.final, a.audio_only) else 1)

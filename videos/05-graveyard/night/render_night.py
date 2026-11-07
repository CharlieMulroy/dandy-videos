"""Renderer for video 05's own look: a graveyard of dead side projects at night, with the reaper of context rot.
Vertical only.

Usage:  python3 videos/05-graveyard/night/render_night.py [--preview] [--final] [--stills]

Everything is procedural: a moon behind thin cloud, parallax hills and bare trees, three layers of drifting
ground fog, engraved tombstones laid out in one continuous world the camera drifts along, the reaper (hooded
cloak, scythe, two cold eye lights), the chat glow of beat 4, the open grave, lantern and lit gate of beat 5,
and the soft end card. Palette is this video's own (night, fog, stone, cold green eyes); the only brand purple
is the lantern and the window beyond the gate, which hands off to the end card.
Scene durations can be overridden by voiceover/night.json; narration captions come from captions.json.
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

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "render"))
import sfx_night  # noqa: E402
from finish import finish, spring  # noqa: E402

with open(os.path.join(ROOT, "style", "contract.json")) as f:
    CONTRACT = json.load(f)
BRAND = CONTRACT["palette"]
FONT_DIR = "/usr/share/fonts/opentype/inter"
FPS = CONTRACT["motion"]["fps"]
W, H = 1080, 1920
SAFE = (int(W * 0.08), CONTRACT["layout"]["vertical_safe_top_px"], W - int(W * 0.08), H - CONTRACT["layout"]["vertical_safe_bottom_px"])

NIGHT = (7, 11, 16)
SKY_TOP = (4, 7, 12)
SKY_LOW = (16, 24, 34)
FOG = (159, 179, 200)
MOON = (232, 238, 242)
STONE = (74, 83, 92)
STONE_DARK = (42, 48, 56)
STONE_LIGHT = (108, 118, 128)
GROUND = (12, 17, 22)
GROUND_LIGHT = (22, 30, 36)
TEXT = (217, 222, 227)
ENGRAVE = (28, 32, 38)
REAPER = (2, 3, 5)
REAPER_EDGE = (34, 42, 52)
EYES = (184, 255, 217)
PURPLE = tuple(int(BRAND["highlight"].lstrip("#")[k:k + 2], 16) for k in (0, 2, 4))
GOLD = tuple(int(BRAND["accent_gold"].lstrip("#")[k:k + 2], 16) for k in (0, 2, 4))

HORIZON = int(H * 0.56)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = max(0.0, min(1.0, t))
    return t * t


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, p):
    return a + (b - a) * p


def mix(c1, c2, p):
    return tuple(int(lerp(c1[i], c2[i], p)) for i in range(3))


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), max(1, int(size)))


def alpha_mul(im, a):
    if a >= 1:
        return im
    im = im.copy()
    im.putalpha(im.split()[3].point(lambda v: int(v * a)))
    return im


# ---------- depth ----------
def depth_scale(p):
    """p is 0 (horizon) to 1 (nearest row). Returns (ground_y, scale)."""
    return HORIZON + (H * 0.22) * (p ** 1.3), 0.12 + 0.88 * (p ** 1.4)


def screen_x(wx, cam, p):
    return W / 2 + (wx - cam) * p


# ---------- noise and sky ----------
def value_noise(w, h, cells, seed, octaves=4):
    r = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        c = cells * (2 ** o)
        g = r.random((max(2, h * c // w + 2), c + 2)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += np.asarray(im).astype(np.float32) / 255 * amp
        total += amp
        amp *= 0.5
    out /= total
    out = (out - out.min()) / (out.max() - out.min() + 1e-6)
    return out


_sky = None


def sky():
    global _sky
    if _sky is None:
        yy = np.linspace(0, 1, H).astype(np.float32)[:, None]
        grad = np.zeros((H, W, 3), np.float32)
        for i in range(3):
            grad[..., i] = SKY_TOP[i] + (SKY_LOW[i] - SKY_TOP[i]) * np.clip(yy / 0.6, 0, 1) ** 1.6
        # ground below the horizon
        grad[HORIZON:, :] = np.array(GROUND, np.float32)
        gy = np.linspace(0, 1, H - HORIZON).astype(np.float32)[:, None, None]
        grad[HORIZON:, :] = np.array(GROUND, np.float32) * (1 - gy * 0.5) + np.array(GROUND_LIGHT, np.float32) * gy * 0.5
        im = Image.fromarray(grad.astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(im)
        rnd = random.Random(5)
        for _ in range(140):
            x, y = rnd.random() * W, rnd.random() * HORIZON * 0.85
            r = rnd.random() * 1.4 + 0.3
            d.ellipse((x - r, y - r, x + r, y + r), fill=mix(SKY_TOP, MOON, rnd.uniform(0.3, 0.8)) + (255,))
        _sky = im
    return _sky.copy()


def draw_moon(frame, t, cam):
    mx, my, mr = W * 0.70 - cam * 0.02, H * 0.19, 92
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for k, (rr, a) in enumerate(((mr * 4.2, 22), (mr * 2.6, 40), (mr * 1.5, 70))):
        gd.ellipse((mx - rr, my - rr, mx + rr, my + rr), fill=mix(SKY_LOW, MOON, 0.6) + (a,))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    frame.alpha_composite(glow)
    d = ImageDraw.Draw(frame, "RGBA")
    d.ellipse((mx - mr, my - mr, mx + mr, my + mr), fill=MOON + (255,))
    # a few maria
    for (ox, oy, r) in ((-20, -10, 22), (18, 20, 16), (-5, 30, 10)):
        d.ellipse((mx + ox - r, my + oy - r, mx + ox + r, my + oy + r), fill=mix(MOON, SKY_LOW, 0.18) + (255,))
    # thin cloud across it, drifting
    cl = cloud_strip()
    off = int((t * 18 + cam * 0.03) % cl.width)
    strip = Image.new("RGBA", (W, cl.height), (0, 0, 0, 0))
    strip.paste(cl, (-off, 0))
    strip.paste(cl, (cl.width - off, 0))
    frame.alpha_composite(strip, (0, int(my - cl.height / 2 + 10)))


_cloud = None


def cloud_strip():
    global _cloud
    if _cloud is None:
        w, h = 2400, 260
        n = value_noise(w, h, 6, 77, octaves=5)
        band = np.exp(-((np.linspace(-1, 1, h)[:, None]) ** 2) / 0.35)
        a = np.clip((n - 0.45) * 2.2, 0, 1) * band * 0.75
        arr = np.zeros((h, w, 4), np.uint8)
        arr[..., :3] = mix(SKY_LOW, FOG, 0.35)
        arr[..., 3] = (a * 255).astype(np.uint8)
        _cloud = Image.fromarray(arr, "RGBA")
    return _cloud


# ---------- far landscape ----------
_hills = {}


def hills_layer(seed, w, h, lift, color):
    key = (seed, w, h, lift)
    if key not in _hills:
        n = value_noise(w, 8, 5, seed, octaves=3)[4]
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        pts = [(x, h - lift - n[x] * lift * 0.9) for x in range(0, w, 4)] + [(w, h), (0, h)]
        d.polygon(pts, fill=color + (255,))
        _hills[key] = im
    return _hills[key]


def branch(d, x, y, ang, length, width, depth, rnd, color):
    if depth == 0 or length < 6:
        return
    x2, y2 = x + math.cos(ang) * length, y - math.sin(ang) * length
    d.line((x, y, x2, y2), fill=color, width=max(1, int(width)))
    for k in range(2 if depth > 2 else rnd.choice((1, 2))):
        a = ang + rnd.uniform(-0.75, 0.75) + (0.35 if k == 0 else -0.35)
        branch(d, x2, y2, a, length * rnd.uniform(0.62, 0.78), width * 0.68, depth - 1, rnd, color)


_trees = None


def trees_layer():
    global _trees
    if _trees is None:
        w, h = 4200, 700
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        rnd = random.Random(12)
        col = (6, 9, 13, 255)
        for x in range(120, w, 330):
            tx = x + rnd.uniform(-90, 90)
            th = rnd.uniform(240, 380)
            d.line((tx, h, tx, h - th), fill=col, width=14)
            branch(d, tx, h - th, math.pi / 2, th * 0.55, 10, 5, rnd, col)
        _trees = im
    return _trees


def draw_landscape(frame, cam):
    far = hills_layer(21, 3000, 180, 110, mix(SKY_LOW, NIGHT, 0.5))
    near = hills_layer(22, 3000, 200, 80, NIGHT)
    for layer, p, yb in ((far, 0.05, HORIZON + 6), (near, 0.09, HORIZON + 10)):
        off = int(cam * p) % layer.width
        strip = Image.new("RGBA", (W, layer.height), (0, 0, 0, 0))
        strip.paste(layer, (-off, 0))
        strip.paste(layer, (layer.width - off, 0))
        frame.alpha_composite(strip, (0, yb - layer.height))
    tl = trees_layer()
    off = int(cam * 0.16) % tl.width
    strip = Image.new("RGBA", (W, tl.height), (0, 0, 0, 0))
    strip.paste(tl, (-off, 0))
    strip.paste(tl, (tl.width - off, 0))
    frame.alpha_composite(strip, (0, HORIZON + 14 - tl.height))
    # ground rows: faint lighter streaks for the paths between rows
    d = ImageDraw.Draw(frame, "RGBA")
    for p in (0.25, 0.5, 0.8):
        gy, _ = depth_scale(p)
        d.line((0, gy + 6, W, gy + 6), fill=GROUND_LIGHT + (45,), width=int(2 + 4 * p))


# ---------- fog ----------
_fog = {}


def fog_tex(seed):
    if seed not in _fog:
        w, h = 3000, 520
        n = value_noise(w, h, 5, seed, octaves=5)
        yy = np.linspace(0, 1, h)[:, None]
        band = np.clip((yy - 0.05) / 0.45, 0, 1) * np.clip((1.0 - yy) / 0.25 + 0.2, 0, 1)
        a = np.clip((n - 0.32) * 1.9, 0, 1) * band
        _fog[seed] = a.astype(np.float32)
    return _fog[seed]


def draw_fog(frame, t, cam, strength=1.0, color=FOG):
    """Three fog layers at different depths; each a scrolled crop of a noise band over the ground."""
    for seed, p, speed, top, height, alpha in ((1, 0.45, 26, HORIZON - 40, 300, 0.30), (2, 0.8, 44, HORIZON + 90, 420, 0.36), (3, 1.2, 70, HORIZON + 420, 560, 0.40)):
        tex = fog_tex(seed)
        th, tw = tex.shape
        off = int(t * speed + cam * p * 0.8) % tw
        band = np.concatenate([tex[:, off:], tex[:, :off]], axis=1)[:, :W]
        if band.shape[1] < W:
            band = np.concatenate([band, tex[:, : W - band.shape[1]]], axis=1)
        band = np.asarray(Image.fromarray((band * 255).astype(np.uint8)).resize((W, height), Image.BILINEAR)).astype(np.float32) / 255
        arr = np.zeros((height, W, 4), np.uint8)
        arr[..., :3] = color
        arr[..., 3] = np.clip(band * alpha * strength * 255, 0, 255).astype(np.uint8)
        frame.alpha_composite(Image.fromarray(arr, "RGBA"), (0, int(top)))


# ---------- stones ----------
STONES = [
    # wx, depth p, kind, name, epitaph
    (0, 1.0, "round", "Budget App", "Started with a prompt.\nBuried in a tab."),
    (1150, 1.0, "slab", "Portfolio Site v3", "Rebuilt the login twice.\nDid not survive the third."),
    (2300, 1.0, "round", "Discord Bot", "Last words:\n\"as I mentioned earlier\""),
    (3450, 1.0, "cross", "Recipe Scraper", "2026 to 2026"),
    (4700, 1.0, "slab", "Habit Tracker", "Explained eleven times.\nFinished zero."),
    # a back row and a far row for depth, names only
    (520, 0.62, "round", "Side Project #14", "Beloved for a weekend."),
    (1800, 0.62, "slab", "Inventory Tool", "Cause of death:\n\"let me catch you up\""),
    (3000, 0.62, "round", "The Newsletter Thing", "Session ended.\nSo did it."),
    (4200, 0.62, "cross", "CLI Helper", ""),
    (5400, 0.62, "slab", "Dashboard v2", "Explained. Re-explained."),
    (-300, 0.36, "round", "", ""), (700, 0.36, "cross", "", ""), (1700, 0.36, "slab", "", ""), (2600, 0.36, "round", "", ""),
    (3600, 0.36, "slab", "", ""), (4500, 0.36, "cross", "", ""), (5400, 0.36, "round", "", ""), (6400, 0.36, "slab", "", ""),
]
_stone_cache = {}


def stone_image(kind, name, epitaph, blank=False):
    key = (kind, name, epitaph, blank)
    if key in _stone_cache:
        return _stone_cache[key]
    w, h = 460, 560
    im = Image.new("RGBA", (w + 80, h + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, y0 = 40, 30
    rnd = random.Random(hash(key) & 0xFFFF)
    tilt = rnd.uniform(-2.5, 2.5)
    if kind == "round":
        body = (x0 + 30, y0 + 20, x0 + w - 30, y0 + h)
        d.rounded_rectangle(body, radius=150, fill=STONE + (255,))
        d.rectangle((x0 + 30, y0 + 220, x0 + w - 30, y0 + h), fill=STONE + (255,))
    elif kind == "slab":
        d.rounded_rectangle((x0 + 20, y0 + 40, x0 + w - 20, y0 + h), radius=26, fill=STONE + (255,))
    else:  # cross
        d.rounded_rectangle((x0 + w / 2 - 50, y0, x0 + w / 2 + 50, y0 + h), radius=18, fill=STONE + (255,))
        d.rounded_rectangle((x0 + 60, y0 + 130, x0 + w - 60, y0 + 230), radius=18, fill=STONE + (255,))
        d.rounded_rectangle((x0 + 10, y0 + h - 70, x0 + w - 10, y0 + h), radius=16, fill=STONE + (255,))
    # moonlit edge on the left, shadow on the right
    mask = im.split()[3]
    light = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(light)
    ld.rectangle((0, 0, x0 + 70, im.height), fill=STONE_LIGHT + (120,))
    ld.rectangle((x0 + w - 120, 0, im.width, im.height), fill=STONE_DARK + (160,))
    light = light.filter(ImageFilter.GaussianBlur(40))
    light.putalpha(Image.fromarray(np.minimum(np.asarray(light.split()[3]), np.asarray(mask))))
    im.alpha_composite(light)
    # weathering speckle
    arr = np.asarray(im).astype(np.int16)
    noise = np.random.default_rng(hash(key) & 0xFFFF).normal(0, 7, arr.shape[:2] + (1,))
    arr[..., :3] = np.clip(arr[..., :3] + noise, 0, 255)
    im = Image.fromarray(arr.astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(im)
    if not blank and name:
        cx = x0 + w / 2
        y = y0 + (150 if kind != "cross" else 260)
        f_small = font("Inter-SemiBold.otf", 26)
        label = "HERE LIES"
        tw = d.textlength(label, font=f_small)
        engrave(d, (cx - tw / 2, y), label, f_small)
        y += 50
        f_name = font("Inter-Bold.otf", 40 if len(name) < 16 else 34)
        for line in wrap(name, f_name, w - 110, d):
            tw = d.textlength(line, font=f_name)
            engrave(d, (cx - tw / 2, y), line, f_name)
            y += f_name.size * 1.18
        y += 26
        f_ep = font("Inter-Regular.otf", 29)
        for para in epitaph.split("\n"):
            for line in wrap(para, f_ep, w - 110, d):
                tw = d.textlength(line, font=f_ep)
                engrave(d, (cx - tw / 2, y), line, f_ep)
                y += f_ep.size * 1.25
    im = im.rotate(tilt, resample=Image.BICUBIC, expand=False)
    _stone_cache[key] = im
    return im


def engrave(d, xy, text, f):
    x, y = xy
    d.text((x + 1, y + 2), text, font=f, fill=STONE_LIGHT + (140,))
    d.text((x, y), text, font=f, fill=ENGRAVE + (255,))


def wrap(text, fnt, max_w, d):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_stone_at(frame, img, sx, ground_y, scale, rise=0.0):
    w, h = int(img.width * scale), int(img.height * scale)
    im = img.resize((w, h), Image.LANCZOS) if scale != 1 else img
    x, y = int(sx - w / 2), int(ground_y - h * 0.94 + rise)
    # soft shadow on the ground
    sh = Image.new("RGBA", (w + 60, int(40 * scale) + 30), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((30, 10, w + 30, int(40 * scale) + 10), fill=(0, 0, 0, 150))
    frame.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)), (x - 30, int(ground_y - 22 * scale)))
    if rise > 0:  # still coming out of the ground: clip below ground
        im = im.crop((0, 0, w, max(1, int(ground_y + 6 - y))))
    frame.alpha_composite(im, (x, y))


def draw_stones(frame, cam, extra=(), skip=(), zoom=1.0):
    items = []
    for i, (wx, p, kind, name, ep) in enumerate(STONES):
        if i in skip:
            continue
        gy, sc = depth_scale(p)
        sx = screen_x(wx, cam, p * zoom)
        if -400 < sx < W + 400:
            items.append((p, sx, gy, sc * zoom, stone_image(kind, name, ep), 0.0))
    items += list(extra)
    for p, sx, gy, sc, img, rise in sorted(items, key=lambda it: it[0]):
        draw_stone_at(frame, haze(img, p), sx, gy, sc, rise)


_haze = {}


def haze(img, p):
    """Atmospheric perspective: far stones sink toward the night."""
    if p >= 0.95:
        return img
    key = (id(img), round(p, 2))
    if key not in _haze:
        k = (1 - p) * 0.62
        arr = np.asarray(img).astype(np.float32)
        arr[..., :3] = arr[..., :3] * (1 - k) + np.array(mix(NIGHT, FOG, 0.25), np.float32) * k
        _haze[key] = Image.fromarray(arr.astype(np.uint8), "RGBA")
    return _haze[key]


# ---------- the reaper ----------
def draw_reaper(frame, sx, ground_y, height, t, eyes=1.0, sway=1.0, step=0.0, fade=1.0):
    """Hooded cloak, scythe, two eye lights. height is the full figure height in px."""
    if fade <= 0:
        return
    hgt = height
    wid = hgt * 0.42
    layer = Image.new("RGBA", (int(wid * 3.4), int(hgt * 1.7)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, base = layer.width / 2, layer.height - 10
    sw = math.sin(t * 1.3) * 0.012 * hgt * sway
    bob = abs(math.sin(step * math.pi)) * hgt * 0.02 if step else 0
    top = base - hgt + bob
    # cloak: shoulders to a ragged hem
    rnd = random.Random(3)
    hem = []
    for k in range(13):
        xx = cx - wid * 0.62 + (wid * 1.24) * k / 12
        yy = base - rnd.uniform(0, hgt * 0.05) - (hgt * 0.02 if k % 2 else 0)
        hem.append((xx + sw * 0.3, yy))
    cloak = [(cx - wid * 0.22 + sw, top + hgt * 0.17), (cx + wid * 0.22 + sw, top + hgt * 0.17), (cx + wid * 0.55 + sw * 0.6, top + hgt * 0.5)] + hem[::-1] + [(cx - wid * 0.55 + sw * 0.6, top + hgt * 0.5)]
    d.polygon(cloak, fill=REAPER + (255,))
    # moonlit edge on the left shoulder
    d.line([(cx - wid * 0.22 + sw, top + hgt * 0.17), (cx - wid * 0.55 + sw * 0.6, top + hgt * 0.5), (cx - wid * 0.62, base)], fill=REAPER_EDGE + (160,), width=max(2, int(hgt * 0.008)))
    # hood
    hw, hh = wid * 0.36, hgt * 0.2
    d.ellipse((cx - hw + sw, top, cx + hw + sw, top + hh * 1.3), fill=REAPER + (255,))
    d.polygon([(cx - hw * 0.95 + sw, top + hh * 0.7), (cx + hw * 0.95 + sw, top + hh * 0.7), (cx + wid * 0.26 + sw, top + hgt * 0.2), (cx - wid * 0.26 + sw, top + hgt * 0.2)], fill=REAPER + (255,))
    d.ellipse((cx - hw * 0.62 + sw, top + hh * 0.42, cx + hw * 0.62 + sw, top + hh * 1.22), fill=(0, 0, 0, 255))
    # scythe: a tall staff in the right hand, a long crescent blade sweeping over the head
    sx0, sy0 = cx + wid * 0.48 + sw * 0.5, base - hgt * 0.03
    sx1, sy1 = cx + wid * 0.58 + sw, top - hgt * 0.16
    d.line((sx0, sy0, sx1, sy1), fill=(22, 18, 14, 255), width=max(3, int(hgt * 0.016)))
    bl = hgt * 0.5
    # crescent hung off the staff tip, sweeping left and drooping: outer arc and a thinner inner arc
    ocx, ocy, orad = sx1 - bl * 0.55, sy1 + bl * 0.55, bl * 0.78
    pts = []
    for k in range(24):
        a = math.radians(45 + 110 * k / 23)
        pts.append((ocx + math.cos(a) * orad, ocy - math.sin(a) * orad))
    for k in range(23, -1, -1):
        a = math.radians(45 + 110 * k / 23)
        taper = 1 - 0.14 * (k / 23) ** 0.7
        pts.append((ocx + math.cos(a) * orad * taper, ocy - math.sin(a) * orad * taper + bl * 0.04))
    d.polygon(pts, fill=(112, 122, 132, 255))
    d.line(pts[:24], fill=(205, 214, 222, 220), width=max(1, int(hgt * 0.005)))
    # eyes
    if eyes > 0:
        ex, ey = cx + sw, top + hh * 0.82
        gap, er = hw * 0.26, max(2, hgt * 0.012)
        flick = 0.85 + 0.15 * math.sin(t * 7.0) * math.sin(t * 3.1)
        glow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for off in (-gap, gap):
            gd.ellipse((ex + off - er * 3, ey - er * 3, ex + off + er * 3, ey + er * 3), fill=EYES + (int(120 * eyes * flick),))
        layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(er * 1.6)))
        for off in (-gap, gap):
            d.ellipse((ex + off - er, ey - er * 0.7, ex + off + er, ey + er * 0.7), fill=EYES + (int(255 * eyes * flick),))
    # ground shadow
    sh = Image.new("RGBA", (int(wid * 1.6), int(hgt * 0.06) + 20), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((10, 8, sh.width - 10, sh.height - 8), fill=(0, 0, 0, 170))
    frame.alpha_composite(alpha_mul(sh.filter(ImageFilter.GaussianBlur(10)), fade), (int(sx - sh.width / 2), int(ground_y - sh.height / 2)))
    frame.alpha_composite(alpha_mul(layer, fade), (int(sx - cx), int(ground_y - base)))


# ---------- display type (same feel as 04: spring word-by-word) ----------
def display(frame, text, y, t, at, size=104, color=TEXT, align="center", slam=True, exit_at=None, width=None, glow=None, x=None, weight="Inter-Black.otf"):
    if t < at or (exit_at is not None and t >= exit_at + 0.3):
        return
    a_exit = 1.0 if exit_at is None or t < exit_at else 1 - ease((t - exit_at) / 0.3)
    f = font(weight, size)
    d = ImageDraw.Draw(frame, "RGBA")
    lines = wrap(text, f, width or (SAFE[2] - SAFE[0]), d)
    lh = size * 1.08
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    k = 0
    space = ld.textlength(" ", font=f)
    for i, line in enumerate(lines):
        tw = ld.textlength(line, font=f)
        lx = (W / 2 - tw / 2) if align == "center" else (x if x is not None else SAFE[0])
        ly = y + i * lh
        wx = lx
        for word in line.split(" "):
            ww = ld.textlength(word, font=f)
            wt = (t - at - k * (0.09 if slam else 0.05))
            k += 1
            if wt > 0:
                if slam:
                    sp = spring(wt / 0.45)
                    sc = 0.6 + 0.4 * sp
                    aa = min(1.0, wt / 0.12)
                else:
                    sp = ease(wt / 0.35)
                    sc = 1.0
                    aa = sp
                wl = Image.new("RGBA", (int(ww) + 80, int(lh) + 80), (0, 0, 0, 0))
                wd = ImageDraw.Draw(wl)
                if glow:
                    wd.text((40, 40), word, font=f, fill=glow + (170,))
                    wl = wl.filter(ImageFilter.GaussianBlur(16))
                    wd = ImageDraw.Draw(wl)
                wd.text((43, 44), word, font=f, fill=(0, 0, 0, 170))
                wd.text((40, 40), word, font=f, fill=color + (255,))
                if sc != 1.0:
                    wl = wl.resize((max(1, int(wl.width * sc)), max(1, int(wl.height * sc))), Image.BILINEAR)
                if aa < 1:
                    wl.putalpha(wl.split()[3].point(lambda v: int(v * aa)))
                rise = 0 if slam else (1 - sp) * 18
                layer.alpha_composite(wl, (int(wx + ww / 2 - wl.width / 2), int(ly + lh / 2 - wl.height / 2 + rise)))
            wx += ww + space
    if a_exit < 1:
        layer.putalpha(layer.split()[3].point(lambda v: int(v * a_exit)))
    frame.alpha_composite(layer)


# ---------- beat 4: the chat glow ----------
def chat_panel(frame, t, at, until, typed, blank=False):
    """A chat window at the lower right. Types `typed` after `at`; fades at `until`."""
    if t < at or t > until + 0.4:
        return
    a = ease((t - at) / 0.4) * (1.0 if t < until else max(0.0, 1 - (t - until) / 0.4))
    x0, y0, x1, y1 = 470, 1150, 994, 1440
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # screen glow spilling onto the fog
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((x0 - 60, y0 - 60, x1 + 60, y1 + 60), radius=60, fill=(150, 180, 210, 70))
    layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(50)))
    d.rounded_rectangle((x0, y0, x1, y1), radius=26, fill=(18, 24, 32, 240), outline=(60, 72, 86, 255), width=2)
    d.rounded_rectangle((x0, y0, x1, y0 + 54), radius=26, fill=(28, 36, 46, 255))
    d.rectangle((x0, y0 + 28, x1, y0 + 54), fill=(28, 36, 46, 255))
    f_t = font("Inter-Medium.otf", 24)
    d.text((x0 + 24, y0 + 14), "new session", font=f_t, fill=(150, 165, 180, 255))
    f_a = font("Inter-Regular.otf", 28)
    d.text((x0 + 28, y0 + 84), "What is this project?", font=f_a, fill=(170, 185, 200, 255))
    # the user's typed reply
    n = 0 if blank else int(max(0, (t - at - 0.9)) * 22)
    shown = typed[:n]
    f_u = font("Inter-Regular.otf", 30)
    lines = wrap(shown, f_u, x1 - x0 - 56, d) if shown else [""]
    yy = y0 + 150
    for line in lines[-3:]:
        d.text((x0 + 28, yy), line, font=f_u, fill=TEXT + (255,))
        yy += 40
    if int(t * 2.4) % 2 == 0:
        last = lines[-1] if lines else ""
        cw = d.textlength(last, font=f_u)
        d.rectangle((x0 + 30 + cw, yy - 40 + 4, x0 + 33 + cw, yy - 4), fill=TEXT + (255,))
    frame.alpha_composite(alpha_mul(layer, a))


# ---------- beat 5: grave, lantern, gate, window ----------
def draw_open_grave(frame, sx, gy, scale, a=1.0):
    w, h = 420 * scale, 150 * scale
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # dirt mound behind
    d.ellipse((sx - w * 0.75, gy - h * 0.55, sx + w * 0.75, gy + h * 0.25), fill=(26, 22, 18, 255))
    d.ellipse((sx - w * 0.6, gy - h * 0.62, sx + w * 0.5, gy + h * 0.1), fill=(36, 30, 24, 255))
    # the hole
    d.polygon([(sx - w / 2, gy - h * 0.1), (sx + w / 2, gy - h * 0.1), (sx + w * 0.42, gy + h * 0.55), (sx - w * 0.42, gy + h * 0.55)], fill=(2, 3, 4, 255))
    d.line([(sx - w / 2, gy - h * 0.1), (sx + w / 2, gy - h * 0.1)], fill=(48, 40, 32, 255), width=max(2, int(4 * scale)))
    frame.alpha_composite(alpha_mul(layer, a))


def draw_lantern(frame, sx, gy, scale, t, a=1.0):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    hh = 90 * scale
    flick = 0.9 + 0.1 * math.sin(t * 9) * math.sin(t * 4.3)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, al in ((hh * 3.2, 40), (hh * 1.8, 80), (hh * 1.0, 120)):
        gd.ellipse((sx - r, gy - hh * 0.5 - r, sx + r, gy - hh * 0.5 + r), fill=PURPLE + (int(al * flick),))
    layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(hh * 0.5)))
    bw = hh * 0.5
    d.rounded_rectangle((sx - bw / 2, gy - hh, sx + bw / 2, gy), radius=int(hh * 0.08), fill=(20, 18, 16, 255), outline=(70, 64, 58, 255), width=2)
    d.rounded_rectangle((sx - bw * 0.36, gy - hh * 0.85, sx + bw * 0.36, gy - hh * 0.15), radius=int(hh * 0.05), fill=mix(PURPLE, (255, 255, 255), 0.45) + (255,))
    d.arc((sx - bw * 0.4, gy - hh * 1.3, sx + bw * 0.4, gy - hh * 0.8), 180, 360, fill=(70, 64, 58, 255), width=3)
    frame.alpha_composite(alpha_mul(layer, a))


def draw_footprints(frame, pts, t, at, a=1.0):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for k, (x, y, s) in enumerate(pts):
        if t < at + k * 0.25:
            break
        q = ease((t - at - k * 0.25) / 0.3)
        d.ellipse((x - 16 * s, y - 8 * s, x + 16 * s, y + 8 * s), fill=(4, 5, 7, int(200 * q)))
    frame.alpha_composite(alpha_mul(layer, a))


def draw_gate(frame, sx, gy, scale, t, a=1.0, window=1.0):
    """Two stone posts, an iron arch and bars, and beyond them the lit window."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    gh, gw = 620 * scale, 300 * scale
    # window beyond, far
    wx, wy = sx + 60 * scale, gy - gh * 0.52
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, al in ((gh * 0.6, 50), (gh * 0.32, 110)):
        gd.ellipse((wx - r, wy - r * 0.8, wx + r, wy + r * 0.8), fill=PURPLE + (int(al * window),))
    layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(gh * 0.12)))
    # a small house silhouette with the window
    hw, hh = gw * 0.9, gh * 0.42
    d.polygon([(wx - hw / 2, gy - 10), (wx - hw / 2, wy + hh * 0.2), (wx, wy - hh * 0.45), (wx + hw / 2, wy + hh * 0.2), (wx + hw / 2, gy - 10)], fill=(5, 7, 10, 255))
    ww, wh = hw * 0.26, hh * 0.3
    d.rounded_rectangle((wx - ww / 2, wy - wh / 2, wx + ww / 2, wy + wh / 2), radius=6, fill=mix(PURPLE, (255, 255, 255), 0.35) + (int(255 * window),))
    d.line((wx, wy - wh / 2, wx, wy + wh / 2), fill=(5, 7, 10, 255), width=max(2, int(4 * scale)))
    d.line((wx - ww / 2, wy, wx + ww / 2, wy), fill=(5, 7, 10, 255), width=max(2, int(4 * scale)))
    # posts
    for px in (sx - gw / 2, sx + gw / 2):
        d.rounded_rectangle((px - 34 * scale, gy - gh, px + 34 * scale, gy), radius=int(10 * scale), fill=STONE_DARK + (255,))
        d.rectangle((px - 34 * scale, gy - gh, px - 20 * scale, gy), fill=STONE + (200,))
        d.rectangle((px - 46 * scale, gy - gh - 30 * scale, px + 46 * scale, gy - gh), fill=STONE + (255,))
    # arch and bars
    d.arc((sx - gw / 2, gy - gh - 120 * scale, sx + gw / 2, gy - gh + 120 * scale), 180, 360, fill=(14, 16, 20, 255), width=max(4, int(12 * scale)))
    for k in range(7):
        bx = sx - gw / 2 + 40 * scale + (gw - 80 * scale) * k / 6
        d.line((bx, gy - gh * 0.78, bx, gy), fill=(14, 16, 20, 255), width=max(2, int(7 * scale)))
    d.line((sx - gw / 2, gy - gh * 0.78, sx + gw / 2, gy - gh * 0.78), fill=(14, 16, 20, 255), width=max(3, int(9 * scale)))
    d.line((sx - gw / 2, gy - gh * 0.3, sx + gw / 2, gy - gh * 0.3), fill=(14, 16, 20, 255), width=max(3, int(9 * scale)))
    frame.alpha_composite(alpha_mul(layer, a))


# ---------- end card ----------
_hat = {}


def hat_img(h):
    if h not in _hat:
        im = Image.open(os.path.join(ROOT, "motifs", "logo-hat-light.png")).convert("RGBA")
        _hat[h] = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
    return _hat[h]


def end_card(t):
    fr = sky()
    draw_moon(fr, t + 40, 0)
    draw_landscape(fr, 0)
    draw_fog(fr, t + 40, 0, strength=0.9)
    dim = Image.new("RGBA", (W, H), NIGHT + (int(200 * ease(t / 1.0)),))
    fr.alpha_composite(dim)
    sizes = CONTRACT["type"]["vertical"]
    d = ImageDraw.Draw(fr, "RGBA")
    display(fr, "Revive your old projects.", H * 0.20, t, 0.3, size=92, glow=PURPLE)
    a = ease((t - 1.0) / 0.6)
    if a > 0:
        hat = hat_img(int(H * 0.10))
        hy = H * 0.42
        fr.alpha_composite(alpha_mul(hat, a), (int(W / 2 - hat.width / 2), int(hy)))
        fh = font("Inter-Bold.otf", int(sizes["headline"] * 1.4))
        tw = d.textlength("Dandy", font=fh)
        ty = hy + hat.height + 36
        d.text((W / 2 - tw / 2, ty), "Dandy", font=fh, fill=TEXT + (int(255 * a),))
        yy = ty + fh.size * 1.1 + 50
        for i, line in enumerate(CONTRACT["copy_rules"]["end_card_lines"]):
            b = ease((t - 1.4 - 0.25 * i) / 0.5)
            fl = font("Inter-Regular.otf" if i == 0 else "Inter-Medium.otf", sizes["body" if i == 0 else "caption"])
            lw = d.textlength(line, font=fl)
            col = GOLD if i == 1 else (200, 190, 220)
            d.text((W / 2 - lw / 2, yy), line, font=fl, fill=col + (int(255 * b),))
            yy += fl.size * 1.1 + 50
    return fr


# ---------- scenes ----------
def base(t, cam, fog=1.0):
    fr = sky()
    draw_moon(fr, t, cam)
    draw_landscape(fr, cam)
    return fr


def s1(t):
    # close on the first stone: camera sits on it, slightly zoomed, fog clears off it in the first second
    cam = 0 + t * 6
    fr = base(t, cam)
    draw_fog(fr, t, cam, strength=0.6)
    draw_stones(fr, cam, zoom=1.18, skip=())
    draw_fog(fr, t + 3, cam, strength=max(0.25, 1.1 - t * 0.5))
    return fr


def s2(t, dur):
    # drift down the row: stone 2 to stone 4, about 2 s each
    cam = 1150 + smooth(t / dur) * 2300 + math.sin(t * 0.6) * 10
    fr = base(t + 4, cam)
    draw_fog(fr, t + 4, cam, strength=0.6)
    draw_stones(fr, cam)
    draw_fog(fr, t + 7, cam, strength=0.75)
    return fr


def s3(t, dur):
    # the reaper, far back between two stones, takes one step; CONTEXT ROT slams in
    cam = 3450 + 560 + t * 4
    fr = base(t + 13, cam)
    draw_fog(fr, t + 13, cam, strength=0.6)
    gy, sc = depth_scale(0.5)
    step = min(1.0, max(0.0, (t - 3.0) / 1.0))
    rx = screen_x(cam + 10, cam, 0.5) + smooth(step) * 38 * sc
    draw_reaper(fr, rx, gy, 760 * sc, t, eyes=min(1.0, max(0.0, (t - 0.8) / 1.5)), step=step if step < 1 else 0, fade=min(1.0, t / 0.8))
    draw_stones(fr, cam)
    draw_fog(fr, t + 16, cam, strength=0.85)
    display(fr, "CONTEXT ROT", H * 0.26, t, 4.6, size=150, glow=(60, 90, 80))
    return fr


S4_PHASES = (0.0, 4.5, 9.0)


def s4(t, dur):
    # the funeral from the viewer's side: three phases, fog thicker and the reaper nearer each time
    cam = 4700 - 560 + t * 2
    fr = base(t + 21, cam)
    phase = 0 if t < S4_PHASES[1] else (1 if t < S4_PHASES[2] else 2)
    draw_fog(fr, t + 21, cam, strength=0.6 + 0.15 * phase)
    # the reaper: a fixed spot per phase, nearer each time; a pulse of fog covers each change
    for k, (p, offx) in enumerate(((0.5, -230), (0.68, -300), (0.86, -330))):
        if k != phase:
            continue
        gy, sc = depth_scale(p)
        since = t - S4_PHASES[k]
        draw_reaper(fr, W / 2 + offx, gy, 760 * sc, t, eyes=1.0, fade=min(1.0, since / 0.6 + (1.0 if k == 0 else 0.0)))
    # a fresh blank stone rising on the last phase
    extra = []
    gy, sc = depth_scale(1.0)
    if t > 10.4:
        q = smooth((t - 10.4) / 2.2)
        img = stone_image("round", "", "", blank=True)
        extra.append((1.0, W * 0.3, gy, sc * 0.9, img, (1 - q) * img.height * 0.9 * sc))
    draw_stones(fr, cam, extra=extra)
    pulse = 0.0
    for ph in S4_PHASES[1:]:
        if ph - 0.5 < t < ph + 0.9:
            pulse = max(pulse, 1 - abs(t - ph - 0.2) / 0.7)
    draw_fog(fr, t + 24, cam, strength=0.8 + 0.2 * phase + 0.9 * pulse)
    chat_panel(fr, t, 0.3, 4.3, "so the project is a budget app, it tracks my spending by category and")
    chat_panel(fr, t, 4.8, 8.8, "ok so, again, the project is a budget app that")
    chat_panel(fr, t, 9.3, 12.6, "", blank=True)
    display(fr, "week 1: you explain it", H * 0.30, t, 0.9, size=62, slam=False, exit_at=4.2, weight="Inter-Bold.otf")
    display(fr, "week 3: you explain it again", H * 0.30, t, 5.3, size=62, slam=False, exit_at=8.7, weight="Inter-Bold.otf")
    display(fr, "week 6:", H * 0.30, t, 9.8, size=62, slam=False, exit_at=13.2, weight="Inter-Bold.otf")
    return fr


def s5(t, dur):
    # the turn: the open grave, the lantern, footprints to the gate, the lit window beyond; the reaper stops at the gate
    cam = 4700 + 900 + smooth(t / 5.5) * 700
    fr = base(t + 35, cam)
    draw_fog(fr, t + 35, cam, strength=0.6)
    # gate and house, mid depth, to the right
    ggy, gsc = depth_scale(0.6)
    gx = screen_x(6700, cam, 0.6)
    draw_gate(fr, gx, ggy, gsc, t, window=0.6 + 0.4 * ease((t - 2.5) / 1.5))
    # the reaper walks to the gate and stops
    rgy, rsc = depth_scale(0.6)
    walk = smooth(min(1.0, t / 6.0))
    rx = screen_x(5500 + 950 * walk, cam, 0.6)
    draw_reaper(fr, rx, rgy, 760 * rsc, t, eyes=1.0 - 0.5 * ease((t - 6.5) / 1.5), step=(t * 1.05) % 1 if walk < 1 else 0)
    # near row: open grave where a stone should be
    gy, sc = depth_scale(1.0)
    grave_x = screen_x(6080, cam, 1.0)
    draw_open_grave(fr, grave_x, gy - 40, sc)
    draw_stones(fr, cam, skip=())
    draw_lantern(fr, grave_x + 300 * sc, gy - 4, sc, t)
    pts = [(grave_x + 120 + k * 70, gy - 60 - k * 38, 1.0 - k * 0.1) for k in range(7)]
    draw_footprints(fr, pts, t, 0.8)
    draw_fog(fr, t + 38, cam, strength=0.7)
    display(fr, "the ones that get out", H * 0.27, t, 0.5, size=72, slam=False, exit_at=4.4, weight="Inter-Bold.otf")
    display(fr, "kept the truth outside the chat", H * 0.27, t, 4.9, size=72, slam=False, exit_at=dur - 0.3, weight="Inter-Bold.otf")
    return fr


SCENES = [
    dict(id="s1-stone", dur=4.0, frame=lambda t, d: s1(t)),
    dict(id="s2-row", dur=9.0, frame=s2),
    dict(id="s3-reaper", dur=8.0, frame=s3),
    dict(id="s4-funeral", dur=14.0, frame=s4),
    dict(id="s5-gate", dur=9.0, frame=s5),
    dict(id="end", dur=6.0, frame=lambda t, d: end_card(t)),
]

ON_SCREEN = ["HERE LIES", "CONTEXT ROT", "week 1: you explain it", "week 3: you explain it again", "week 6:", "the ones that get out",
             "kept the truth outside the chat", "Revive your old projects.", "new session", "What is this project?"] + [s[3] for s in STONES] + [s[4] for s in STONES]


def apply_timing():
    path = os.path.join(VIDEO, "voiceover", "night.json")
    if os.path.exists(path):
        with open(path) as f:
            timing = json.load(f).get("durations", {})
        for sc in SCENES:
            if sc["id"] in timing:
                sc["dur"] = float(timing[sc["id"]])


def copy_qa():
    rules = CONTRACT["copy_rules"]
    problems = []
    for tx in ON_SCREEN:
        for ch in rules["banned_characters"]:
            if ch in tx:
                problems.append(("copy", f"banned character in {tx!r}"))
        for ph in rules["banned_phrases"]:
            if ph in tx.lower():
                problems.append(("copy", f"banned phrase {ph!r} in {tx!r}"))
    return problems


def draw_cue(frame, cues, t_global):
    cue = next((c for c in cues if c["start"] <= t_global < c["end"]), None)
    if cue is None:
        return
    sizes = CONTRACT["type"]["vertical"]
    fnt = font("Inter-Bold.otf", int(sizes["body"] * 0.95))
    d = ImageDraw.Draw(frame, "RGBA")
    lines = wrap(cue["text"], fnt, SAFE[2] - SAFE[0], d)
    lh = fnt.size * 1.15
    y = 0.80 * H
    pad = 18
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=fnt)
        x = W / 2 - tw / 2
        yy = y + i * (lh + pad * 0.8)
        d.rounded_rectangle((x - pad, yy - pad * 0.6, x + tw + pad, yy + lh + pad * 0.4), radius=14, fill=NIGHT + (210,))
        d.text((x, yy), line, font=fnt, fill=TEXT + (255,))


AUDIO_PRE = ("highpass=f=130,asendcmd=c='0.0 afftdn sn start; 0.6 afftdn sn stop',afftdn=nf=-25:nr=30:tn=1,"
             "agate=threshold=0.02:ratio=4:attack=8:release=200:knee=4,acompressor=threshold=-20dB:ratio=3:attack=8:release=120")


def audio_chain(path, mixed=False):
    pre = "" if mixed else AUDIO_PRE + ","
    out = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "info", "-i", path, "-af", pre + "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = json.loads(out[out.rfind("{"):out.rfind("}") + 1])
    gain = -16.0 - float(m["input_i"])
    return f"{pre}volume={gain:.2f}dB,alimiter=limit=0.84:attack=5:release=60:level=0,apad"


def render(preview=False, final=False, stills=False):
    apply_timing()
    out = os.path.join(VIDEO, "out")
    os.makedirs(out, exist_ok=True)
    problems = copy_qa()
    with open(os.path.join(out, "qa-night-vertical.json"), "w") as f:
        json.dump(dict(canvas="vertical", look="night", problems=[list(p) for p in problems], scenes=[dict(id=s["id"], duration=s["dur"]) for s in SCENES]), f, indent=2)
    if problems:
        print("QA FAILED:", problems)
        return False
    cues = None
    cap_path = os.path.join(VIDEO, "captions.json")
    if os.path.exists(cap_path) and not preview:
        with open(cap_path) as f:
            cues = json.load(f)["cues"]
    tmp = tempfile.mkdtemp(prefix="dandy-night-")
    n, offset, contact = 0, 0.0, []
    step = 1.0 / FPS
    for sc in SCENES:
        frames = int(sc["dur"] * FPS)
        for i in range(frames):
            if preview and i % 3:
                continue
            if stills and i not in (int(0.5 * FPS), int((sc["dur"] * 0.5) * FPS), int((sc["dur"] - 0.6) * FPS)):
                continue
            t = i * step
            fr = sc["frame"](t, sc["dur"])
            shake = 7.0 * max(0.0, 1 - (t - 4.6) / 0.35) if sc["id"] == "s3-reaper" and t >= 4.6 else 0.0
            fr = finish(fr, t, offset + t, shake=shake, bloom=0.8, grain=5.0, vignette=0.45, drift=0.6)
            if cues:
                draw_cue(fr, cues, offset + t)
            if stills:
                fr.convert("RGB").save(os.path.join(out, f"night-{sc['id']}-{t:04.1f}.png"))
                continue
            fr.convert("RGB").save(os.path.join(tmp, f"f{n:06d}.png"), compress_level=1)
            n += 1
            if i == int((sc["dur"] - 0.6) * FPS) - (int((sc["dur"] - 0.6) * FPS) % 3 if preview else 0):
                contact.append(fr.convert("RGB"))
        offset += sc["dur"]
    if stills:
        print("stills in", out)
        return True
    fps = FPS // 3 if preview else FPS
    mp4 = os.path.join(out, f"05-graveyard-vertical{'-final' if final else ''}.mp4")
    total = sum(s["dur"] for s in SCENES)
    bed = sfx_night.build_bed([(s["id"], s["dur"]) for s in SCENES], os.path.join(out, "sfx-bed.wav"))
    cmd = ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "f%06d.png"), "-i", bed]
    apath = os.path.join(VIDEO, "voiceover", "night.json")
    audio = {}
    if os.path.exists(apath):
        with open(apath) as f:
            audio = json.load(f)
    voice = audio.get("file") if not preview else None
    music = audio.get("music")
    parts, mixn, idx = ["[1:a]volume=0.9[sfx]"], ["[sfx]"], 2
    if voice:
        cmd += ["-ss", str(audio.get("offset_s", 0)), "-i", os.path.join(ROOT, voice)]
        parts.append(f"[{idx}:a]{audio_chain(os.path.join(ROOT, voice), bool(audio.get('mixed')))}[voice]")
        idx += 1
    if music:
        cmd += ["-stream_loop", "-1", "-i", os.path.join(ROOT, music)]
        parts.append(f"[{idx}:a]volume={audio.get('music_db', -14)}dB[m0]")
        if voice:
            parts.append("[voice]asplit[v1][v2]")
            parts.append("[m0][v2]sidechaincompress=threshold=0.05:ratio=6:attack=40:release=500[mduck]")
            mixn = ["[v1]", "[sfx]", "[mduck]"]
        else:
            mixn = ["[sfx]", "[m0]"]
    elif voice:
        mixn = ["[voice]", "[sfx]"]
    fc = ";".join(parts) + ";" + "".join(mixn) + f"amix=inputs={len(mixn)}:normalize=0:duration=first,alimiter=limit=0.89:level=0[aout]"
    cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]", "-t", str(total), "-c:a", "aac", "-b:a", "192k"]
    if final:
        cmd += ["-c:v", "libx264", "-preset", "slow", "-pix_fmt", "yuv420p", "-crf", "17", "-movflags", "+faststart", mp4]
    else:
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", mp4]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    th = 480
    thumbs = [im.resize((int(im.width * th / im.height), th)) for im in contact]
    sheet = Image.new("RGB", (len(thumbs) * (thumbs[0].width + 24) + 24, th + 48), NIGHT)
    for i, im in enumerate(thumbs):
        sheet.paste(im, (24 + i * (thumbs[0].width + 24), 24))
    sheet.save(os.path.join(out, "contact-night-vertical.png"))
    print(f"rendered {mp4} ({n} frames)")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--stills", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if render(a.preview, a.final, a.stills) else 1)

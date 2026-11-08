"""Shared drawing helpers for video 05's night look: easing, sky, moon, far landscape, fog textures, stone images,
the reaper, display type and the chat panel. render_night.py holds the camera, the scenes and the pipeline."""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "render"))
from finish import spring  # noqa: E402

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


# ---------- camera and projection ----------
F_SCALE = 2.0   # a stone image is drawn at scale 1 when it is 2 world units away
PX = 540        # lateral pixels per world unit at distance 1


def project(x, z, cam):
    """World (x, z) to (screen_x, ground_y, scale, distance) for camera dict(x, z, k). None when behind."""
    d = z - cam["z"]
    if d <= 0.18:
        return None
    s = F_SCALE / d
    return W / 2 + (x - cam["x"]) * PX / d, HORIZON + cam["k"] / d, s, d


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


# ---------- fog ----------
_fog = {}


def fog_tex(seed):
    if seed not in _fog:
        w, h = 3000, 520
        n = value_noise(w, h, 5, seed, octaves=5)
        _fog[seed] = np.clip((n - 0.32) * 1.9, 0, 1).astype(np.float32)
    return _fog[seed]


def draw_fog(frame, t, cam, strength=1.0, color=FOG, push=0.0):
    """Three fog layers at different depths; each a scrolled crop of a noise band over the ground."""
    for seed, p, speed, top, height, alpha in ((1, 0.45, 26, HORIZON - 40, 300, 0.30), (2, 0.8, 44, HORIZON + 90, 420, 0.36), (3, 1.2, 70, HORIZON + 420, 560, 0.40)):
        tex = fog_tex(seed)
        th, tw = tex.shape
        off = int(t * speed + cam * p * 0.8) % tw
        voff = int(push * p * 90) % th
        tex = np.concatenate([tex[voff:], tex[:voff]], axis=0)
        band = np.concatenate([tex[:, off:], tex[:, :off]], axis=1)[:, :W]
        if band.shape[1] < W:
            band = np.concatenate([band, tex[:, : W - band.shape[1]]], axis=1)
        yy = np.linspace(0, 1, th)[:, None]
        band = band * (np.clip((yy - 0.05) / 0.45, 0, 1) * np.clip((1.0 - yy) / 0.25 + 0.2, 0, 1))
        band = np.asarray(Image.fromarray((band * 255).astype(np.uint8)).resize((W, height), Image.BILINEAR)).astype(np.float32) / 255
        arr = np.zeros((height, W, 4), np.uint8)
        arr[..., :3] = color
        arr[..., 3] = np.clip(band * alpha * strength * 255, 0, 255).astype(np.uint8)
        frame.alpha_composite(Image.fromarray(arr, "RGBA"), (0, int(top)))


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
    im = painterly(im, rnd.randrange(1 << 30))
    # fine grit
    arr = np.asarray(im).astype(np.int16)
    noise = np.random.default_rng(hash(key) & 0xFFFF).normal(0, 4, arr.shape[:2] + (1,))
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


def painterly(im, seed):
    """Make a flat stone look painted and old, to sit beside the painted rider: chipped and uneven edges, broad
    tone variation, brush strokes along the grain, rain stains down from the top, lichen at the base, a crack."""
    rnd = random.Random(seed)
    h, w = im.height, im.width
    arr = np.asarray(im).astype(np.float32)
    a = arr[..., 3] > 127
    if not a.any():
        return im
    ys, xs = np.where(a)
    top, bot, left, right = ys.min(), ys.max(), xs.min(), xs.max()
    # chipped, uneven edges: eat into the silhouette by a noisy depth
    dist = ndi.distance_transform_edt(a)
    chip = value_noise(w, h, 7, seed % 9973, octaves=3) * 10 + value_noise(w, h, 30, seed % 7919 + 1, octaves=2) * 4
    keep = dist > chip - 3
    for _ in range(rnd.randint(1, 3)):
        # a few bigger chips off the edge
        ex = rnd.choice((left, right)) + rnd.uniform(-10, 10)
        ey = rnd.uniform(top + 20, bot - 60)
        r = rnd.uniform(8, 20)
        yy, xx = np.ogrid[:h, :w]
        keep &= (xx - ex) ** 2 + (yy - ey) ** 2 > r * r
    arr[..., 3] = np.where(keep, arr[..., 3], 0)
    # broad tone variation
    tone = (value_noise(w, h, 3, seed % 6151 + 2, octaves=4) - 0.5) * 30
    arr[..., :3] += tone[..., None]
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    mask = out.split()[3]
    # brush strokes along the grain (mostly vertical), light and dark
    strokes = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(strokes)
    for _ in range(260):
        x = rnd.uniform(left, right)
        y = rnd.uniform(top, bot)
        ang = math.pi / 2 + rnd.gauss(0, 0.3)
        ln = rnd.uniform(14, 42)
        col = STONE_LIGHT if rnd.random() < 0.45 else STONE_DARK
        col = mix(col, STONE, rnd.uniform(0.0, 0.5))
        sd.line((x, y, x + math.cos(ang) * ln, y + math.sin(ang) * ln), fill=col + (rnd.randint(25, 60),), width=rnd.randint(7, 16))
    # rain stains running down from the top
    stains = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    td = ImageDraw.Draw(stains)
    for _ in range(rnd.randint(6, 14)):
        x = rnd.uniform(left + 15, right - 15)
        y0 = top + rnd.uniform(0, 60)
        td.line((x, y0, x + rnd.uniform(-6, 6), y0 + rnd.uniform(80, 320)), fill=(22, 26, 30, rnd.randint(30, 70)), width=rnd.randint(6, 18))
    stains = stains.filter(ImageFilter.GaussianBlur(4))
    # lichen at the base
    lich = value_noise(w, h, 12, seed % 4099 + 3, octaves=3)
    base_w = np.clip((np.arange(h)[:, None] - (bot - (bot - top) * 0.3)) / ((bot - top) * 0.3), 0, 1)
    la = np.clip((lich - 0.55) * 4, 0, 1) * base_w * 120
    lichen = np.zeros((h, w, 4), np.uint8)
    lichen[..., :3] = (44, 54, 46)
    lichen[..., 3] = la.astype(np.uint8)
    # a crack
    crack = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if rnd.random() < 0.6:
        cd = ImageDraw.Draw(crack)
        x, y = rnd.uniform(left + 30, right - 30), top + rnd.uniform(10, 80)
        pts = [(x, y)]
        for _ in range(rnd.randint(4, 8)):
            x += rnd.uniform(-22, 22)
            y += rnd.uniform(15, 45)
            pts.append((x, y))
        cd.line(pts, fill=(18, 21, 25, 200), width=2)
    for layer in (strokes.filter(ImageFilter.GaussianBlur(2.2)), stains, Image.fromarray(lichen, "RGBA"), crack):
        al = np.minimum(np.asarray(layer.split()[3]), np.asarray(mask))
        layer.putalpha(Image.fromarray(al.astype(np.uint8)))
        out.alpha_composite(layer)
    return out


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



"""The world around video 05's graveyard, in the same perspective space as the stones (world units: x across,
z away from the camera, heights in the same units; a stone is about 2 tall, the held camera about 2.4 up).

- draw_far(frame, cam, t): a denser treeline and faint town lights on the horizon (after the sky, before the ground)
- draw_ground(frame, cam, t): ground texture, the dirt path up the centre aisle, grass tufts and fallen leaves
- actors(cam, t, light): (z, draw_fn) pairs for render_night.draw_field to interleave with the stones by depth:
  the iron fence and its stone pillars on all four sides (an open gate at the front, which the push passes
  through, and a gate at the back), big bare trees inside the yard, the chapel and steeple near the moon, and a
  dead tree outside the front fence that frames the wide opening.
Colours stay in the night palette; nothing here is purple except where the lantern's light falls (light arg).
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from night_lib import FOG, GROUND, GROUND_LIGHT, H, HORIZON, NIGHT, PURPLE, PX, SKY_LOW, STONE, STONE_DARK, STONE_LIGHT, W, branch, mix, project, value_noise

YARD_X = 15.0          # side fences at +-YARD_X
FRONT_Z = 0.0          # front fence; the aisle gate is open
BACK_Z = 53.0          # back fence, just past the last row
GATE_HALF = 1.6
IRON = (13, 15, 19)
PATH = (30, 30, 30)


def haze(col, d, strength=0.9):
    k = min(0.82, max(0.0, (d - 2.0) / 14) * strength)
    return mix(col, mix(NIGHT, FOG, 0.25), k)


def lit(col, x, z, light):
    if light is None:
        return col
    lx, lz, ls = light
    k = min(0.3, 0.6 * ls / (1 + ((x - lx) ** 2 + (z - lz) ** 2 * 0.6) * 1.1))
    return mix(col, mix(PURPLE, (255, 255, 255), 0.2), k)


def up(cam, x, z, h):
    """Screen point of world (x, z) raised h units."""
    pr = project(x, z, cam)
    if pr is None:
        return None
    sx, gy, s, d = pr
    return sx, gy - h * PX / d, d


# ---------- far: treeline and town lights ----------
_treeline = None


def treeline():
    global _treeline
    if _treeline is None:
        w, h = 4200, 260
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        rnd = random.Random(44)
        col = (5, 8, 12, 255)
        for x in range(0, w, 46):
            tx = x + rnd.uniform(-20, 20)
            th = rnd.uniform(90, 200)
            d.line((tx, h, tx, h - th), fill=col, width=6)
            branch(d, tx, h - th, math.pi / 2, th * 0.45, 5, 4, rnd, col)
        d.rectangle((0, h - 40, w, h), fill=col)
        _treeline = im.filter(ImageFilter.GaussianBlur(1.2))
    return _treeline


def draw_far(frame, cam, t):
    # the chapel on the far rise, a silhouette against the moonlit sky
    ch = chapel_img()
    hh = 470
    key = ("chapel_sky", hh)
    if key not in _scaled:
        im = ch.resize((int(ch.width * hh / ch.height), hh), Image.LANCZOS)
        arr = np.asarray(im).astype(np.float32)
        arr[..., :3] = np.array((3, 4, 7), np.float32)
        _scaled[key] = Image.fromarray(arr.astype(np.uint8), "RGBA")
    im = _scaled[key]
    cx = 790 - cam["x"] * 6 - cam["z"] * 0.4
    # a low rise under it
    d = ImageDraw.Draw(frame, "RGBA")
    d.ellipse((cx - 460, HORIZON - 64, cx + 420, HORIZON + 140), fill=(4, 6, 9, 255))
    frame.alpha_composite(im, (int(cx - im.width / 2), int(HORIZON - 46 - im.height)))
    tl = treeline()
    off = int(cam["x"] * 12 + cam["z"] * 1.5) % tl.width
    strip = Image.new("RGBA", (W, tl.height), (0, 0, 0, 0))
    strip.paste(tl, (-off, 0))
    strip.paste(tl, (tl.width - off, 0))
    frame.alpha_composite(strip, (0, HORIZON + 6 - tl.height))
    # town lights: a few dim warm points low on the left horizon, flickering slightly
    d = ImageDraw.Draw(frame, "RGBA")
    rnd = random.Random(9)
    for k in range(26):
        x = 40 + rnd.random() * 300 - cam["x"] * 3
        y = HORIZON - 4 - rnd.random() * 26 * (1 - x / 400)
        r = rnd.uniform(1.0, 2.2)
        a = int(rnd.uniform(70, 150) * (0.85 + 0.15 * math.sin(t * rnd.uniform(1, 3) + k)))
        d.ellipse((x - r * 3, y - r * 3, x + r * 3, y + r * 3), fill=(255, 214, 160, a // 6))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 226, 180, a))


# ---------- ground: texture, path, tufts, leaves ----------
_ground_tex = None


def ground_tex():
    global _ground_tex
    if _ground_tex is None:
        n = value_noise(W, H - HORIZON, 9, 51, octaves=5)
        n2 = value_noise(W, H - HORIZON, 40, 52, octaves=2)
        _ground_tex = (n * 0.7 + n2 * 0.3).astype(np.float32)
    return _ground_tex


rnd_g = random.Random(17)
TUFTS = [(rnd_g.uniform(-YARD_X - 6, YARD_X + 6), rnd_g.uniform(-12, BACK_Z), rnd_g.random()) for _ in range(900)]
LEAVES = [(rnd_g.uniform(-YARD_X, YARD_X), rnd_g.uniform(-6, 40), rnd_g.random()) for _ in range(500)]


def draw_ground(frame, cam, t, light=None):
    # mottled ground: darker and lighter patches, mostly visible near the camera
    tex = ground_tex()
    gh = H - HORIZON
    yy = np.linspace(0, 1, gh)[:, None]
    near = np.clip(yy * 1.4, 0, 1)
    shade = (tex - 0.5) * 26 * near
    arr = np.zeros((gh, W, 4), np.uint8)
    base = np.array(GROUND_LIGHT, np.float32)
    arr[..., :3] = np.clip(base[None, None, :] + shade[..., None] * np.array([0.9, 1.0, 0.9]), 0, 255).astype(np.uint8)
    arr[..., 3] = (np.clip(np.abs(shade) / 10, 0, 1) * 150).astype(np.uint8)
    frame.alpha_composite(Image.fromarray(arr, "RGBA"), (0, HORIZON))
    # the path: a worn strip up the centre aisle, through both gates
    layer = Image.new("RGBA", (W, gh), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    z0 = max(-12.0, cam["z"] + 0.3)
    zs = [z0 + (BACK_Z + 4 - z0) * (k / 40) ** 1.6 for k in range(41)]
    for za, zb in zip(zs, zs[1:]):
        pa, pb = project(-0.85, za, cam), project(-0.85, zb, cam)
        qa, qb = project(0.85, za, cam), project(0.85, zb, cam)
        if not (pa and pb and qa and qb):
            continue
        col = haze(PATH, (za + zb) / 2 - cam["z"])
        col = lit(col, 0.0, (za + zb) / 2, light)
        d.polygon([(pa[0], pa[1] - HORIZON), (qa[0], qa[1] - HORIZON), (qb[0], qb[1] - HORIZON), (pb[0], pb[1] - HORIZON)], fill=col + (170,))
    # ruts and stones in the path, near the camera only
    rnd = random.Random(3)
    for k in range(160):
        x, z = rnd.uniform(-0.9, 0.9), rnd.uniform(-10, 30)
        p = project(x, z, cam)
        if p and p[3] < 14:
            r = max(1.0, 0.05 * PX / p[3])
            d.ellipse((p[0] - r * 1.6, p[1] - HORIZON - r * 0.5, p[0] + r * 1.6, p[1] - HORIZON + r * 0.5), fill=mix(PATH, STONE_LIGHT, 0.25) + (60,))
    frame.alpha_composite(layer.filter(ImageFilter.GaussianBlur(5)), (0, HORIZON))
    # grass tufts and leaves
    d = ImageDraw.Draw(frame, "RGBA")
    for (x, z, r) in LEAVES:
        p = project(x, z, cam)
        if not p or p[3] > 12 or p[3] < 0.6:
            continue
        sz = 0.09 * PX / p[3]
        col = haze(mix((46, 38, 30), (70, 60, 44), r), p[3])
        a = (r * 6.28)
        pts = [(p[0] + math.cos(a + q) * sz * (1.0 if q in (0, math.pi) else 0.45), p[1] + math.sin(a + q) * sz * 0.35) for q in (0, math.pi / 2, math.pi, 3 * math.pi / 2)]
        d.polygon(pts, fill=col + (200,))
    for (x, z, r) in TUFTS:
        if abs(x) < 1.05 and z > -2:
            continue  # the path is worn bare
        p = project(x, z, cam)
        if not p or p[3] > 22 or p[3] < 0.6 or p[0] < -60 or p[0] > W + 60:
            continue
        hgt = (0.25 + 0.3 * r) * PX / p[3]
        col = lit(haze(mix((26, 34, 30), (44, 54, 46), r), p[3]), x, z, None)
        wdt = max(1, int(0.03 * PX / p[3]))
        sway = math.sin(t * 1.3 + x) * 0.15
        for b in range(5):
            ang = -math.pi / 2 + (b - 2) * 0.32 + sway
            d.line((p[0] + (b - 2) * wdt, p[1], p[0] + (b - 2) * wdt + math.cos(ang) * hgt, p[1] + math.sin(ang) * hgt), fill=col + (220,), width=wdt)


# ---------- fence ----------
def fence_posts():
    """Segments as (x0, z0, x1, z1, kind). kind: 'bars' or 'gate' (open leaf)."""
    segs = []
    step = 1.5
    xs = np.arange(-YARD_X, YARD_X + 0.01, step)
    for zf in (FRONT_Z, BACK_Z):
        for x0, x1 in zip(xs, xs[1:]):
            if x1 <= -GATE_HALF or x0 >= GATE_HALF:
                segs.append((x0, zf, x1, zf, "bars"))
        segs.append((-GATE_HALF - 0.2, zf, -GATE_HALF, zf, "bars"))
        segs.append((GATE_HALF, zf, GATE_HALF + 0.2, zf, "bars"))
    zs = np.arange(FRONT_Z, BACK_Z + 0.01, step)
    for xf in (-YARD_X, YARD_X):
        for z0, z1 in zip(zs, zs[1:]):
            segs.append((xf, z0, xf, z1, "bars"))
    # open gate leaves at the front, swung inward
    segs.append((-GATE_HALF, FRONT_Z, -GATE_HALF + 0.25, FRONT_Z + 1.5, "leaf"))
    segs.append((GATE_HALF, FRONT_Z, GATE_HALF - 0.25, FRONT_Z + 1.5, "leaf"))
    return segs


SEGS = fence_posts()
PILLARS = [(x, z) for z in (FRONT_Z, BACK_Z) for x in np.arange(-YARD_X, YARD_X + 0.01, 6.0) if abs(x) > GATE_HALF + 1] + \
          [(x, z) for x in (-YARD_X, YARD_X) for z in np.arange(FRONT_Z + 6, BACK_Z, 6.0)] + \
          [(s * GATE_HALF, z) for s in (-1, 1) for z in (FRONT_Z, BACK_Z)] + [(s * YARD_X, z) for s in (-1, 1) for z in (FRONT_Z, BACK_Z)]


def draw_fence_seg(frame, cam, seg, light):
    x0, z0, x1, z1, kind = seg
    h = 2.3
    n = max(2, int(math.hypot(x1 - x0, z1 - z0) / 0.22))
    pts = []
    for k in range(n + 1):
        q = k / n
        x, z = x0 + (x1 - x0) * q, z0 + (z1 - z0) * q
        b = up(cam, x, z, 0.0)
        tp = up(cam, x, z, h)
        if b is None or tp is None:
            return
        pts.append((x, z, b, tp))
    dmid = pts[len(pts) // 2][2][2]
    if dmid > 75:
        return
    col = lit(haze(IRON, dmid), (x0 + x1) / 2, (z0 + z1) / 2, light)
    d = ImageDraw.Draw(frame, "RGBA")
    if all((p[2][0] < -200 or p[2][0] > W + 200) for p in pts):
        return
    w = max(1, int(0.05 * PX / dmid))
    for (x, z, b, tp) in pts:
        d.line((b[0], b[1], tp[0], tp[1]), fill=col + (255,), width=w)
        # spear tip
        r = max(1.0, 0.06 * PX / b[2])
        d.polygon([(tp[0] - r, tp[1]), (tp[0] + r, tp[1]), (tp[0], tp[1] - r * 3)], fill=col + (255,))
    for hh in (0.25, h * 0.86):
        line = [up(cam, x, z, hh) for (x, z, _, _) in pts]
        d.line([(p[0], p[1]) for p in line], fill=col + (255,), width=max(1, int(0.07 * PX / dmid)))


def draw_pillar(frame, cam, x, z, light):
    b = up(cam, x, z, 0)
    if b is None or b[2] > 75:
        return
    d_ = b[2]
    hw = 0.32 * PX / d_
    top = up(cam, x, z, 2.9)
    if b[0] + hw < -50 or b[0] - hw > W + 50:
        return
    col = lit(haze(STONE_DARK, d_), x, z, light)
    capc = lit(haze(STONE, d_), x, z, light)
    d = ImageDraw.Draw(frame, "RGBA")
    d.rectangle((b[0] - hw, top[1], b[0] + hw, b[1]), fill=col + (255,))
    d.rectangle((b[0] - hw, top[1], b[0] - hw * 0.4, b[1]), fill=capc + (120,))
    cap = up(cam, x, z, 3.15)
    d.rectangle((b[0] - hw * 1.35, cap[1], b[0] + hw * 1.35, top[1]), fill=capc + (255,))
    d.ellipse((b[0] - hw * 0.7, cap[1] - hw * 0.9, b[0] + hw * 0.7, cap[1] + hw * 0.3), fill=capc + (255,))


def draw_arch(frame, cam, z, light):
    """The iron arch over a gate."""
    pts = []
    for k in range(25):
        q = k / 24
        x = -GATE_HALF + 2 * GATE_HALF * q
        h = 3.15 + 1.1 * math.sin(math.pi * q)
        p = up(cam, x, z, h)
        if p is None:
            return
        pts.append(p)
    d_ = pts[12][2]
    if d_ > 75:
        return
    col = lit(haze(IRON, d_), 0.0, z, light)
    d = ImageDraw.Draw(frame, "RGBA")
    w = max(1, int(0.09 * PX / d_))
    d.line([(p[0], p[1]) for p in pts], fill=col + (255,), width=w)
    inner = [up(cam, -GATE_HALF + 2 * GATE_HALF * (k / 24), z, 3.15 + 0.75 * math.sin(math.pi * k / 24)) for k in range(25)]
    d.line([(p[0], p[1]) for p in inner], fill=col + (255,), width=max(1, w // 2))
    for k in range(3, 22, 3):
        d.line((pts[k][0], pts[k][1], inner[k][0], inner[k][1]), fill=col + (255,), width=max(1, w // 2))


# ---------- trees and chapel (pre-rendered, scaled per frame) ----------
_imgs = {}
REF = 100.0   # image pixels per world unit


def tree_img(seed, height, lean=0.0, dead=False):
    key = ("tree", seed, height, lean, dead)
    if key not in _imgs:
        hpx = int(height * REF)
        wpx = int(hpx * 1.1)
        im = Image.new("RGBA", (wpx, hpx + 20), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        rnd = random.Random(seed)
        col = (8, 10, 13, 255)
        x0, y0 = wpx / 2, hpx + 10
        trunk = hpx * (0.36 if not dead else 0.42)
        tx, ty = x0 + lean * trunk, y0 - trunk
        tw = hpx * 0.055
        d.polygon([(x0 - tw * 1.6, y0), (x0 + tw * 1.6, y0), (tx + tw * 0.6, ty), (tx - tw * 0.6, ty)], fill=col)
        # roots
        for s in (-1, 1):
            d.polygon([(x0 + s * tw * 1.2, y0 - tw), (x0 + s * tw * 3.2, y0), (x0 + s * tw * 0.8, y0)], fill=col)
        for k in range(4 if not dead else 3):
            a = math.pi / 2 + (k - 1.5) * 0.45 + rnd.uniform(-0.15, 0.15) - lean * 0.4
            branch(d, tx, ty, a, hpx * rnd.uniform(0.28, 0.36), tw * 1.1, 7 if not dead else 5, rnd, col)
        _imgs[key] = im.filter(ImageFilter.GaussianBlur(0.8))
    return _imgs[key]


def chapel_img():
    key = ("chapel",)
    if key not in _imgs:
        u = REF
        w, h = int(16 * u), int(26 * u)
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        col = (6, 9, 13, 255)
        g = h - 10
        # nave with pitched roof
        d.rectangle((1 * u, g - 7 * u, 11 * u, g), fill=col)
        d.polygon([(0.5 * u, g - 7 * u), (11.5 * u, g - 7 * u), (6 * u, g - 11 * u)], fill=col)
        # tower and steeple
        d.rectangle((11 * u, g - 13 * u, 15 * u, g), fill=col)
        d.polygon([(10.6 * u, g - 13 * u), (15.4 * u, g - 13 * u), (13 * u, g - 23 * u)], fill=col)
        d.line((13 * u, g - 23 * u, 13 * u, g - 25.5 * u), fill=col, width=int(0.25 * u))
        d.line((12.2 * u, g - 24.8 * u, 13.8 * u, g - 24.8 * u), fill=col, width=int(0.25 * u))
        # arched windows, unlit
        for wx in (3 * u, 6 * u, 9 * u):
            d.rounded_rectangle((wx - 0.5 * u, g - 5.5 * u, wx + 0.5 * u, g - 2.5 * u), radius=int(0.5 * u), fill=(14, 18, 24, 255))
        d.rounded_rectangle((12.4 * u, g - 11 * u, 13.6 * u, g - 9 * u), radius=int(0.6 * u), fill=(14, 18, 24, 255))
        _imgs[key] = im
    return _imgs[key]


_scaled = {}


def blit(frame, img, cam, x, z, light=None, ref_ground=10, fade=1.0, haze_strength=0.9):
    """Draw a pre-rendered world object standing at (x, z); img is REF px per world unit."""
    pr = project(x, z, cam)
    if pr is None:
        return
    sx, gy, s, d = pr
    sc = (PX / d) / REF
    w, h = int(img.width * sc), int(img.height * sc)
    if w < 2 or h < 2 or sx + w < -50 or sx - w > W + 50 or gy - h > H:
        return
    if w > 5000 or h > 7000:
        return
    key = (id(img), round(sc, 3))
    if key not in _scaled:
        if len(_scaled) > 300:
            _scaled.clear()
        _scaled[key] = img.resize((w, h), Image.LANCZOS if sc < 1 else Image.BILINEAR)
    im = _scaled[key]
    k = min(0.82, max(0.0, (d - 2.0) / 14) * haze_strength)
    if k > 0.02 or light is not None:
        arr = np.asarray(im).astype(np.float32)
        tgt = np.array(mix(NIGHT, FOG, 0.25), np.float32)
        arr[..., :3] = arr[..., :3] * (1 - k) + tgt * k
        if light is not None:
            lx, lz, ls = light
            tk = min(0.3, 0.6 * ls / (1 + ((x - lx) ** 2 + (z - lz) ** 2 * 0.6) * 1.1))
            arr[..., :3] = arr[..., :3] * (1 - tk) + np.array(mix(PURPLE, (255, 255, 255), 0.2), np.float32) * tk
        if fade < 1:
            arr[..., 3] *= fade
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    frame.alpha_composite(im, (int(sx - w / 2), int(gy - h + ref_ground * sc)))


YARD_TREES = [(-7.5, 11.9, 1, 13.0, 0.08), (7.5, 19.1, 2, 14.0, -0.06), (-9.7, 26.3, 3, 15.0, 0.05), (5.3, 33.5, 4, 13.0, 0.1),
              (11.9, 8.3, 5, 12.0, -0.1), (-11.9, 40.7, 6, 14.0, 0.0), (9.7, 46.1, 7, 13.0, 0.04)]
DEAD_TREE = (-6.2, -7.0, 8, 11.0, 0.22)
CHAPEL = (24.0, 64.0)


def actors(cam, t, light=None):
    out = []
    for seg in SEGS:
        zm = (seg[1] + seg[3]) / 2
        out.append((zm, lambda fr, seg=seg: draw_fence_seg(fr, cam, seg, light)))
    for (x, z) in PILLARS:
        out.append((z - 0.01, lambda fr, x=x, z=z: draw_pillar(fr, cam, x, z, light)))
    for z in (FRONT_Z, BACK_Z):
        out.append((z - 0.02, lambda fr, z=z: draw_arch(fr, cam, z, light)))
    for (x, z, seed, hgt, lean) in YARD_TREES:
        out.append((z, lambda fr, x=x, z=z, seed=seed, hgt=hgt, lean=lean: blit(fr, tree_img(seed, hgt, lean), cam, x, z, light, haze_strength=0.7)))
    x, z, seed, hgt, lean = DEAD_TREE
    out.append((z, lambda fr: blit(fr, tree_img(seed, hgt, lean, dead=True), cam, x, z, light, haze_strength=0.4)))
    return out

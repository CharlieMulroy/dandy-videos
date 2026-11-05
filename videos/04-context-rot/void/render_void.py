"""Renderer for video 04's own look: context rot as a black hole in a dark void. Vertical only.

Usage:  python3 videos/04-context-rot/void/render_void.py [--preview] [--final] [--stills]

Everything is procedural: the hole (an accretion spiral computed in numpy), falling particles, the project
cards that stretch and spiral in, the context-window gauge, the damage tally, the beacon, and the soft end
card. Palette is this video's own (void, orange, ember, cyan) except the end card, which keeps the brand hat.
Narration captions come from captions.json; scene durations can be overridden by voiceover/void.json.
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "render"))
import sfx  # noqa: E402
from finish import finish, spring  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
with open(os.path.join(ROOT, "style", "contract.json")) as f:
    CONTRACT = json.load(f)
BRAND = CONTRACT["palette"]
FONT_DIR = "/usr/share/fonts/opentype/inter"
FPS = CONTRACT["motion"]["fps"]
W, H = 1080, 1920
SAFE = (int(W * 0.08), CONTRACT["layout"]["vertical_safe_top_px"], W - int(W * 0.08), H - CONTRACT["layout"]["vertical_safe_bottom_px"])

VOID, ORANGE, EMBER, CYAN, TEXT, RED = (7, 6, 15), (255, 122, 26), (255, 179, 71), (53, 224, 255), (246, 242, 236), (255, 77, 77)
HOLE = (540, 760)  # centre of the hole in most scenes
HOLE_R = 230


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = max(0.0, min(1.0, t))
    return t * t


def lerp(a, b, p):
    return a + (b - a) * p


def mix(c1, c2, p):
    return tuple(int(lerp(c1[i], c2[i], p)) for i in range(3))


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(size))


# ---------- background ----------
_bg = None


def background():
    global _bg
    if _bg is None:
        rnd = random.Random(4)
        im = Image.new("RGB", (W, H), VOID)
        d = ImageDraw.Draw(im)
        for _ in range(160):
            x, y, r = rnd.random() * W, rnd.random() * H, rnd.random() * 1.6 + 0.4
            a = rnd.randint(60, 170)
            d.ellipse((x - r, y - r, x + r, y + r), fill=mix(VOID, TEXT, a / 255))
        # vignette
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        v = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)
        v = np.clip(1 - v * 0.9, 0.35, 1.0)
        arr = np.asarray(im).astype(np.float32) * v[..., None]
        _bg = Image.fromarray(arr.astype(np.uint8))
    return _bg.copy()


# ---------- the hole ----------
_grid = None


def grid():
    global _grid
    if _grid is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        _grid = (xx, yy)
    return _grid


def draw_hole(frame, t, center=HOLE, radius=HOLE_R, strength=1.0, speed=1.0):
    """Accretion spiral: an orange-to-cyan disk with trailing arms, a pitch-black core and a thin bright rim."""
    if strength <= 0:
        return
    xx, yy = grid()
    cx, cy = center
    dx, dy = xx - cx, (yy - cy) * 1.0
    r = np.sqrt(dx * dx + dy * dy) / radius
    th = np.arctan2(dy, dx)
    arms = 0.55 + 0.45 * np.sin(3 * th - 7.0 * np.log(np.maximum(r, 0.2)) + t * 2.6 * speed)
    disk = np.exp(-((r - 1.15) ** 2) / 0.45) * arms
    outer = np.exp(-((r - 2.1) ** 2) / 1.6) * (0.35 + 0.25 * np.sin(2 * th + 4.0 * np.log(np.maximum(r, 0.2)) - t * 1.4 * speed))
    rim = np.exp(-((r - 0.62) ** 2) / 0.004) * (1.2 + 0.3 * math.sin(t * 9.0)) + np.exp(-((r - 0.72) ** 2) / 0.02) * 0.5
    streaks = np.exp(-((r - 1.0) ** 2) / 1.2) * np.clip(np.sin(9 * th + t * 0.8) * 8 - 7, 0, 1) * 0.25
    disk = disk + streaks
    glow = np.clip(disk * 1.1 + outer * 0.9, 0, 1.6)
    # colour: hot orange near the core, ember mid, cyan at the far edge
    col = np.zeros((H, W, 3), np.float32)
    near = np.clip(1.6 - r, 0, 1)[..., None]
    far = np.clip((r - 1.4) / 1.2, 0, 1)[..., None]
    base = np.array(ORANGE, np.float32) * near + np.array(EMBER, np.float32) * (1 - near)
    col = base * (1 - far) + np.array(CYAN, np.float32) * far
    out = np.asarray(frame.convert("RGB")).astype(np.float32)
    a = np.clip(glow * strength, 0, 1)[..., None]
    out = out * (1 - a) + col * a
    rimc = np.clip(rim * strength, 0, 1)[..., None]
    out = out * (1 - rimc) + np.array(TEXT, np.float32) * rimc
    core = np.clip((0.62 - r) / 0.05, 0, 1)[..., None] * strength
    out = out * (1 - core)
    frame.paste(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).convert("RGBA"))


def draw_particles(frame, t, center=HOLE, n=90, strength=1.0, seed=9):
    if strength <= 0:
        return
    d = ImageDraw.Draw(frame, "RGBA")
    rnd = random.Random(seed)
    cx, cy = center
    for i in range(n):
        phase = rnd.random()
        th0 = rnd.random() * math.tau
        r0 = 520 + rnd.random() * 700
        size = 2 + rnd.random() * 3
        speed = 0.09 + rnd.random() * 0.06
        s = (phase + t * speed) % 1.0
        rr = r0 * (1 - s) ** 1.4 + 20
        if rr < 150:
            continue
        th = th0 + s * 5.5
        x, y = cx + math.cos(th) * rr, cy + math.sin(th) * rr * 0.9
        a = int(230 * strength * min(1, s * 4) * (1 - max(0, (0.15 - s)) * 3))
        col = mix(EMBER, CYAN, rnd.random() * 0.6)
        d.ellipse((x - size, y - size, x + size, y + size), fill=col + (max(0, a),))


# ---------- things that fall in ----------
def card_image(label, w=330, h=92, color=TEXT, glow=ORANGE):
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 20, 20 + w, 20 + h), radius=18, fill=color + (255,))
    f = font("Inter-Bold.otf", 34)
    tw = d.textlength(label, font=f)
    d.text((20 + w / 2 - tw / 2, 20 + h / 2 - 20), label, font=f, fill=VOID + (255,))
    halo = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).rounded_rectangle((14, 14, 26 + w, 26 + h), radius=22, fill=glow + (120,))
    halo = halo.filter(ImageFilter.GaussianBlur(14))
    halo.alpha_composite(im)
    return halo


def fall_in(frame, img, t, start, dur, from_xy, center=HOLE, turn=2.4):
    """Card spirals from from_xy into the hole over dur seconds after start: stretches toward the centre, shrinks, fades."""
    if t < start:
        return
    s = ease_in(min(1.0, (t - start) / dur))
    if s >= 1:
        return
    cx, cy = center
    fx, fy = from_xy
    ang0 = math.atan2(fy - cy, fx - cx)
    r0 = math.hypot(fx - cx, fy - cy)
    r = r0 * (1 - s) + 40
    ang = ang0 + s * turn
    x, y = cx + math.cos(ang) * r, cy + math.sin(ang) * r
    stretch = 1 + 0.9 * ease_in(s)
    squash = 1 - 0.35 * ease_in(s)
    scale = 1.1 - 0.5 * s
    w, h = int(img.width * scale * stretch), max(2, int(img.height * scale * squash))
    im = img.resize((w, h), Image.LANCZOS)
    im = im.rotate(-math.degrees(ang) - 180, expand=True, resample=Image.BICUBIC)
    a = 1 - ease_in(max(0, (s - 0.7) / 0.3))
    if a < 1:
        im.putalpha(im.split()[3].point(lambda v: int(v * a)))
    frame.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))


def eat_flash(frame, t, at, center=HOLE, radius=HOLE_R):
    """A ring of light bursts off the rim when the hole swallows something."""
    if t < at or t > at + 0.5:
        return
    q = (t - at) / 0.5
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = radius * (0.62 + 0.5 * ease(q))
    d.ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), outline=TEXT + (int(220 * (1 - q)),), width=int(10 * (1 - q)) + 2)
    frame.alpha_composite(layer.filter(ImageFilter.GaussianBlur(3)))


def token_stream(frame, t, start, end, src, dst, seed=21):
    """Little token squares fly from a chat bubble into the gauge while it fills."""
    if t < start or t > end + 0.6:
        return
    d = ImageDraw.Draw(frame, "RGBA")
    bw, bh = 300, 110
    bx, by = src
    a = ease((t - start) / 0.3) * (1 if t < end else max(0, 1 - (t - end) / 0.5))
    d.rounded_rectangle((bx - bw / 2, by - bh / 2, bx + bw / 2, by + bh / 2), radius=22, fill=TEXT + (int(235 * a),))
    f = font("Inter-Medium.otf", 30)
    for i, line in enumerate(("you: here's my", "project...")):
        d.text((bx - bw / 2 + 24, by - bh / 2 + 18 + i * 36), line, font=f, fill=VOID + (int(255 * a),))
    rnd = random.Random(seed)
    for k in range(40):
        t0 = start + rnd.random() * (end - start)
        if t < t0 or t > t0 + 0.7:
            continue
        q = ease_in((t - t0) / 0.7)
        x = lerp(bx + bw / 2, dst[0], q) + math.sin(q * 6 + k) * 20
        y = lerp(by, dst[1], q)
        sz = 14 - 6 * q
        d.rounded_rectangle((x - sz, y - sz / 2, x + sz, y + sz / 2), radius=4, fill=mix(ORANGE, CYAN, rnd.random()) + (int(255 * (1 - q * 0.3)),))


def place(frame, img, xy, t, at, alpha=1.0, pop=True):
    if t < at:
        return
    p = ease((t - at) / 0.35)
    sc = (0.7 + 0.3 * p) if pop else 1.0
    im = img if sc == 1 else img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.LANCZOS)
    a = p * alpha
    if a < 1:
        im = im.copy()
        im.putalpha(im.split()[3].point(lambda v: int(v * a)))
    frame.alpha_composite(im, (int(xy[0] - im.width / 2), int(xy[1] - im.height / 2)))


# ---------- display type ----------
def display(frame, text, y, t, at, size=104, color=TEXT, align="center", slam=True, exit_at=None, width=None, glow=None, x=None):
    if t < at or (exit_at is not None and t >= exit_at + 0.3):
        return
    a_exit = 1.0 if exit_at is None or t < exit_at else 1 - ease((t - exit_at) / 0.3)
    f = font("Inter-Black.otf", size)
    d = ImageDraw.Draw(frame, "RGBA")
    lines = wrap(text, f, width or (SAFE[2] - SAFE[0]), d)
    lh = size * 1.08
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    # words arrive one after another (slam: 90 ms apart with a spring pop; otherwise a quick rise)
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


# ---------- the gauge (context window) ----------
def draw_gauge(frame, t, x, y, w, h, fill_to, drain_at=None, overflow_at=None, center=HOLE):
    """A tall glass gauge that fills with token blocks; drains into the hole; or overflows at the top."""
    d = ImageDraw.Draw(frame, "RGBA")
    d.rounded_rectangle((x, y, x + w, y + h), radius=26, outline=TEXT + (200,), width=5, fill=(255, 255, 255, 14))
    f = font("Inter-Medium.otf", 30)
    d.text((x, y - 48), "context window", font=f, fill=CYAN + (255,))
    n_slots = 14
    bh = (h - 24) / n_slots
    filled = int(n_slots * ease(fill_to(t)))
    rnd = random.Random(2)
    cols = [mix(ORANGE, CYAN, rnd.random() * 0.8) for _ in range(n_slots + 6)]
    drain = drain_at is not None and t >= drain_at
    over = overflow_at is not None and t >= overflow_at
    cx, cy = center
    for i in range(n_slots):
        by = y + h - 12 - (i + 1) * bh + 4
        if i < filled and not drain:
            d.rounded_rectangle((x + 12, by, x + w - 12, by + bh - 8), radius=10, fill=cols[i] + (235,))
        elif i < filled and drain:
            q = ease_in(min(1, (t - drain_at) / 1.2 + i * 0.03))
            bx, byy = lerp(x + w / 2, cx, q), lerp(by + bh / 2, cy, q)
            sz = (w - 24) * (1 - q * 0.8)
            d.rounded_rectangle((bx - sz / 2, byy - (bh - 8) * (1 - q * 0.8) / 2, bx + sz / 2, byy + (bh - 8) * (1 - q * 0.8) / 2), radius=10,
                                fill=cols[i] + (int(235 * (1 - q)),))
    if over:
        # extra blocks arrive at the top and the oldest (bottom) ones are pushed out and fall into the hole
        k = int((t - overflow_at) / 0.5)
        for j in range(min(k, 6)):
            q = ease_in(min(1, (t - overflow_at - j * 0.5) / 1.4))
            by = y + h - 12 - (j + 1) * bh + 4
            bx, byy = lerp(x + w / 2, cx, q), lerp(by + bh / 2, cy + 60, q)
            sz = (w - 24) * (1 - q * 0.85)
            d.rounded_rectangle((bx - sz / 2, byy - 14 * (1 - q), bx + sz / 2, byy + 14 * (1 - q)), radius=8, fill=cols[j] + (int(235 * (1 - q)),))
        # the incoming block at the top rim
        q2 = (t - overflow_at) % 0.5 / 0.5
        d.rounded_rectangle((x + 12, y - 30 + q2 * 24, x + w - 12, y - 30 + q2 * 24 + bh - 8), radius=10, fill=cols[n_slots + 1] + (200,))


def sticky(frame, t, at, xy, stale_at):
    if t < at:
        return
    p = ease((t - at) / 0.35)
    q = ease(max(0, (t - stale_at)) / 2.0) if stale_at is not None else 0.0
    w, h = 520, 380
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = mix(EMBER, (120, 96, 60), q)
    d.rectangle((30, 30, 30 + w, 30 + h), fill=col + (int(255 * p),))
    f = font("Inter-Medium.otf", 46)
    for i, line in enumerate(("memory file", "- auth done", "- schema v2", "- next: charts")):
        d.text((60, 60 + i * 72), line, font=f, fill=VOID + (int(255 * p * (1 - q * 0.5)),))
    if q > 0:
        fs = font("Inter-Black.otf", 96)
        tw = d.textlength("STALE", font=fs)
        st = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(st).text((30 + w / 2 - tw / 2, 30 + h / 2 - 52), "STALE", font=fs, fill=RED + (int(255 * q),))
        im.alpha_composite(st.rotate(-12, resample=Image.BICUBIC))
    im = im.rotate(-4 + q * 10, expand=True, resample=Image.BICUBIC)
    frame.alpha_composite(im, (int(xy[0] - im.width / 2), int(xy[1] - im.height / 2)))


def tally(frame, t, lines, x, y, start, gap=1.9):
    d = ImageDraw.Draw(frame, "RGBA")
    f = font("Inter-Bold.otf", 52)
    fv = font("Inter-Black.otf", 64)
    for i, (label, value, color) in enumerate(lines):
        at = start + i * gap
        if t < at:
            continue
        p = ease((t - at) / 0.4)
        if value.isdigit():  # count up
            value = str(int(int(value) * ease((t - at) / 1.2)))
        yy = y + i * 118 + (1 - p) * 20
        d.text((x, yy + 8), label, font=f, fill=TEXT + (int(255 * p),))
        vw = d.textlength(value, font=fv)
        d.text((SAFE[2] - vw, yy - 4), value, font=fv, fill=color + (int(255 * p),))
        d.line([(x, yy + 86), (SAFE[2], yy + 86)], fill=TEXT + (int(70 * p),), width=2)


def progress_bar(frame, t, at, x, y, w):
    if t < at:
        return
    d = ImageDraw.Draw(frame, "RGBA")
    q = ease((t - at) / 2.4)
    val = 0.82 - 0.62 * q
    d.rounded_rectangle((x, y, x + w, y + 34), radius=17, fill=(255, 255, 255, 30))
    d.rounded_rectangle((x, y, x + w * val, y + 34), radius=17, fill=mix(CYAN, RED, q) + (255,))
    f = font("Inter-Medium.otf", 30)
    d.text((x, y - 44), "your progress", font=f, fill=TEXT + (220,))


def beacon(frame, t, at, xy, strength=1.0):
    if t < at:
        return
    p = ease((t - at) / 0.8) * strength
    cx, cy = xy
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = 70 + 10 * math.sin(t * 3)
    d.ellipse((cx - r * 2.6, cy - r * 2.6, cx + r * 2.6, cy + r * 2.6), fill=CYAN + (int(70 * p),))
    layer = layer.filter(ImageFilter.GaussianBlur(40))
    d = ImageDraw.Draw(layer)
    for k in range(8):
        ang = k * math.pi / 4 + t * 0.4
        d.line([(cx, cy), (cx + math.cos(ang) * r * 2.2, cy + math.sin(ang) * r * 2.2)], fill=CYAN + (int(120 * p),), width=4)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=TEXT + (int(255 * p),))
    d.ellipse((cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55), fill=CYAN + (int(255 * p),))
    frame.alpha_composite(layer)


def orbit(frame, img, t, at, center, radius, phase, speed=0.5):
    if t < at:
        return
    p = ease((t - at) / 0.6)
    ang = phase + t * speed
    x, y = center[0] + math.cos(ang) * radius, center[1] + math.sin(ang) * radius * 0.55
    im = img.copy()
    im.putalpha(im.split()[3].point(lambda v: int(v * p)))
    frame.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))


# ---------- end card (soft, no Dandy Man) ----------
_hat = {}


def hat_img(h):
    if h not in _hat:
        im = Image.open(os.path.join(ROOT, "motifs", "logo-hat-light.png")).convert("RGBA")
        _hat[h] = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
    return _hat[h]


def end_card(t):
    fr = background().convert("RGBA")
    draw_hole(fr, t, strength=max(0.0, 0.5 - t * 0.25), speed=0.5)
    sizes = CONTRACT["type"]["vertical"]
    d = ImageDraw.Draw(fr, "RGBA")
    display(fr, "We solved it.", H * 0.22, t, 0.3, size=96, glow=ORANGE)
    a = ease((t - 0.9) / 0.6)
    if a > 0:
        hat = hat_img(int(H * 0.10))
        hy = H * 0.40
        h2 = hat.copy()
        h2.putalpha(h2.split()[3].point(lambda v: int(v * a)))
        fr.alpha_composite(h2, (int(W / 2 - hat.width / 2), int(hy)))
        fh = font("Inter-Bold.otf", int(sizes["headline"] * 1.4))
        tw = d.textlength("Dandy", font=fh)
        ty = hy + hat.height + 36
        d.text((W / 2 - tw / 2, ty), "Dandy", font=fh, fill=TEXT + (int(255 * a),))
        yy = ty + fh.size * 1.1 + 50
        for i, line in enumerate(CONTRACT["copy_rules"]["end_card_lines"]):
            b = ease((t - 1.3 - 0.25 * i) / 0.5)
            fl = font("Inter-Regular.otf" if i == 0 else "Inter-Medium.otf", sizes["body" if i == 0 else "caption"])
            lw = d.textlength(line, font=fl)
            col = BRAND and (tuple(int(BRAND["accent_gold"].lstrip("#")[k:k + 2], 16) for k in (0, 2, 4)) if i == 1 else (200, 190, 220))
            d.text((W / 2 - lw / 2, yy), line, font=fl, fill=col + (int(255 * b),))
            yy += fl.size * 1.1 + 50
    return fr


# ---------- scenes ----------
CARDS = {name: card_image(name) for name in ("Budget app", "Week 3", "Portfolio site", "the schema", "Chatbot", "auth flow")}


def s1(t):
    fr = background().convert("RGBA")
    draw_hole(fr, t)
    draw_particles(fr, t)
    for i, (name, start, frm) in enumerate((("Budget app", 0.0, (150, 300)), ("Week 3", 0.5, (950, 420)), ("Portfolio site", 1.1, (120, 1300)),
                                             ("the schema", 1.8, (980, 1250)), ("Chatbot", 2.7, (220, 1550)), ("auth flow", 3.4, (900, 220)))):
        fall_in(fr, CARDS[name], t, start, 2.6, frm)
        eat_flash(fr, t, start + 2.3)
    display(fr, "Something is eating your projects.", H * 0.60, t, 0.15, size=92, glow=ORANGE)
    return fr


def s2(t):
    fr = background().convert("RGBA")
    draw_hole(fr, t + 5, speed=1.15)
    draw_particles(fr, t + 5)
    for i, (name, start, frm) in enumerate((("Week 3", 0.2, (980, 300)), ("auth flow", 1.6, (120, 1400)), ("Chatbot", 3.2, (960, 1500)))):
        fall_in(fr, CARDS[name], t, start, 2.8, frm)
        eat_flash(fr, t, start + 2.5)
    display(fr, "CONTEXT", H * 0.17, t, 0.3, size=150, glow=ORANGE)
    display(fr, "ROT", H * 0.615, t, 0.55, size=170, glow=CYAN)
    return fr


def s3(t):
    fr = background().convert("RGBA")
    hole = (820, 1480)
    draw_hole(fr, t + 11, center=hole, radius=150, speed=1.2)
    draw_particles(fr, t + 11, center=hole, n=50, seed=3)
    # gauge: fills 0.5-3.5, drains at 4.6; second gauge (long session) fills 7.5-9.5 and overflows at 9.6
    if t < 7.2:
        draw_gauge(fr, t, 160, 420, 170, 760, lambda tt: (tt - 0.6) / 3.0, drain_at=4.6, center=hole)
        token_stream(fr, t, 0.6, 3.4, (640, 520), (245, 1100))
        display(fr, "every session starts empty", H * 0.12, t, 0.3, size=66, align="left", x=SAFE[0], width=SAFE[2] - SAFE[0] - 40, slam=False, exit_at=6.6)
        display(fr, "you explain, it fills", H * 0.665, t, 1.2, size=52, align="left", x=390, width=560, slam=False, exit_at=4.4, color=CYAN)
        display(fr, "session ends: gone", H * 0.665, t, 4.7, size=52, align="left", x=390, width=560, slam=False, exit_at=6.6, color=ORANGE)
    elif t < 11.8:
        tt = t - 7.2
        draw_gauge(fr, tt, 160, 420, 170, 760, lambda u: 0.3 + u / 2.2, overflow_at=2.4, center=hole)
        display(fr, "one long session", H * 0.12, tt, 0.0, size=66, align="left", x=SAFE[0], width=SAFE[2] - SAFE[0] - 40, slam=False, exit_at=4.3)
        display(fr, "oldest things fall out first", H * 0.665, tt, 2.5, size=52, align="left", x=390, width=560, slam=False, color=ORANGE, exit_at=4.3)
    else:
        tt = t - 11.8
        sticky(fr, tt, 0.0, (540, 780), stale_at=1.6)
        display(fr, "notes go stale", H * 0.12, tt, 0.0, size=66, align="left", x=SAFE[0], width=SAFE[2] - SAFE[0] - 40, slam=False)
        display(fr, "someone has to keep them current", H * 0.63, tt, 1.8, size=48, align="left", x=SAFE[0], width=SAFE[2] - SAFE[0], slam=False, color=EMBER)
    return fr


def s4(t):
    fr = background().convert("RGBA")
    draw_hole(fr, t + 27, center=(540, 1500), radius=190, speed=1.3)
    draw_particles(fr, t + 27, center=(540, 1500), n=70, seed=5)
    display(fr, "the damage", H * 0.15, t, 0.0, size=72, align="left", x=SAFE[0], slam=False, color=EMBER)
    tally(fr, t, [("re-explained", "4x", TEXT), ("rebuilt", "2 features", TEXT), ("two agents, one file", "!", RED), ("hours lost this week", "6", ORANGE)],
          SAFE[0], H * 0.23, 0.8, gap=2.6)
    progress_bar(fr, t, 10.0, SAFE[0], H * 0.545, SAFE[2] - SAFE[0])
    return fr


def s5(t):
    fr = background().convert("RGBA")
    shrink = ease(t / 5.0)
    draw_hole(fr, t + 41, center=(540, 1500), radius=int(190 * (1 - 0.6 * shrink)), speed=1.0, strength=1 - 0.5 * shrink)
    draw_particles(fr, t + 41, center=(540, 1500), n=40, seed=5, strength=1 - shrink)
    bc = (540, 720)
    beacon(fr, t, 0.4, bc)
    for i, name in enumerate(("Budget app", "Portfolio site", "Chatbot", "the schema")):
        orbit(fr, CARDS[name], t, 1.0 + i * 0.3, bc, 330, i * math.pi / 2, speed=0.45)
    display(fr, "keep the truth outside the chat", H * 0.16, t, 0.6, size=62, slam=False, glow=CYAN)
    display(fr, "where every session reads first", H * 0.56, t, 3.2, size=48, slam=False, color=CYAN)
    return fr


SCENES = [
    dict(id="s1-hook", dur=5.0, frame=s1),
    dict(id="s2-name", dur=6.0, frame=s2),
    dict(id="s3-why", dur=16.0, frame=s3),
    dict(id="s4-damage", dur=14.0, frame=s4),
    dict(id="s5-fix", dur=9.0, frame=s5),
    dict(id="end", dur=5.0, frame=end_card),
]


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
        d.rounded_rectangle((x - pad, yy - pad * 0.6, x + tw + pad, yy + lh + pad * 0.4), radius=14, fill=VOID + (210,))
        d.text((x, yy), line, font=fnt, fill=TEXT + (255,))


def apply_timing():
    path = os.path.join(VIDEO, "voiceover", "void.json")
    if os.path.exists(path):
        with open(path) as f:
            timing = json.load(f).get("durations", {})
        for sc in SCENES:
            if sc["id"] in timing:
                sc["dur"] = float(timing[sc["id"]])


ON_SCREEN = ["Something is eating your projects.", "CONTEXT", "ROT", "every session starts empty", "you explain, it fills", "session ends: gone",
             "one long session", "oldest things fall out first", "notes go stale", "someone has to keep them current", "the damage", "re-explained",
             "rebuilt", "two agents, one file", "hours lost this week", "your progress", "keep the truth outside the chat", "where every session reads first", "We solved it."]


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
    with open(os.path.join(out, "qa-void-vertical.json"), "w") as f:
        json.dump(dict(canvas="vertical", look="void", problems=[list(p) for p in problems], scenes=[dict(id=s["id"], duration=s["dur"]) for s in SCENES]), f, indent=2)
    if problems:
        print("QA FAILED:", problems)
        return False
    cues = None
    cap_path = os.path.join(VIDEO, "captions.json")
    if os.path.exists(cap_path) and not preview:
        with open(cap_path) as f:
            cues = json.load(f)["cues"]
    tmp = tempfile.mkdtemp(prefix="dandy-void-")
    n, offset, contact = 0, 0.0, []
    step = 1.0 / FPS
    for sc in SCENES:
        frames = int(sc["dur"] * FPS)
        for i in range(frames):
            if preview and i % 3:
                continue
            if stills and i not in (int(0.4 * FPS), int((sc["dur"] * 0.5) * FPS), int((sc["dur"] - 0.6) * FPS)):
                continue
            t = i * step
            fr = sc["frame"](t)
            shake = 9.0 * max(0.0, 1 - t / 0.35) if sc["id"] in ("s1-hook", "s2-name") else 0.0
            fr = finish(fr, t, offset + t, shake=shake, bloom=0.6 if sc["id"] == "end" else 1.0)
            if cues:
                draw_cue(fr, cues, offset + t)
            if stills:
                fr.convert("RGB").save(os.path.join(out, f"void-{sc['id']}-{t:04.1f}.png"))
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
    mp4 = os.path.join(out, f"04-context-rot-vertical{'-final' if final else ''}.mp4")
    total = sum(s["dur"] for s in SCENES)
    bed = sfx.build_bed([(s["id"], s["dur"]) for s in SCENES], os.path.join(out, "sfx-bed.wav"))
    cmd = ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "f%06d.png"), "-i", bed]
    apath = os.path.join(VIDEO, "voiceover", "void.json")
    audio = {}
    if os.path.exists(apath):
        with open(apath) as f:
            audio = json.load(f)
    voice = audio.get("file") if not preview else None
    music = audio.get("music")
    parts, mix, idx = ["[1:a]volume=0.9[sfx]"], ["[sfx]"], 2
    if voice:
        cmd += ["-ss", str(audio.get("offset_s", 0)), "-i", os.path.join(ROOT, voice)]
        parts.append(f"[{idx}:a]{audio_chain(os.path.join(ROOT, voice), bool(audio.get('mixed')))}[voice]")
        idx += 1
    if music:
        cmd += ["-stream_loop", "-1", "-i", os.path.join(ROOT, music)]
        parts.append(f"[{idx}:a]volume={audio.get('music_db', -14)}dB[m0]")
        if voice:  # music ducks under the voice
            parts.append("[voice]asplit[v1][v2]")
            parts.append("[m0][v2]sidechaincompress=threshold=0.05:ratio=6:attack=40:release=500[mduck]")
            mix = ["[v1]", "[sfx]", "[mduck]"]
        else:
            mix = ["[sfx]", "[m0]"]
    elif voice:
        mix = ["[voice]", "[sfx]"]
    fc = ";".join(parts) + ";" + "".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,alimiter=limit=0.89:level=0[aout]"
    cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]", "-t", str(total), "-c:a", "aac", "-b:a", "192k"]
    if final:
        cmd += ["-c:v", "libx264", "-preset", "slow", "-pix_fmt", "yuv420p", "-crf", "17", "-movflags", "+faststart", mp4]
    else:
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", mp4]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    th = 480
    thumbs = [im.resize((int(im.width * th / im.height), th)) for im in contact]
    sheet = Image.new("RGB", (len(thumbs) * (thumbs[0].width + 24) + 24, th + 48), VOID)
    for i, im in enumerate(thumbs):
        sheet.paste(im, (24 + i * (thumbs[0].width + 24), 24))
    sheet.save(os.path.join(out, "contact-void-vertical.png"))
    print(f"rendered {mp4} ({n} frames)")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--stills", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if render(a.preview, a.final, a.stills) else 1)

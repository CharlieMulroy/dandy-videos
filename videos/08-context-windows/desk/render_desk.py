"""Renderer for video 08, Context Windows: the desk metaphor, drawn in code. Vertical 1080x1920.

Usage:  python3 videos/08-context-windows/desk/render_desk.py [--preview] [--stills] [--final] [--audio-only]

A desk seen straight down is the context window. Cards land on it: blue for what you say, grey for what the model
says, cream for a pasted file. A token ruler along the left edge fills as they land. When the desk is full, each new
card pushes every row down one and the bottom row tips off the edge into the dark. A crowded-desk beat shows cards
overlapping and dimmed, with two contradicting decisions pulled forward. A clean sweep clears the desk; one brief
lands. A notebook beside the desk opens and stays while cards keep coming and going. End card without Dandy Man.
No brand purple anywhere but the end card (variant A: Dandy is not named in the narration).

Scene timings move to voiceover/desk.json ("durations", "file", "offset_s", "lines") once Charlie records; captions
are burned in from CAPTIONS until then.
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

with open(os.path.join(ROOT, "style", "contract.json")) as f:
    CONTRACT = json.load(f)
PAL = CONTRACT["palette"]
W, H = 1080, 1920
FPS = CONTRACT["motion"]["fps"]
FONT_DIR = "/usr/share/fonts/opentype/inter"
SAFE = (int(W * 0.08), CONTRACT["layout"]["vertical_safe_top_px"], W - int(W * 0.08), H - CONTRACT["layout"]["vertical_safe_bottom_px"])

# look
SLATE, SLATE_DEEP = (31, 37, 50), (18, 22, 32)
WOOD, WOOD_EDGE, WOOD_GRAIN = (168, 128, 90), (120, 88, 60), (150, 112, 78)
LAMP = (255, 228, 180)
YOU, YOU_INK = (116, 160, 222), (34, 52, 86)
MODEL, MODEL_INK = (214, 218, 226), (78, 84, 98)
FILE, FILE_INK = (244, 234, 206), (120, 104, 70)
NOTE, NOTE_INK = (226, 222, 214), (60, 58, 56)
TEXT = (243, 238, 255)
WARN = (255, 107, 107)

DESK = (70, 440, 860, 1340)                 # x0, y0, x1, y1
BOOK = (892, 470, 1032, 660)                # closed notebook beside the desk
COLS, ROWS = 4, 6
CARD_W, CARD_H = 168, 104
PAD_X = (DESK[2] - DESK[0] - 70 - COLS * CARD_W) / (COLS + 1)   # 70 px reserved on the left for the token ruler
PAD_Y = (DESK[3] - DESK[1] - ROWS * CARD_H) / (ROWS + 1)


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


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


def slot(col, row):
    """Centre of a grid slot on the desk (row may be fractional, for the push-down)."""
    x = DESK[0] + 70 + PAD_X + col * (CARD_W + PAD_X) + CARD_W / 2
    y = DESK[1] + PAD_Y + row * (CARD_H + PAD_Y) + CARD_H / 2
    return x, y


KIND_SEQ = ["you", "model", "file", "you", "model", "you", "model", "file", "you", "model", "you", "model", "file", "you", "model", "you", "model", "you", "file", "model", "you", "model", "you", "model", "you", "model", "file", "you", "model", "you"]
KIND_COL = {"you": (YOU, YOU_INK), "model": (MODEL, MODEL_INK), "file": (FILE, FILE_INK)}


# ---------------------------------------------------------------- drawing
_base = None


def base():
    """Slate, lamp light, the desk with grain and a soft shadow, the closed notebook, the empty token ruler."""
    global _base
    if _base is not None:
        return _base.copy()
    im = Image.new("RGB", (W, H), SLATE)
    arr = np.asarray(im).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - 460) / 900) ** 2 + ((yy - 700) / 1100) ** 2)
    lamp = np.clip(1 - r, 0, 1) ** 1.6
    arr = arr * (0.82 + 0.5 * lamp[..., None]) + lamp[..., None] * np.array(LAMP) * 0.08
    arr[..., :] = np.where(r[..., None] > 1.2, np.array(SLATE_DEEP, np.float32), arr)
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im, "RGBA")
    x0, y0, x1, y1 = DESK
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0 + 10, y0 + 26, x1 + 10, y1 + 34), radius=26, fill=(0, 0, 0, 120))
    im.paste(sh.filter(ImageFilter.GaussianBlur(22)), (0, 0), sh.filter(ImageFilter.GaussianBlur(22)))
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle((x0, y0, x1, y1), radius=22, fill=WOOD_EDGE)
    d.rounded_rectangle((x0 + 6, y0 + 6, x1 - 6, y1 - 6), radius=18, fill=WOOD)
    rnd = random.Random(3)
    for _ in range(90):
        gy = rnd.uniform(y0 + 10, y1 - 10)
        gx = rnd.uniform(x0 + 10, x1 - 300)
        d.line((gx, gy, gx + rnd.uniform(80, 280), gy + rnd.uniform(-2, 2)), fill=WOOD_GRAIN + (rnd.randint(40, 110),), width=rnd.randint(1, 3))
    # lamp glint across the desk
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).ellipse((x0 + 60, y0 - 200, x0 + 760, y0 + 420), fill=LAMP + (46,))
    im.paste(gl.filter(ImageFilter.GaussianBlur(70)), (0, 0), gl.filter(ImageFilter.GaussianBlur(70)))
    d = ImageDraw.Draw(im, "RGBA")
    # token ruler groove
    d.rounded_rectangle((x0 + 26, y0 + 30, x0 + 46, y1 - 30), radius=8, fill=(100, 72, 48, 255))
    # closed notebook
    bx0, by0, bx1, by1 = BOOK
    d.rounded_rectangle((bx0 + 6, by0 + 10, bx1 + 6, by1 + 10), radius=10, fill=(0, 0, 0, 90))
    d.rounded_rectangle((bx0, by0, bx1, by1), radius=10, fill=(58, 64, 82))
    d.rounded_rectangle((bx0, by0, bx0 + 18, by1), radius=6, fill=(44, 49, 64))
    d.line((bx0 + 40, by0 + 40, bx1 - 20, by0 + 40), fill=(90, 98, 118), width=4)
    _base = im
    return im.copy()


def card(d, cx, cy, kind, scale=1.0, rot=0.0, alpha=1.0, lines=None, big_text=None, dim=0.0, img=None):
    """A card with text bars (or real lines). Drawn through a rotated layer so rotation and alpha work."""
    fill, ink = KIND_COL[kind]
    fill = mix(fill, SLATE, dim * 0.55)
    ink = mix(ink, fill, dim * 0.6)
    w, h = int(CARD_W * scale), int(CARD_H * scale)
    lay = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle((22, 26, 22 + w, 26 + h), radius=int(10 * scale), fill=(0, 0, 0, int(70 * alpha)))
    ld.rounded_rectangle((20, 20, 20 + w, 20 + h), radius=int(10 * scale), fill=fill + (int(255 * alpha),))
    if big_text:
        size = 24 * scale
        f = font("Inter-Bold.otf", size)
        words = big_text.split()
        lines_ = [" ".join(words[:len(words) // 2 or 1]), " ".join(words[len(words) // 2 or 1:])] if ld.textlength(big_text, font=f) > w - 24 and len(words) > 1 else [big_text]
        while max(ld.textlength(l, font=f) for l in lines_) > w - 24 and size > 10:
            size -= 1
            f = font("Inter-Bold.otf", size)
        th = len(lines_) * size * 1.15
        for i, l in enumerate(lines_):
            tw = ld.textlength(l, font=f)
            ld.text((20 + w / 2 - tw / 2, 20 + h / 2 - th / 2 + i * size * 1.15), l, font=f, fill=ink + (int(255 * alpha),))
    elif lines:
        f = font("Inter-Medium.otf", 18 * scale)
        for i, ln in enumerate(lines[:3]):
            ld.text((20 + 14 * scale, 20 + 12 * scale + i * 26 * scale), ln, font=f, fill=ink + (int(255 * alpha),))
    else:
        rnd = random.Random(int(cx * 7 + cy * 13))
        for i in range(3):
            bw = w * rnd.uniform(0.45, 0.8)
            ld.rounded_rectangle((20 + 14 * scale, 20 + (18 + i * 26) * scale, 20 + 14 * scale + bw, 20 + (26 + i * 26) * scale),
                                 radius=int(4 * scale), fill=ink + (int(200 * alpha),))
    if rot:
        lay = lay.rotate(rot, resample=Image.BICUBIC, expand=True)
    target = img
    target.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))


def ruler(img, fill_frac, label=True):
    x0, y0, x1, y1 = DESK
    d = ImageDraw.Draw(img, "RGBA")
    top, bot = y0 + 30, y1 - 30
    fy = bot - (bot - top) * clamp(fill_frac)
    col = mix((120, 200, 150), WARN, clamp((fill_frac - 0.7) / 0.3))
    d.rounded_rectangle((x0 + 28, fy, x0 + 44, bot), radius=7, fill=col + (235,))
    if label:
        f = font("Inter-Medium.otf", 22)
        txt = f"{int(clamp(fill_frac) * 128)}k tokens"
        lay = Image.new("RGBA", (260, 40), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((0, 4), txt, font=f, fill=(236, 228, 210, 230))
        lay = lay.rotate(90, expand=True)
        img.alpha_composite(lay, (x0 + 50 - 20, int((top + bot) / 2 - lay.height / 2)))


def tag(img, x, y, text, alpha=1.0, color=TEXT, size=26):
    f = font("Inter-Medium.otf", size)
    d = ImageDraw.Draw(img, "RGBA")
    tw = d.textlength(text, font=f)
    d.rounded_rectangle((x - tw / 2 - size * 0.6, y - size * 0.8, x + tw / 2 + size * 0.6, y + size * 0.9), radius=size * 0.4, fill=(10, 13, 20, int(190 * alpha)))
    d.text((x - tw / 2, y - size * 0.62), text, font=f, fill=color + (int(255 * alpha),))


def label(img, text, alpha=1.0):
    """The beat's on-screen line, large, in the top safe area above the desk."""
    tag(img, (DESK[0] + DESK[2]) / 2, 345, text, alpha=alpha, size=44)


def land(t, at, dur=0.55):
    """Progress of a landing card: 0 before, spring to 1."""
    if t < at:
        return None
    return spring(clamp((t - at) / dur))


def landing_offset(p):
    """Cards drop in from above and shrink to size: (dy, scale, alpha)."""
    return (1 - p) * -260, 1.25 - 0.25 * p, clamp(p * 2.5)


# ---------------------------------------------------------------- scenes
def desk_frame():
    return base().convert("RGBA")


def s1(t, dur):
    img = desk_frame()
    ruler(img, 0.0, label=False)
    p = ease_out((t - 1.6) / 0.6)
    if p > 0:
        label(img, "the context window", alpha=p)
    return img


N_S2 = 17
S2_GAP = 0.42


def s2_cards(t):
    """Cards present at the end of s2 (and their landing times), used by s3 too."""
    out = []
    for i in range(N_S2):
        out.append((i % COLS, i // COLS, KIND_SEQ[i], 0.6 + i * S2_GAP))
    return out


def s2(t, dur):
    img = desk_frame()
    n = 0
    for col, row, kind, at in s2_cards(t):
        p = land(t, at)
        if p is None:
            continue
        n += 1
        dy, sc, a = landing_offset(p)
        x, y = slot(col, row)
        card(None, x, y + dy, kind, scale=sc, alpha=a, rot=(-3 + (col * 7 % 6)) * (1 - p * 0.6), img=img)
    ruler(img, n / 24.0)
    for k, (lab, at) in enumerate((("everything you say", 0.6), ("everything it says", 2.3), ("every file you paste", 4.0), ("measured in tokens", 5.6))):
        a = ease_out((t - at) / 0.4) * (1 - ease_out((t - at - 1.5) / 0.3)) if k < 3 else ease_out((t - at) / 0.4)
        if a > 0:
            label(img, lab, alpha=a)
    return img


S3_FILL = [(i % COLS, i // COLS, KIND_SEQ[i], 0.25 + (i - N_S2) * 0.22) for i in range(N_S2, COLS * ROWS)]
PUSH_T0, PUSH_GAP = 2.6, 1.9
PUSH_TAGS = {0: "the decision from an hour ago", 1: "the file it read this morning"}


def s3(t, dur):
    img = desk_frame()
    k = 0 if t < PUSH_T0 else int((t - PUSH_T0) // PUSH_GAP) + 1          # pushes completed or in progress
    frac = 0.0 if t < PUSH_T0 else smooth(((t - PUSH_T0) % PUSH_GAP) / 0.7)   # progress of the current push
    shift = (k - 1) + frac if k else 0.0
    cards = [(c, r, kd, None) for c, r, kd, _ in s2_cards(t)] + [(c, r, kd, at) for c, r, kd, at in S3_FILL]
    # new cards pushed in at the top, one per push
    for j in range(k):
        cards.append((j % COLS, -1 - j, KIND_SEQ[(j * 5 + 2) % len(KIND_SEQ)], None))
    drawn = sorted(cards, key=lambda c: c[1] + (shift if c[1] >= -100 else 0))
    for col, row, kind, at in drawn:
        p = 1.0 if at is None else land(t, at)
        if p is None:
            continue
        dy, sc, a = landing_offset(p)
        r_eff = row + shift
        if r_eff >= ROWS - 0.02:
            # tipping off the bottom edge
            over = r_eff - (ROWS - 1)
            x, y = slot(col, ROWS - 1)
            fall = clamp(over)
            yy = y + fall * 260 + fall * fall * 320
            rot = -fall * 38 * (1 if col % 2 else -1)
            alpha = 1 - clamp((fall - 0.35) / 0.55)
            if alpha <= 0:
                continue
            card(None, x + fall * 30 * (1 if col % 2 else -1), yy, kind, rot=rot, alpha=alpha, dim=fall * 0.6, img=img)
            push_index = row + k - ROWS if row >= 0 else None
            idx = int(round(r_eff - ROWS + 0.02)) if False else None
            continue
        if r_eff < -0.5:
            continue
        x, y = slot(col, max(r_eff, -0.95))
        card(None, x, y + dy, kind, scale=sc, alpha=a * clamp((r_eff + 1.0) / 0.6), rot=0, img=img)
    # tags for the first two pushed-off cards: the row that is tipping during push j
    for j, ptag in PUSH_TAGS.items():
        tj = PUSH_T0 + j * PUSH_GAP + 0.25
        a = ease_out((t - tj) / 0.3) * (1 - ease_out((t - tj - 1.3) / 0.35))
        if a > 0:
            tag(img, (DESK[0] + DESK[2]) / 2 + 40, DESK[3] + 70, ptag, alpha=a)
    ruler(img, min(1.0, (N_S2 + sum(1 for *_, at in S3_FILL if t >= at)) / 24.0))
    for lab, at, off in (("fixed size", 0.2, 1.8), ("oldest pages slide off", 2.9, 99)):
        a = ease_out((t - at) / 0.4) * (1 - ease_out((t - at - off) / 0.3))
        if a > 0:
            label(img, lab, alpha=a)
    return img


def s4(t, dur):
    img = desk_frame()
    rnd = random.Random(8)
    cards = []
    for i in range(30):
        col, row = i % COLS, (i // COLS) % ROWS
        x, y = slot(col, row)
        cards.append((x + rnd.uniform(-40, 40), y + rnd.uniform(-30, 30), KIND_SEQ[i % len(KIND_SEQ)], rnd.uniform(-14, 14), rnd.uniform(0.0, 0.75) if i < 18 else rnd.uniform(0, 0.2)))
    for x, y, kind, rot, dim in cards:
        card(None, x, y, kind, rot=rot, dim=dim, img=img)
    ruler(img, 1.0)
    # two decisions pulled forward
    q = ease_out((t - 3.0) / 0.7)
    if q > 0:
        img.alpha_composite(Image.new("RGBA", (W, H), (10, 13, 20, int(150 * q))))
        cx = (DESK[0] + 70 + DESK[2]) / 2
        cy = (DESK[1] + DESK[3]) / 2 - 60
        sc = lerp(1.0, 2.0, q)
        card(None, lerp(cx - 100, cx - 175, q), lerp(cy + 120, cy, q), "you", scale=sc, rot=lerp(-6, -3, q), dim=0.5, big_text="use Postgres", img=img)
        card(None, lerp(cx + 120, cx + 175, q), lerp(cy - 90, cy, q), "you", scale=sc, rot=lerp(5, 2, q), dim=0.0, big_text="switched to SQLite", img=img)
        tag(img, cx - 175, cy - 150, "an hour ago", alpha=q * 0.9, size=30)
        tag(img, cx + 175, cy - 150, "just now", alpha=q * 0.9, size=30)
    p = land(t, 6.4, 0.6)
    if p is not None:
        dy, sc, a = landing_offset(p)
        cx = (DESK[0] + 70 + DESK[2]) / 2
        cy = (DESK[1] + DESK[3]) / 2 + 200
        card(None, cx, cy + dy, "model", scale=2.0 * sc, alpha=a, big_text="Setting up Postgres", img=img)
        u = ease_out((t - 7.3) / 0.4)
        if u > 0:
            d = ImageDraw.Draw(img, "RGBA")
            w = CARD_W * 2.0
            d.line((cx - w * 0.33, cy + 36, cx - w * 0.33 + w * 0.64 * u, cy + 36), fill=WARN + (230,), width=6)
            tag(img, cx, cy + 110, "the old one", alpha=u * 0.9, size=30, color=WARN)
    a = ease_out((t - 0.4) / 0.4)
    if a > 0:
        label(img, "crowded desk, sloppy work", alpha=a)
    # the pull back
    z = lerp(1.0, 0.92, smooth(t / 1.4))
    if z < 1:
        small = img.resize((int(W * z), int(H * z)), Image.LANCZOS)
        out = Image.new("RGBA", (W, H), SLATE_DEEP + (255,))
        out.alpha_composite(small, ((W - small.width) // 2, (H - small.height) // 2 + 20))
        return out
    return img


def s5(t, dur):
    img = desk_frame()
    rnd = random.Random(8)
    q = smooth((t - 0.2) / 1.1)
    for i in range(30):
        col, row = i % COLS, (i // COLS) % ROWS
        x, y = slot(col, row)
        jx, jy, rot = rnd.uniform(-40, 40), rnd.uniform(-30, 30), rnd.uniform(-14, 14)
        dimv = rnd.uniform(0.0, 0.75) if i < 18 else rnd.uniform(0, 0.2)
        sx = x + jx - q * (1100 + row * 90)
        a = 1 - clamp((q - 0.75) / 0.25)
        if sx > -300 and a > 0:
            card(None, sx, y + jy, KIND_SEQ[i % len(KIND_SEQ)], rot=rot - q * 20, dim=dimv, alpha=a, img=img)
    ruler(img, 1.0 - q)
    p = land(t, 3.4, 0.7)
    if p is not None:
        dy, sc, a = landing_offset(p)
        cx = (DESK[0] + 70 + DESK[2]) / 2
        cy = (DESK[1] + DESK[3]) / 2
        card(None, cx, cy + dy, "you", scale=1.6 * sc, alpha=a, lines=["the brief:", "budget app, Postgres,", "billing is next"], img=img)
        ruler(img, 0.06 * p)
    for lab, at, off in (("a fresh chat is a clean desk", 1.3, 3.4), ("sharp. and blank.", 5.1, 99)):
        a = ease_out((t - at) / 0.4) * (1 - ease_out((t - at - off) / 0.3))
        if a > 0:
            label(img, lab, alpha=a)
    return img


def s6(t, dur):
    img = desk_frame()
    # cards come and go in a loop while the notebook stays
    cycle = 2.2
    for i in range(6):
        at = 0.3 + i * 0.5
        col, row = i % COLS, i // COLS
        p = land(t, at)
        if p is None:
            continue
        dy, sc, a = landing_offset(p)
        slide = clamp((t - at - 2.4) / 0.9)
        x, y = slot(col, row)
        card(None, x, y + dy + slide * slide * 700, KIND_SEQ[i], scale=sc, alpha=a * (1 - clamp((slide - 0.5) / 0.5)), rot=-slide * 25, img=img)
    ruler(img, 0.3 + 0.1 * math.sin(t))
    # the notebook opens: it grows out from beside the desk into an open spread over the desk's right half
    q = spring(clamp((t - 0.6) / 0.9))
    bx0, by0, bx1, by1 = BOOK
    ox0, oy0, ox1, oy1 = (DESK[2] - 440, DESK[1] + 180, DESK[2] + 120, DESK[1] + 560)
    x0, y0, x1, y1 = lerp(bx0, ox0, q), lerp(by0, oy0, q), lerp(bx1, ox1, q), lerp(by1, oy1, q)
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((x0 + 8, y0 + 14, x1 + 8, y1 + 14), radius=12, fill=(0, 0, 0, 110))
    d.rounded_rectangle((x0, y0, x1, y1), radius=12, fill=(58, 64, 82))
    if q > 0.3:
        inner = (x0 + 14, y0 + 12, x1 - 14, y1 - 12)
        d.rounded_rectangle(inner, radius=8, fill=NOTE)
        mid = (inner[0] + inner[2]) / 2
        d.line((mid, inner[1], mid, inner[3]), fill=(190, 184, 176), width=3)
        f = font("Inter-Medium.otf", 22)
        write = clamp((t - 1.6) / 2.2)
        lines = ["budget app", "Postgres (decided Tue)", "auth: done", "billing: next", "", "do not rebuild login"]
        n_show = int(write * len(lines) + 0.999)
        for i, ln in enumerate(lines[:n_show]):
            page = 0 if i < 4 else 1
            lx = inner[0] + 22 + page * ((inner[2] - inner[0]) / 2)
            ly = inner[1] + 24 + (i if page == 0 else i - 4) * 36
            d.text((lx, ly), ln, font=f, fill=NOTE_INK + (255,))
        for i in range(6):
            ly = inner[1] + 56 + i * 36
            d.line((inner[0] + 14, ly, mid - 14, ly), fill=(200, 196, 190, 160), width=1)
            d.line((mid + 14, ly, inner[2] - 14, ly), fill=(200, 196, 190, 160), width=1)
    for lab, at, off in (("the desk is for working", 0.3, 2.6), ("keep the record off the desk", 3.1, 99)):
        a = ease_out((t - at) / 0.4) * (1 - ease_out((t - at - off) / 0.3))
        if a > 0:
            label(img, lab, alpha=a)
    return img


def end_card(last, t):
    p = ease_out(t / 1.0)
    bg = last.filter(ImageFilter.GaussianBlur(int(16 * p)))
    bg.alpha_composite(Image.new("RGBA", bg.size, rgb(PAL["background"]) + (int(222 * p),)))
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W * 0.12, H * 0.28, W * 0.88, H * 0.72), fill=rgb(PAL["primary"]) + (int(120 * p),))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(130)))
    d = ImageDraw.Draw(bg)
    sizes = CONTRACT["type"]["vertical"]
    a = ease_out((t - 0.5) / 0.6)
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
        d.text((W / 2 - tw / 2, ty), "Dandy", font=fh, fill=rgb(PAL["text"]) + (int(255 * a),))
        yy = ty + fh.size * 1.1 + 60
        for i, line in enumerate(CONTRACT["copy_rules"]["end_card_lines"]):
            b = ease_out((t - 0.9 - 0.25 * i) / 0.5)
            fl = font("Inter-Medium.otf", sizes["body" if i == 0 else "caption"])
            lw = d.textlength(line, font=fl)
            d.text((W / 2 - lw / 2, yy), line, font=fl, fill=(rgb(PAL["accent_gold"]) if i == 1 else rgb(PAL["soft"])) + (int(255 * b),))
            yy += fl.size * 1.1 + 50
    return bg


SCENES = [("s1", 5.0, s1), ("s2", 8.0, s2), ("s3", 11.0, s3), ("s4", 10.0, s4), ("s5", 10.0, s5), ("s6", 6.0, s6), ("end", 4.5, None)]
CAPTIONS = [
    (0.6, 2.4, "Every AI chat has a desk."), (2.6, 4.8, "It's called the context window."),
    (5.6, 8.4, "Everything you say, everything it says, every file you paste:"),
    (8.6, 9.9, "it all lands on the desk,"), (10.0, 11.3, "measured in tokens, rough chunks of words."),
    (11.5, 13.0, "And that desk is all the model can see."),
    (13.4, 15.2, "The desk has a fixed size."), (15.6, 18.0, "When it fills, the oldest pages slide off."),
    (18.3, 19.9, "The decision from an hour ago."), (20.1, 21.7, "The file it read this morning."), (22.0, 23.8, "Gone, without a word."),
    (24.6, 27.4, "Even before it's full, a crowded desk makes it sloppy."),
    (27.6, 30.2, "It mixes up what's current and what's old."), (30.6, 33.6, "That's why a long chat gets dumber."),
    (34.6, 36.6, "So a fresh chat isn't a failure."), (36.8, 38.4, "It's a clean desk."), (38.8, 40.6, "Sharp, and blank."),
    (40.9, 43.8, "Whatever it needs to know, you put back on the desk."),
    (44.4, 46.6, "The desk is for working."), (46.9, 49.9, "Keep the record somewhere that doesn't slide off."),
]
ON_SCREEN = ["the context window", "everything you say", "everything it says", "every file you paste", "measured in tokens",
             "fixed size", "oldest pages slide off", "the decision from an hour ago", "the file it read this morning",
             "crowded desk, sloppy work", "an hour ago", "just now", "use Postgres", "switched to SQLite", "setting up Postgres...",
             "a fresh chat is a clean desk", "sharp. and blank.", "the desk is for working", "keep the record off the desk"]


def apply_timing():
    p = os.path.join(VIDEO, "voiceover", "desk.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        vo = json.load(f)
    for i, (sid, dur, fn) in enumerate(SCENES):
        if sid in vo.get("durations", {}):
            SCENES[i] = (sid, float(vo["durations"][sid]), fn)
    global CAPTIONS
    if "lines" in vo:
        CAPTIONS = [(s - 0.05, e + 0.35, tx) for s, e, tx in vo["lines"]]
    return vo


def draw_caption(img, tg):
    cue = next((c for c in CAPTIONS if c[0] <= tg < c[1]), None)
    if cue is None:
        return
    a = min(1.0, (tg - cue[0]) / 0.25, (cue[1] - tg) / 0.2)
    fnt = font("Inter-Bold.otf", int(CONTRACT["type"]["vertical"]["body"] * 0.95))
    d = ImageDraw.Draw(img)
    words, lines, cur = cue[2].split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if d.textlength(trial, font=fnt) <= SAFE[2] - SAFE[0] - 40 or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    lh = fnt.size * 1.18
    pad = 20
    y = SAFE[3] - len(lines) * (lh + pad * 0.6) - 10
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=fnt)
        x, yy = W / 2 - tw / 2, y + i * (lh + pad * 0.6)
        d.rounded_rectangle((x - pad, yy - pad * 0.55, x + tw + pad, yy + lh + pad * 0.3), radius=14, fill=(6, 8, 14, int(190 * a)))
        d.text((x, yy), line, font=fnt, fill=TEXT + (int(255 * a),))


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


# ---------------------------------------------------------------- sound: paper and room tone
SR = 48000
_rng = np.random.default_rng(11)


def _band(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x).astype(np.float32)


def snd_tap(gain=0.5):
    n = int(SR * 0.16)
    t = np.arange(n) / SR
    x = _band(_rng.normal(0, 1, n), 900, 5000) * np.exp(-t * 60) + np.sin(2 * np.pi * 140 * t) * np.exp(-t * 45) * 0.5
    return x / (np.abs(x).max() + 1e-9) * gain


def snd_slide(gain=0.4, dur=0.5):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = _band(_rng.normal(0, 1, n), 700, 4000) * np.sin(np.pi * t / dur) ** 1.5
    return x / (np.abs(x).max() + 1e-9) * gain


def snd_fall(gain=0.35):
    n = int(SR * 0.7)
    t = np.arange(n) / SR
    x = _band(_rng.normal(0, 1, n), 300, 2500) * np.exp(-t * 5) * (1 - np.exp(-t * 40)) + np.sin(2 * np.pi * 90 * t) * np.exp(-t * 12) * 0.4
    return x / (np.abs(x).max() + 1e-9) * gain


def snd_sweep(gain=0.5):
    n = int(SR * 1.3)
    t = np.arange(n) / SR
    x = _band(_rng.normal(0, 1, n), 400, 6000) * np.sin(np.pi * t / 1.3) ** 1.2
    return x / (np.abs(x).max() + 1e-9) * gain


def snd_page(gain=0.4):
    n = int(SR * 0.45)
    t = np.arange(n) / SR
    x = _band(_rng.normal(0, 1, n), 1200, 7000) * np.sin(np.pi * t / 0.45) ** 2 * (1 + 0.5 * np.sin(2 * np.pi * 9 * t))
    return x / (np.abs(x).max() + 1e-9) * gain


def snd_tone(gain=0.25):
    n = int(SR * 2.2)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * 440 * f * t + k) * np.exp(-t * (1.4 + 1.2 * k)) / (k + 1) for k, f in enumerate((1.0, 2.0, 3.01)))
    return x / (np.abs(x).max() + 1e-9) * gain


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

    room = sosfilt(butter(2, [60, 500], btype="band", fs=SR, output="sos"), _rng.normal(0, 1, n)).astype(np.float32)
    room = room / (np.abs(room).max() + 1e-9) * 0.05
    L += room
    R += np.roll(room, 3000)
    s2, s3, s4, s5, s6 = (starts[k] for k in ("s2", "s3", "s4", "s5", "s6"))
    for i in range(N_S2):
        put(snd_tap(0.45), s2 + 0.6 + i * S2_GAP + 0.3, pan=-0.3 + 0.2 * (i % COLS))
    for c, r, kd, at in S3_FILL:
        put(snd_tap(0.45), s3 + at + 0.3, pan=-0.3 + 0.2 * c)
    for j in range(5):
        put(snd_slide(0.3), s3 + PUSH_T0 + j * PUSH_GAP)
        put(snd_fall(0.35), s3 + PUSH_T0 + j * PUSH_GAP + 0.55)
    put(snd_slide(0.25, 0.8), s4 + 3.0)
    put(snd_tap(0.4), s4 + 6.4 + 0.35)
    put(snd_sweep(0.45), s5 + 0.2)
    put(snd_tap(0.5), s5 + 3.4 + 0.4)
    put(snd_page(0.4), s6 + 0.7)
    for i in range(6):
        put(snd_tap(0.3), s6 + 0.3 + i * 0.5 + 0.3)
    put(snd_tone(0.22), starts["end"] + 0.5)
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
    with open(os.path.join(out, "qa-desk-vertical.json"), "w") as f:
        json.dump(dict(canvas="vertical", look="desk", duration=total, problems=problems,
                       scenes=[dict(id=s, start=round(starts[s], 2), duration=d) for s, d, _ in SCENES]), f, indent=2)
    if problems:
        print("QA FAILED:", problems)
        return False
    mp4 = os.path.join(out, "08-context-windows-vertical.mp4")
    wav = os.path.join(out, "desk-bed.wav")
    if not audio_only:
        tmp = tempfile.mkdtemp(prefix="dandy-desk-")
        step = 3 if preview else 1
        n, last = 0, None
        for sid, dur, fn in SCENES:
            frames = int(round(dur * FPS))
            picks = {int(frames * 0.3), int(frames * 0.75)}
            for i in range(frames):
                if i % step or (stills and i not in picks):
                    continue
                t = i / FPS
                tg = starts[sid] + t
                img = end_card(last, t) if fn is None else fn(t, dur)
                if fn is not None:
                    last = img
                fr = finish(img, t, tg, bloom=0.35, grain=2.2, vignette=0.32, drift=0.45, zoom=1.03)
                draw_caption(fr, tg)
                if stills:
                    fr.convert("RGB").save(os.path.join(out, f"desk-{sid}-{t:04.1f}.png"))
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
        fc = (f"[2:a]atrim=start={vo.get('offset_s', 0)},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
              f"highpass=f=70,volume={vo.get('voice_db', 7.5)}dB,asplit=2[v][vk];[1:a]volume={vo.get('bed_db', 0)}dB[b];"
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

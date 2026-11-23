"""Video 14, MCP: the universal plug. The inventor's blueprint, opening in the dark. Vertical 1080x1920.

Usage:  python3 videos/14-mcp/blueprint/render_mcp.py [--preview] [--final] [--at 1.0,5.2,...] [--workers 2]

One patent drawing, seen through a camera that never cuts. Everything is drawn in world coordinates on a single
sheet and the camera slides across it.

The dark half (lock, reach, tangle) is a floor plan of a sealed cell seen by the only light there is: the mind, an
amber glow that flickers like a failing bulb. Shot like found footage: handheld shake, heavy grain, frames that cut
out. Tally marks are scratched inside the walls. The mind reaches for your files, calendar and code and hits the wall.
Cables slither in like living things, knot the cell shut, and one taps on the wall from outside.

The turn: a socket is cut into the wall and light pours out of it, washing the sheet from black to blueprint blue.
From there it is calm: the title block, three panels (the menu, the ask, the answer), and a wall of sockets where
GitHub, Notion, Slack, Figma and a browser plug in, then thousands more. The last plug is the only purple on the
sheet: Dandy, which unfolds a small map into the room. Soft end card without Dandy Man.

Placeholder timing until Charlie records; then voiceover/blueprint.json ("durations", "lines", "file") takes over.
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
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "render"))
from finish import finish, spring  # noqa: E402
from checks import run_all  # noqa: E402

with open(os.path.join(ROOT, "style", "contract.json")) as f:
    CONTRACT = json.load(f)
PAL = CONTRACT["palette"]
W, H = 1080, 1920
FPS = CONTRACT["motion"]["fps"]
FONT_DIR = "/usr/share/fonts/opentype/inter"
SAFE = (int(W * 0.08), CONTRACT["layout"]["vertical_safe_top_px"], W - int(W * 0.08), H - CONTRACT["layout"]["vertical_safe_bottom_px"])


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------- look
NIGHT = (4, 5, 8)
NIGHT_GRID = (44, 48, 58)
OLD_CHALK = (196, 194, 186)              # chalk in the dark: only ever seen through the mind's light
VINE, VINE_EDGE, VINE_HEAD = (58, 64, 78), (104, 112, 128), (122, 128, 142)
BLUE, BLUE_DEEP = (22, 62, 128), (11, 34, 80)
GRID_MINOR, GRID_MAJOR = (58, 100, 168), (84, 128, 196)
CHALK = (236, 243, 255)
CHALK_SOFT = (176, 198, 232)
AMBER, AMBER_HOT = (255, 172, 64), (255, 236, 196)
PURPLE, PURPLE_DEEP, PURPLE_LIGHT = rgb(PAL["highlight"]), rgb(PAL["primary"]), (188, 160, 255)
TEXT = (243, 238, 255)


def font(name, size):
    return _font(name, max(6, int(round(size))))


_fonts = {}


def _font(name, size):
    k = (name, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    return _fonts[k]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = clamp(t)
    return t * t * t


def ease_io(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def lerp(a, b, p):
    return a + (b - a) * p


def mix(c1, c2, p):
    return tuple(int(lerp(c1[i], c2[i], clamp(p))) for i in range(3))


def win(t, a, b, fade_in=0.25, fade_out=0.25):
    """1 inside [a, b], easing in and out at the edges."""
    return ease_out((t - a) / fade_in) * (1 - ease_out((t - b) / fade_out))


# ---------------------------------------------------------------- timing (placeholder until Charlie records)
SCENES = [("lock", 6.5), ("reach", 6.5), ("tangle", 6.5), ("turn", 7.0), ("how", 2.0), ("menu", 6.0), ("ask", 4.5),
          ("answer", 4.0), ("plugq", 2.0), ("tools", 13.0), ("more", 3.0), ("dandy", 7.5), ("end", 4.0)]
CAPTIONS = [
    (0.5, 3.6, "The smartest AI you've ever used is locked in a room."), (4.0, 4.8, "No doors."), (5.1, 6.2, "No windows."),
    (6.9, 8.9, "It can think. It can write."), (9.2, 12.6, "But it can't touch your files, your calendar, or your code."),
    (13.4, 15.7, "Every connection used to be built by hand."), (16.0, 18.9, "One custom cable for every tool, for every AI."),
    (20.1, 22.8, "Then came MCP, the Model Context Protocol."), (23.1, 26.1, "One standard plug that any AI and any tool can share."),
    (26.7, 28.2, "Here's how it works."),
    (28.8, 30.7, "A tool sets up an MCP server."), (31.0, 34.2, "Think of it as a menu: here's what I can do."),
    (34.7, 38.5, "Your AI reads the menu, picks what it needs, and asks."),
    (39.2, 42.6, "The tool does the work and hands back the result."),
    (43.1, 44.8, "So what can you plug in?"),
    (45.2, 47.8, "GitHub, to read your code and open pull requests."), (48.0, 50.3, "Notion, to find and update your docs."),
    (50.6, 52.7, "Slack, to catch you up on a thread."), (53.0, 55.0, "Figma, to build from your designs."),
    (55.3, 57.7, "Even a browser, to test your site."),
    (58.2, 60.7, "Thousands more, and anyone can build one."),
    (61.2, 62.3, "Including us."), (62.5, 64.9, "Our tool, Dandy, plugs in the same way"),
    (65.1, 68.2, "and gives your AI a live map of your project."),
]
# Scene-relative cue times (seconds from the start of the scene). voiceover/blueprint.json "cues" overrides them.
CUE = dict(
    wall_shut=(0.35, 1.5), dies=(1.75, 2.3), door=3.85, window=4.95, cutout=5.32,
    think=[0.55, 1.75], reaches=[3.55, 4.55, 5.55],
    cables_t0=0.45, cables_gap=0.21, cable_dur=1.35, taps=[4.95, 5.5, 6.05], hush=6.1,
    socket=0.62, wash=(0.78, 1.9), title=(2.6, 1.6),
    menu_plug=(1.35, 0.85), menu_card=2.55, ask_scan=(0.9, 1.3), ask_pick=2.3, ask_pulse=(3.0, 0.7),
    gear=(0.85, 0.9), page=(1.85, 1.15),
    plugs=[0.35, 3.15, 5.75, 8.15, 10.45], more_fill=(0.45, 2.4),
    dandy_plug=(1.45, 1.0), dandy_label=1.9, map=(4.1, 1.7), light=(4.6, 1.8),
)
START = {}
TOTAL = 0.0


def build_starts():
    global TOTAL
    acc = 0.0
    for sid, d in SCENES:
        START[sid] = acc
        acc += d
    TOTAL = acc


def scene_at(tg):
    for sid, d in SCENES:
        if tg < START[sid] + d:
            return sid, tg - START[sid]
    return SCENES[-1][0], tg - START[SCENES[-1][0]]


# ---------------------------------------------------------------- world layout
CELL_S, CELL_WT = 440, 28
CELLS = [(-640, 0), (0, 0), (640, 0)]          # the middle one is ours
TOOLS = [("chat", -800, 700), ("folder", -400, 700), ("calendar", 0, 700), ("code", 400, 700), ("db", 800, 700)]
TOOL_S = 210
TITLE = (0, 535)                                 # title block centre, under the cell
PANELS = [(0, 2240), (0, 2860), (0, 3480)]       # FIG. 2
PANEL_W, PANEL_H = 950, 540
WALL_X = 2600                                    # FIG. 3, the long wall of sockets (the room is to its left)
SOCKET_GAP = 200
SOCKETS = [y for y in range(-1400, 7001, SOCKET_GAP)]
NAMED = [("GitHub", "code and pull requests", 2400), ("Notion", "your docs", 2600), ("Slack", "your threads", 2800),
         ("Figma", "your designs", 3000), ("A browser", "tests your site", 3200)]
DANDY_Y = 3400
ROOM_MIND = (2390, 2800)


# ---------------------------------------------------------------- camera
class Cam:
    def __init__(self, cx, cy, z, ox=0.0, oy=0.0):
        self.cx, self.cy, self.z, self.ox, self.oy = cx, cy, z, ox, oy

    def p(self, x, y):
        return ((x - self.cx) * self.z + W / 2 + self.ox, (y - self.cy) * self.z + H / 2 + self.oy)

    def pa(self, arr):
        return (np.asarray(arr, np.float64) - (self.cx, self.cy)) * self.z + (W / 2 + self.ox, H / 2 + self.oy)

    def w(self, sx, sy):
        return ((sx - W / 2 - self.ox) / self.z + self.cx, (sy - H / 2 - self.oy) / self.z + self.cy)


def moves():
    S = START
    return [  # (start, duration, (cx, cy, z), zoom dip on the way, easing)
        (0.0, SCENES[0][1], (0, 8, 1.82), 0.0, "linear"),
        (S["reach"], 1.5, (0, 440, 0.92), 0.0, "io"),
        (S["tangle"], 0.42, (0, 350, 0.52), 0.0, "spring"),
        (S["tangle"] + 3.7, 2.8, (70, 150, 0.74), 0.0, "io"),
        (S["turn"] + 0.05, 1.15, (0, 330, 1.0), 0.0, "io"),
        (S["how"], 1.5, (0, 2770, 0.5), 0.3, "io"),
        (S["menu"], 0.95, (0, 2240, 1.0), 0.0, "io"),
        (S["ask"], 0.95, (0, 2860, 1.0), 0.12, "io"),
        (S["answer"], 0.95, (0, 3480, 1.0), 0.12, "io"),
        (S["plugq"], 1.6, (2760, 2880, 0.95), 0.3, "io"),
        (S["more"], 1.8, (2720, 2840, 0.34), 0.0, "io"),
        (S["dandy"], 1.5, (2581, 3290, 1.0), 0.0, "io"),
    ]


def cam_at(tg):
    st = (0.0, 0.0, 1.55)
    for t0, dur, tgt, dip, kind in moves():
        if tg < t0:
            break
        u = clamp((tg - t0) / dur)
        p = {"linear": smooth(u) * 0.5 + u * 0.5, "io": ease_io(u), "spring": spring(u)}[kind]
        z = math.exp(lerp(math.log(st[2]), math.log(tgt[2]), p)) * (1 - dip * math.sin(math.pi * clamp(u)))
        st = (lerp(st[0], tgt[0], p), lerp(st[1], tgt[1], p), z) if u < 1 else tgt
    cx, cy, z = st
    # handheld: only in the dark half, fading out as the light comes in
    hh = 1.0 - smooth((tg - START["turn"] - 0.6) / 1.2)
    ox = oy = 0.0
    if hh > 0:
        ox = (7 * math.sin(tg * 1.31) + 4 * math.sin(tg * 2.97 + 1.1) + 2.2 * math.sin(tg * 7.3 + 2.0)) * hh
        oy = (6 * math.cos(tg * 1.07) + 3.5 * math.sin(tg * 3.41 + 0.4) + 2.0 * math.sin(tg * 6.1 + 1.3)) * hh
        for kt in knock_times():
            k = tg - kt
            if 0 <= k < 0.5:
                oy += 11 * math.exp(-k * 10) * math.sin(k * 55)
    return Cam(cx, cy, z, ox, oy)


def knock_times():
    return [START["reach"] + r + 0.36 for r in CUE["reaches"]] + [START["tangle"] + t for t in CUE["taps"]]


# ---------------------------------------------------------------- hand-drawn paths
_wob = {}


def wpath(pts, seed=0, amp=1.1, step=14.0, closed=False):
    """A polyline in world units with a slight hand wobble; cached. Returns (points array, cumulative length)."""
    key = (tuple((round(x, 2), round(y, 2)) for x, y in pts), seed, amp, step, closed)
    if key in _wob:
        return _wob[key]
    P = list(pts) + ([pts[0]] if closed else [])
    rnd = random.Random(seed * 7919 + len(P))
    ph1, ph2 = rnd.uniform(0, 6.3), rnd.uniform(0, 6.3)
    out, s_tot = [], 0.0
    for a, b in zip(P[:-1], P[1:]):
        L = math.dist(a, b)
        n = max(1, int(L / step))
        nx, ny = ((-(b[1] - a[1]) / L, (b[0] - a[0]) / L) if L > 0 else (0.0, 0.0))
        for k in range(n):
            u = k / n
            s = s_tot + u * L
            off = amp * (0.7 * math.sin(s * 0.023 + ph1) + 0.3 * math.sin(s * 0.061 + ph2))
            out.append((a[0] + (b[0] - a[0]) * u + nx * off, a[1] + (b[1] - a[1]) * u + ny * off))
        s_tot += L
    out.append(P[-1])
    arr = np.array(out, np.float64)
    cum = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(arr, axis=0).T))])
    _wob[key] = (arr, cum)
    return arr, cum


def raw(pts):
    arr = np.array(pts, np.float64)
    cum = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(arr, axis=0).T))])
    return arr, cum


def cut(path, prog):
    arr, cum = path
    prog = clamp(prog)
    if prog >= 1:
        return arr
    L = cum[-1] * prog
    i = int(np.searchsorted(cum, L))
    if i <= 0:
        return arr[:1]
    a, b = arr[i - 1], arr[i]
    seg = cum[i] - cum[i - 1]
    u = (L - cum[i - 1]) / seg if seg > 0 else 0
    return np.vstack([arr[:i], a + (b - a) * u])


def stroke(d, cam, path, prog=1.0, width=3.0, col=CHALK, alpha=1.0, double=True, minw=1):
    if prog <= 0 or alpha <= 0.004:
        return
    pts = cut(path, prog)
    if len(pts) < 2:
        return
    sp = cam.pa(pts)
    w = max(minw, int(round(width * cam.z)))
    flat = [tuple(p) for p in sp]
    d.line(flat, fill=col + (int(255 * clamp(alpha)),), width=w, joint="curve")
    if double and w >= 2:
        d.line([(x + 0.9, y + 0.7) for x, y in flat], fill=col + (int(90 * clamp(alpha)),), width=max(1, w - 1))


def rect_pts(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]


def rrect_pts(x0, y0, x1, y1, r, n=5):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.append(pts[0])
    return pts


def ellipse_pts(cx, cy, rx, ry, a0=0, a1=360, n=40):
    return [(cx + rx * math.cos(math.radians(lerp(a0, a1, k / n))), cy + ry * math.sin(math.radians(lerp(a0, a1, k / n)))) for k in range(n + 1)]


# ---------------------------------------------------------------- text (records boxes for QA)
REC = None
DIM = 1.0          # the layer being drawn will be composited at this opacity (QA ignores text that ends up faint)


def text_world(img, cam, x, y, s, size, col=CHALK, alpha=1.0, name=None, fnt="Inter-Bold.otf", anchor="lm", role="body", lines=None):
    if alpha <= 0.01:
        return None
    sx, sy = cam.p(x, y)
    f = font(fnt, size * cam.z)
    return text_screen(img, sx, sy, s, f, col, alpha, name, anchor, role, lines)


def text_screen(img, sx, sy, s, f, col=CHALK, alpha=1.0, name=None, anchor="lm", role="body", lines=None):
    d = ImageDraw.Draw(img, "RGBA")
    d.text((sx, sy), s, font=f, fill=col + (int(255 * clamp(alpha)),), anchor=anchor)
    box = d.textbbox((sx, sy), s, font=f, anchor=anchor)
    if REC is not None and alpha * DIM > 0.5 and on_screen(box):
        REC.append(dict(name=name or s, type="text", role=role, text=s, lines=lines or [s], bbox=box))
    return box


def on_screen(box):
    return box[2] > 0 and box[0] < W and box[3] > 0 and box[1] < H


def record_block(name, text, lines, box, role="body"):
    if REC is not None and DIM > 0.5 and on_screen(box):
        REC.append(dict(name=name, type="text", role=role, text=text, lines=lines, bbox=box))


# ---------------------------------------------------------------- sprites
_glow = {}


def glow_sprite(col, size, power=2.2):
    k = (col, size, power)
    if k not in _glow:
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
        r = np.hypot(xx - size / 2, yy - size / 2) / (size / 2)
        a = np.clip(1 - r, 0, 1) ** power
        arr = np.zeros((size, size, 4), np.uint8)
        arr[..., :3] = col
        arr[..., 3] = (a * 255).astype(np.uint8)
        _glow[k] = Image.fromarray(arr, "RGBA")
    return _glow[k]


def put_glow(img, sx, sy, radius_px, col, alpha):
    if alpha <= 0.01 or radius_px < 2:
        return
    r = int(radius_px)
    spr = glow_sprite(col, 256).resize((2 * r, 2 * r), Image.BILINEAR)
    if alpha < 1:
        spr.putalpha(spr.split()[3].point(lambda v: int(v * clamp(alpha))))
    img.alpha_composite(spr, (int(sx - r), int(sy - r)))


def orb(img, cam, x, y, inten, size=1.0, hot=0.0):
    """The mind: an amber glow with a hot core."""
    sx, sy = cam.p(x, y)
    z = cam.z * size
    put_glow(img, sx, sy, 210 * z, AMBER, 0.55 * inten)
    put_glow(img, sx, sy, 90 * z, AMBER, 0.95 * inten)
    put_glow(img, sx, sy, 36 * z, mix(AMBER_HOT, (255, 255, 255), hot), min(1.0, 1.05 * inten + 0.2 * hot))
    d = ImageDraw.Draw(img, "RGBA")
    a = int(255 * clamp(inten * 1.3))
    if a > 3:
        # a coiled filament between two leads, the heart of a failing bulb
        pts = []
        for k in range(41):
            u = k / 40
            pts.append((sx + (-26 + 52 * u) * z, sy + (-4 + 9 * math.sin(u * math.pi * 7)) * z))
        lead = [(sx - 26 * z, sy - 4 * z), (sx - 30 * z, sy + 22 * z)], [(sx + 26 * z, sy - 4 * z), (sx + 30 * z, sy + 22 * z)]
        for ln in lead:
            d.line(ln, fill=AMBER + (int(a * 0.7),), width=max(1, int(2.2 * z)))
        d.line(pts, fill=mix(AMBER_HOT, (255, 255, 255), hot) + (a,), width=max(1, int(3.4 * z)), joint="curve")


# ---------------------------------------------------------------- the cell
def cell_geom(cx, cy):
    s, t = CELL_S / 2, CELL_WT
    return cx - s, cy - s, cx + s, cy + s, t


def draw_cell(d, cam, cx, cy, col, alpha, right_prog=1.0, seed=1, hatch=0.45, socket=False):
    x0, y0, x1, y1, t = cell_geom(cx, cy)
    outer = {"top": [(x0, y0), (x1, y0)], "left": [(x0, y0), (x0, y1)], "bottom": [(x0, y1), (x1, y1)], "right": [(x1, y1), (x1, y0)]}
    inner = {"top": [(x0 + t, y0 + t), (x1 - t, y0 + t)], "left": [(x0 + t, y0 + t), (x0 + t, y1 - t)],
             "bottom": [(x0 + t, y1 - t), (x1 - t, y1 - t)], "right": [(x1 - t, y1 - t), (x1 - t, y0 + t)]}
    for k in ("top", "left", "bottom", "right"):
        p = right_prog if k == "right" else 1.0
        if socket and k == "bottom":
            gap = 52
            for seg in ([(x0, y1), (cx - gap, y1)], [(cx + gap, y1), (x1, y1)]):
                stroke(d, cam, wpath(seg, seed + 11), 1.0, 3.2, col, alpha)
            for seg in ([(x0 + t, y1 - t), (cx - gap, y1 - t)], [(cx + gap, y1 - t), (x1 - t, y1 - t)]):
                stroke(d, cam, wpath(seg, seed + 12), 1.0, 2.4, col, alpha)
            continue
        stroke(d, cam, wpath(outer[k], seed + hash(k) % 97), p, 3.2, col, alpha)
        stroke(d, cam, wpath(inner[k], seed + 31 + hash(k) % 89), p, 2.4, col, alpha)
    if hatch > 0:
        h = 22
        hl = []
        for xx in np.arange(x0 + 6, x1 - 6, h):                     # top and bottom walls
            hl.append(((xx, y0 + t - 3), (xx + t - 6, y0 + 3), "top"))
            if not (socket and abs(xx - cx) < 64):
                hl.append(((xx, y1 - 3), (xx + t - 6, y1 - t + 3), "bottom"))
        for yy in np.arange(y0 + t + 6, y1 - t - 6, h):             # left and right walls
            hl.append(((x0 + 3, yy + t - 6), (x0 + t - 3, yy), "left"))
            hl.append(((x1 - t + 3, yy + t - 6), (x1 - 3, yy), "right"))
        for a, b, k in hl:
            if k == "right":
                frac = 1 - (a[1] - y0) / (y1 - y0)
                if frac > right_prog:
                    continue
            sa, sb = cam.p(*a), cam.p(*b)
            d.line((sa, sb), fill=col + (int(255 * alpha * hatch),), width=max(1, int(1.3 * cam.z)))


def door_symbol(d, cam, prog, col, alpha):
    x0, y0, x1, y1, t = cell_geom(0, 0)
    hx, hy = x0 + t, -64
    leaf = wpath([(hx, hy), (hx + 118, hy)], 41, amp=0.6)
    arc = wpath([(hx + 118 * math.cos(math.radians(a)), hy + 118 * math.sin(math.radians(a))) for a in range(0, 91, 6)], 42, amp=0.6)
    stroke(d, cam, leaf, prog * 2, 2.4, col, alpha)
    stroke(d, cam, arc, prog * 2 - 1, 2.0, col, alpha * 0.85)


def window_symbol(d, cam, prog, col, alpha):
    x0, y0, x1, y1, t = cell_geom(0, 0)
    for i, f in enumerate((0.22, 0.5, 0.78)):
        stroke(d, cam, wpath([(-78, y0 + t * f), (78, y0 + t * f)], 50 + i, amp=0.5), prog * 1.3 - i * 0.15, 2.0, col, alpha)
    for i, xx in enumerate((-78, 78)):
        stroke(d, cam, wpath([(xx, y0 - 4), (xx, y0 + t + 4)], 55 + i, amp=0.3), prog * 2 - 1, 2.0, col, alpha)


def scrawl_x(d, cam, cx, cy, r, prog, col, alpha, seed):
    a = wpath([(cx - r, cy - r * 0.9), (cx + r * 1.05, cy + r)], seed, amp=3.5, step=9)
    b = wpath([(cx + r, cy - r), (cx - r * 0.95, cy + r * 1.05)], seed + 1, amp=3.5, step=9)
    stroke(d, cam, a, prog * 2, 4.0, col, alpha)
    stroke(d, cam, b, prog * 2 - 1, 4.0, col, alpha)


def tally_groups():
    """Groups of five scratched inside the walls, in the order they are revealed."""
    x0, y0, x1, y1, t = cell_geom(0, 0)
    xi0, yi0, xi1, yi1 = x0 + t + 14, y0 + t + 14, x1 - t - 14, y1 - t - 14
    spots = []
    for row, yy in enumerate((yi0 + 4, yi0 + 52)):
        for k in range(7):
            spots.append((xi0 + 8 + k * 48 + (row * 18), yy))
    for row, yy in enumerate((yi1 - 44, yi1 - 92)):
        for k in range(7):
            spots.append((xi0 + 8 + k * 48 + (row * 12), yy))
    for k in range(3):
        spots.append((xi1 - 40, yi0 + 110 + k * 50))
    rnd = random.Random(5)
    spots = [s for s in spots if s[0] < xi1 - 34]
    rnd.shuffle(spots)
    out = []
    for i, (x, y) in enumerate(spots):
        n = 5 if i != 29 else 3
        rot = rnd.uniform(-0.12, 0.12)
        out.append((x, y, n, rot, rnd.randint(0, 9999)))
    return out


TALLIES = tally_groups()


def draw_tallies(d, cam, n_groups, col, alpha):
    for gi, (x, y, n, rot, sd) in enumerate(TALLIES[:n_groups]):
        rnd = random.Random(sd)
        c, s = math.cos(rot), math.sin(rot)
        for k in range(min(n, 4)):
            px = x + k * 7.5 + rnd.uniform(-1, 1)
            a = (px, y + rnd.uniform(-2, 2))
            b = (px + rnd.uniform(-1.5, 1.5), y + 36 + rnd.uniform(-2, 2))
            a = (x + (a[0] - x) * c - (a[1] - y) * s, y + (a[0] - x) * s + (a[1] - y) * c)
            b = (x + (b[0] - x) * c - (b[1] - y) * s, y + (b[0] - x) * s + (b[1] - y) * c)
            d.line((cam.p(*a), cam.p(*b)), fill=col + (int(255 * alpha * rnd.uniform(0.7, 1)),), width=max(1, int(2.0 * cam.z)))
        if n == 5:
            a = (x - 4, y + 30)
            b = (x + 30, y + 6)
            d.line((cam.p(*a), cam.p(*b)), fill=col + (int(255 * alpha),), width=max(1, int(2.0 * cam.z)))


# ---------------------------------------------------------------- tools (line art, local size s = width)
def tool_paths(kind, x, y, s, seed=0):
    h = s * 0.78
    x0, y0, x1, y1 = x - s / 2, y - h / 2, x + s / 2, y + h / 2
    P = []
    if kind == "folder":
        P.append(rrect_pts(x0, y0 + h * 0.16, x1, y1, s * 0.05))
        P.append([(x0 + s * 0.02, y0 + h * 0.16), (x0 + s * 0.04, y0), (x0 + s * 0.36, y0), (x0 + s * 0.44, y0 + h * 0.16)])
        P.append([(x0 + s * 0.08, y0 + h * 0.36), (x1 - s * 0.08, y0 + h * 0.36)])
    elif kind == "calendar":
        P.append(rrect_pts(x0, y0, x1, y1, s * 0.05))
        P.append([(x0, y0 + h * 0.24), (x1, y0 + h * 0.24)])
        for fx in (0.28, 0.72):
            P.append([(x0 + s * fx, y0 - h * 0.1), (x0 + s * fx, y0 + h * 0.1)])
        for r in range(3):
            for c in range(4):
                cx_, cy_ = x0 + s * (0.17 + c * 0.22), y0 + h * (0.42 + r * 0.19)
                P.append(rect_pts(cx_ - s * 0.04, cy_ - s * 0.03, cx_ + s * 0.04, cy_ + s * 0.03))
    elif kind == "code":
        P.append(rrect_pts(x0, y0, x1, y1, s * 0.05))
        P.append([(x0, y0 + h * 0.2), (x1, y0 + h * 0.2)])
        for k in range(3):
            P.append(ellipse_pts(x0 + s * (0.08 + k * 0.07), y0 + h * 0.1, s * 0.02, s * 0.02, n=10))
        P.append([(x - s * 0.2, y0 + h * 0.46), (x - s * 0.32, y0 + h * 0.6), (x - s * 0.2, y0 + h * 0.74)])
        P.append([(x + s * 0.06, y0 + h * 0.42), (x - s * 0.06, y0 + h * 0.78)])
        P.append([(x + s * 0.2, y0 + h * 0.46), (x + s * 0.32, y0 + h * 0.6), (x + s * 0.2, y0 + h * 0.74)])
    elif kind == "chat":
        P.append(rrect_pts(x0, y0, x1, y1 - h * 0.18, s * 0.12) )
        P.append([(x0 + s * 0.22, y1 - h * 0.18), (x0 + s * 0.14, y1), (x0 + s * 0.38, y1 - h * 0.18)])
        for k in range(3):
            P.append([(x0 + s * 0.16, y0 + h * (0.2 + k * 0.17)), (x0 + s * (0.84 - k * 0.18), y0 + h * (0.2 + k * 0.17))])
    elif kind == "db":
        rx, ry = s * 0.42, h * 0.13
        P.append(ellipse_pts(x, y0 + ry, rx, ry))
        P.append(ellipse_pts(x, y - h * 0.06, rx, ry, 0, 180, 24))
        P.append(ellipse_pts(x, y1 - ry, rx, ry, 0, 180, 24))
        P.append([(x - rx, y0 + ry), (x - rx, y1 - ry)])
        P.append([(x + rx, y0 + ry), (x + rx, y1 - ry)])
    return [wpath(p, seed + i * 13, amp=0.8, step=10) for i, p in enumerate(P)]


def draw_tool(d, cam, kind, x, y, s, col, alpha, prog=1.0, seed=0, width=2.6):
    for i, p in enumerate(tool_paths(kind, x, y, s, seed)):
        stroke(d, cam, p, prog * 1.6 - i * 0.06, width, col, alpha)


def gear_pts(cx, cy, r, rot, teeth=8):
    pts = []
    for k in range(teeth * 4 + 1):
        a = rot + 2 * math.pi * k / (teeth * 4)
        rr = r if (k % 4) in (0, 1) else r * 0.76
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


# ---------------------------------------------------------------- the standard plug (seen from above, prongs pointing left)
def plug_paths(x, y, scale=1.0):
    """Plug whose prong tips sit at x (the socket face). Body 112 x 66, cable leaves to the right."""
    s = scale
    bx0, bx1 = x + 26 * s, x + 138 * s
    P = [rrect_pts(bx0, y - 33 * s, bx1, y + 33 * s, 12 * s),
         rect_pts(x, y - 18 * s, x + 26 * s, y - 9 * s), rect_pts(x, y + 9 * s, x + 26 * s, y + 18 * s),
         [(bx1, y - 20 * s), (bx1 + 34 * s, y - 9 * s), (bx1 + 34 * s, y + 9 * s), (bx1, y + 20 * s)],
         [(bx0 + 24 * s, y - 33 * s), (bx0 + 24 * s, y + 33 * s)]]
    return [raw(p) for p in P], (bx1 + 34 * s, y)


def draw_plug(d, cam, x, y, col, alpha, fill=None, scale=1.0, width=2.6):
    paths, tail = plug_paths(x, y, scale)
    if fill is not None:
        body = cam.pa(rrect_pts(x + 26 * scale, y - 33 * scale, x + 138 * scale, y + 33 * scale, 12 * scale))
        d.polygon([tuple(p) for p in body], fill=fill)
    for p in paths:
        stroke(d, cam, p, 1.0, width, col, alpha, double=False)
    return tail


def socket_wall(d, cam, y, col, alpha, empty=True):
    """A socket on the outer face of the long wall: a framed opening with two slots."""
    x = WALL_X
    fr = wpath(rect_pts(x - 6, y - 40, x + 16, y + 40), int(y) % 997, amp=0.5)
    stroke(d, cam, fr, 1.0, 2.2, col, alpha)
    if empty:
        for sy in (-14, 14):
            a, b = cam.p(x + 2, y + sy), cam.p(x + 12, y + sy)
            d.line((a, b), fill=col + (int(220 * alpha),), width=max(1, int(4 * cam.z)))


# ---------------------------------------------------------------- the grid and backgrounds
_paper = None


def paper():
    global _paper
    if _paper is None:
        rng = np.random.default_rng(14)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.85)) ** 2 + ((yy - H * 0.46) / (H * 0.7)) ** 2)
        base = np.array(BLUE, np.float32) * (1 - 0.35 * np.clip(r, 0, 1)[..., None]) + np.array(BLUE_DEEP, np.float32) * 0.35 * np.clip(r, 0, 1)[..., None]
        blot = np.asarray(Image.fromarray((rng.random((H // 16, W // 16)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)
        base += ((blot - 128) / 128 * 5)[..., None]
        _paper = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    return _paper.copy()


def draw_grid(d, cam, minor_col, major_col, a_minor, a_major):
    wx0, wy0 = cam.w(0, 0)
    wx1, wy1 = cam.w(W, H)
    for stepw, col, a, wd in ((40, minor_col, a_minor, 1), (200, major_col, a_major, 1)):
        if stepw * cam.z < 9 or a <= 0:
            continue
        x = math.floor(wx0 / stepw) * stepw
        while x <= wx1:
            sx = cam.p(x, 0)[0]
            d.line((sx, 0, sx, H), fill=col + (int(255 * a),), width=wd)
            x += stepw
        y = math.floor(wy0 / stepw) * stepw
        while y <= wy1:
            sy = cam.p(0, y)[1]
            d.line((0, sy, W, sy), fill=col + (int(255 * a),), width=wd)
            y += stepw


# ---------------------------------------------------------------- the dark half
def light_level(tg):
    """The mind's brightness: a failing bulb. 0 is dead."""
    sid, t = scene_at(tg)
    n = 0.5 + 0.5 * math.sin(tg * 37.0) * math.sin(tg * 23.0 + 1.3)          # fast shimmer
    stut = 1.0 if math.sin(tg * 11.0) * math.sin(tg * 5.3 + 0.7) > -0.82 else 0.35
    if sid == "lock":
        a, b = CUE["dies"]
        if t < 0.45:
            return 0.62 + 0.05 * n
        if t < 0.95:
            return (0.62 if int(t * 22) % 3 else 0.12) + 0.05 * n
        if t < a:
            return 0.8 * stut + 0.06 * n
        if t < b:
            q = (t - a) / (b - a)
            return 0.02 + 0.3 * (1 - smooth(q * 4)) if q < 0.25 else 0.015
        if t < b + 0.35:
            return (1.0 if int((t - b) * 26) % 2 == 0 else 0.25)
        return 0.92 * stut + 0.08 * n
    if sid == "reach":
        base = 0.95
        for i, r in enumerate(CUE["reaches"]):
            if t > r + 0.36:
                base -= 0.11
        thinking = sum(math.exp(-((t - c) / 0.25) ** 2) for c in CUE["think"]) * 0.25
        dip = sum(0.55 * math.exp(-max(0, t - (r + 0.36)) * 7) for r in CUE["reaches"] if t >= r + 0.36)
        return max(0.05, base * stut + thinking - dip + 0.06 * n)
    if sid == "tangle":
        base = 0.6 * stut + 0.06 * n
        for k in CUE["taps"]:
            if t >= k:
                base -= 0.35 * math.exp(-(t - k) * 6)
        if t > CUE["hush"]:
            base *= 1 - 0.85 * smooth((t - CUE["hush"]) / 0.3)
        return max(0.04, base)
    if sid == "turn":
        w0 = CUE["socket"]
        if t < w0:
            return 0.09
        return lerp(0.09, 1.0, smooth((t - w0) / 0.6))
    return 1.0


def mind_pos(tg):
    sid, t = scene_at(tg)
    if sid == "tangle":
        back = sum(ease_out((t - k) / 0.25) for k in CUE["taps"] if t >= k)
        return (-18 * back, 6 * back)
    if sid == "turn":
        return (lerp(-54, 0, smooth(t / 1.2)), lerp(18, 0, smooth(t / 1.2)))
    return (0, 0)


def light_mask(cam, lights):
    """Per-pixel light from the minds (quarter resolution). Walls block most of it: outside a cell is dimmer."""
    gw, gh = W // 4, H // 4
    ys, xs = np.mgrid[0:gh, 0:gw].astype(np.float32)
    wx = (xs * 4 + 2 - W / 2 - cam.ox) / cam.z + cam.cx
    wy = (ys * 4 + 2 - H / 2 - cam.oy) / cam.z + cam.cy
    m = np.full((gh, gw), 0.035, np.float32)
    for (lx, ly, inten, cx, cy) in lights:
        x0, y0, x1, y1, t = cell_geom(cx, cy)
        inside = (wx > x0 + t) & (wx < x1 - t) & (wy > y0 + t) & (wy < y1 - t)
        onwall = (wx > x0 - 4) & (wx < x1 + 4) & (wy > y0 - 4) & (wy < y1 + 4) & ~inside
        dd = np.hypot(wx - lx, wy - ly)
        m += inten * np.where(inside, 1.25 * np.exp(-(dd / 255) ** 2) + 0.03,
                              np.where(onwall, 1.0 * np.exp(-(dd / 265) ** 2), 0.62 * np.exp(-(dd / 720) ** 2)))
    m = np.clip(m, 0, 1.3)
    return np.asarray(Image.fromarray((np.clip(m / 1.3, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255 * 1.3


def cable_specs():
    """Fifteen cables, one for every tool from every cell, each with its own crooked plug."""
    rnd = random.Random(21)
    out = []
    order = [(i, j) for i in range(3) for j in range(5)]
    rnd.shuffle(order)
    for k, (i, j) in enumerate(order):
        cx, cy = CELLS[i]
        _, tx, ty = TOOLS[j]
        start = (cx + (j - 2) * 34, cy + CELL_S / 2 + 2)
        end = (tx + (i - 1) * 40, ty - TOOL_S * 0.39 - 26)
        v1 = (rnd.uniform(-170, 170), 330 + rnd.uniform(-60, 50))
        v2 = (rnd.uniform(-150, 150), 430 + rnd.uniform(-60, 60))
        ctrl = [start, (start[0], start[1] + 70), v1, v2, (end[0], end[1] - 90), end]
        shape = [(rnd.uniform(-1, 1) * 14, rnd.uniform(-1, 1) * 14) for _ in range(rnd.randint(4, 7))]
        out.append(dict(i=i, j=j, ctrl=ctrl, shape=shape, phase=rnd.uniform(0, 6.3)))
    return out


CABLES = cable_specs()


def catmull(ctrl, n=90):
    P = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
    out = []
    for s in range(1, len(P) - 2):
        p0, p1, p2, p3 = (np.array(P[s + k], np.float64) for k in (-1, 0, 1, 2))
        for k in range(n // (len(P) - 3)):
            u = k / (n // (len(P) - 3))
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    out.append(np.array(P[-2], np.float64))
    return np.array(out)


_cpaths = {}


def cable_curve(k):
    if k not in _cpaths:
        arr = catmull(CABLES[k]["ctrl"], 120)
        cum = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(arr, axis=0).T))])
        nrm = np.gradient(arr, axis=0)
        nrm = np.stack([-nrm[:, 1], nrm[:, 0]], 1) / (np.hypot(nrm[:, 0], nrm[:, 1])[:, None] + 1e-9)
        _cpaths[k] = (arr, cum, nrm)
    return _cpaths[k]


def cable_state(t):
    """For the tangle scene: (head progress 0..1) per cable and how many have arrived."""
    st = []
    arrived = 0
    for k in range(len(CABLES)):
        t0 = CUE["cables_t0"] + k * CUE["cables_gap"]
        p = clamp((t - t0) / CUE["cable_dur"])
        p = 1 - (1 - p) ** 2.2
        st.append(p)
        if p >= 1:
            arrived += 1
    return st, arrived


def draw_cables(img, cam, t, tg, alpha=1.0, burn=None):
    """Living cables: the head slithers, the body undulates behind it, and they keep breathing once they arrive."""
    d = ImageDraw.Draw(img, "RGBA")
    st, _ = cable_state(t)
    for k, p in enumerate(st):
        if p <= 0:
            continue
        arr, cum, nrm = cable_curve(k)
        L = cum[-1] * p
        n = int(np.searchsorted(cum, L)) + 1
        n = max(2, min(n, len(arr)))
        s = cum[:n]
        behind = (L - s)
        env = np.exp(-behind / 260) * (1 - p ** 6) + 0.18
        ph = CABLES[k]["phase"]
        wav = (24 * np.sin(s / 64 - tg * 7.0 + ph) * env)[:, None] * nrm[:n]
        pts = arr[:n] + wav
        sp = cam.pa(pts)
        wd = max(2, int(9 * cam.z))
        if burn is not None:
            bx, by, br = burn
            dist = np.hypot(sp[:, 0] - bx, sp[:, 1] - by)
            if dist.max() < br - 10:
                continue
            step = 6
            for c0 in range(0, len(sp) - 1, step):
                seg = sp[c0:c0 + step + 1]
                if len(seg) < 2:
                    continue
                dm = dist[c0:c0 + step + 1].mean()
                hot = clamp((br + 220 - dm) / 220)
                flat = [tuple(q) for q in seg]
                d.line(flat, fill=mix(VINE, AMBER, hot) + (int(235 * alpha),), width=wd, joint="curve")
                d.line(flat, fill=mix(VINE_EDGE, AMBER_HOT, hot) + (int(150 * alpha),), width=max(1, int(2.2 * cam.z)), joint="curve")
        else:
            flat = [tuple(q) for q in sp]
            d.line(flat, fill=VINE + (int(235 * alpha),), width=wd, joint="curve")
            d.line(flat, fill=VINE_EDGE + (int(150 * alpha),), width=max(1, int(2.2 * cam.z)), joint="curve")
        hx, hy = sp[-1]
        if p < 1:
            ang = math.atan2(*(sp[-1] - sp[-2])[::-1])
        else:
            ang = math.pi / 2
        poly = []
        for (a, b) in CABLES[k]["shape"]:
            r = 12 + abs(a)
            th = math.atan2(b, a)
            poly.append((hx + math.cos(th + ang) * r * cam.z * 1.6, hy + math.sin(th + ang) * r * cam.z * 1.6))
        d.polygon(poly, fill=VINE_HEAD + (int(240 * alpha),), outline=VINE_EDGE + (int(200 * alpha),))


def tap_cable(img, cam, t, tg, alpha=1.0):
    """The one that lifts and knocks on the wall from outside."""
    t0 = CUE["taps"][0] - 1.0
    if t < t0:
        return
    rise = ease_out((t - t0) / 0.8)
    x1 = CELL_S / 2
    rest = x1 + 70
    knock = 0.0
    for k in CUE["taps"]:
        q = t - (k - 0.18)
        if 0 <= q < 0.42:
            knock = max(knock, math.sin(math.pi * clamp(q / 0.36)) if q < 0.36 else 0)
    hx = lerp(rest + 120, rest, rise) - knock * 62
    hy = lerp(330, 40, rise)
    ctrl = [(150, 430), (300, 380), (rest + 40, 220), (hx + 20, hy + 60), (hx, hy)]
    arr = catmull(ctrl, 70)
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(arr, axis=0).T))])
    nrm = np.gradient(arr, axis=0)
    nrm = np.stack([-nrm[:, 1], nrm[:, 0]], 1) / (np.hypot(nrm[:, 0], nrm[:, 1])[:, None] + 1e-9)
    env = np.clip(s / s[-1], 0, 1) ** 2
    pts = arr + (10 * np.sin(s / 50 - tg * 5) * env)[:, None] * nrm
    sp = cam.pa(pts)
    d = ImageDraw.Draw(img, "RGBA")
    flat = [tuple(q) for q in sp]
    a = alpha * rise
    d.line(flat, fill=VINE + (int(235 * a),), width=max(2, int(9 * cam.z)), joint="curve")
    d.line(flat, fill=VINE_EDGE + (int(150 * a),), width=max(1, int(2.2 * cam.z)), joint="curve")
    hx_, hy_ = sp[-1]
    r = 20 * cam.z
    poly = [(hx_ - r * 1.2, hy_ - r * 0.2), (hx_ - r * 0.3, hy_ - r), (hx_ + r * 0.9, hy_ - r * 0.6), (hx_ + r, hy_ + r * 0.7), (hx_ - r * 0.2, hy_ + r * 0.9)]
    d.polygon(poly, fill=VINE_HEAD + (int(240 * a),), outline=VINE_EDGE + (int(220 * a),))


def splash(img, cam, hx, hy, age, k):
    """A hand on glass: a palm and five fingers spreading along the wall face, then going out."""
    if age < 0 or age > 0.9:
        return
    a = (1 - smooth((age - 0.25) / 0.65)) * ease_out(age / 0.06)
    spread = ease_out(age / 0.22)
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(70 + k)
    for i in range(5):
        ang = math.radians(-160 + i * 35 + rnd.uniform(-6, 6))
        ln = (70 + rnd.uniform(-10, 18) + (20 if i == 2 else 0)) * spread
        pts = [cam.p(hx + math.cos(ang) * 10, hy + math.sin(ang) * 6)]
        for q in range(1, 5):
            u = q / 4
            pts.append(cam.p(hx + math.cos(ang) * (10 + ln * u) + rnd.uniform(-2, 2), hy + math.sin(ang) * (6 + ln * u) * 0.75))
        d.line(pts, fill=AMBER + (int(240 * a),), width=max(2, int(6 * cam.z)), joint="curve")
    sx, sy = cam.p(hx, hy - 4)
    rr = 26 * cam.z * spread
    d.ellipse((sx - rr * 1.3, sy - rr * 0.7, sx + rr * 1.3, sy + rr * 0.5), fill=AMBER + (int(150 * a),))
    put_glow(img, sx, sy, 190 * cam.z, AMBER, 0.7 * a)


def dark_frame(tg, cam, t_turn_extra=None):
    """Render the dark sheet at tg. Returns RGBA."""
    sid, t = scene_at(tg)
    I = light_level(tg)
    mx, my = mind_pos(tg)
    ink = Image.new("RGBA", (W, H), NIGHT + (255,))
    d = ImageDraw.Draw(ink, "RGBA")
    draw_grid(d, cam, NIGHT_GRID, (60, 66, 78), 0.55, 0.8)
    # our cell
    right = 1.0
    if sid == "lock":
        a, b = CUE["wall_shut"]
        right = 0.62 + 0.38 * smooth((t - a) / (b - a))
    draw_cell(d, cam, 0, 0, OLD_CHALK, 0.95, right_prog=right, hatch=0.5)
    # door and window, sketched then crossed out
    if sid == "lock":
        if t >= CUE["door"]:
            door_symbol(d, cam, ease_out((t - CUE["door"]) / 0.4), OLD_CHALK, 0.9)
            scrawl_x(d, cam, -CELL_S / 2 + 70, -10, 62, ease_out((t - CUE["door"] - 0.5) / 0.22), (230, 226, 214), 1.0, 91)
        if t >= CUE["window"]:
            window_symbol(d, cam, ease_out((t - CUE["window"]) / 0.35), OLD_CHALK, 0.9)
            scrawl_x(d, cam, 0, -CELL_S / 2 + 14, 70, ease_out((t - CUE["window"] - 0.62) / 0.22), (230, 226, 214), 1.0, 93)
    else:
        door_symbol(d, cam, 1, OLD_CHALK, 0.9)
        scrawl_x(d, cam, -CELL_S / 2 + 70, -10, 62, 1, (230, 226, 214), 1.0, 91)
        window_symbol(d, cam, 1, OLD_CHALK, 0.9)
        scrawl_x(d, cam, 0, -CELL_S / 2 + 14, 70, 1, (230, 226, 214), 1.0, 93)
    # tally marks: none before the light first dies, then more with every flicker
    n_t = 0
    if sid == "lock" and t >= CUE["dies"][1]:
        n_t = 14
    elif sid != "lock":
        n_t = 14 + 4 * sum(1 for r in CUE["reaches"] if sid != "reach" or t >= r + 0.36) + (2 if sid in ("tangle", "turn") else 0)
    draw_tallies(d, cam, n_t, (214, 208, 194), 0.95)
    # the tools out in the dark
    show_tools = [1, 2, 3] if sid in ("lock", "reach") else [0, 1, 2, 3, 4]
    for j in show_tools:
        kind, x, y = TOOLS[j]
        a = 1.0 if j in (1, 2, 3) else ease_out((t - 0.3) / 0.8) if sid == "tangle" else 1.0
        draw_tool(d, cam, kind, x, y, TOOL_S, OLD_CHALK, 0.9 * a, seed=j * 5, width=3.0)
    # the other cells (from the tangle on)
    lights = [(mx, my, I, 0, 0)]
    if sid in ("tangle", "turn"):
        side_a = ease_out((t - 0.2) / 0.9) if sid == "tangle" else 1.0
        for ci, (cx, cy) in enumerate(CELLS):
            if ci == 1:
                continue
            draw_cell(d, cam, cx, cy, OLD_CHALK, 0.9 * side_a, hatch=0.45, seed=ci * 3 + 7)
            li = (0.42 + 0.1 * math.sin(tg * (13 + ci * 4)) * math.sin(tg * 7 + ci)) * side_a
            lights.append((cx, cy, li, cx, cy))
    # light it: only what the minds can reach is visible
    arr = np.asarray(ink.convert("RGB"), np.float32)
    m = light_mask(cam, lights)
    tint = np.array([1.0, 0.86, 0.66], np.float32)
    arr = arr * m[..., None] * (0.55 + 0.45 * tint)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    # the cables are dark things that move in the dark: drawn over the light, unlit
    if sid in ("tangle", "turn"):
        tt = t if sid == "tangle" else SCENES[2][1] + t
        draw_cables(out, cam, tt, tg, alpha=1.0, burn=t_turn_extra)
        tap_cable(out, cam, tt, tg, alpha=1.0 if sid == "tangle" else 1.0)
    # emissive: the reach and the minds
    em = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if sid == "reach":
        for k, r in enumerate(CUE["reaches"]):
            age = t - r
            if age < 0 or age > 1.3:
                continue
            _, tx, ty = TOOLS[1 + k]
            hit_y = CELL_S / 2 - CELL_WT - 3
            hit_x = mx + (tx - mx) * (hit_y - my) / (ty - my)
            ext = ease_out(age / 0.36)
            fade = 1 - smooth((age - 0.5) / 0.6)
            ex, ey = lerp(mx, hit_x, ext), lerp(my, hit_y, ext)
            dd = ImageDraw.Draw(em, "RGBA")
            dd.line((cam.p(mx, my), cam.p(ex, ey)), fill=AMBER + (int(235 * fade),), width=max(2, int(7 * cam.z)))
            dd.line((cam.p(mx, my), cam.p(ex, ey)), fill=AMBER_HOT + (int(200 * fade),), width=max(1, int(2.5 * cam.z)))
            put_glow(em, *cam.p(ex, ey), 60 * cam.z, AMBER, 0.6 * fade)
            splash(em, cam, hit_x, hit_y, age - 0.36, k)
    for (lx, ly, li, cx, cy) in lights[1:]:
        orb(em, cam, lx, ly, li * 0.85, size=0.8)
    orb(em, cam, mx, my, I, size=1.0 if sid != "tangle" else 1.0 - 0.12 * sum(ease_out((t - k) / 0.3) for k in CUE["taps"] if t >= k), hot=0.0)
    gl = em.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR)
    out.alpha_composite(gl)
    out.alpha_composite(em)
    return out


# ---------------------------------------------------------------- the bright half
def bright_base(cam, grid=1.0):
    img = paper()
    d = ImageDraw.Draw(img, "RGBA")
    draw_grid(d, cam, GRID_MINOR, GRID_MAJOR, 0.16 * grid, 0.3 * grid)
    return img


def socket_cell(d, cam, glow=0.0):
    """The socket cut into the bottom wall of the cell (plan view)."""
    x0, y0, x1, y1, t = cell_geom(0, 0)
    box = wpath(rrect_pts(-50, y1 - t - 6, 50, y1 + 8, 8), 61, amp=0.5)
    stroke(d, cam, box, 1.0, 3.0, mix(CHALK, AMBER_HOT, glow), 1.0)
    for sx in (-18, 18):
        a, b = cam.p(sx, y1 - t + 3), cam.p(sx, y1 - 1)
        d.line((a, b), fill=mix(CHALK, AMBER_HOT, glow) + (255,), width=max(2, int(5 * cam.z)))


def title_block(img, cam, prog, alpha=1.0):
    """Patent title block under the cell: a drawing of the standard plug on the left, the name on the right."""
    if prog <= 0:
        return
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = TITLE
    w, h = 700, 210
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    stroke(d, cam, wpath(rect_pts(x0, y0, x1, y1), 70, amp=0.6), ease_out(prog / 0.45), 3.0, CHALK, alpha)
    stroke(d, cam, wpath([(x0 + 200, y0), (x0 + 200, y1)], 71, amp=0.5), ease_out((prog - 0.3) / 0.25), 2.4, CHALK, alpha)
    stroke(d, cam, wpath([(x0 + 200, cy + 22), (x1, cy + 22)], 72, amp=0.5), ease_out((prog - 0.38) / 0.25), 2.0, CHALK_SOFT, alpha)
    pa = ease_out((prog - 0.45) / 0.3)
    if pa > 0:
        draw_plug(d, cam, x0 + 34, cy, CHALK, alpha * pa, scale=0.86, width=2.6)
    ta = ease_out((prog - 0.55) / 0.3)
    t1 = text_world(img, cam, x0 + 232, cy - 40, "MCP", 92, CHALK, alpha * ta, "title MCP", "Inter-Bold.otf", "lm", "headline")
    t2 = text_world(img, cam, x0 + 234, cy + 62, "Model Context Protocol", 38, CHALK_SOFT, alpha * ta, "title name", "Inter-Medium.otf", "lm", "headline")
    if REC is not None and t1 and t2 and alpha * ta > 0.5:
        REC[:] = [e for e in REC if e["name"] not in ("title MCP", "title name")]
        record_block("title block", "MCP: Model Context Protocol", ["MCP", "Model Context Protocol"],
                     (min(t1[0], t2[0]), t1[1], max(t1[2], t2[2]), t2[3]), role="headline")


def fig_label(img, cam, x, y, s, alpha):
    text_world(img, cam, x, y, s, 30, CHALK_SOFT, alpha, s, "Inter-SemiBold.otf", "lm", "body")


def bright_cell_scene(img, cam, glow=0.0, title=0.0, fig=0.0):
    d = ImageDraw.Draw(img, "RGBA")
    draw_cell(d, cam, 0, 0, CHALK, 1.0, hatch=0.42, socket=True)
    door_symbol(d, cam, 1, CHALK_SOFT, 0.55)
    window_symbol(d, cam, 1, CHALK_SOFT, 0.55)
    socket_cell(d, cam, glow)
    title_block(img, cam, title)
    if fig > 0:
        fig_label(img, cam, -CELL_S / 2, -CELL_S / 2 - 52, "FIG. 1", fig)


# ---------------------------------------------------------------- FIG. 2: three panels
def panel_frame(img, cam, k, prog, alpha=1.0):
    px, py = PANELS[k]
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = px - PANEL_W / 2, py - PANEL_H / 2, px + PANEL_W / 2, py + PANEL_H / 2
    stroke(d, cam, wpath(rrect_pts(x0, y0, x1, y1, 18), 80 + k, amp=0.7), prog, 2.6, CHALK_SOFT, alpha)
    return x0, y0


def panel_title(img, cam, k, title_a, num_a=1.0):
    px, py = PANELS[k]
    x0, y0 = px - PANEL_W / 2, py - PANEL_H / 2
    titles = ["The menu", "The ask", "The answer"]
    sx, sy = cam.p(x0 + 40, y0 + 50)
    f = font("Inter-Bold.otf", 52 * cam.z)
    num = f"{k + 1}."
    d = ImageDraw.Draw(img, "RGBA")
    if num_a > 0.01:
        d.text((sx, sy), num, font=f, fill=AMBER + (int(255 * num_a),), anchor="lm")
        nb = d.textbbox((sx, sy), num, font=f, anchor="lm")
        nx = nb[2] + 16 * cam.z
        box = nb
        if title_a > 0.01:
            d.text((nx, sy), titles[k], font=f, fill=CHALK + (int(255 * title_a),), anchor="lm")
            tb = d.textbbox((nx, sy), titles[k], font=f, anchor="lm")
            box = (nb[0], min(nb[1], tb[1]), tb[2], max(nb[3], tb[3]))
            if title_a > 0.5:
                record_block(f"panel {k + 1} title", f"{num} {titles[k]}", [f"{num} {titles[k]}"], box, "headline")
        elif num_a > 0.5:
            record_block(f"panel {k + 1} number", num, [num], box, "headline")


ROOM_P = (-290, 120)      # inside each panel, relative to its centre
TOOL_P = (330, 120)
CARD_P = (20, -40)
MENU = ["read a file", "search files", "save a file"]


def panel_room(d, img, cam, px, py, prog, mind=1.0, mind_hot=0.0, plugged=1.0, seed=0):
    rx, ry = px + ROOM_P[0], py + ROOM_P[1]
    s = 118
    stroke(d, cam, wpath(rect_pts(rx - s, ry - s, rx + s, ry + s), 90 + seed, amp=0.7), prog, 3.0, CHALK, 1.0)
    stroke(d, cam, wpath(rect_pts(rx - s + 16, ry - s + 16, rx + s - 16, ry + s - 16), 91 + seed, amp=0.6), prog, 2.0, CHALK_SOFT, 0.8)
    # socket on its right wall
    sxw = rx + s
    stroke(d, cam, wpath(rect_pts(sxw - 18, ry - 30, sxw + 4, ry + 30), 92 + seed, amp=0.4), ease_out((prog - 0.6) / 0.4), 2.4, CHALK, 1.0)
    if mind > 0:
        orb(img, cam, rx - 10, ry, mind * ease_out((prog - 0.3) / 0.5), size=0.55, hot=mind_hot)
    return (sxw + 4, ry)


def panel_tool(d, cam, px, py, prog, gear_rot=None, seed=0):
    tx, ty = px + TOOL_P[0], py + TOOL_P[1]
    draw_tool(d, cam, "folder", tx, ty, 210, CHALK, 1.0, prog, seed=40 + seed, width=2.8)
    if gear_rot is not None:
        stroke(d, cam, raw(gear_pts(tx + 58, ty + 34, 34, gear_rot)), 1.0, 2.6, AMBER, 1.0, double=False)
        stroke(d, cam, raw(ellipse_pts(tx + 58, ty + 34, 11, 11, n=16)), 1.0, 2.4, AMBER, 1.0, double=False)
    return (tx - 105, ty)


def cable_between(d, cam, a, b, prog=1.0, col=CHALK, width=4.0):
    """A cable from the plug tail at a to the tool at b, with a soft sag."""
    pts = []
    for k in range(25):
        u = k / 24
        pts.append((lerp(a[0], b[0], u), lerp(a[1], b[1], u) + 26 * math.sin(math.pi * u)))
    stroke(d, cam, raw(pts), prog, width, col, 1.0, double=False)
    return pts


def menu_card(img, cam, px, py, drop=1.0, hl=None, hl_a=0.0, scan=None, alpha=1.0):
    """The menu card hangs from a nail on two strings; it swings in from above and settles."""
    if drop <= 0:
        return
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = px + CARD_P[0], py + CARD_P[1]
    nail = (cx, cy - 150)
    sw = math.sin(drop * 9) * math.exp(-drop * 4) * 0.22 if drop < 1 else 0
    yoff = (1 - spring(drop)) * -140
    w, h = 320, 190
    ang = sw
    def rot(x, y):
        dx, dy = x - nail[0], y - nail[1]
        return (nail[0] + dx * math.cos(ang) - dy * math.sin(ang), nail[1] + dx * math.sin(ang) + dy * math.cos(ang) + yoff)
    corners = [rot(cx - w / 2, cy - h / 2), rot(cx + w / 2, cy - h / 2), rot(cx + w / 2, cy + h / 2), rot(cx - w / 2, cy + h / 2)]
    sc = [cam.p(*c) for c in corners]
    d.polygon(sc, fill=(255, 255, 255, int(34 * alpha)))
    d.line(sc + [sc[0]], fill=CHALK + (int(255 * alpha),), width=max(2, int(2.8 * cam.z)), joint="curve")
    n = cam.p(nail[0], nail[1] + yoff)
    for c in (corners[0], corners[1]):
        d.line((n, cam.p(*c)), fill=CHALK_SOFT + (int(200 * alpha),), width=max(1, int(1.8 * cam.z)))
    d.ellipse((n[0] - 6 * cam.z, n[1] - 6 * cam.z, n[0] + 6 * cam.z, n[1] + 6 * cam.z), fill=CHALK + (int(255 * alpha),))
    f = font("Inter-Medium.otf", 36 * cam.z)
    boxes = []
    for i, line in enumerate(MENU):
        lx, ly = rot(cx - w / 2 + 52, cy - h / 2 + 42 + i * 52)
        sx, sy = cam.p(lx, ly)
        if hl == i and hl_a > 0:
            bx0, by0 = cam.p(*rot(cx - w / 2 + 14, cy - h / 2 + 20 + i * 52))
            bx1, by1 = cam.p(*rot(cx + w / 2 - 14, cy - h / 2 + 64 + i * 52))
            d.rounded_rectangle((bx0, by0, bx1, by1), radius=8 * cam.z, fill=AMBER + (int(70 * hl_a),), outline=AMBER + (int(255 * hl_a),), width=max(1, int(2.4 * cam.z)))
        col = mix(CHALK, AMBER_HOT, hl_a if hl == i else 0)
        bsx, bsy = cam.p(*rot(cx - w / 2 + 30, cy - h / 2 + 42 + i * 52))
        d.rectangle((bsx - 6 * cam.z, bsy - 6 * cam.z, bsx + 6 * cam.z, bsy + 6 * cam.z), outline=col + (int(255 * alpha),), width=max(1, int(2 * cam.z)))
        d.text((sx, sy), line, font=f, fill=col + (int(255 * alpha),), anchor="lm")
        boxes.append(d.textbbox((sx, sy), line, font=f, anchor="lm"))
    if scan is not None and 0 <= scan <= 1:
        yy = cy - h / 2 + 22 + scan * (h - 44)
        a_, b_ = cam.p(*rot(cx - w / 2 + 10, yy)), cam.p(*rot(cx + w / 2 - 10, yy))
        d.line((a_, b_), fill=AMBER + (220,), width=max(2, int(3 * cam.z)))
        put_glow(img, (a_[0] + b_[0]) / 2, a_[1], 90 * cam.z, AMBER, 0.45)
    if boxes and alpha > 0.5 and drop >= 0.95:
        record_block("menu card", " ".join(MENU), MENU, (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)))
    return cam.p(cx - w / 2, cy)


def panel_contents(img, cam, k, t, build, state):
    """state: plug (0..1 travel), card drop, highlight, scan, pulse, gear, page."""
    px, py = PANELS[k]
    d = ImageDraw.Draw(img, "RGBA")
    sock = panel_room(d, img, cam, px, py, build, mind=1.0, mind_hot=state.get("hot", 0.0), seed=k * 3)
    tl = panel_tool(d, cam, px, py, build, state.get("gear"), seed=k)
    plug_t = state.get("plug", 1.0)
    if build > 0.5 and plug_t >= 0:
        u = ease_io(plug_t)
        hx = lerp(tl[0] - 200, sock[0], u)
        tail = draw_plug(d, cam, hx, sock[1], CHALK, ease_out((build - 0.5) / 0.3), fill=BLUE + (255,), scale=0.72, width=2.4)
        cable_between(d, cam, tail, tl, 1.0, CHALK, 4.2)
    menu_card(img, cam, px, py, state.get("card", 1.0), state.get("hl"), state.get("hl_a", 0.0), state.get("scan"))
    if "pulse" in state and 0 <= state["pulse"] <= 1:
        u = state["pulse"]
        x = lerp(sock[0] + 100, tl[0], u)
        y = sock[1] + 26 * math.sin(math.pi * clamp((x - sock[0] - 100) / (tl[0] - sock[0] - 100)))
        sx, sy = cam.p(x, y)
        put_glow(img, sx, sy, 70 * cam.z, AMBER, 0.9)
        dd = ImageDraw.Draw(img, "RGBA")
        dd.ellipse((sx - 9 * cam.z, sy - 9 * cam.z, sx + 9 * cam.z, sy + 9 * cam.z), fill=AMBER_HOT + (255,))
    if "page" in state and state["page"] is not None and 0 <= state["page"] <= 1.2:
        u = state["page"]
        rx, ry = px + ROOM_P[0], py + ROOM_P[1]
        if u <= 1:
            x = lerp(tl[0], sock[0] - 30, ease_io(u))
            y = sock[1] + 26 * math.sin(math.pi * clamp((x - sock[0] - 100) / (tl[0] - sock[0] - 100))) - 44
        else:
            q = (u - 1) / 0.2
            x, y = lerp(sock[0] - 30, rx + 40, q), lerp(sock[1] - 44, ry - 40, q)
        pw, ph = 46, 58
        dd = ImageDraw.Draw(img, "RGBA")
        poly = [cam.p(x - pw / 2, y - ph / 2), cam.p(x + pw / 2, y - ph / 2), cam.p(x + pw / 2, y + ph / 2), cam.p(x - pw / 2, y + ph / 2)]
        dd.polygon(poly, fill=AMBER_HOT + (230,), outline=AMBER + (255,))
        for i in range(3):
            a, b = cam.p(x - pw / 2 + 9, y - ph / 2 + 14 + i * 13), cam.p(x + pw / 2 - 9 - (i == 2) * 12, y - ph / 2 + 14 + i * 13)
            dd.line((a, b), fill=(170, 110, 30, 255), width=max(1, int(3 * cam.z)))
        put_glow(img, *cam.p(x, y), 80 * cam.z, AMBER, 0.5)


def panels_scene(img, cam, sid, t):
    """Everything on FIG. 2 at this moment (all three panels, in whatever state they are in)."""
    global DIM
    tgn = START[sid] + t
    base_img = img
    layers = [Image.new("RGBA", (W, H), (0, 0, 0, 0)) for _ in range(3)]
    focus = []
    for k in range(3):
        dist = abs(cam.cy - PANELS[k][1])
        f = 0.28 + 0.72 * smooth(1 - dist / 420)
        focus.append(lerp(1.0, f, smooth((cam.z - 0.62) / 0.3)))
    for k in range(3):
        fr = 1.0 if tgn >= START["how"] + 0.6 else ease_out((tgn - START["how"] - 0.2) / 0.5)
        panel_frame(layers[k], cam, k, fr)
    # build state per panel from the global clock
    menu_t = tgn - START["menu"]
    ask_t = tgn - START["ask"]
    ans_t = tgn - START["answer"]
    num_a = ease_out((tgn - START["how"] - 0.5) / 0.4)
    # panel 1
    DIM = focus[0]
    if menu_t >= 0:
        b = ease_out((menu_t - 0.35) / 0.8)
        pa, pd = CUE["menu_plug"]
        st = dict(plug=clamp((menu_t - pa) / pd), card=clamp((menu_t - CUE["menu_card"]) / 0.9))
        panel_contents(layers[0], cam, 0, menu_t, b, st)
        panel_title(layers[0], cam, 0, ease_out((menu_t - 0.55) / 0.4), num_a)
    else:
        panel_title(layers[0], cam, 0, 0.0, num_a)
    # panel 2
    DIM = focus[1]
    if ask_t >= 0:
        b = ease_out((ask_t - 0.2) / 0.55)
        a0, ad = CUE["ask_scan"]
        scan = (ask_t - a0) / ad if a0 <= ask_t <= a0 + ad else None
        hl_a = ease_out((ask_t - CUE["ask_pick"]) / 0.25)
        p0, pd = CUE["ask_pulse"]
        st = dict(plug=1.0, card=1.0, scan=scan, hl=1, hl_a=hl_a, hot=0.6 * win(ask_t, a0, a0 + ad, 0.2, 0.3))
        if p0 <= ask_t <= p0 + pd:
            st["pulse"] = ease_io((ask_t - p0) / pd)
        panel_contents(layers[1], cam, 1, ask_t, b, st)
        panel_title(layers[1], cam, 1, ease_out((ask_t - 0.45) / 0.4), num_a)
        if scan is not None:
            rx, ry = PANELS[1][0] + ROOM_P[0] - 10, PANELS[1][1] + ROOM_P[1]
            cx_, cy_ = PANELS[1][0] + CARD_P[0] - 150, PANELS[1][1] + CARD_P[1] - 70 + scan * 140
            dd = ImageDraw.Draw(layers[1], "RGBA")
            dd.line((cam.p(rx, ry), cam.p(cx_, cy_)), fill=AMBER + (150,), width=max(1, int(2.5 * cam.z)))
    else:
        panel_title(layers[1], cam, 1, 0.0, num_a)
    # panel 3
    DIM = focus[2]
    if ans_t >= 0:
        b = ease_out((ans_t - 0.2) / 0.5)
        g0, gd = CUE["gear"]
        p0, pd = CUE["page"]
        gear = 2 * math.pi * ease_io((ans_t - g0) / gd) if ans_t >= g0 - 0.3 else None
        page = (ans_t - p0) / pd if ans_t >= p0 else None
        hot = 0.8 * math.exp(-max(0, ans_t - (p0 + pd * 1.2)) * 2.5) if ans_t >= p0 + pd * 1.2 else 0.0
        st = dict(plug=1.0, card=1.0, hl=1, hl_a=0.55, gear=gear, page=page if page is not None and page <= 1.2 else None, hot=hot)
        panel_contents(layers[2], cam, 2, ans_t, b, st)
        panel_title(layers[2], cam, 2, ease_out((ans_t - 0.45) / 0.4), num_a)
    else:
        panel_title(layers[2], cam, 2, 0.0, num_a)
    DIM = 1.0
    for k in range(3):
        L = layers[k]
        if focus[k] < 0.999:
            L.putalpha(L.split()[3].point(lambda v, f=focus[k]: int(v * f)))
        base_img.alpha_composite(L)
    # header over the panels (seen in the overview)
    ha = win(tgn, START["how"] + 0.5, START["menu"] + 0.3, 0.4, 0.4)
    if ha > 0:
        text_world(img, cam, 0, PANELS[0][1] - PANEL_H / 2 - 170, "How it works", 124, CHALK, ha, "how it works", "Inter-Bold.otf", "mm", "headline")
        fig_label(img, cam, PANELS[0][0] + PANEL_W / 2 - 140, PANELS[0][1] - PANEL_H / 2 + 50, "FIG. 2", ha)


# ---------------------------------------------------------------- FIG. 3: the wall of sockets
def more_plugs():
    rnd = random.Random(33)
    named = {y for _, _, y in NAMED} | {DANDY_Y}
    cand = [y for y in SOCKETS if y not in named]
    rnd.shuffle(cand)
    keep_empty = set(cand[-6:])
    fill = [y for y in cand if y not in keep_empty]
    a, d = CUE["more_fill"]
    return [(y, a + d * (i / len(fill)) ** 0.8 + rnd.uniform(-0.05, 0.05), rnd.randint(0, 9999)) for i, y in enumerate(fill)]


MORE = more_plugs()


def dive(tail, y, sag, drop=78):
    """A cable that drops away from the plug and runs off to the right under the label."""
    pts = []
    for k in range(9):
        u = k / 8
        pts.append((tail[0] + 46 * math.sin(u * math.pi / 2), y + drop * (1 - math.cos(u * math.pi / 2))))
    x0 = pts[-1][0]
    for k in range(1, 21):
        u = k / 20
        pts.append((x0 + 900 * u, y + drop + sag * math.sin(math.pi * u / 2)))
    return pts


def plug_in(d, cam, y, u, col, alpha, fill=BLUE + (255,), cable_col=None, width=2.6, seed=0):
    """A plug travelling in from the right; u=1 is seated. Returns the plug tail position."""
    x = lerp(WALL_X + 16 + 620, WALL_X + 16, ease_out(u))
    tail = draw_plug(d, cam, x, y, col, alpha, fill=fill, scale=0.9, width=width)
    cc = cable_col or col
    rnd = random.Random(seed)
    sag = rnd.uniform(30, 70)
    stroke(d, cam, raw(dive(tail, y, sag * 0.5)), 1.0, 4.4, cc, alpha, double=False)
    return tail


def wall_scene(img, cam, sid, t):
    tgn = START[sid] + t
    d = ImageDraw.Draw(img, "RGBA")
    # the long wall: drawn top to bottom as the camera arrives, then it is simply there
    prog = ease_out((tgn - START["plugq"] - 0.15) / 1.1)
    top, bot = SOCKETS[0] - 300, SOCKETS[-1] + 300
    mid = 2800
    for k, xx in enumerate((WALL_X, WALL_X - 30)):
        stroke(d, cam, wpath([(xx, mid), (xx, top)], 200 + k, amp=0.8, step=30), prog, 3.2 if k == 0 else 2.4, CHALK, 1.0)
        stroke(d, cam, wpath([(xx, mid), (xx, bot)], 210 + k, amp=0.8, step=30), prog, 3.2 if k == 0 else 2.4, CHALK, 1.0)
    # hatch in the wall
    wy0, wy1 = cam.w(0, 0)[1], cam.w(0, H)[1]
    reach = (bot - mid) * prog
    for yy in np.arange(math.floor(wy0 / 24) * 24, wy1 + 24, 24):
        if abs(yy - mid) > reach:
            continue
        a, b = cam.p(WALL_X - 27, yy + 24), cam.p(WALL_X - 3, yy)
        d.line((a, b), fill=CHALK + (100,), width=max(1, int(1.2 * cam.z)))
    # the mind in its room
    orb(img, cam, *ROOM_MIND, 1.0, size=0.9, hot=state_hot(sid, t))
    # sockets
    for y in SOCKETS:
        if abs(y - mid) <= reach and wy0 - 100 < y < wy1 + 100:
            socket_wall(d, cam, y, CHALK, 1.0)
    # the five named plugs
    tools_t = tgn - START["tools"]
    labels = []
    for i, (name, desc, y) in enumerate(NAMED):
        at = CUE["plugs"][i]
        if tools_t < at:
            continue
        u = clamp((tools_t - at) / 0.55)
        plug_in(d, cam, y, u, CHALK, 1.0, seed=i)
        if u >= 1:
            age = tools_t - at - 0.55
            if age < 0.6:
                put_glow(img, *cam.p(WALL_X + 6, y), 70 * cam.z, AMBER, 0.8 * (1 - age / 0.6))
            # a little current runs into the room
            q = (tools_t - at - 0.55) / 0.7
            if 0 <= q <= 1:
                x = lerp(WALL_X - 40, ROOM_MIND[0] + 40, ease_io(q))
                yy_ = lerp(y, ROOM_MIND[1], ease_io(q))
                put_glow(img, *cam.p(x, yy_), 50 * cam.z, AMBER, 0.9 * (1 - q * 0.6))
        nxt = CUE["plugs"][i + 1] if i + 1 < len(NAMED) else 1e9
        cur = tools_t < nxt + 0.2
        la = ease_out((tools_t - at - 0.35) / 0.35)
        if la > 0:
            labels.append((name, desc, y, la, cur and sid == "tools", ease_out((tools_t - at - 0.55) / 0.35) * (1 - ease_out((tools_t - nxt) / 0.3))))
    # thousands more
    more_t = tgn - START["more"]
    for y, at, sd in MORE:
        if more_t < at:
            continue
        u = clamp((more_t - at) / 0.35)
        if not (wy0 - 200 < y < wy1 + 200):
            continue
        plug_in(d, cam, y, u, CHALK_SOFT, 0.9, seed=sd)
        rnd = random.Random(sd)
        if u >= 1:
            for b in range(2):
                bx0 = WALL_X + 236
                bw = rnd.uniform(140, 260) * (0.6 if b else 1)
                a_, b_ = cam.p(bx0, y - 16 + b * 30), cam.p(bx0 + bw, y - 16 + b * 30)
                d.line((a_, b_), fill=CHALK_SOFT + (int(170 * ease_out(more_t - at - 0.35)),), width=max(1, int(10 * cam.z * (0.8 if b else 1))))
    # labels for the named five
    back = 1 - 0.65 * smooth((tgn - START["more"]) / 0.9)
    for name, desc, y, la, cur, da in labels:
        la *= back
        da *= back
        nx = WALL_X + 236
        nb = text_world(img, cam, nx, y - (16 if da > 0.02 else 0), name, 50, CHALK if cur else mix(CHALK, CHALK_SOFT, 0.5), la, f"label {name}", "Inter-Bold.otf", "lm", "body")
        if da > 0.02:
            db = text_world(img, cam, nx + 2, y + 34, desc, 34, AMBER_HOT, da, f"desc {name}", "Inter-Medium.otf", "lm", "body")
            if REC is not None and nb and db and la > 0.5 and da > 0.5:
                REC[:] = [e for e in REC if e["name"] not in (f"label {name}", f"desc {name}")]
                record_block(f"label {name}", f"{name} {desc}", [name, desc], (nb[0], nb[1], max(nb[2], db[2]), db[3]))
    fa = ease_out((tgn - START["plugq"] - 0.8) / 0.5) * back
    fig_label(img, cam, WALL_X + 40, NAMED[0][2] - 150, "FIG. 3", fa)


def state_hot(sid, t):
    if sid == "tools":
        return max([math.exp(-max(0, t - (at + 1.25)) * 3) * 0.7 if t >= at + 1.2 else 0 for at in CUE["plugs"]] + [0])
    return 0.0


# ---------------------------------------------------------------- Dandy
MAP_NODES = [(2435, 3235), (2210, 3150), (2210, 3330), (2435, 3420), (2210, 3510)]
MAP_EDGES = [(0, 1), (0, 2), (3, 2), (3, 4), (2, 4)]


def dandy_scene(img, cam, t):
    d = ImageDraw.Draw(img, "RGBA")
    p0, pd = CUE["dandy_plug"]
    if t >= p0:
        u = clamp((t - p0) / pd)
        x = lerp(WALL_X + 16 + 620, WALL_X + 16, ease_out(u))
        tail = draw_plug(d, cam, x, DANDY_Y, PURPLE_LIGHT, 1.0, fill=PURPLE_DEEP + (255,), scale=0.9, width=2.8)
        stroke(d, cam, raw(dive(tail, DANDY_Y, 20)), 1.0, 5.0, PURPLE, 1.0, double=False)
        if u >= 1:
            age = t - p0 - pd
            put_glow(img, *cam.p(WALL_X + 6, DANDY_Y), 160 * cam.z, PURPLE, 0.85 * math.exp(-age * 1.2) + 0.25)
    la = ease_out((t - CUE["dandy_label"]) / 0.4)
    if la > 0:
        text_world(img, cam, WALL_X + 236, DANDY_Y - 8, "Dandy", 58, CHALK, la, "label Dandy", "Inter-Bold.otf", "lm", "body")
    # the map unfolds into the room
    m0, md = CUE["map"]
    mt = (t - m0) / md
    if mt > 0:
        src = (WALL_X - 40, DANDY_Y)
        for k, (a, b) in enumerate([(None, 0), (None, 3)] + MAP_EDGES):
            pa_ = src if a is None else MAP_NODES[a]
            pb_ = MAP_NODES[b]
            q = ease_out((mt - 0.08 * k) / 0.35)
            if q > 0:
                ex, ey = lerp(pa_[0], pb_[0], q), lerp(pa_[1], pb_[1], q)
                d.line((cam.p(*pa_), cam.p(ex, ey)), fill=CHALK + (int(220 * q),), width=max(1, int(2.6 * cam.z)))
        for k, (nx, ny) in enumerate(MAP_NODES):
            q = spring(clamp((mt - 0.15 - 0.1 * k) / 0.45))
            if q <= 0:
                continue
            w_, h_ = 150 * q, 76 * q
            box = (cam.p(nx - w_ / 2, ny - h_ / 2), cam.p(nx + w_ / 2, ny + h_ / 2))
            d.rounded_rectangle((box[0][0], box[0][1], box[1][0], box[1][1]), radius=12 * cam.z, fill=BLUE_DEEP + (255,), outline=CHALK + (255,), width=max(2, int(2.6 * cam.z)))
            if q > 0.9:
                for b in range(2):
                    a_, b_ = cam.p(nx - 50, ny - 12 + b * 22), cam.p(nx + (30 if b == 0 else 4), ny - 12 + b * 22)
                    d.line((a_, b_), fill=CHALK_SOFT + (220,), width=max(1, int(7 * cam.z)))
                dx, dy = cam.p(nx + 52, ny - 14)
                live = (k == 4)
                col = AMBER if live else CHALK
                r = 8 * cam.z * (1 + (0.25 * math.sin(t * 6) if live else 0))
                d.ellipse((dx - r, dy - r, dx + r, dy + r), fill=col + (255,))
                if live:
                    put_glow(img, dx, dy, 46 * cam.z, AMBER, 0.6)
    # light in every corner
    l0, ld = CUE["light"]
    lt = smooth((t - l0) / ld)
    if lt > 0:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        wx_ = cam.p(WALL_X - 32, 0)[0]
        gd.rectangle((0, 0, wx_, H), fill=(255, 236, 200, int(46 * lt)))
        glow = glow.filter(ImageFilter.GaussianBlur(40))
        img.alpha_composite(glow)
        put_glow(img, *cam.p(*ROOM_MIND), 520 * cam.z * lt, AMBER, 0.35 * lt)


# ---------------------------------------------------------------- frame assembly
def bright_frame(tg, cam):
    sid, t = scene_at(tg)
    img = bright_base(cam)
    if tg < START["plugq"] + 2 or True:
        glow = 0.0
        if sid == "turn":
            glow = 1 - smooth((t - CUE["wash"][0] - CUE["wash"][1]) / 1.5)
        title = 0.0
        if sid == "turn":
            a, dur = CUE["title"]
            title = clamp((t - a) / dur)
        elif tg >= START["how"]:
            title = 1.0
        bright_cell_scene(img, cam, glow=glow, title=title, fig=ease_out((tg - START["turn"] - CUE["title"][0] - 1.0) / 0.5))
        mx, my = mind_pos(tg)
        orb(img, cam, mx, my, light_level(tg) if sid == "turn" else 1.0, size=1.0)
        if sid == "turn":
            # light pouring out of the socket
            g = clamp(glow)
            if g > 0:
                sx, sy = cam.p(0, CELL_S / 2)
                beam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                bd = ImageDraw.Draw(beam)
                L = 900 * cam.z
                bd.polygon([(sx - 40 * cam.z, sy), (sx + 40 * cam.z, sy), (sx + 360 * cam.z, sy + L), (sx - 360 * cam.z, sy + L)], fill=AMBER_HOT + (int(70 * g),))
                beam = beam.filter(ImageFilter.GaussianBlur(30))
                img.alpha_composite(beam)
                put_glow(img, sx, sy, 160 * cam.z, AMBER_HOT, 0.9 * g)
    if tg >= START["how"] - 0.5:
        panels_scene(img, cam, sid, t)
    if tg >= START["plugq"] - 0.5:
        wall_scene(img, cam, sid, t)
    if sid == "dandy" or sid == "end":
        dandy_scene(img, cam, t if sid == "dandy" else SCENES[-2][1] + t)
    return img


def turn_frame(tg, cam):
    """The wash: blueprint light spreads out of the socket over the dark sheet."""
    sid, t = scene_at(tg)
    a, dur = CUE["wash"]
    u = (t - a) / dur
    sx, sy = cam.p(0, CELL_S / 2)
    if u <= 0:
        dk = dark_frame(tg, cam)
        if t >= CUE["socket"]:
            # the socket is cut: a crack of white light in the wall
            q = ease_out((t - CUE["socket"]) / 0.12)
            dd = ImageDraw.Draw(dk, "RGBA")
            x0, y0, x1, y1, tt = cell_geom(0, 0)
            box = [cam.p(-50, y1 - tt - 6), cam.p(50, y1 + 8)]
            dd.rounded_rectangle((box[0][0], box[0][1], box[1][0], box[1][1]), radius=8 * cam.z, outline=AMBER_HOT + (int(255 * q),), width=max(2, int(4 * cam.z)))
            put_glow(dk, sx, sy, 200 * cam.z * q, AMBER_HOT, 0.9 * q)
        return dk
    if u >= 1:
        return bright_frame(tg, cam)
    r = (ease_in(u) * 0.35 + ease_io(u) * 0.65) * 2300
    dk = dark_frame(tg, cam, t_turn_extra=(sx, sy, r))
    br = bright_frame(tg, cam)
    yy, xx = np.ogrid[0:H, 0:W]
    dist = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2).astype(np.float32)
    edge = 90.0
    m = np.clip((r - dist) / edge + 0.5, 0, 1)
    out = (np.asarray(br, np.float32) * m[..., None] + np.asarray(dk, np.float32) * (1 - m[..., None]))
    ring = np.exp(-((dist - r) / 70) ** 2) * (1 - u) ** 0.7
    out[..., :3] += ring[..., None] * np.array(AMBER_HOT, np.float32) * 0.85
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
    # embers where the tangle burns
    rnd = random.Random(int(tg * 30))
    dd = ImageDraw.Draw(img, "RGBA")
    for _ in range(int(90 * (1 - u))):
        ang = rnd.uniform(0, 6.283)
        rr = r + rnd.uniform(-30, 60)
        ex, ey = sx + math.cos(ang) * rr, sy + math.sin(ang) * rr
        if 0 <= ex < W and 0 <= ey < H:
            s = rnd.uniform(1.5, 4)
            dd.ellipse((ex - s, ey - s, ex + s, ey + s), fill=AMBER_HOT + (rnd.randint(120, 255),))
    return img


DROPOUTS = None


def dropouts():
    S = START
    return [(S["lock"] + CUE["cutout"], 0.14), (S["tangle"] + 0.02, 0.1), (S["tangle"] + CUE["taps"][2] + 0.05, 0.07)]


def found_footage(img, tg):
    """Cut-outs and tears: a few frames where the picture drops out."""
    for t0, dur in dropouts():
        k = tg - t0
        if -1 / FPS <= k < 0:      # a tear just before the cut
            arr = np.asarray(img).copy()
            rnd = np.random.default_rng(int(tg * 1000))
            for _ in range(4):
                y0 = int(rnd.integers(0, H - 80))
                hgt = int(rnd.integers(20, 80))
                arr[y0:y0 + hgt] = np.roll(arr[y0:y0 + hgt], int(rnd.integers(-60, 60)), axis=1)
            return Image.fromarray(arr)
        if 0 <= k < dur:
            arr = np.zeros((H, W, 4), np.uint8)
            arr[..., 3] = 255
            rnd = np.random.default_rng(int(tg * 1000) + 3)
            noise = (rnd.random((H // 6, W // 6)) * 30).astype(np.uint8)
            n = np.asarray(Image.fromarray(noise).resize((W, H), Image.NEAREST))
            arr[..., 0] = n
            arr[..., 1] = n
            arr[..., 2] = (n * 1.1).clip(0, 255).astype(np.uint8)
            y0 = int(rnd.integers(0, H))
            arr[y0:y0 + 3, :, :3] = 90
            return Image.fromarray(arr)
    return img


def chroma(img, amt):
    if amt <= 0:
        return img
    arr = np.asarray(img).copy()
    s = int(round(2 * amt))
    if s:
        arr[..., 0] = np.roll(arr[..., 0], s, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -s, axis=1)
    return Image.fromarray(arr)


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


def caption_layout(text):
    fnt = font("Inter-Bold.otf", int(CONTRACT["type"]["vertical"]["body"] * 0.92))
    d = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    words, maxw = text.split(), SAFE[2] - SAFE[0] - 40
    if d.textlength(text, font=fnt) <= maxw:
        lines = [text]
    else:
        # two balanced lines: the split that keeps the longer line shortest (no lone word on the second line)
        best = None
        for k in range(1, len(words)):
            a, b = " ".join(words[:k]), " ".join(words[k:])
            wa, wb = d.textlength(a, font=fnt), d.textlength(b, font=fnt)
            if wa <= maxw and wb <= maxw and (best is None or max(wa, wb) < best[0]):
                best = (max(wa, wb), [a, b])
        lines = best[1]
    lh, pad = fnt.size * 1.18, 20
    y = SAFE[3] - len(lines) * (lh + pad * 0.6) - 10
    boxes = []
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=fnt)
        x, yy = W / 2 - tw / 2, y + i * (lh + pad * 0.6)
        boxes.append((line, x, yy, tw, lh))
    return fnt, boxes, pad


def draw_caption(img, tg):
    cue = next((c for c in CAPTIONS if c[0] <= tg < c[1]), None)
    if cue is None:
        return None
    a = min(1.0, (tg - cue[0]) / 0.2, (cue[1] - tg) / 0.18)
    fnt, boxes, pad = caption_layout(cue[2])
    d = ImageDraw.Draw(img, "RGBA")
    for line, x, yy, tw, lh in boxes:
        d.rounded_rectangle((x - pad, yy - pad * 0.55, x + tw + pad, yy + lh + pad * 0.3), radius=14, fill=(4, 6, 12, int(185 * a)))
        d.text((x, yy), line, font=fnt, fill=TEXT + (int(255 * a),))
    return cue


def caption_box(tg):
    cue = next((c for c in CAPTIONS if c[0] <= tg < c[1]), None)
    if cue is None:
        return None
    fnt, boxes, pad = caption_layout(cue[2])
    return dict(name="caption", type="caption", role="body", text=cue[2], lines=[b[0] for b in boxes],
                bbox=(min(b[1] for b in boxes) - pad, boxes[0][2] - pad * 0.55, max(b[1] + b[3] for b in boxes) + pad, boxes[-1][2] + boxes[-1][4] + pad * 0.3))


def counter(img, tg):
    sid, t = scene_at(tg)
    if sid != "tangle" and not (sid == "turn" and t < CUE["wash"][0] + 0.3):
        return
    tt = t if sid == "tangle" else SCENES[2][1] + t
    _, n = cable_state(tt)
    a = ease_out((tt - CUE["cables_t0"] - CUE["cable_dur"] + 0.1) / 0.3)
    if sid == "turn":
        a *= 1 - ease_out((t - CUE["wash"][0]) / 0.3)
    if a <= 0 or n == 0:
        return
    s = f"{n} custom cable" + ("s" if n != 1 else "")
    f = font("Inter-Bold.otf", 58)
    text_screen(img, W / 2, 360, s, f, (226, 222, 210), a * 0.95, "counter", "mm", "headline")


_last_cache = {}


def scene_frame(tg):
    sid, t = scene_at(tg)
    cam = cam_at(tg)
    if sid in ("lock", "reach", "tangle"):
        img = dark_frame(tg, cam)
    elif sid == "turn":
        img = turn_frame(tg, cam)
    elif sid == "end":
        return None, cam
    else:
        img = bright_frame(tg, cam)
    counter(img, tg)
    return img, cam


def dark_amount(tg):
    """1 in the dark half, 0 once the wash has finished."""
    if tg < START["turn"]:
        return 1.0
    t = tg - START["turn"]
    a, dur = CUE["wash"]
    return 1 - smooth((t - a) / (dur + 0.4))


def frame(tg):
    sid, t = scene_at(tg)
    if sid == "end":
        if "last" not in _last_cache:
            img, _ = scene_frame(START["end"] - 1 / FPS)
            _last_cache["last"] = img
        img = end_card(_last_cache["last"], t)
        fr = finish(img, t, tg, bloom=0.3, grain=2.0, vignette=0.3, drift=0.0, zoom=1.0)
    else:
        img, cam = scene_frame(tg)
        dk = dark_amount(tg)
        fr = finish(img, t, tg, bloom=lerp(0.32, 0.85, dk), grain=lerp(2.2, 9.5, dk), vignette=lerp(0.3, 0.55, dk), drift=0.0, zoom=1.0)
        fr = chroma(fr, dk)
        fr = found_footage(fr, tg)
    draw_caption(fr, tg)
    return fr.convert("RGB")


# ---------------------------------------------------------------- QA
QA_TIMES = {"lock": [6.0], "reach": [2.0, 6.0], "tangle": [5.5, 6.3], "turn": [4.6, 6.6], "how": [1.6], "menu": [3.8, 5.8],
            "ask": [2.6, 3.4, 4.3], "answer": [3.6], "plugq": [1.8], "tools": [2.0, 4.6, 7.2, 9.8, 12.4], "more": [2.8], "dandy": [6.2, 7.3]}


def qa():
    global REC
    scenes = []
    for sid, dur in SCENES:
        if sid == "end":
            scenes.append(dict(id="end", type="end_card", duration=dur, laid_out=[]))
            continue
        for ts in QA_TIMES.get(sid, []):
            REC = []
            tg = START[sid] + min(ts, dur - 0.02)
            img, _ = scene_frame(tg)
            els = list(REC)
            cb = caption_box(tg)
            if cb:
                els.append(cb)
            REC = None
            scenes.append(dict(id=f"{sid}@{ts}", type="blueprint", duration=dur, laid_out=els))
    problems = [f"{s}: {m}" for s, m in run_all(scenes, CONTRACT["canvases"]["vertical"], CONTRACT)]
    # captions on their own: banned characters, banned phrases, word limit
    rules = CONTRACT["copy_rules"]
    for _, _, tx in CAPTIONS:
        for ch in rules["banned_characters"]:
            if ch in tx:
                problems.append(f"caption: banned character in {tx!r}")
        for ph in rules["banned_phrases"] + ["state layer"]:
            if ph in tx.lower():
                problems.append(f"caption: banned phrase {ph!r} in {tx!r}")
        if len(tx.split()) > CONTRACT["type"]["max_words_on_screen"]:
            problems.append(f"caption: too many words in {tx!r}")
    return problems, scenes


# ---------------------------------------------------------------- sound (effects only; Charlie brings the music)
SR = 48000
_rng = np.random.default_rng(14)


def _band(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x).astype(np.float32)


def _low(x, hi):
    return sosfilt(butter(2, hi, btype="low", fs=SR, output="sos"), x).astype(np.float32)


def _n(x, g):
    return x / (np.abs(x).max() + 1e-9) * g


def snd_knock(g=0.6):
    n = int(SR * 0.6)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * (58 + 30 * np.exp(-t * 25)) * t) * np.exp(-t * 9) + 0.5 * _band(_rng.normal(0, 1, n), 120, 700) * np.exp(-t * 30)
    return _n(x, g)


def snd_tap(g=0.55):
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 28) + 0.8 * _band(_rng.normal(0, 1, n), 400, 2400) * np.exp(-t * 55)
    return _n(x, g)


def snd_static(g=0.3, dur=0.14):
    n = int(SR * dur)
    x = _band(_rng.normal(0, 1, n), 800, 9000) * (0.6 + 0.4 * (_rng.random(n) > 0.5))
    x *= np.minimum(1, np.minimum(np.arange(n), n - np.arange(n)) / (SR * 0.004))
    return _n(x, g)


def snd_whoosh(g=0.35, dur=0.6, lo=150, hi=1800):
    n = int(SR * dur)
    t = np.arange(n) / SR
    return _n(_band(_rng.normal(0, 1, n), lo, hi) * np.sin(np.pi * t / dur) ** 2, g)


def snd_scratch(g=0.25, dur=1.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    env = np.sin(np.pi * t / dur) * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 7 * t + _rng.random() * 3)))
    return _n(_band(_rng.normal(0, 1, n), 2500, 9000) * env, g)


def snd_click(g=0.5):
    n = int(SR * 0.12)
    t = np.arange(n) / SR
    x = _band(_rng.normal(0, 1, n), 1500, 9000) * np.exp(-t * 180) + 0.5 * np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 90)
    return _n(x, g)


def snd_plug(g=0.45):
    a = snd_click(1.0)
    b = snd_click(0.7)
    n = int(SR * 0.2)
    x = np.zeros(n, np.float32)
    x[:len(a)] += a
    x[int(SR * 0.035):int(SR * 0.035) + len(b)] += b
    t = np.arange(n) / SR
    x += 0.4 * np.sin(2 * np.pi * 130 * t) * np.exp(-t * 40)
    return _n(x, g)


def snd_blip(g=0.22, f=880):
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    return _n(np.sin(2 * np.pi * f * t) * np.exp(-t * 9) * (1 - np.exp(-t * 300)), g)


def snd_paper(g=0.28):
    n = int(SR * 0.5)
    t = np.arange(n) / SR
    return _n(_band(_rng.normal(0, 1, n), 1200, 7000) * np.sin(np.pi * t / 0.5) ** 2 * (1 + 0.5 * np.sin(2 * np.pi * 11 * t)), g)


def snd_chord(g=0.25, root=261.6):
    n = int(SR * 2.4)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * root * r * t) * np.exp(-t * 1.6) for r in (1, 1.26, 1.5, 2.0))
    return _n(x * (1 - np.exp(-t * 60)), g)


def snd_swell(g=0.22, dur=1.4):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = _band(_rng.normal(0, 1, n), 300, 5000) * (t / dur) ** 2 * np.exp(-np.maximum(0, t - dur * 0.85) * 20)
    return _n(x, g)


def build_bed(path):
    n = int(SR * TOTAL) + SR
    L = np.zeros(n, np.float32)
    R = np.zeros(n, np.float32)

    def put(x, at, pan=0.0):
        i = int(at * SR)
        if 0 <= i < n:
            x = x[:n - i]
            L[i:i + len(x)] += x * math.cos((pan + 1) * math.pi / 4) * 1.41
            R[i:i + len(x)] += x * math.sin((pan + 1) * math.pi / 4) * 1.41

    S = START
    # the buzz of a failing bulb, following the flicker, dark half only, silent for the hush before the turn
    hush0 = S["tangle"] + CUE["hush"]
    hush1 = S["turn"] + CUE["socket"]
    tt = np.arange(int(SR * (hush1 + 0.5))) / SR
    lv = np.array([light_level(x) for x in np.arange(0, hush1 + 0.5, 0.01)], np.float32)
    lvs = np.interp(tt, np.arange(len(lv)) * 0.01, lv)
    hum = (np.sin(2 * np.pi * 120 * tt) + 0.5 * np.sin(2 * np.pi * 240 * tt + 0.3) + 0.25 * np.sign(np.sin(2 * np.pi * 60 * tt))) * 0.5
    hum = _low(hum.astype(np.float32), 900)
    crackle = _band(_rng.normal(0, 1, len(tt)), 2000, 8000) * (np.abs(np.gradient(lvs)) * SR * 0.004).clip(0, 1)
    buzz = (hum * (0.05 + 0.08 * lvs) + crackle * 0.5) * (1 - np.clip((tt - hush0) / 0.15, 0, 1))
    L[:len(buzz)] += buzz
    R[:len(buzz)] += buzz
    # lock: the wall scratching shut, the door and window scrawls
    a, b = CUE["wall_shut"]
    put(snd_scratch(0.18, b - a), S["lock"] + a, 0.3)
    put(snd_scratch(0.2, 0.35), S["lock"] + CUE["door"] + 0.5, -0.2)
    put(snd_scratch(0.2, 0.35), S["lock"] + CUE["window"] + 0.62, 0.0)
    for t0, dur in dropouts():
        put(snd_static(0.32, dur + 0.02), t0, 0.0)
    for r in CUE["reaches"]:
        put(snd_knock(0.62), S["reach"] + r + 0.36, 0.0)
    put(snd_whoosh(0.4, 0.5, 90, 900), S["tangle"] - 0.05, 0.0)
    st, _ = cable_state(0)
    for k in range(len(CABLES)):
        t0 = S["tangle"] + CUE["cables_t0"] + k * CUE["cables_gap"]
        put(snd_whoosh(0.09, CUE["cable_dur"], 200, 1400), t0, (CABLES[k]["j"] - 2) * 0.35)
    for k in CUE["taps"]:
        put(snd_tap(0.6), S["tangle"] + k, 0.35)
    # the turn: one clean switch click, and the light comes up
    put(snd_click(0.7), S["turn"] + CUE["socket"], 0.0)
    put(snd_swell(0.16, CUE["wash"][1] + 0.4), S["turn"] + CUE["wash"][0] - 0.1, 0.0)
    put(snd_scratch(0.1, CUE["title"][1]), S["turn"] + CUE["title"][0], 0.0)
    # bright half: camera slides, plugs, card, pulses
    for sid in ("how", "plugq"):
        put(snd_whoosh(0.16, 1.2, 300, 2500), S[sid], 0.0)
    for sid in ("menu", "ask", "answer"):
        put(snd_whoosh(0.1, 0.8, 400, 3000), S[sid], 0.0)
    pa, pdur = CUE["menu_plug"]
    put(snd_plug(0.5), S["menu"] + pa + pdur, 0.2)
    put(snd_paper(0.26), S["menu"] + CUE["menu_card"], 0.0)
    put(snd_blip(0.16, 660), S["ask"] + CUE["ask_pick"], 0.0)
    put(snd_blip(0.2, 990), S["ask"] + CUE["ask_pulse"][0] + CUE["ask_pulse"][1], 0.4)
    g0, gd = CUE["gear"]
    for k in range(6):
        put(snd_tap(0.12), S["answer"] + g0 + k * gd / 6, 0.4)
    put(snd_whoosh(0.12, 1.0, 600, 4000), S["answer"] + CUE["page"][0], 0.0)
    put(snd_blip(0.2, 880), S["answer"] + CUE["page"][0] + CUE["page"][1] * 1.2, -0.3)
    for i, at in enumerate(CUE["plugs"]):
        put(snd_plug(0.55), S["tools"] + at + 0.55, 0.25)
        put(snd_blip(0.1, 740 + 60 * i), S["tools"] + at + 1.2, -0.3)
    put(snd_whoosh(0.14, 1.6, 200, 2000), S["more"], 0.0)
    for y, at, sd in MORE:
        put(snd_plug(0.16), S["more"] + at + 0.35, random.Random(sd).uniform(-0.6, 0.6))
    put(snd_whoosh(0.14, 1.4, 200, 2000), S["dandy"], 0.0)
    put(snd_plug(0.6), S["dandy"] + CUE["dandy_plug"][0] + CUE["dandy_plug"][1], 0.25)
    put(snd_chord(0.2, 261.6), S["dandy"] + CUE["dandy_plug"][0] + CUE["dandy_plug"][1] + 0.05, 0.0)
    for k in range(5):
        put(snd_blip(0.07, 520 + k * 90), S["dandy"] + CUE["map"][0] + 0.15 + 0.1 * k, -0.4)
    put(snd_chord(0.2, 329.6), S["end"] + 0.5, 0.0)
    peak = max(np.abs(L).max(), np.abs(R).max(), 1e-6)
    st = np.stack([L, R], 1)[:int(SR * TOTAL)] / peak * 0.6
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- timing file and render loop
def apply_timing():
    p = os.path.join(VIDEO, "voiceover", "blueprint.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        vo = json.load(f)
    for i, (sid, dur) in enumerate(SCENES):
        if sid in vo.get("durations", {}):
            SCENES[i] = (sid, float(vo["durations"][sid]))
    global CAPTIONS
    if "lines" in vo:
        ln = vo["lines"]
        CAPTIONS = [(s - 0.05, min(e + 0.3, ln[i + 1][0] - 0.08) if i + 1 < len(ln) else e + 0.3, tx) for i, (s, e, tx) in enumerate(ln)]
    CUE.update(vo.get("cues", {}))
    return vo


def _work(args):
    i, tg, path = args
    frame(tg).save(path, compress_level=1)
    return i


def render(preview=False, final=False, at=None, workers=2):
    vo = apply_timing()
    build_starts()
    global MORE
    MORE = more_plugs()
    out = os.path.join(VIDEO, "out")
    os.makedirs(out, exist_ok=True)
    problems, scenes = qa()
    with open(os.path.join(out, "qa-blueprint-vertical.json"), "w") as f:
        json.dump(dict(canvas="vertical", look="blueprint", duration=TOTAL, problems=problems,
                       checks=["check_layout", "check_copy", "check_gold", "check_end_card"], end_card="without Dandy Man",
                       scenes=[dict(id=s, start=round(START[s], 2), duration=d) for s, d in SCENES]), f, indent=2)
    if problems:
        print("QA FAILED:")
        for p in problems:
            print("  ", p)
        if not at:
            return False
    if at:
        for tg in at:
            sid, t = scene_at(tg)
            frame(tg).save(os.path.join(out, f"at-{tg:05.2f}-{sid}.png"))
        print("stills in", out)
        return True
    step = 3 if preview else 1
    n_frames = int(round(TOTAL * FPS))
    tmp = tempfile.mkdtemp(prefix="dandy-mcp-")
    jobs = [(k, i / FPS, os.path.join(tmp, f"f{k:06d}.png")) for k, i in enumerate(range(0, n_frames, step))]
    with Pool(workers) as pool:
        for done, _ in enumerate(pool.imap_unordered(_work, jobs, chunksize=4)):
            if done % 150 == 0:
                print(f"  {done}/{len(jobs)} frames", flush=True)
    wav = os.path.join(out, "blueprint-bed.wav")
    build_bed(wav)
    mp4 = os.path.join(out, "14-mcp-vertical.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS // step), "-i", os.path.join(tmp, "f%06d.png"), "-i", wav]
    if vo and vo.get("file") and not preview:
        hp = "" if vo.get("mixed") else "highpass=f=70,"
        fc = (f"[2:a]atrim=start={vo.get('offset_s', 0)},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
              f"{hp}volume={vo.get('voice_db', 0)}dB,apad=whole_dur={TOTAL},asplit=2[v][vk];[1:a]volume={vo.get('bed_db', -4)}dB[b];"
              f"[b][vk]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350[bd];"
              f"[v][bd]amix=inputs=2:normalize=0:duration=longest,atrim=0:{TOTAL},afade=t=out:st={TOTAL - vo.get('fade_s', 1.0)}:d={vo.get('fade_s', 1.0)},alimiter=limit=0.89:level=0[a]")
        cmd += ["-i", os.path.join(ROOT, vo["file"]), "-filter_complex", fc, "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17" if final else "20", "-preset", "slow" if final else "medium",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    if vo and vo.get("file") and not preview and vo.get("loudness_lufs"):
        # bring the finished mix to a social-feed level (two-pass loudnorm, then a limiter); the video stream is copied
        tgt = vo["loudness_lufs"]
        meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", mp4, "-af", f"loudnorm=I={tgt}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                              capture_output=True, text=True).stderr
        j = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
        af = (f"loudnorm=I={tgt}:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
              f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,alimiter=limit=0.84:level=0,aresample=48000")
        tmp4 = mp4.replace(".mp4", ".loud.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp4], check=True)
        os.replace(tmp4, mp4)
    print(f"rendered {mp4} ({TOTAL:.1f} s)")
    return True


build_starts()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--at", type=str, default="")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    at = [float(x) for x in a.at.split(",") if x.strip()] if a.at else None
    sys.exit(0 if render(a.preview, a.final, at, a.workers) else 1)

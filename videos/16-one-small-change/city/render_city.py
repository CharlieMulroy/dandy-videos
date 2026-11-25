"""Video 16, One Small Change: propagation, as a city at night. Vertical 1080x1920.

Usage:  python3 videos/16-one-small-change/city/render_city.py [--preview] [--stills] [--final]

It opens on a project map (cards joined by lines), which rises into a city at night: "Think of your project as a
city." Each piece is a building, its name on a card-style sign; the pieces that depend on each other are joined by
power lines, and the column each one reads hangs as a sign on its line. One camera glides over the city for the
whole film and never cuts.

The agent (a small white light) renames Bookings' column and leaves. Across town, three buildings that were reading
it go dark one window at a time, with no alarm, until red beacons come on. Rewind, like tape. Then Dandy: the power
lines light up purple, the agent makes the same change, and a pulse runs down each line, flipping each sign as it
passes; every building it reaches stays lit and raises a purple flag, and a pulse runs back to tell the agent what
it touched. The camera pulls up, the rest of the city links up in purple, and the city flattens back into the map,
now Dandy's. End card with Dandy Man.

Purple appears only once Dandy does. No Dandy Man in the scenes (narrated plainly); he signs off on the end card.
Built on render/stage.py for captions, sound, the finish pass, the end card and the render loop.
Placeholder timing; voiceover/city.json ("durations", "lines", "cues", "file") replaces it once Charlie records.
QA boxes for signs are taken where the camera settles at the end of each scene.
"""
import argparse
import json
import math
import os
import random
import sys

import numpy as np

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(VIDEO, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "render"))
import stage as S  # noqa: E402
from stage import clamp, ease_out, smooth, lerp, mix  # noqa: E402

W, H = S.W, S.H
STILL = 0.5
VO = os.path.join(VIDEO, "voiceover", "city.json")

# ---------------------------------------------------------------- palette (night; purple is Dandy's alone)
NIGHT = (7, 10, 22)
GROUND = (11, 15, 30)
STREET = (19, 25, 44)
CURB = (28, 35, 58)
FACE = (22, 27, 46)
FACE_DARK = (14, 17, 30)
ROOF = (33, 40, 64)
ROOF_EDGE = (52, 61, 92)
WIN_ON = (255, 200, 120)
WIN_COOL = (255, 228, 180)
WIN_OFF = (26, 31, 50)
LAMP = (255, 190, 110)
WIRE = (86, 94, 122)
INK = (236, 238, 248)
PLATE = (10, 13, 26)
PLATE_EDGE = (120, 130, 160)
DANDY, DANDY_HI = S.PURPLE, S.PURPLE_HI
WARN = S.WARN
GLOW_WARM = S._radial(300, (255, 176, 90), 2.0, 130)
FILLER_DIM = 0.62

# ---------------------------------------------------------------- the city
KEY = {   # footprint x, y, width, depth, height (world px); a building's face hangs below its roof
    "Bookings": (1080, 520, 300, 150, 330),
    "Reminders": (470, 1460, 250, 130, 250),
    "Payments": (1110, 1600, 250, 130, 230),
    "Reports": (1740, 1440, 250, 130, 260),
}
TOP, KIDS = "Bookings", ["Reminders", "Payments", "Reports"]
OLD, NEW = "date", "start_time"
BLOCK, ST = 340, 54
CITY_X0, CITY_Y0, CITY_W, CITY_H = -1360, -1360, 3740, 4080
# The part of the city any camera in the film can see; it is baked once into a still layer (see bake()).
BX0, BY0, BX1, BY1 = -160, -1320, 2640, 3640
DOWNTOWN = (1230, 900)

STYLES = {   # face colour, roof colour, window size and gaps (world px), window colours, how lit
    "glass": dict(face=(18, 28, 46), roof=(26, 34, 52), win=(10, 13, 6, 7), cols=[(150, 190, 240), (190, 215, 250), (120, 160, 220)], lit=0.55, floors=0.0),
    "office": dict(face=(30, 32, 44), roof=(32, 35, 48), win=(14, 15, 8, 11), cols=[(250, 240, 220), (226, 232, 250)], lit=0.0, floors=0.38),
    "apartment": dict(face=(40, 31, 35), roof=(36, 31, 38), win=(12, 15, 13, 13), cols=[(255, 196, 112), (255, 214, 150), (255, 176, 96)], lit=0.5, floors=0.0),
    "lowrise": dict(face=(46, 34, 30), roof=(40, 33, 32), win=(12, 14, 15, 14), cols=[(255, 190, 110), (255, 205, 140)], lit=0.38, floors=0.0),
}
TV = (150, 180, 255)


def _overlaps(a, b, pad=0):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def _span(x, y, w, d, h):
    return (x, y, x + w, y + d + h)


def _windows(rnd, x, y, w, d, h, style, key=False):
    """Windows on the face. Offices light whole floors; homes light windows one by one, with the odd blue TV."""
    stl = STYLES[style]
    ww, wh, gx, gy = stl["win"]
    cols = max(1, int((w - 20 + gx) // (ww + gx)))
    rows = max(1, int((h - 22 + gy) // (wh + gy)))
    ox = x + (w - (cols * ww + (cols - 1) * gx)) / 2
    oy = y + d + 12
    out = []
    for r in range(rows):
        floor_on = rnd.random() < stl["floors"] if stl["floors"] else None
        for c in range(cols):
            if key:
                on = rnd.random() > 0.06
                col = rnd.choice(((255, 200, 120), (255, 214, 150), (255, 186, 104)))
            else:
                on = floor_on if floor_on is not None else rnd.random() < stl["lit"]
                if floor_on is not None and rnd.random() < 0.08:
                    on = not on
                col = TV if (style in ("apartment", "lowrise") and rnd.random() < 0.05) else rnd.choice(stl["cols"])
            out.append((ox + c * (ww + gx), oy + r * (wh + gy), ww, wh, on, rnd.random(), rnd.random(), col))
    return out


def _props(rnd, w, d, style, h):
    """Rooftop clutter: vents and AC boxes, a water tank on older buildings, an antenna on the tallest."""
    out = []
    for _ in range(rnd.randint(0, 3)):
        pw, pd = rnd.uniform(10, 26), rnd.uniform(8, 18)
        out.append(("box", rnd.uniform(6, max(7, w - pw - 6)), rnd.uniform(4, max(5, d - pd - 4)), pw, pd))
    if style in ("apartment", "lowrise") and rnd.random() < 0.35 and w > 70:
        r = rnd.uniform(9, 14)
        out.append(("tank", rnd.uniform(r + 4, w - r - 4), d / 2, r, r))
    return out


def _bldg(rnd, name, x, y, w, d, h, style, key=False):
    stl = STYLES[style]
    j = rnd.uniform(-4, 4)
    return dict(name=name, x=x, y=y, w=w, d=d, h=h, style=style,
                face=tuple(int(max(0, v + j)) for v in stl["face"]), roof=tuple(int(max(0, v + j)) for v in stl["roof"]),
                win=_windows(rnd, x, y, w, d, h, style, key), props=_props(rnd, w, d, style, h),
                antenna=(h > 340 and not key), ph=rnd.random() * 6.28)


def build_city():
    """Every block is filled. A block is split into lots; each lot holds one building that rises from it (its roof
    drawn up-screen of the lot by its height), so nearer buildings overlap farther ones as in a real aerial view.
    Some blocks are parks or car parks. Heights grow toward downtown, around Bookings."""
    rnd = random.Random(16)
    bl, parks, lots_park = [], [], []
    keys = {n: _span(*v) for n, v in KEY.items()}
    for n, (x, y, w, d, h) in KEY.items():
        bl.append(_bldg(rnd, n, x, y, w, d, h, "apartment", key=True))
    for by in range(CITY_Y0, CITY_H, BLOCK):
        for bx in range(CITY_X0, CITY_W, BLOCK):
            x0, y0 = bx + ST / 2 + 8, by + ST / 2 + 8
            inner = BLOCK - ST - 16
            if not (BX0 - 400 < x0 < BX1 + 100 and BY0 - 200 < y0 < BY1 + 300):
                continue
            blk = (x0, y0, x0 + inner, y0 + inner)
            roll = rnd.random()
            if roll < 0.07 and not any(_overlaps(blk, k, 20) for k in keys.values()):
                parks.append(("park", blk, rnd.random()))
                continue
            if roll < 0.11 and not any(_overlaps(blk, k, 20) for k in keys.values()):
                parks.append(("lot", blk, rnd.random()))
                continue
            dist = math.hypot(x0 + inner / 2 - DOWNTOWN[0], y0 + inner / 2 - DOWNTOWN[1])
            core = clamp(1 - dist / 2300)
            nx, ny = rnd.choice(((2, 2), (2, 3), (3, 2), (3, 3), (2, 2)))
            lw, ld = inner / nx, inner / ny
            for iy in range(ny):
                for ix in range(nx):
                    if rnd.random() < 0.1:
                        continue
                    gx = x0 + ix * lw + rnd.uniform(3, 8)
                    gy = y0 + iy * ld + rnd.uniform(3, 8)
                    w = lw - rnd.uniform(8, 18)
                    d = max(26, ld * rnd.uniform(0.45, 0.7))
                    h = rnd.uniform(60, 150) + core ** 1.6 * rnd.uniform(60, 330)
                    if rnd.random() < 0.05 * core:
                        h += rnd.uniform(80, 160)
                    x, y = gx, gy + (ld - 10 - d) - h      # the lot is where it stands; the roof sits up-screen by its height
                    sp = _span(x, y, w, d, h)
                    if any(_overlaps(sp, k, 14) for k in keys.values()):
                        continue
                    style = ("glass" if h > 260 and rnd.random() < 0.6 else "office" if h > 180 and rnd.random() < 0.6
                             else "apartment" if h > 110 else "lowrise")
                    bl.append(_bldg(rnd, None, x, y, w, d, h, style))
    bl.sort(key=lambda b: b["y"] + b["d"] + b["h"])
    lamps = []
    for k in range(CITY_X0, CITY_W + 1, BLOCK):
        for v in range(CITY_Y0 + 40, CITY_H, 85):
            lamps.append((k - ST / 2 + 4, v))
    for k in range(CITY_Y0, CITY_H + 1, BLOCK):
        for u in range(CITY_X0 + 40, CITY_W, 85):
            lamps.append((u, k - ST / 2 + 4))
    lamps = [p for p in lamps if BX0 - 200 < p[0] < BX1 + 200 and BY0 - 200 < p[1] < BY1 + 200]
    return bl, lamps, parks


BUILDINGS, LAMPS, PARKS = build_city()
BY_NAME = {b["name"]: b for b in BUILDINGS if b["name"]}
FILLERS = [b for b in BUILDINGS if not b["name"]]
_r = random.Random(5)
TWINKLE = []   # a few windows that switch on and off while you watch
for b in _r.sample(FILLERS, min(140, len(FILLERS))):
    wn = _r.choice(b["win"])
    TWINKLE.append((wn, _r.uniform(2.0, 9.0), _r.uniform(0, 10), b["style"]))
BEACONS = [b for b in FILLERS if b["antenna"]]
CARS = []      # headlights moving along the streets
for i in range(110):
    vertical = _r.random() < 0.5
    line = _r.choice(range(CITY_X0 if vertical else CITY_Y0, (CITY_W if vertical else CITY_H) + 1, BLOCK))
    d_ = _r.choice((-1, 1))
    CARS.append((vertical, line - ST / 2 + (ST / 2 + d_ * 11), d_, _r.uniform(0, 5000), _r.uniform(70, 150)))


def roof_c(n):
    x, y, w, d, h = KEY[n]
    return x + w / 2, y + d / 2


def base_c(n, m=1.0):
    x, y, w, d, h = KEY[n]
    return x + w / 2, y + d + h * m


def quad(a, b, sag, n=28):
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + sag
    return [((1 - u) ** 2 * a[0] + 2 * (1 - u) * u * mx + u * u * b[0], (1 - u) ** 2 * a[1] + 2 * (1 - u) * u * my + u * u * b[1])
            for u in (i / (n - 1) for i in range(n))]


def wire_pts(k, m=1.0):
    """The line from Bookings to piece k: straight on the flat map (m=0), a sagging power line in the city (m=1).
    It leaves from the foot of Bookings, the column it puts out, and lands on the roof of the piece that reads it."""
    return quad(base_c(TOP, m), roof_c(k), 140 * m)


WIRE_U = {"Reminders": 0.5, "Payments": 0.78, "Reports": 0.5}   # where each column sign hangs on its line

# The rest of the city's connections: grey links on the opening map, purple when the city flattens back at the end.
_big = [b for b in FILLERS if b["h"] > 170]


def _rc(b):
    return b["x"] + b["w"] / 2, b["y"] + b["d"] / 2


NETWORK, _seen = [], set()
_hubs = _big + [BY_NAME[n] for n in KIDS]
for a in _hubs:
    near = sorted((math.hypot(_rc(a)[0] - _rc(b)[0], _rc(a)[1] - _rc(b)[1]), j) for j, b in enumerate(_hubs) if b is not a)
    for dist, j in near[:2]:
        key = tuple(sorted((id(a), id(_hubs[j]))))
        if 240 < dist < 560 and key not in _seen and not (a["name"] in KIDS and _hubs[j]["name"] in KIDS):
            _seen.add(key)
            far = math.hypot(_rc(a)[0] - 1230, _rc(a)[1] - 600)   # the reveal spreads outward from Bookings
            NETWORK.append((_rc(a), _rc(_hubs[j]), clamp(far / 2200)))


# ---------------------------------------------------------------- timing
SCENES_BASE = [("title", 2.6), ("city", 3.8), ("b1", 6.6), ("b2", 9.8), ("b3", 2.8), ("b4", 9.8), ("b5", 7.2), ("b6", 4.8), ("end", 3.0)]
TITLE_OUT = 1.9
CITY_RISE = (0.3, 2.4)           # the map rises into the city
B1_TAG, B1_ARRIVE, B1_CH, B1_LEAVE = 2.6, 3.3, 4.2, 5.2
B2_PULL, B2_WIRES, B2_IN = 0.2, 1.3, [1.6, 1.9, 2.2]
B2_OFF = [6.3, 6.7, 7.1]
B2_RED = 8.4
B3_BACK = 0.3
B4_IN, B4_OUT, B4_ARRIVE, B4_CH, B4_RIP, B4_LAND = 2.4, 3.9, 5.4, 6.1, 7.2, 8.4
B4_DANDY = 0.4                     # "In Dandy": the lines turn purple
B5_FLAG = [1.9, 2.2, 2.5]
B5_BACK, B5_TOLD = 3.7, 4.6
B6_CLEAR = [0.4, 0.7, 1.0]
B6_NET, B6_FLAT = 1.0, (1.7, 1.6)  # the network lights up, then the city flattens back into the map (start, length)

DURS = dict(SCENES_BASE)
if os.path.exists(VO):
    with open(VO) as _f:
        _vo = json.load(_f)
    DURS.update({k: float(v) for k, v in _vo.get("durations", {}).items()})
    _c = _vo.get("cues", {})
    TITLE_OUT = _c.get("title_out", TITLE_OUT)
    CITY_RISE = tuple(_c.get("city_rise", CITY_RISE))
    B1_TAG, B1_ARRIVE, B1_CH, B1_LEAVE = _c.get("b1", (B1_TAG, B1_ARRIVE, B1_CH, B1_LEAVE))
    B2_IN, B2_OFF, B2_RED = _c.get("b2_in", B2_IN), _c.get("b2_off", B2_OFF), _c.get("b2_red", B2_RED)
    B4_IN, B4_OUT, B4_ARRIVE, B4_CH, B4_RIP, B4_LAND = _c.get("b4", (B4_IN, B4_OUT, B4_ARRIVE, B4_CH, B4_RIP, B4_LAND))
    B4_DANDY = _c.get("b4_dandy", B4_DANDY)
    B2_WIRES = _c.get("b2_wires", B2_WIRES)
    B5_FLAG = _c.get("b5_flag", B5_FLAG)
    B5_BACK, B5_TOLD = _c.get("b5", (B5_BACK, B5_TOLD))
    B6_CLEAR = _c.get("b6_clear", B6_CLEAR)
    B6_NET = _c.get("b6_net", B6_NET)
    B6_FLAT = tuple(_c.get("b6_flat", B6_FLAT))
START, _acc = {}, 0.0
for _sid, _ in SCENES_BASE:
    START[_sid] = _acc
    _acc += DURS[_sid]
LAND = [B4_LAND + 0.15 * i for i in range(3)]


# ---------------------------------------------------------------- the camera: one move, never cut
def _cam_keys():
    s, d = START, DURS
    return [
        (0.0, 1230, 1000, 0.45), (s["city"] + 0.3, 1230, 1000, 0.45), (s["city"] + 2.2, 1230, 1205, 0.46), (s["city"] + d["city"], 1230, 1215, 0.46),
        (s["b1"] + 2.4, 1230, 900, 1.02), (s["b1"] + d["b1"] - 0.2, 1240, 890, 1.06),
        (s["b2"] + B2_PULL + 1.3, 1230, 1330, 0.48), (s["b2"] + d["b2"], 1220, 1360, 0.5),
        (s["b3"] + d["b3"], 1230, 1340, 0.49),
        (s["b4"] + B4_ARRIVE - 0.4, 1230, 1300, 0.53), (s["b4"] + B4_CH + 0.4, 1230, 1305, 0.54),
        (s["b4"] + B4_LAND + 0.3, 1230, 1330, 0.49), (s["b5"] + d["b5"], 1240, 1320, 0.5),
        (s["b6"] + B6_NET, 1240, 1300, 0.49), (s["b6"] + d["b6"], 1230, 1020, 0.45), (1e9, 1230, 1020, 0.45),
    ]


CAM = _cam_keys()


def cam(tg):
    for (t0, x0, y0, s0), (t1, x1, y1, s1) in zip(CAM, CAM[1:]):
        if tg <= t1:
            q = smooth((tg - t0) / (t1 - t0)) if t1 > t0 else 1.0
            return lerp(x0, x1, q), lerp(y0, y1, q), math.exp(lerp(math.log(s0), math.log(s1), q))
    return CAM[-1][1:]


def to_s(c, X, Y):
    cx, cy, s = c
    return W / 2 + (X - cx) * s, H / 2 + (Y - cy) * s


# ---------------------------------------------------------------- drawing
MAP_EDGE = (110, 122, 168)
ASPHALT = (9, 11, 20)
SIDEWALK = (21, 23, 34)
LOT_IN = (13, 15, 25)


def draw_bldg(img, d, b, T, k, tg, m=1.0, lit=1.0, glow=None, beacon=0.0, purple=0.0, live=True):
    """One building. T maps world to pixels and k is pixels per world unit, so the same drawing serves the live
    camera and the baked layer. m=0 draws it flat as a card on the project map; m=1 stands it up."""
    hh = b["h"] * m
    x0, y0 = T(b["x"], b["y"] + b["h"] * (1 - m))
    x1, y1 = T(b["x"] + b["w"], b["y"] + b["h"] * (1 - m) + b["d"])
    _, y2 = T(0, b["y"] + b["d"] + b["h"])
    if x1 < -60 or x0 > img.width + 60 or y2 < -60 or y0 > img.height + 60:
        return
    if glow:
        col, a = glow
        if a > 0.01:
            S.put_sprite(img, S.GLOW_P if col == "purple" else S.GLOW_W, (x0 + x1) / 2, (y0 + y2) / 2, scale=max(0.4, (x1 - x0) / 210), alpha=a)
    if b["name"] and lit > 0.02 and m > 0.05:
        S.put_sprite(img, GLOW_WARM, (x0 + x1) / 2, (y1 + y2) / 2, scale=max(0.6, (x1 - x0) / 130), alpha=1.0 * lit * m)
    face = b["face"] if not b["name"] else mix(FACE_DARK, FACE, 0.4 + 0.6 * lit)
    if m > 0.01 and y2 > y1:
        d.rectangle((x0, y1, x1, y2), fill=face)
        cw = (x1 - x0) * 0.17   # the corner: the right of the face falls into shadow
        d.rectangle((x1 - cw, y1, x1, y2), fill=mix(face, (4, 5, 10), 0.45))
        if (y2 - y1) > 6:
            d.rectangle((x0, y2 - (y2 - y1) * 0.12, x1, y2), fill=mix(face, (4, 5, 10), 0.3))
    map_edge, map_fill = (MAP_EDGE, (30, 37, 64)) if b["name"] else ((58, 66, 98), (20, 24, 42))
    edge = mix(mix(map_edge, mix(b["roof"], (110, 118, 150), 0.35), m), DANDY_HI, purple * (1 - m) * (1.0 if b["name"] else 0.55))
    d.rounded_rectangle((x0, y0, x1, y1), radius=max(1, 10 * k * (1 - m)), fill=mix(map_fill, b["roof"], m), outline=edge, width=max(1, int(1.6 * k + 1 - m)))
    if m < 0.04:
        return
    if m > 0.6 and k * b["w"] > 30:
        for kind, px, py, pw, pd in b["props"]:
            ax, ay = T(b["x"] + px, b["y"] + b["h"] * (1 - m) + py)
            if kind == "box":
                d.rectangle((ax, ay, ax + pw * k, ay + pd * k), fill=mix(b["roof"], (6, 7, 12), 0.5), outline=mix(b["roof"], (120, 126, 150), 0.3))
            else:
                d.ellipse((ax - pw * k, ay - pw * k, ax + pw * k, ay + pw * k), fill=(34, 30, 30), outline=(70, 62, 58))
    top = b["y"] + b["d"]
    yoff = b["h"] * (1 - m)
    for (wx, wy, ww, wh, on, thr, ph, col) in b["win"]:
        sx0, sy0 = T(wx, top + (wy - top) * m + yoff)
        sx1, sy1 = sx0 + ww * k, sy0 + wh * k * m
        if sx0 > x1 - (x1 - x0) * 0.17 and on:
            col = mix(col, (0, 0, 0), 0.35)   # windows on the shadowed corner
        if not on or (b["name"] and thr > lit):
            c = mix(face, (8, 10, 18), 0.5)
        else:
            tw = 0.88 + 0.12 * math.sin(max(0.0, tg - STILL) * (0.6 + ph) + ph * 9) if live else 1.0
            c = mix(mix(face, (8, 10, 18), 0.5), col, tw * (1.0 if b["name"] else 0.64))
        d.rectangle((sx0, sy0, sx1, sy1), fill=mix(face, c, m))
    if beacon > 0:   # a red light on the roof: something here is wrong, and you just found out
        bx, by = (x0 + x1) / 2, (y0 + y1) / 2
        blink = 0.55 + 0.45 * math.sin(tg * 9)
        S.put_sprite(img, S.GLOW_W, bx, by, scale=0.7 * max(0.6, k * 1.6), alpha=beacon * blink)
        r = 9 * max(0.8, k * 1.4)
        d.ellipse((bx - r, by - r, bx + r, by + r), fill=WARN, outline=(255, 220, 220), width=2)


def draw_ground_layer(img, T, k):
    """Streets, sidewalks, lane lines, crosswalks, parks and car parks: everything under the buildings."""
    d = ImageDraw.Draw(img, "RGBA")
    for by in range(CITY_Y0, CITY_H, BLOCK):
        for bx in range(CITY_X0, CITY_W, BLOCK):
            a = T(bx + ST / 2, by + ST / 2)
            b = T(bx + BLOCK - ST / 2, by + BLOCK - ST / 2)
            d.rectangle((*a, *b), fill=SIDEWALK)
            a2 = T(bx + ST / 2 + 8, by + ST / 2 + 8)
            b2 = T(bx + BLOCK - ST / 2 - 8, by + BLOCK - ST / 2 - 8)
            d.rectangle((*a2, *b2), fill=LOT_IN)
    for kind, (x0, y0, x1, y1), seed in PARKS:
        rnd = random.Random(int(seed * 1e6))
        a, b = T(x0, y0), T(x1, y1)
        if kind == "park":
            d.rectangle((*a, *b), fill=(13, 27, 21))
            pa, pb = T(x0, (y0 + y1) / 2), T(x1, (y0 + y1) / 2)
            d.line((*pa, *pb), fill=(36, 38, 42), width=max(1, int(6 * k)))
            pa, pb = T(x0, y0), T(x1, y1)
            d.line((*pa, *pb), fill=(36, 38, 42), width=max(1, int(5 * k)))
            for _ in range(46):
                tx, ty, r = rnd.uniform(x0 + 10, x1 - 10), rnd.uniform(y0 + 10, y1 - 10), rnd.uniform(9, 20)
                cx, cy = T(tx, ty)
                d.ellipse((cx - r * k, cy - r * k, cx + r * k, cy + r * k), fill=(15, 36, 24))
                d.ellipse((cx - r * k * 0.5, cy - r * k * 0.7, cx + r * k * 0.1, cy - r * k * 0.1), fill=(24, 50, 33))
        else:
            d.rectangle((*a, *b), fill=(20, 22, 30))
            for row in range(3):
                yy = y0 + 20 + row * (y1 - y0 - 40) / 2.6
                for col in range(12):
                    xx = x0 + 12 + col * (x1 - x0 - 24) / 12
                    p, q = T(xx, yy), T(xx, yy + 36)
                    d.line((*p, *q), fill=(52, 54, 64), width=max(1, int(1.5 * k)))
                    if rnd.random() < 0.45:
                        cx, cy = T(xx + 4, yy + 6)
                        d.rectangle((cx, cy, cx + 12 * k, cy + 22 * k), fill=rnd.choice(((60, 62, 74), (44, 50, 70), (70, 52, 50), (80, 80, 88))))
    for kx in range(CITY_X0, CITY_W + 1, BLOCK):    # lane dashes down the middle of each street
        for v in range(CITY_Y0, CITY_H, 40):
            p, q = T(kx - ST / 2 + ST / 2 - 1, v), T(kx + 1, v + 18)
            p = T(kx - 1, v)
            d.rectangle((p[0], p[1], p[0] + max(1, 2 * k), p[1] + 18 * k), fill=(64, 58, 40))
    for ky in range(CITY_Y0, CITY_H + 1, BLOCK):
        for u in range(CITY_X0, CITY_W, 40):
            p = T(u, ky - 1)
            d.rectangle((p[0], p[1], p[0] + 18 * k, p[1] + max(1, 2 * k)), fill=(64, 58, 40))
    for kx in range(CITY_X0, CITY_W + 1, BLOCK):    # crosswalks at each corner
        for ky in range(CITY_Y0, CITY_H + 1, BLOCK):
            for i in range(5):
                p = T(kx - ST / 2 + 8 + i * 9, ky + ST / 2 + 2)
                d.rectangle((p[0], p[1], p[0] + 5 * k, p[1] + 10 * k), fill=(48, 50, 62))
                p = T(kx + ST / 2 + 2, ky - ST / 2 + 8 + i * 9)
                d.rectangle((p[0], p[1], p[0] + 10 * k, p[1] + 5 * k), fill=(48, 50, 62))


def _light_layer(size, T, k, buildings):
    """Additive night light: pools under the streetlights, spill from lit windows, and a warm haze over downtown."""
    lw, lh = size[0] // 4, size[1] // 4
    lay = Image.new("RGB", (lw, lh), (0, 0, 0))
    d = ImageDraw.Draw(lay)
    for X, Y in LAMPS:
        x, y = T(X, Y)
        r = 34 * k / 4
        d.ellipse((x / 4 - r, y / 4 - r, x / 4 + r, y / 4 + r), fill=(78, 54, 26))
    for b in buildings:
        lit_share = sum(1 for wn in b["win"] if wn[4]) / max(1, len(b["win"]))
        x0, _ = T(b["x"], 0)
        x1, y2 = T(b["x"] + b["w"], b["y"] + b["d"] + b["h"])
        a = int(46 * lit_share)
        d.ellipse((x0 / 4 - 4, y2 / 4 - 3, x1 / 4 + 4, y2 / 4 + 10 * k), fill=(a, int(a * 0.7), int(a * 0.4)))
    cx, cy = T(*DOWNTOWN)
    d.ellipse((cx / 4 - 1100 * k / 4, cy / 4 - 1000 * k / 4, cx / 4 + 1100 * k / 4, cy / 4 + 1300 * k / 4), fill=(14, 11, 12))
    lay = lay.filter(ImageFilter.GaussianBlur(int(max(2, 10 * k))))
    return lay.resize(size, Image.BILINEAR)


BAKE_K = 1.1
_bake = {}


def bake():
    """The still city: ground, light and every building but the four that act. Drawn once, then filmed by the camera."""
    if "city" in _bake:
        return _bake
    size = (int((BX1 - BX0) * BAKE_K), int((BY1 - BY0) * BAKE_K))

    def T(X, Y):
        return (X - BX0) * BAKE_K, (Y - BY0) * BAKE_K

    g = Image.new("RGB", size, ASPHALT)
    draw_ground_layer(g, T, BAKE_K)
    light = _light_layer(size, T, BAKE_K, FILLERS)
    ga = np.asarray(g).astype(np.int16)
    lit_ground = Image.fromarray(np.clip(ga + np.asarray(light).astype(np.int16), 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(lit_ground, "RGBA")
    r = max(1.5, 3.0 * BAKE_K)
    for X, Y in LAMPS:
        x, y = T(X, Y)
        d.ellipse((x - r, y - r, x + r, y + r), fill=LAMP)
    city = lit_ground.copy()
    d = ImageDraw.Draw(city, "RGBA")
    for b in FILLERS:
        draw_bldg(city, d, b, T, BAKE_K, 0.0, live=False)
    haze = Image.new("RGB", size, (30, 34, 58))   # distance: the far (upper) city sinks into haze
    mask = np.zeros((size[1], size[0]), np.uint8)
    yy = np.linspace(0, 1, size[1])
    mask[:] = (np.clip(1 - (yy - 0.0) / 0.35, 0, 1) * 70).astype(np.uint8)[:, None]
    city = Image.composite(haze, city, Image.fromarray(mask))
    _bake.update(city=city, ground=lit_ground, size=size)
    return _bake


def film(layer, c):
    """What the camera sees of a baked layer."""
    cx, cy, s = c
    X0, Y0 = cx - W / 2 / s, cy - H / 2 / s
    X1, Y1 = cx + W / 2 / s, cy + H / 2 / s
    box = ((X0 - BX0) * BAKE_K, (Y0 - BY0) * BAKE_K, (X1 - BX0) * BAKE_K, (Y1 - BY0) * BAKE_K)
    k = s / BAKE_K
    return layer.resize((W, H), Image.BOX if k < 1 else Image.BILINEAR, box=box, reducing_gap=None)


def draw_life(img, c, tg):
    """What moves on top of the still city: headlights, windows switching on and off, tower beacons."""
    d = ImageDraw.Draw(img, "RGBA")
    s = c[2]
    live = max(0.0, tg - STILL)
    for vertical, line, dirn, start, speed in CARS:
        span = (CITY_H - CITY_Y0) if vertical else (CITY_W - CITY_X0)
        pos = ((start + dirn * speed * live) % span) + (CITY_Y0 if vertical else CITY_X0)
        X, Y = (line, pos) if vertical else (pos, line)
        x, y = to_s(c, X, Y)
        if not (-20 < x < W + 20 and -20 < y < H + 20):
            continue
        r = max(1.3, 2.6 * s)
        S.put_sprite(img, S.HALO, x, y, scale=0.11 * max(0.6, s * 1.5), alpha=0.55)
        if vertical:
            fy = y + dirn * 6 * s
            d.ellipse((x - r * 2.2, fy - r, x - r * 0.2, fy + r), fill=(255, 244, 220, 255))
            d.ellipse((x + r * 0.2, fy - r, x + r * 2.2, fy + r), fill=(255, 244, 220, 255))
        else:
            fx = x + dirn * 6 * s
            d.ellipse((fx - r, y - r * 2.2, fx + r, y - r * 0.2), fill=(255, 244, 220, 255))
            d.ellipse((fx - r, y + r * 0.2, fx + r, y + r * 2.2), fill=(255, 244, 220, 255))
    for (wx, wy, ww, wh, on, thr, ph, col), period, off, style in TWINKLE:
        state = int((live + off) / period) % 2 == 0
        x0, y0 = to_s(c, wx, wy)
        if -10 < x0 < W + 10 and -10 < y0 < H + 10:
            d.rectangle((x0, y0, x0 + ww * s, y0 + wh * s), fill=(col if state else (14, 16, 26)) + (255,))
    for b in BEACONS:
        blink = 1 if (live * 0.7 + b["ph"]) % 1.6 < 0.25 else 0
        if blink:
            x, y = to_s(c, b["x"] + b["w"] / 2, b["y"] + b["d"] / 2)
            S.put_sprite(img, S.HALO, x, y, scale=0.16, alpha=0.9)
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 250, 240, 255))


def draw_wire(img, d, c, pts, col, width, alpha=1.0, p=1.0, glow=0.0):
    k = max(2, int(len(pts) * clamp(p)))
    sp = [to_s(c, *q) for q in pts[:k]]
    if glow > 0:
        d.line([v for q in sp for v in q], fill=DANDY_HI + (int(110 * glow * alpha),), width=int(width * 4), joint="curve")
    d.line([v for q in sp for v in q], fill=col + (int(255 * alpha),), width=int(width), joint="curve")


def along(pts, u):
    u = clamp(u) * (len(pts) - 1)
    i = min(int(u), len(pts) - 2)
    f = u - i
    return lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f)


def pulse(img, c, X, Y, size=1.0):
    x, y = to_s(c, X, Y)
    S.put_sprite(img, S.GLOW_P, x, y, scale=0.42 * size, alpha=1.0)
    r = 11 * size
    ImageDraw.Draw(img, "RGBA").ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 255))


PLATE_SIZE, TAG_SIZE = 36, 32


def plate_box(cx, cy, text, size=PLATE_SIZE, card=False):
    f = S.font("Inter-Bold.otf", size)
    tw = f.getlength(text)
    if card:   # a name sign, styled like a piece on Dandy's map
        return (cx - tw / 2 - size * 0.8, cy - size * 0.95, cx + tw / 2 + size * 0.8, cy + size * 0.95)
    return (cx - tw / 2 - size * 0.7, cy - size * 0.82, cx + tw / 2 + size * 0.7, cy + size * 0.82)


def plate(img, cx, cy, text, alpha=1.0, size=PLATE_SIZE, edge=PLATE_EDGE, bold=True, strike=0.0, glow=0.0, dim=0.0, card=False):
    if alpha <= 0.01:
        return
    if glow > 0:
        S.put_sprite(img, S.GLOW_P, cx, cy, scale=0.55, alpha=0.9 * glow * alpha)
    d = ImageDraw.Draw(img, "RGBA")
    b = plate_box(cx, cy, text, size, card)
    if card:
        d.rounded_rectangle((b[0] + 3, b[1] + 7, b[2] + 3, b[3] + 9), radius=14, fill=(0, 0, 0, int(110 * alpha)))
        d.rounded_rectangle(b, radius=14, fill=(24, 29, 50, int(245 * alpha)), outline=edge + (int(255 * alpha),), width=3)
    else:
        d.rounded_rectangle(b, radius=(b[3] - b[1]) / 2, fill=PLATE + (int(225 * alpha),), outline=edge + (int(255 * alpha),), width=3)
    f = S.font("Inter-Bold.otf" if bold else "Inter-SemiBold.otf", size)
    tw = f.getlength(text)
    d.text((cx - tw / 2, cy - size * 0.62), text, font=f, fill=mix(INK, (120, 126, 150), dim) + (int(255 * alpha),))
    if strike > 0:
        x0 = cx - tw / 2 - 6
        d.line((x0, cy + 2, x0 + (tw + 12) * clamp(strike), cy + 2), fill=WARN + (int(255 * alpha),), width=4)


def name_at(c, n, m=1.0):
    """On the flat map a name sits in the middle of its card; in the city, Bookings' sign stands on its roof and the
    others' hang at their feet, so the power lines arriving on their roofs stay clear."""
    x, y, w, d, h = KEY[n]
    mx, my = to_s(c, *roof_c(n))
    if n == TOP:
        cx, cy = to_s(c, x + w / 2, y)
        cy -= 44
    else:
        cx, cy = to_s(c, *base_c(n, 1.0))
        cy += 44
    return lerp(mx, cx, m), lerp(my, cy, m)


def tag_at(c, n, m=1.0):
    if n == TOP:
        sx, sy = to_s(c, *base_c(TOP, m))
        return sx, sy + 40
    return to_s(c, *along(wire_pts(n, m), WIRE_U[n]))


def told_at(c):
    sx, sy = name_at(c, TOP)
    return sx - 300, sy


def flag(img, c, n, a, color=DANDY_HI):
    """A small flag on the roof: this building was touched by the change."""
    if a <= 0.01:
        return
    x, y, w, d, h = KEY[n]
    px, py = to_s(c, x + w - 26, y + d / 2)
    s = c[2]
    k = max(0.8, s * 1.4)
    pole = 90 * k * ease_out(a)
    dd = ImageDraw.Draw(img, "RGBA")
    S.put_sprite(img, S.GLOW_P, px + 18, py - pole + 14, scale=0.35, alpha=0.8 * a)
    dd.line((px, py, px, py - pole), fill=(230, 230, 245, int(255 * a)), width=3)
    fw, fh = 58 * k, 40 * k
    dd.polygon([(px, py - pole), (px + fw, py - pole + fh / 2), (px, py - pole + fh)], fill=color + (int(255 * a),))


# ---------------------------------------------------------------- one frame of the city
def frame(tg, st):
    """st: the state of the story at this moment (see the scene functions)."""
    c = cam(tg)
    m = st.get("m", 1.0)
    s = c[2]

    def T(X, Y):
        return to_s(c, X, Y)

    B = bake()
    net_grey, net = st.get("net_grey", 0.0), st.get("network", 0.0)
    lit, glows, beacons = st.get("lit", {}), st.get("glow", {}), st.get("beacon", {})
    pp = st.get("card_purple", 0.0)
    if m >= 0.999:
        img = film(B["city"], c)
    else:   # the flat map, rising into the city (or flattening back into the map at the end)
        img = Image.new("RGB", (W, H), NIGHT)
        if m > 0.01:
            img = Image.blend(img, film(B["ground"], c), clamp(m * 1.3))
        d = ImageDraw.Draw(img, "RGBA")
        if net_grey > 0.01:   # the opening map's links, under the cards
            for p, q, _ in NETWORK:
                d.line((*T(*p), *T(*q)), fill=MAP_EDGE + (int(150 * net_grey),), width=2)
        for b in FILLERS:
            draw_bldg(img, d, b, T, s, tg, m=m, purple=pp)
        fade = smooth((m - 0.8) / 0.2)
        if fade > 0:
            img = Image.blend(img, film(B["city"], c), fade)
    if m > 0.95:
        draw_life(img, c, tg)
    d = ImageDraw.Draw(img, "RGBA")
    for n in [TOP] + KIDS:
        draw_bldg(img, d, BY_NAME[n], T, s, tg, m=m, lit=lit.get(n, 1.0), glow=glows.get(n), beacon=beacons.get(n, 0.0), purple=pp)
    d = ImageDraw.Draw(img, "RGBA")
    if net > 0:
        for p, q, at in NETWORK:
            a = ease_out((net - at) / 0.35)
            if a > 0:
                pts = [(lerp(p[0], q[0], u), lerp(p[1], q[1], u)) for u in (i / 7 for i in range(8))]
                draw_wire(img, d, c, pts, DANDY_HI, 2.5, alpha=0.7, p=a, glow=0.35)
                for (X, Y), when in ((p, 0.0), (q, 0.9)):
                    if a > when:
                        x, y = to_s(c, X, Y)
                        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=DANDY_HI + (230,))
    for k in KIDS:
        wa = st.get("wire", {}).get(k, 0.0)
        purple = st.get("purple", {}).get(k, 0.0)
        if wa > 0:
            col = mix(mix(MAP_EDGE, (150, 158, 186), m), DANDY_HI, purple)
            if purple < 0.99:
                draw_wire(img, d, c, wire_pts(k, m), (4, 5, 10), max(5, 9 * c[2]), alpha=0.8 * (1 - purple), p=wa)
            draw_wire(img, d, c, wire_pts(k, m), col, max(3, 5 * c[2] + 1.5 * purple), alpha=1.0, p=wa, glow=purple + st.get("hot", {}).get(k, 0))
    for k, u in st.get("pulses", []):
        pulse(img, c, *along(wire_pts(k, m), u))
    for k in KIDS:
        flag(img, c, k, st.get("flag", {}).get(k, 0.0))
    ag = st.get("agent")
    if ag:
        X, Y, a = ag
        x, y = to_s(c, X, Y)
        S.orb(img, x, y, tg, alpha=a)
    labels = st.get("labels", 0.0)
    kids_a = st.get("labels_kids", labels)
    edge = mix(PLATE_EDGE, DANDY_HI, max(st.get("plate_purple", 0.0), pp))
    for n in [TOP] + KIDS:
        plate(img, *name_at(c, n, m), n, alpha=labels if n == TOP else kids_a, edge=edge, card=True)
    tp = st.get("tag_purple", 0.0)
    for n, (text, a, strike, glow) in st.get("tags", {}).items():
        a *= st.get("tags_alpha", 1.0) if n != TOP else 1.0
        plate(img, *tag_at(c, n, m), text, alpha=a, size=TAG_SIZE, bold=False, strike=strike, glow=glow,
              edge=mix(PLATE_EDGE, WARN, strike) if strike else mix(PLATE_EDGE, DANDY_HI, tp))
    for n, (old, new, at, t) in st.get("swaps", {}).items():
        a_old = 1 - ease_out((t - at) / 0.18)
        a_new = ease_out((t - at - 0.06) / 0.25)
        e = mix(PLATE_EDGE, DANDY_HI, tp)
        plate(img, *tag_at(c, n, m), old, alpha=a_old, size=TAG_SIZE, bold=False, edge=e)
        plate(img, *tag_at(c, n, m), new, alpha=a_new, size=TAG_SIZE, bold=False, glow=1 - clamp((t - at) / 0.9), edge=e)
    told = st.get("told", 0.0)
    if told > 0:
        plate(img, *told_at(c), "3 touched", alpha=told, size=TAG_SIZE, edge=DANDY_HI, glow=st.get("told_glow", 0.0))
    rw = st.get("rewind", 0.0)
    if 0 < rw < 1:   # tape rewinding: bright bands roll up the frame
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        k = math.sin(math.pi * rw)
        for i in range(7):
            y = (H * (1 - rw * 2.2) + i * 310) % (H + 200) - 100
            od.rectangle((0, y, W, y + 26 + 10 * (i % 3)), fill=(230, 235, 255, int(60 * k)))
        img = img.convert("RGBA")
        img.alpha_composite(ov)
        img = img.convert("RGB")
        img = Image.blend(img, Image.new("RGB", (W, H), (40, 44, 70)), 0.18 * k)
    return img


# ---------------------------------------------------------------- title text
TITLE = ["One small", "change"]
TITLE_Y, TITLE_SIZE = 360, 148


def title_boxes():
    f = S.font("Inter-ExtraBold.otf", TITLE_SIZE)
    out, y = [], TITLE_Y
    for line in TITLE:
        w = f.getlength(line)
        out.append((W / 2 - w / 2, y, W / 2 + w / 2, y + TITLE_SIZE * 1.12))
        y += TITLE_SIZE * 1.12
    return out


def draw_title(img, out):
    a = 1 - ease_out(out)
    if a <= 0:
        return img
    img = img.convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle((0, 0, W, 760), fill=NIGHT + (int(190 * a),))
    ov = ov.filter(ImageFilter.GaussianBlur(90))
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img, "RGBA")
    f = S.font("Inter-ExtraBold.otf", TITLE_SIZE)
    for i, (line, b) in enumerate(zip(TITLE, title_boxes())):
        col = INK if i == 0 else WIN_ON
        d.text((b[0], b[1] - 80 * ease_out(out)), line, font=f, fill=col + (int(255 * a),))
    return img.convert("RGB")


# ---------------------------------------------------------------- scenes
def perch():
    x, y, w, d, h = KEY[TOP]
    return x + 40, y + 20


def agent_path(t, keys):
    if t <= keys[0][0]:
        return keys[0][1], keys[0][2]
    for (t0, x0, y0), (t1, x1, y1) in zip(keys, keys[1:]):
        if t <= t1:
            q = smooth((t - t0) / (t1 - t0))
            return lerp(x0, x1, q), lerp(y0, y1, q)
    return keys[-1][1], keys[-1][2]


def s_title(t, dur, tg):
    st = dict(m=0.0, labels=1.0, net_grey=1.0, wire={k: 1.0 for k in KIDS})
    return draw_title(frame(tg, st), (t - TITLE_OUT) / 0.7)


def s_city(t, dur, tg):
    m = smooth((t - CITY_RISE[0]) / CITY_RISE[1])
    st = dict(m=m, labels=1.0, net_grey=1 - smooth((t - CITY_RISE[0]) / (CITY_RISE[1] * 0.6)), wire={k: 1.0 for k in KIDS})
    return frame(tg, st)


def s_b1(t, dur, tg):
    st = dict(labels=1.0, labels_kids=1 - ease_out(t / 0.6), wire={k: 1 - ease_out(t / 0.6) for k in KIDS})
    st["tags"] = {TOP: (OLD, ease_out((t - B1_TAG) / 0.3), 0, 0)} if t < B1_CH else {}
    if t >= B1_CH:
        st["swaps"] = {TOP: (OLD, NEW, B1_CH, t)}
    px, py = perch()
    X, Y = agent_path(t, [(B1_ARRIVE - 0.8, 700, 300), (B1_ARRIVE, px, py), (B1_LEAVE, px, py), (B1_LEAVE + 0.8, 1900, 300)])
    wig = 6 * math.sin(t * 26) if B1_ARRIVE + 0.1 < t < B1_CH else 0
    st["agent"] = (X + wig, Y, clamp((t - B1_ARRIVE + 0.8) / 0.3) * (1 - clamp((t - B1_LEAVE - 0.5) / 0.3)))
    return frame(tg, st)


def b2_lit(t):
    lit = {}
    for k, at in zip(KIDS, B2_OFF):
        p = clamp((t - at) / 0.8)
        flick = 0.18 * math.sin(t * 47 + at) * (1 - abs(2 * p - 1)) if 0 < p < 1 else 0
        lit[k] = clamp(1 - ease_out(p) + flick)
    return lit


def s_b2(t, dur, tg):
    st = dict(labels=1.0, labels_kids=ease_out((t - 1.3) / 0.4), lit=b2_lit(t))
    st["wire"] = {k: ease_out((t - B2_WIRES - 0.15 * i) / 0.7) for i, k in enumerate(KIDS)}
    st["tags"] = {TOP: (NEW, 1, 0, 0)}
    for k, at, off in zip(KIDS, B2_IN, B2_OFF):
        st["tags"][k] = (OLD, ease_out((t - at) / 0.3), ease_out((t - off - 0.3) / 0.35), 0)
    red = ease_out((t - B2_RED) / 0.25)
    st["beacon"] = {k: red for k in KIDS}
    st["glow"] = {k: ("red", 0.5 * red) for k in KIDS}
    return frame(tg, st)


def s_b3(t, dur, tg):
    rw = clamp((t - B3_BACK) / 1.6)
    back = smooth(rw)
    st = dict(labels=1.0, rewind=rw, lit={k: back for k in KIDS})
    st["wire"] = {k: 1.0 for k in KIDS}
    st["beacon"] = {k: 1 - back for k in KIDS}
    st["glow"] = {k: ("red", 0.5 * (1 - back)) for k in KIDS}
    st["tags"] = {k: (OLD, 1, 1 - back, 0) for k in KIDS}
    flip = B3_BACK + 0.55 * 1.6
    if t < flip:
        st["tags"][TOP] = (NEW, 1, 0, 0)
    else:
        st["swaps"] = {TOP: (NEW, OLD, flip, t)}
    return frame(tg, st)


def s_b4(t, dur, tg):
    pin = ease_out((t - B4_DANDY) / 0.8)
    st = dict(labels=1.0, plate_purple=pin, tag_purple=pin)
    st["wire"] = {k: 1.0 for k in KIDS}
    st["purple"] = {k: pin for k in KIDS}
    st["hot"], st["tags"], st["swaps"] = {}, {}, {}
    gi = max(0.0, 1 - abs(t - B4_IN - 0.3) / 0.8)
    go = max(0.0, 1 - abs(t - B4_OUT - 0.3) / 0.8)
    if t < B4_CH:
        st["tags"][TOP] = (OLD, 1, 0, go)
    else:
        st["swaps"][TOP] = (OLD, NEW, B4_CH, t)
    pulses = []
    for i, k in enumerate(KIDS):
        if t < LAND[i]:
            st["tags"][k] = (OLD, 1, 0, gi)
        else:
            st["swaps"][k] = (OLD, NEW, LAND[i], t)
        u = (t - B4_RIP) / (LAND[i] - B4_RIP)
        if 0 < u < 1:
            pulses.append((k, u))
        st["hot"][k] = 0.8 * (1 - clamp(abs(u - 0.5) / 0.6)) if 0 < u < 1.2 else 0
    st["pulses"] = pulses
    st["glow"] = {k: ("purple", 0.75 * (1 - clamp((t - LAND[i]) / 1.0))) for i, k in enumerate(KIDS) if t >= LAND[i]}
    if t >= B4_CH:
        st["glow"][TOP] = ("purple", 0.75 * (1 - clamp((t - B4_CH) / 1.0)))
    px, py = perch()
    X, Y = agent_path(t, [(B4_ARRIVE - 0.9, 1900, 400), (B4_ARRIVE, px, py), (dur, px, py)])
    wig = 6 * math.sin(t * 26) if B4_ARRIVE + 0.1 < t < B4_CH else 0
    st["agent"] = (X + wig, Y, clamp((t - B4_ARRIVE + 0.9) / 0.3))
    return frame(tg, st)


def s_b5(t, dur, tg):
    st = dict(labels=1.0, plate_purple=1.0, tag_purple=1.0)
    st["wire"] = {k: 1.0 for k in KIDS}
    st["purple"] = {k: 1.0 for k in KIDS}
    st["flag"] = {k: ease_out((t - at) / 0.4) for k, at in zip(KIDS, B5_FLAG)}
    st["tags"] = {n: (NEW, 1, 0, 0) for n in [TOP] + KIDS}
    u = 1 - (t - B5_BACK) / 0.9
    st["pulses"] = [(k, u) for k in KIDS] if 0 < u < 1 else []
    st["hot"] = {k: 0.8 * (1 - clamp(abs(u - 0.5) / 0.6)) for k in KIDS} if 0 < u < 1 else {}
    if t >= B5_TOLD:
        st["told"] = ease_out((t - B5_TOLD) / 0.3) * (1 - ease_out((t - dur + 0.3) / 0.3))
        st["told_glow"] = 1 - clamp((t - B5_TOLD) / 1.0)
        st["glow"] = {TOP: ("purple", 0.7 * (1 - clamp((t - B5_TOLD) / 1.0)))}
    st["agent"] = (*perch(), 1.0)
    return frame(tg, st)


def s_b6(t, dur, tg):
    fade = 1 - ease_out((t - B6_NET) / 0.6)
    m = 1 - smooth((t - B6_FLAT[0]) / B6_FLAT[1])
    st = dict(m=m, labels=1.0, labels_kids=fade, tags_alpha=fade, plate_purple=1.0, tag_purple=1.0, card_purple=1 - m)
    st["wire"] = {k: 1.0 for k in KIDS}
    st["purple"] = {k: 1.0 for k in KIDS}
    st["flag"] = {k: (1 - ease_out((t - at) / 0.35)) for k, at in zip(KIDS, B6_CLEAR)}
    st["tags"] = {n: (NEW, 1 if n != TOP else fade, 0, 0) for n in [TOP] + KIDS}
    st["network"] = max(0.0, (t - B6_NET) / 1.6)
    st["agent"] = (*perch(), 1 - clamp((t - B6_FLAT[0]) / 0.6))
    return frame(tg, st)


SCENES = [(sid, dur, fn) for (sid, dur), fn in zip(SCENES_BASE, (s_title, s_city, s_b1, s_b2, s_b3, s_b4, s_b5, s_b6, None))]

_CAPS = [
    ("title", 0.5, 2.4, "Think of your project as a city."),
    ("city", 0.2, 1.7, "Every part is a building,"), ("city", 1.75, 3.6, "wired to the parts it depends on."),
    ("b1", 0.2, 1.3, "You ask your agent"), ("b1", 1.35, 2.7, "for one small change."),
    ("b1", 3.0, 4.2, "Rename a column."), ("b1", 4.5, 6.3, "Done in ten seconds."),
    ("b2", 0.2, 1.2, "What it didn't know:"), ("b2", 1.25, 3.1, "three other parts of your project"), ("b2", 3.15, 4.6, "were reading that column."),
    ("b2", 5.0, 6.0, "Nothing errors."), ("b2", 6.2, 7.8, "They just quietly go wrong,"), ("b2", 7.9, 9.5, "and you find out next week."),
    ("b3", 0.4, 2.5, "That's what propagation fixes."),
    ("b4", 0.3, 2.2, "In Dandy, every piece of your project"), ("b4", 2.25, 3.6, "says what it takes in"), ("b4", 3.65, 5.0, "and what it puts out."),
    ("b4", 5.4, 7.0, "So when one piece changes,"), ("b4", 7.1, 9.3, "the change travels down the map."),
    ("b5", 0.3, 1.9, "Everything that depends on it"), ("b5", 1.95, 3.4, "gets updated or flagged,"),
    ("b5", 3.6, 4.9, "and your agent is told"), ("b5", 4.95, 6.7, "exactly what it just touched."),
    ("b6", 0.3, 1.2, "One change."), ("b6", 1.4, 3.3, "Nothing caught off guard."),
]
CAPTIONS = [(round(START[s] + a, 2), round(START[s] + b, 2), tx) for s, a, b, tx in _CAPS]
assert all(len(S.caption_lines(c[2])) == 1 for c in CAPTIONS)


def qa_scenes(starts, durs, captions):
    def el(name, text, box, **kw):
        return S.text_el(name, text, box, **kw)

    def names(c, m=1.0, which=None, **kw):
        return [el(f"name {n}", n, plate_box(*name_at(c, n, m), n, card=True), **kw) for n in (which or [TOP] + KIDS)]

    def tags(c, word, which, **kw):
        return [el(f"tag {n}", word, plate_box(*tag_at(c, n), word, TAG_SIZE), **kw) for n in which]

    def caps(sid):
        return S.caption_els(captions, starts[sid], durs[sid])

    tb = title_boxes()
    out = [dict(id="title", type="title", duration=durs["title"], laid_out=[
        el("title", " ".join(TITLE), (min(b[0] for b in tb), tb[0][1], max(b[2] for b in tb), tb[-1][3]), role="headline", lines=TITLE, exit_at=TITLE_OUT)]
        + names(cam(0.0), 0.0) + caps("title"))]
    out.append(dict(id="city", type="stage", duration=durs["city"], laid_out=names(cam(starts["city"] + durs["city"] - 0.01)) + caps("city")))
    c = cam(starts["b1"] + durs["b1"] - 0.01)
    out.append(dict(id="b1", type="stage", duration=durs["b1"], laid_out=names(c, which=[TOP]) + tags(c, NEW, [TOP], enter_at=B1_TAG) + caps("b1")))
    for sid, word in (("b2", OLD), ("b3", OLD), ("b4", NEW), ("b5", NEW), ("b6", NEW)):
        c = cam(starts[sid] + durs[sid] - 0.01) if sid != "b6" else cam(starts["b6"] + B6_NET)
        laid = names(c) + tags(c, NEW, [TOP]) + tags(c, word, KIDS)
        if sid == "b5":
            laid.append(el("told", "3 touched", plate_box(*told_at(c), "3 touched", TAG_SIZE), enter_at=B5_TOLD))
        if sid == "b6":   # the kids' signs and every column sign fade as the camera pulls up; the Bookings card stays
            laid = [dict(e, exit_at=B6_NET + 0.6) if e["name"] != "name Bookings" else e for e in laid]
        out.append(dict(id=sid, type="stage", duration=durs[sid], laid_out=laid + caps(sid)))
    out.append(S.end_card_scene(durs["end"]))
    return out


def events(starts, durs):
    ci, b1, b2, b3, b4, b5, b6 = (starts[k] for k in ("city", "b1", "b2", "b3", "b4", "b5", "b6"))
    pan = {"Reminders": -0.6, "Payments": 0.0, "Reports": 0.6}
    ev = [(STILL, "whoosh", dict(gain=0.16, dur=1.2), 0.0), (starts["title"] + TITLE_OUT, "whoosh", dict(gain=0.26, dur=0.9), 0.0),
          (ci + CITY_RISE[0], "zip", dict(gain=0.2), 0.0), (ci + CITY_RISE[0] + 0.2, "whoosh", dict(gain=0.3, dur=1.8), 0.0)]
    for k in range(9):   # the buildings rise
        ev.append((ci + CITY_RISE[0] + 0.25 + 0.2 * k, "pop", dict(gain=0.14, f=220 + 40 * k), -0.6 + 0.15 * k))
    ev.append((ci + CITY_RISE[0] + CITY_RISE[1], "chime", dict(gain=0.24, f0=659), 0.0))
    ev += [(b1 + 1.0, "whoosh", dict(gain=0.3, dur=1.4), 0.0), (b1 + B1_TAG, "pop", dict(gain=0.2, f=784), 0.3),
           (b1 + B1_ARRIVE - 0.5, "whoosh", dict(gain=0.16, dur=0.45), -0.4)]
    for k in range(4):
        ev.append((b1 + B1_ARRIVE + 0.15 + 0.12 * k, "tick", dict(gain=0.16), 0.0))
    ev += [(b1 + B1_CH, "chime", dict(gain=0.26, f0=880), 0.2), (b1 + B1_LEAVE, "whoosh", dict(gain=0.18, dur=0.5), 0.5),
           (b2 + B2_PULL, "whoosh", dict(gain=0.28, dur=1.3), 0.0)]
    for i, k in enumerate(KIDS):
        ev.append((b2 + B2_WIRES + 0.15 * i, "zip", dict(gain=0.1), pan[k]))
        ev.append((b2 + B2_IN[i], "pop", dict(gain=0.2, f=620), pan[k]))
    for k, at in zip(KIDS, B2_OFF):   # lights going out: a dry click and a low thump, nothing like an alarm
        ev.append((b2 + at, "tick", dict(gain=0.24), pan[k]))
        ev.append((b2 + at + 0.25, "pop", dict(gain=0.32, f=70), pan[k]))
    ev += [(b2 + B2_RED, "pop", dict(gain=0.38, f=180), 0.0), (b2 + B2_RED + 0.07, "pop", dict(gain=0.3, f=150), 0.0)]
    for k in range(10):
        ev.append((b3 + B3_BACK + 0.14 * k, "tick", dict(gain=0.18 + 0.01 * k), 0.0))
    ev += [(b3 + B3_BACK, "whoosh", dict(gain=0.3, dur=1.5), 0.0),
           (b4 + B4_DANDY, "chime", dict(gain=0.26, f0=659), 0.0), (b4 + B4_IN, "pop", dict(gain=0.2, f=587), 0.0), (b4 + B4_OUT, "pop", dict(gain=0.22, f=784), 0.0),
           (b4 + B4_ARRIVE - 0.5, "whoosh", dict(gain=0.16, dur=0.45), 0.5), (b4 + B4_CH, "chime", dict(gain=0.3, f0=1047), 0.0),
           (b4 + B4_RIP, "zip", dict(gain=0.22), 0.0)]
    for i, k in enumerate(KIDS):
        ev.append((b4 + LAND[i], "pop", dict(gain=0.3, f=660 * 2 ** (i * 2 / 12)), pan[k]))
    ev.append((b4 + LAND[-1] + 0.3, "chime", dict(gain=0.22, f0=1319), 0.0))
    for k, at in zip(KIDS, B5_FLAG):
        ev.append((b5 + at, "pop", dict(gain=0.26, f=520), pan[k]))
    ev += [(b5 + B5_BACK, "zip", dict(gain=0.16), 0.0), (b5 + B5_TOLD, "chime", dict(gain=0.3, f0=988), -0.3)]
    for i, (k, at) in enumerate(zip(KIDS, B6_CLEAR)):
        ev.append((b6 + at, "pop", dict(gain=0.22, f=660 + 110 * i), pan[k]))
    ev += [(b6 + B6_NET, "whoosh", dict(gain=0.26, dur=1.6), 0.0), (b6 + B6_FLAT[0], "whoosh", dict(gain=0.24, dur=1.5), 0.0),
           (b6 + B6_FLAT[0] + B6_FLAT[1], "chime", dict(gain=0.28, f0=784), 0.0), (starts["end"] + 0.3, "chime", dict(gain=0.32, f0=660), 0.0)]
    return ev


SPEC = dict(video_dir=VIDEO, slug="16-one-small-change", look_tag="city", look="city at night", scenes=SCENES, captions=CAPTIONS,
            qa_scenes=qa_scenes, events=events, still_s=STILL, voiceover=VO)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if S.render_video(SPEC, a.preview, a.stills, a.final) else 1)

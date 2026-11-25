"""Video 16, One Small Change: propagation, as a city at night. Vertical 1080x1920.

Usage:  python3 videos/16-one-small-change/city/render_city.py [--preview] [--stills] [--final]

Your project is a small city seen from above at night. Each piece is a building; the pieces that depend on each
other are joined by power lines. One camera glides over the city for the whole film and never cuts.

The agent (a small white light) renames one building's column and leaves. Across town, three buildings that were
reading it go dark one window at a time, with no alarm, until red beacons come on: you find out next week. Rewind,
like tape. Then Dandy: the power lines light up purple, the agent makes the same change, and a pulse of purple runs
down each line; every building it reaches stays lit and raises a purple flag, and a pulse runs back to tell the
agent what it touched. The camera pulls up and the whole city's lines are purple. End card with Dandy Man.

Purple appears only once Dandy does. No Dandy Man in the scenes (narrated plainly); he signs off on the end card.
Built on render/stage.py for captions, sound, the finish pass, the end card and the render loop.
Placeholder timing; voiceover/city.json ("durations", "lines", "cues", "file") replaces it once Charlie records.
QA boxes for labels are taken where the camera settles at the end of each scene.
"""
import argparse
import json
import math
import os
import random
import sys

from PIL import Image, ImageDraw

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
BLOCK, ST = 340, 46
CITY_X0, CITY_Y0, CITY_W, CITY_H = -1360, -1360, 3740, 4080


def _overlaps(a, b, pad=0):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def _span(x, y, w, d, h):
    return (x, y, x + w, y + d + h)


def _windows(rnd, x, y, w, d, h, dark_share):
    out = []
    ww, wh, gx, gy = 16, 20, 12, 16
    cols = max(1, int((w - 24 + gx) // (ww + gx)))
    rows = max(1, int((h - 30 + gy) // (wh + gy)))
    ox = x + (w - (cols * ww + (cols - 1) * gx)) / 2
    oy = y + d + 18
    for r in range(rows):
        for c in range(cols):
            on = rnd.random() > dark_share
            out.append((ox + c * (ww + gx), oy + r * (wh + gy), ww, wh, on, rnd.random(), rnd.random()))
    return out


def build_city():
    rnd = random.Random(16)
    bl = []
    keys = {n: _span(*v) for n, v in KEY.items()}
    for n, (x, y, w, d, h) in KEY.items():
        bl.append(dict(name=n, x=x, y=y, w=w, d=d, h=h, win=_windows(rnd, x, y, w, d, h, 0.06)))
    for by in range(CITY_Y0, CITY_H, BLOCK):
        for bx in range(CITY_X0, CITY_W, BLOCK):
            x0, y0 = bx + ST / 2 + 10, by + ST / 2 + 10
            inner = BLOCK - ST - 20
            for _ in range(rnd.choice((1, 2, 2, 3))):
                w = rnd.uniform(80, 170)
                d = rnd.uniform(50, 95)
                h = rnd.uniform(70, 300)
                if w > inner or d + h > inner + 120:
                    h = max(60, inner + 100 - d)
                x = x0 + rnd.uniform(0, max(1, inner - w))
                y = y0 + rnd.uniform(-60, max(1, inner - d - h + 60))
                sp = _span(x, y, w, d, h)
                if any(_overlaps(sp, k, 40) for k in keys.values()):
                    continue
                if any(_overlaps(sp, _span(b["x"], b["y"], b["w"], b["d"], b["h"]), 14) for b in bl):
                    continue
                bl.append(dict(name=None, x=x, y=y, w=w, d=d, h=h, win=_windows(rnd, x, y, w, d, h, 0.42)))
    bl.sort(key=lambda b: b["y"])
    lamps = []
    for k in range(CITY_X0, CITY_W + 1, BLOCK):
        for v in range(CITY_Y0 + 40, CITY_H, 90):
            lamps.append((k + 4, v))
    for k in range(CITY_Y0, CITY_H + 1, BLOCK):
        for u in range(CITY_X0 + 40, CITY_W, 90):
            lamps.append((u, k + 4))
    return bl, lamps


BUILDINGS, LAMPS = build_city()
BY_NAME = {b["name"]: b for b in BUILDINGS if b["name"]}


def roof_c(n):
    x, y, w, d, h = KEY[n]
    return x + w / 2, y + d / 2


def base_c(n):
    x, y, w, d, h = KEY[n]
    return x + w / 2, y + d + h


def wire_pts(a, b, sag=140, n=28):
    (x0, y0), (x1, y1) = roof_c(a), roof_c(b)
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2 + sag
    return [((1 - u) ** 2 * x0 + 2 * (1 - u) * u * mx + u * u * x1, (1 - u) ** 2 * y0 + 2 * (1 - u) * u * my + u * u * y1)
            for u in (i / (n - 1) for i in range(n))]


WIRES = {k: wire_pts(TOP, k) for k in KIDS}
# The rest of the city's connections, drawn in purple only when the camera pulls back at the end.
_rnd = random.Random(7)
_big = [b for b in BUILDINGS if b["name"] is None and b["h"] > 150]
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
            # the reveal spreads outward from Bookings
            far = math.hypot(_rc(a)[0] - 1230, _rc(a)[1] - 600)
            NETWORK.append((_rc(a), _rc(_hubs[j]), clamp(far / 2200)))


# ---------------------------------------------------------------- timing
SCENES_BASE = [("title", 2.8), ("b1", 4.8), ("b2", 9.8), ("b3", 2.8), ("b4", 9.8), ("b5", 7.2), ("b6", 3.8), ("end", 3.0)]
TITLE_OUT = 2.0
B1_ARRIVE, B1_CH, B1_LEAVE = 1.9, 2.6, 3.5
B2_PULL, B2_WIRES, B2_IN = 0.2, 1.3, [1.6, 1.9, 2.2]
B2_OFF = [6.3, 6.7, 7.1]
B2_RED = 8.4
B3_BACK = 0.3
B4_IN, B4_OUT, B4_ARRIVE, B4_CH, B4_RIP, B4_LAND = 2.4, 3.9, 5.4, 6.1, 7.2, 8.4
B5_FLAG = [1.9, 2.2, 2.5]
B5_BACK, B5_TOLD = 3.7, 4.6
B6_CLEAR = [0.4, 0.7, 1.0]
B6_NET = 1.2

DURS = dict(SCENES_BASE)
if os.path.exists(VO):
    with open(VO) as _f:
        _vo = json.load(_f)
    DURS.update({k: float(v) for k, v in _vo.get("durations", {}).items()})
    _c = _vo.get("cues", {})
    TITLE_OUT = _c.get("title_out", TITLE_OUT)
    B1_ARRIVE, B1_CH, B1_LEAVE = _c.get("b1", (B1_ARRIVE, B1_CH, B1_LEAVE))
    B2_IN, B2_OFF, B2_RED = _c.get("b2_in", B2_IN), _c.get("b2_off", B2_OFF), _c.get("b2_red", B2_RED)
    B4_IN, B4_OUT, B4_ARRIVE, B4_CH, B4_RIP, B4_LAND = _c.get("b4", (B4_IN, B4_OUT, B4_ARRIVE, B4_CH, B4_RIP, B4_LAND))
    B5_FLAG = _c.get("b5_flag", B5_FLAG)
    B5_BACK, B5_TOLD = _c.get("b5", (B5_BACK, B5_TOLD))
    B6_CLEAR = _c.get("b6_clear", B6_CLEAR)
START, _acc = {}, 0.0
for _sid, _ in SCENES_BASE:
    START[_sid] = _acc
    _acc += DURS[_sid]
LAND = [B4_LAND + 0.15 * i for i in range(3)]


# ---------------------------------------------------------------- the camera: one move, never cut
def _cam_keys():
    s = START
    d = DURS
    return [
        (0.0, 1230, 1260, 0.36), (s["title"] + TITLE_OUT, 1230, 1220, 0.37),
        (s["b1"] + 1.4, 1230, 900, 1.02), (s["b1"] + d["b1"] - 0.2, 1240, 890, 1.06),
        (s["b2"] + B2_PULL + 1.3, 1230, 1330, 0.48), (s["b2"] + d["b2"], 1220, 1360, 0.5),
        (s["b3"] + d["b3"], 1230, 1340, 0.49),
        (s["b4"] + B4_ARRIVE - 0.4, 1230, 1240, 0.54), (s["b4"] + B4_CH + 0.4, 1230, 1250, 0.55),
        (s["b4"] + B4_LAND + 0.3, 1230, 1330, 0.49), (s["b5"] + d["b5"], 1240, 1320, 0.5),
        (s["b6"] + d["b6"], 1260, 1300, 0.355), (1e9, 1260, 1300, 0.355),
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
def draw_ground(d, c, tg):
    cx, cy, s = c
    for k in range(CITY_X0, CITY_W + 1, BLOCK):
        x0, _ = to_s(c, k - ST / 2, 0)
        x1, _ = to_s(c, k + ST / 2, 0)
        _, y0 = to_s(c, 0, CITY_Y0 - 400)
        _, y1 = to_s(c, 0, CITY_H + 400)
        d.rectangle((x0, y0, x1, y1), fill=STREET)
    for k in range(CITY_Y0, CITY_H + 1, BLOCK):
        _, y0 = to_s(c, 0, k - ST / 2)
        _, y1 = to_s(c, 0, k + ST / 2)
        x0, _ = to_s(c, CITY_X0 - 400, 0)
        x1, _ = to_s(c, CITY_W + 400, 0)
        d.rectangle((x0, y0, x1, y1), fill=STREET)
    r = max(1.2, 3.2 * s)
    for (X, Y) in LAMPS:
        x, y = to_s(c, X, Y)
        if -10 < x < W + 10 and -10 < y < H + 10:
            d.ellipse((x - r, y - r, x + r, y + r), fill=LAMP)


def draw_building(img, d, b, c, tg, lit=1.0, glow=None, beacon=0.0):
    cx, cy, s = c
    x0, y0 = to_s(c, b["x"], b["y"])
    x1, y1 = to_s(c, b["x"] + b["w"], b["y"] + b["d"])
    _, y2 = to_s(c, 0, b["y"] + b["d"] + b["h"])
    if x1 < -40 or x0 > W + 40 or y2 < -40 or y0 > H + 40:
        return
    if glow:
        col, a = glow
        if a > 0.01:
            S.put_sprite(img, S.GLOW_P if col == "purple" else S.GLOW_W, (x0 + x1) / 2, (y0 + y2) / 2, scale=max(0.4, (x1 - x0) / 210), alpha=a)
    if b["name"] and lit > 0.02:
        S.put_sprite(img, GLOW_WARM, (x0 + x1) / 2, (y1 + y2) / 2, scale=max(0.5, (x1 - x0) / 170), alpha=0.85 * lit)
    dim = 1.0 if b["name"] else FILLER_DIM
    face = mix(FACE_DARK, FACE, 0.4 + 0.6 * lit)
    d.rectangle((x0, y1, x1, y2), fill=face)
    d.rectangle((x0, y0, x1, y1), fill=ROOF, outline=ROOF_EDGE, width=max(1, int(2 * s)))
    for (wx, wy, ww, wh, on, thr, ph) in b["win"]:
        sx0, sy0 = to_s(c, wx, wy)
        sx1, sy1 = sx0 + ww * s, sy0 + wh * s
        if not on:
            d.rectangle((sx0, sy0, sx1, sy1), fill=WIN_OFF)
            continue
        if thr > lit:
            col = WIN_OFF
        else:
            tw = 0.85 + 0.15 * math.sin(max(0.0, tg - STILL) * (0.6 + ph) + ph * 9)
            col = mix(WIN_OFF, mix(WIN_ON, WIN_COOL, ph), tw * dim)
        d.rectangle((sx0, sy0, sx1, sy1), fill=col)
    if beacon > 0:   # a red light on the roof: something here is wrong, and you just found out
        bx, by = (x0 + x1) / 2, (y0 + y1) / 2
        blink = 0.55 + 0.45 * math.sin(tg * 9)
        S.put_sprite(img, S.GLOW_W, bx, by, scale=0.7 * max(0.6, s * 1.6), alpha=beacon * blink)
        r = 9 * max(0.8, s * 1.4)
        d.ellipse((bx - r, by - r, bx + r, by + r), fill=WARN, outline=(255, 220, 220), width=2)


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


def pulse(img, c, X, Y, color="purple", size=1.0):
    x, y = to_s(c, X, Y)
    S.put_sprite(img, S.GLOW_P if color == "purple" else S.HALO, x, y, scale=0.42 * size, alpha=1.0)
    r = 11 * size
    ImageDraw.Draw(img, "RGBA").ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 255))


PLATE_SIZE, TAG_SIZE = 36, 32


def plate_box(cx, cy, text, size=PLATE_SIZE):
    f = S.font("Inter-Bold.otf", size)
    tw = f.getlength(text)
    return (cx - tw / 2 - size * 0.7, cy - size * 0.82, cx + tw / 2 + size * 0.7, cy + size * 0.82)


def plate(img, cx, cy, text, alpha=1.0, size=PLATE_SIZE, edge=PLATE_EDGE, bold=True, strike=0.0, glow=0.0, dim=0.0):
    if alpha <= 0.01:
        return
    if glow > 0:
        S.put_sprite(img, S.GLOW_P, cx, cy, scale=0.55, alpha=0.9 * glow * alpha)
    d = ImageDraw.Draw(img, "RGBA")
    b = plate_box(cx, cy, text, size)
    d.rounded_rectangle(b, radius=(b[3] - b[1]) / 2, fill=PLATE + (int(225 * alpha),), outline=edge + (int(255 * alpha),), width=3)
    f = S.font("Inter-Bold.otf" if bold else "Inter-SemiBold.otf", size)
    tw = f.getlength(text)
    d.text((cx - tw / 2, cy - size * 0.62), text, font=f, fill=mix(INK, (120, 126, 150), dim) + (int(255 * alpha),))
    if strike > 0:
        x0 = cx - tw / 2 - 6
        d.line((x0, cy + 2, x0 + (tw + 12) * clamp(strike), cy + 2), fill=WARN + (int(255 * alpha),), width=4)


def name_at(c, n):
    x, y, w, d, h = KEY[n]
    sx, sy = to_s(c, x + w / 2, y)
    return sx, sy - 40


def tag_at(c, n):
    sx, sy = to_s(c, *base_c(n))
    return sx, sy + 38


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
    pole = 90 * max(0.8, s * 1.4) * ease_out(a)
    dd = ImageDraw.Draw(img, "RGBA")
    S.put_sprite(img, S.GLOW_P, px + 18, py - pole + 14, scale=0.35, alpha=0.8 * a)
    dd.line((px, py, px, py - pole), fill=(230, 230, 245, int(255 * a)), width=3)
    fw, fh = 58 * max(0.8, s * 1.4), 40 * max(0.8, s * 1.4)
    wave_ = 4 * math.sin(c[0] * 0 + a * 6)
    dd.polygon([(px, py - pole), (px + fw, py - pole + fh / 2 + wave_ * 0.3), (px, py - pole + fh)], fill=color + (int(255 * a),))


# ---------------------------------------------------------------- one frame of the city
def frame(tg, st):
    """st: the state of the story at this moment (see the scene functions)."""
    c = cam(tg)
    img = Image.new("RGB", (W, H), NIGHT)
    d = ImageDraw.Draw(img, "RGBA")
    gx0, gy0 = to_s(c, CITY_X0 - 400, CITY_Y0 - 400)
    gx1, gy1 = to_s(c, CITY_W + 400, CITY_H + 400)
    d.rectangle((gx0, gy0, gx1, gy1), fill=GROUND)
    draw_ground(d, c, tg)
    lit, glows, beacons = st.get("lit", {}), st.get("glow", {}), st.get("beacon", {})
    for b in BUILDINGS:
        n = b["name"]
        draw_building(img, d, b, c, tg, lit=lit.get(n, 1.0), glow=glows.get(n), beacon=beacons.get(n, 0.0))
    d = ImageDraw.Draw(img, "RGBA")
    net = st.get("network", 0.0)
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
            col = mix(WIRE, DANDY_HI, purple)
            draw_wire(img, d, c, WIRES[k], col, max(2, 4 * c[2] + 1.5 * purple), alpha=1.0, p=wa, glow=purple + st.get("hot", {}).get(k, 0))
    for k, u, kind in st.get("pulses", []):
        X, Y = along(WIRES[k], u)
        pulse(img, c, X, Y, color=kind)
    for k in KIDS:
        flag(img, c, k, st.get("flag", {}).get(k, 0.0))
    ag = st.get("agent")
    if ag:
        X, Y, a = ag
        x, y = to_s(c, X, Y)
        S.orb(img, x, y, tg, alpha=a)
    labels = st.get("labels", 0.0)
    kids_a = st.get("labels_kids", labels)
    edge = mix(PLATE_EDGE, DANDY_HI, st.get("plate_purple", 0.0))
    for n in [TOP] + KIDS:
        plate(img, *name_at(c, n), n, alpha=labels if n == TOP else kids_a, edge=edge)
    for n, (text, a, strike, glow) in st.get("tags", {}).items():
        a *= st.get("tags_alpha", 1.0) if n != TOP else 1.0
        plate(img, *tag_at(c, n), text, alpha=a, size=TAG_SIZE, bold=False, strike=strike, glow=glow,
              edge=mix(PLATE_EDGE, WARN, strike) if strike else mix(PLATE_EDGE, DANDY_HI, st.get("tag_purple", 0.0)))
    for n, (old, new, at, t) in st.get("swaps", {}).items():
        a_old = 1 - ease_out((t - at) / 0.18)
        a_new = ease_out((t - at - 0.06) / 0.25)
        e = mix(PLATE_EDGE, DANDY_HI, st.get("tag_purple", 0.0))
        plate(img, *tag_at(c, n), old, alpha=a_old, size=TAG_SIZE, bold=False, edge=e)
        plate(img, *tag_at(c, n), new, alpha=a_new, size=TAG_SIZE, bold=False, glow=1 - clamp((t - at) / 0.9), edge=e)
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
    od = ImageDraw.Draw(ov)
    od.rectangle((0, 0, W, 900), fill=NIGHT + (int(150 * a),))
    from PIL import ImageFilter
    ov = ov.filter(ImageFilter.GaussianBlur(120))
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
    img = frame(tg, dict(labels=0.0))
    return draw_title(img, (t - TITLE_OUT) / 0.7)


def s_b1(t, dur, tg):
    st = dict(labels=ease_out((t - 0.9) / 0.4), labels_kids=0.0)
    st["tags"] = {TOP: (OLD, ease_out((t - 1.2) / 0.3), 0, 0)} if t < B1_CH else {}
    if t >= B1_CH:
        st["swaps"] = {TOP: (OLD, NEW, B1_CH, t)}
        st["glow"] = {TOP: ("white", 0)}
    px, py = perch()
    X, Y = agent_path(t, [(0.6, 700, 300), (B1_ARRIVE, px, py), (B1_LEAVE, px, py), (B1_LEAVE + 0.8, 1900, 300)])
    wig = 6 * math.sin(t * 26) if B1_ARRIVE + 0.1 < t < B1_CH else 0
    st["agent"] = (X + wig, Y, 1 - clamp((t - B1_LEAVE - 0.5) / 0.3))
    return frame(tg, st)


def b2_lit(t):
    lit = {}
    for k, at in zip(KIDS, B2_OFF):
        p = clamp((t - at) / 0.8)
        flick = 0.18 * math.sin(t * 47 + at) * (1 - abs(2 * p - 1)) if 0 < p < 1 else 0
        lit[k] = clamp(1 - ease_out(p) + flick)
    return lit


def s_b2(t, dur, tg):
    st = dict(labels=1.0, labels_kids=ease_out((t - 1.0) / 0.4), lit=b2_lit(t))
    st["wire"] = {k: ease_out((t - B2_WIRES - 0.15 * i) / 0.7) for i, k in enumerate(KIDS)}
    st["tags"] = {TOP: (NEW, 1, 0, 0)}
    for k, at, off in zip(KIDS, B2_IN, B2_OFF):
        st["tags"][k] = (OLD, ease_out((t - at) / 0.3), ease_out((t - off - 0.3) / 0.35), (1 - clamp((t - at) / 0.8)) * 0 if t >= at else 0)
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
    pin = ease_out((t - B4_IN) / 0.6)
    pout = ease_out((t - B4_OUT) / 0.6)
    st = dict(labels=1.0, plate_purple=pin, tag_purple=pin)
    st["wire"] = {k: 1.0 for k in KIDS}
    st["purple"] = {k: pin for k in KIDS}
    st["hot"] = {}
    st["tags"], st["swaps"] = {}, {}
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
            pulses.append((k, u, "purple"))
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
    st["pulses"] = [(k, u, "purple") for k in KIDS] if 0 < u < 1 else []
    st["hot"] = {k: 0.8 * (1 - clamp(abs(u - 0.5) / 0.6)) for k in KIDS} if 0 < u < 1 else {}
    if t >= B5_TOLD:
        st["told"] = ease_out((t - B5_TOLD) / 0.3) * (1 - ease_out((t - dur + 0.3) / 0.3))
        st["told_glow"] = 1 - clamp((t - B5_TOLD) / 1.0)
        st["glow"] = {TOP: ("purple", 0.7 * (1 - clamp((t - B5_TOLD) / 1.0)))}
    px, py = perch()
    st["agent"] = (px, py, 1.0)
    return frame(tg, st)


def s_b6(t, dur, tg):
    fade = 1 - ease_out((t - B6_NET) / 0.6)
    st = dict(labels=1.0, labels_kids=fade, tags_alpha=fade, plate_purple=1.0, tag_purple=1.0)
    st["wire"] = {k: 1.0 for k in KIDS}
    st["purple"] = {k: 1.0 for k in KIDS}
    st["flag"] = {k: 1 - ease_out((t - at) / 0.35) for k, at in zip(KIDS, B6_CLEAR)}
    st["tags"] = {n: (NEW, 1 if n != TOP else fade, 0, 0) for n in [TOP] + KIDS}
    st["network"] = max(0.0, (t - B6_NET) / 1.6)
    px, py = perch()
    st["agent"] = (px, py, 1.0)
    return frame(tg, st)


SCENES = [(sid, dur, fn) for (sid, dur), fn in zip(SCENES_BASE, (s_title, s_b1, s_b2, s_b3, s_b4, s_b5, s_b6, None))]

_CAPS = [
    ("title", 0.6, 1.6, "You ask your agent"), ("title", 1.65, 2.7, "for one small change."),
    ("b1", 0.4, 1.8, "Rename a column."), ("b1", 2.5, 4.3, "Done in ten seconds."),
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
    def at_end(sid):
        return cam(starts[sid] + durs[sid] - 0.01)

    def el(name, text, box, **kw):
        return S.text_el(name, text, box, **kw)

    def names(c):
        return [el(f"name {n}", n, plate_box(*name_at(c, n), n)) for n in [TOP] + KIDS]

    def tags(c, word, which=None):
        return [el(f"tag {n}", word, plate_box(*tag_at(c, n), word, TAG_SIZE)) for n in (which or [TOP] + KIDS)]

    def caps(sid):
        return S.caption_els(captions, starts[sid], durs[sid])

    tb = title_boxes()
    out = [dict(id="title", type="title", duration=durs["title"], laid_out=[
        el("title", " ".join(TITLE), (min(b[0] for b in tb), tb[0][1], max(b[2] for b in tb), tb[-1][3]), role="headline", lines=TITLE, exit_at=TITLE_OUT)] + caps("title"))]
    c = at_end("b1")
    out.append(dict(id="b1", type="stage", duration=durs["b1"], laid_out=[el("name Bookings", TOP, plate_box(*name_at(c, TOP), TOP)),
                                                                         el("tag Bookings", NEW, plate_box(*tag_at(c, TOP), NEW, TAG_SIZE))] + caps("b1")))
    for sid, word, extra in (("b2", OLD, []), ("b3", OLD, []), ("b4", NEW, []), ("b5", NEW, ["told"]), ("b6", NEW, [])):
        c = at_end(sid) if sid != "b6" else cam(starts["b6"] + B6_NET)
        laid = names(c) + tags(c, NEW, [TOP]) + tags(c, word, KIDS)
        if sid == "b6":   # the kids' plates and tags fade as the camera pulls up; the Bookings plate stays
            laid = [dict(e, exit_at=B6_NET + 0.6) if e["name"] not in ("name Bookings",) else e for e in laid]
        if "told" in extra:
            laid.append(el("told", "3 touched", plate_box(*told_at(c), "3 touched", TAG_SIZE), enter_at=B5_TOLD))
        out.append(dict(id=sid, type="stage", duration=durs[sid], laid_out=laid + caps(sid)))
    out.append(S.end_card_scene(durs["end"]))
    return out


def events(starts, durs):
    b1, b2, b3, b4, b5, b6 = (starts[k] for k in ("b1", "b2", "b3", "b4", "b5", "b6"))
    pan = {"Reminders": -0.6, "Payments": 0.0, "Reports": 0.6}
    ev = [(STILL, "whoosh", dict(gain=0.18, dur=1.2), 0.0), (starts["title"] + TITLE_OUT, "whoosh", dict(gain=0.32, dur=1.0), 0.0),
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
           (b4 + B4_IN, "chime", dict(gain=0.24, f0=659), 0.0), (b4 + B4_OUT, "pop", dict(gain=0.22, f=784), 0.0),
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
    ev += [(b6 + B6_NET, "whoosh", dict(gain=0.26, dur=1.6), 0.0), (b6 + B6_NET + 0.6, "chime", dict(gain=0.26, f0=784), 0.0),
           (starts["end"] + 0.3, "chime", dict(gain=0.32, f0=660), 0.0)]
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

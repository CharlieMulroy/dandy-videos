"""Video 15, Roommates: two builders, one app. The apartment cutaway. Vertical 1080x1920.

Usage:  python3 videos/15-roommates/cutaway/render_cutaway.py [--preview] [--final] [--at 1.0,5.2,...] [--workers 2]

A dollhouse cross-section of a two-storey house at night: Sam's room upstairs (teal), Jo's room downstairs
(coral), and between the floors a band where the app they are building lives, three pages side by side: Bills,
Chores, Groceries. Each roommate's agent sends what it builds down a wire into the band in its owner's colour, so
you can always see whose work is whose. Without a shared map the agents keep building over each other; with
Dandy the band becomes the map and both agents build side by side. Purple appears only when Dandy does.

Real-life use case: Charlie narrates plainly, no Dandy Man, soft end card without him.
Placeholder timing until Charlie records; then voiceover/cutaway.json ("durations", "lines", "cues", "file").
"""
import argparse
import io
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

import cairosvg
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


def hexc(c):
    return "#%02x%02x%02x" % c


# ---------------------------------------------------------------- palette
TEAL, TEAL_DEEP, TEAL_SOFT = (52, 200, 190), (22, 120, 116), (150, 232, 224)
CORAL, CORAL_DEEP, CORAL_SOFT = (255, 122, 99), (176, 70, 58), (255, 190, 172)
OWNER = {"sam": (TEAL, TEAL_DEEP, TEAL_SOFT), "jo": (CORAL, CORAL_DEEP, CORAL_SOFT)}
PURPLE, PURPLE_DEEP, PURPLE_LIGHT = rgb(PAL["highlight"]), rgb(PAL["primary"]), (196, 172, 255)
TEXT = (243, 238, 255)
INK = (24, 18, 40)
SCREEN_BG = (18, 14, 34)
BAND_BG = (20, 16, 36)

ROOF = (54, 40, 78)
BRICK = (44, 34, 64)
WALL_SAM, WALL_JO = (66, 58, 96), (84, 60, 88)
FLOOR = (92, 62, 54)
WOOD = (120, 84, 66)
WOOD_DARK = (74, 52, 46)
EARTH, EARTH_DEEP = (34, 24, 40), (18, 12, 24)
GRASS = (46, 86, 74)


def font(name, size):
    k = (name, max(6, int(round(size))))
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(os.path.join(FONT_DIR, k[0]), k[1])
    return _fonts[k]


_fonts = {}


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_io(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def lerp(a, b, p):
    return a + (b - a) * p


def mix(c1, c2, p):
    return tuple(int(lerp(c1[i], c2[i], clamp(p))) for i in range(3))


def win(t, a, b, fi=0.25, fo=0.25):
    return ease_out((t - a) / fi) * (1 - ease_out((t - b) / fo))


# ---------------------------------------------------------------- timing (placeholder until Charlie records)
SCENES = [("hook", 4.0), ("setup", 6.0), ("problem", 7.0), ("switch", 3.5), ("fix", 14.5), ("payoff", 4.5), ("end", 3.5)]
CAPTIONS = [
    (4.4, 7.4, "Sam and Jo are building an app to split bills for their apartment."),
    (7.6, 9.9, "Each one works at night, with their own Claude Code."),
    (10.3, 12.9, "The problem: neither agent knows what the other one did."),
    (13.2, 16.6, "So every morning, something one of them built has been redone."),
    (17.5, 19.8, "Then they pointed both agents at Dandy."),
    (20.8, 23.7, "Now each agent checks the same live map before it starts."),
    (24.0, 27.9, "It sees what's built, and what the other one is working on right now."),
    (28.3, 30.5, "When Jo's agent reached for Groceries, Dandy stopped it."),
    (30.6, 31.8, "Sam's agent already had it."),
    (32.1, 34.7, "And nothing's marked done until a different agent reviews it."),
    (36.5, 39.2, "Same app. Two builders. One map."),
]
CUE = dict(
    hook_sam=0.3, hook_jo=1.55,
    rewind=(0.0, 0.85),
    p_sam_bills=0.35, p_jo_bills=2.75, p_jo_chores=4.55, p_sam_chores=5.45, p_sam_bills2=6.25,
    morning1=(4.1, 4.75), morning2=(5.95, 6.5),
    slump=0.0, type=(1.0, 1.1), map=(2.35, 1.0),
    f_jo=0.35, f_say=1.3, f_sam=2.5, f_build=(0.9, 4.6), g_end=11.4,
    catch=(7.7, 0.75), catch_say=(8.15, 10.8), review=(11.75, 1.4),
    pay_jo=0.45, pay_sam=1.7,
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


# ---------------------------------------------------------------- layout (screen coordinates)
HOUSE = (60, 1020)
ROOM_SAM = (80, 262, 1000, 700)
SLAB = (60, 700, 1020, 990)
ROOM_JO = (80, 990, 1000, 1400)
GROUND_Y = 1400
WIN_SAM = (112, 318, 330, 520)
WIN_JO = (750, 1040, 968, 1240)
MON_SAM = (640, 410, 930, 572)          # monitor screen (Sam faces right, desk on the right)
MON_JO = (150, 1130, 440, 1292)         # Jo faces left, desk on the left
DESK_SAM_Y, DESK_JO_Y = 586, 1306
HIP_SAM, HIP_JO = (470, 620), (610, 1340)
BAND = (100, 724, 980, 966)
TILES = [(124, 788, 385, 946), (410, 788, 671, 946), (696, 788, 956, 946)]
TILE_NAMES = ["Bills", "Chores", "Groceries"]
WIRE_SAM_X, WIRE_JO_X = 785, 295


# ---------------------------------------------------------------- static art (SVG, rendered once)
def svg(body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">' + "".join(body) + "</svg>"


def render_svg(s):
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=s.encode(), output_width=W, output_height=H))).convert("RGBA")


def house_svg():
    x0, x1 = HOUSE
    b = ["<defs>",
         f'<linearGradient id="earth" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{hexc(EARTH)}"/><stop offset="1" stop-color="{hexc(EARTH_DEEP)}"/></linearGradient>',
         f'<linearGradient id="wallS" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{hexc(mix(WALL_SAM, (0, 0, 0), 0.15))}"/><stop offset="1" stop-color="{hexc(WALL_SAM)}"/></linearGradient>',
         f'<linearGradient id="wallJ" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{hexc(mix(WALL_JO, (0, 0, 0), 0.15))}"/><stop offset="1" stop-color="{hexc(WALL_JO)}"/></linearGradient>',
         "</defs>"]
    # ground
    b.append(f'<rect x="0" y="{GROUND_Y}" width="{W}" height="{H - GROUND_Y}" fill="url(#earth)"/>')
    b.append(f'<rect x="0" y="{GROUND_Y - 6}" width="{W}" height="16" rx="6" fill="{hexc(GRASS)}"/>')
    rnd = random.Random(4)
    for _ in range(40):
        x = rnd.uniform(0, W)
        y = rnd.uniform(GROUND_Y + 60, H)
        r = rnd.uniform(3, 9)
        b.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r * 1.6:.1f}" ry="{r:.1f}" fill="#ffffff" opacity="0.035"/>')
    # roof and chimney
    b.append(f'<rect x="760" y="120" width="70" height="120" fill="{hexc(BRICK)}"/>')
    b.append(f'<rect x="750" y="110" width="90" height="20" rx="4" fill="{hexc(mix(BRICK, (0, 0, 0), 0.3))}"/>')
    b.append(f'<path d="M{x0 - 30} 270 L540 92 L{x1 + 30} 270 Z" fill="{hexc(ROOF)}"/>')
    b.append(f'<path d="M{x0 - 30} 270 L540 92 L{x1 + 30} 270" stroke="{hexc(mix(ROOF, (255, 255, 255), 0.12))}" stroke-width="10" fill="none" stroke-linejoin="round"/>')
    # attic round window
    b.append(f'<circle cx="540" cy="190" r="34" fill="{hexc(mix(ROOF, (0, 0, 0), 0.35))}"/>')
    # house shell (brick), rooms cut in with window holes
    b.append(f'<rect x="{x0}" y="250" width="{x1 - x0}" height="{GROUND_Y - 250 + 8}" fill="{hexc(BRICK)}"/>')

    def room(rect, wall_id, win, floor_y):
        rx0, ry0, rx1, ry1 = rect
        wx0, wy0, wx1, wy1 = win
        d = f"M{rx0} {ry0} H{rx1} V{ry1} H{rx0} Z M{wx0} {wy0} V{wy1} H{wx1} V{wy0} Z"
        out = [f'<path d="{d}" fill="url(#{wall_id})" fill-rule="evenodd"/>']
        # skirting and floor
        out.append(f'<rect x="{rx0}" y="{floor_y}" width="{rx1 - rx0}" height="{ry1 - floor_y}" fill="{hexc(FLOOR)}"/>')
        for k in range(rx0, rx1, 90):
            out.append(f'<rect x="{k}" y="{floor_y}" width="2" height="{ry1 - floor_y}" fill="#000" opacity="0.12"/>')
        out.append(f'<rect x="{rx0}" y="{floor_y - 10}" width="{rx1 - rx0}" height="10" fill="{hexc(mix(FLOOR, (255, 255, 255), 0.1))}"/>')
        # window frame and sill
        out.append(f'<rect x="{wx0 - 10}" y="{wy0 - 10}" width="{wx1 - wx0 + 20}" height="{wy1 - wy0 + 20}" rx="6" fill="none" stroke="{hexc(WOOD)}" stroke-width="14"/>')
        out.append(f'<rect x="{(wx0 + wx1) / 2 - 4}" y="{wy0}" width="8" height="{wy1 - wy0}" fill="{hexc(WOOD)}"/>')
        out.append(f'<rect x="{wx0}" y="{(wy0 + wy1) / 2 - 4}" width="{wx1 - wx0}" height="8" fill="{hexc(WOOD)}"/>')
        out.append(f'<rect x="{wx0 - 24}" y="{wy1 + 8}" width="{wx1 - wx0 + 48}" height="14" rx="4" fill="{hexc(mix(WOOD, (255, 255, 255), 0.08))}"/>')
        return out

    b += room(ROOM_SAM, "wallS", WIN_SAM, 660)
    b += room(ROOM_JO, "wallJ", WIN_JO, 1360)
    # slab between floors (the band sits in it)
    sx0, sy0, sx1, sy1 = SLAB
    b.append(f'<rect x="{sx0}" y="{sy0}" width="{sx1 - sx0}" height="{sy1 - sy0}" fill="{hexc(mix(BRICK, (0, 0, 0), 0.25))}"/>')
    for yy in range(sy0 + 12, sy1, 34):
        off = 0 if (yy // 34) % 2 else 40
        for xx in range(sx0 - off, sx1, 80):
            b.append(f'<rect x="{xx + 3}" y="{yy}" width="74" height="28" rx="3" fill="#ffffff" opacity="0.025"/>')
    # Sam's room furniture: poster, shelf, lamp, desk, monitor frame
    b.append(f'<rect x="400" y="320" width="130" height="170" rx="6" fill="{hexc(mix(TEAL_DEEP, WALL_SAM, 0.35))}"/>')
    b.append(f'<circle cx="465" cy="390" r="36" fill="{hexc(mix(TEAL, WALL_SAM, 0.4))}"/>')
    b.append(f'<rect x="420" y="448" width="90" height="10" rx="4" fill="#fff" opacity="0.25"/>')
    b.append(f'<rect x="590" y="300" width="220" height="12" rx="4" fill="{hexc(WOOD_DARK)}"/>')
    for i, (w_, h_, c) in enumerate(((22, 60, TEAL), (16, 48, TEXT), (26, 66, CORAL_SOFT), (18, 52, TEAL_SOFT))):
        b.append(f'<rect x="{606 + i * 34}" y="{300 - h_}" width="{w_}" height="{h_}" rx="3" fill="{hexc(c)}" opacity="0.8"/>')
    b.append(f'<path d="M760 300 Q770 258 790 250 M770 300 Q790 270 800 268" stroke="{hexc(GRASS)}" stroke-width="7" fill="none" stroke-linecap="round"/>')
    b.append(f'<rect x="752" y="286" width="40" height="16" rx="4" fill="{hexc(WOOD_DARK)}"/>')
    # floor lamp (Sam, near the window)
    b.append(f'<rect x="352" y="420" width="8" height="240" fill="{hexc(WOOD_DARK)}"/>')
    b.append(f'<path d="M322 420 L390 420 L374 372 L338 372 Z" fill="{hexc((236, 214, 170))}"/>')
    b.append(f'<ellipse cx="356" cy="660" rx="38" ry="8" fill="{hexc(WOOD_DARK)}"/>')
    # desk Sam
    b.append(f'<rect x="590" y="{DESK_SAM_Y}" width="380" height="18" rx="5" fill="{hexc(WOOD)}"/>')
    b.append(f'<rect x="606" y="{DESK_SAM_Y + 18}" width="14" height="{660 - DESK_SAM_Y - 18}" fill="{hexc(WOOD_DARK)}"/>')
    b.append(f'<rect x="940" y="{DESK_SAM_Y + 18}" width="14" height="{660 - DESK_SAM_Y - 18}" fill="{hexc(WOOD_DARK)}"/>')
    mx0, my0, mx1, my1 = MON_SAM
    b.append(f'<rect x="{mx0 - 12}" y="{my0 - 12}" width="{mx1 - mx0 + 24}" height="{my1 - my0 + 24}" rx="12" fill="#0b0816"/>')
    b.append(f'<rect x="{(mx0 + mx1) / 2 - 10}" y="{my1 + 12}" width="20" height="{DESK_SAM_Y - my1 - 12}" fill="#0b0816"/>')
    b.append(f'<rect x="{(mx0 + mx1) / 2 - 50}" y="{DESK_SAM_Y - 6}" width="100" height="8" rx="3" fill="#0b0816"/>')
    b.append(f'<rect x="600" y="{DESK_SAM_Y - 8}" width="110" height="8" rx="3" fill="#2a2440"/>')
    # mug
    b.append(f'<rect x="900" y="{DESK_SAM_Y - 36}" width="30" height="36" rx="5" fill="{hexc(TEAL_SOFT)}"/>')
    # Jo's room furniture: plant, string lights, bookshelf, lamp, desk, monitor frame
    b.append(f'<rect x="520" y="1040" width="190" height="12" rx="4" fill="{hexc(WOOD_DARK)}"/>')
    for i, (w_, h_, c) in enumerate(((20, 54, CORAL), (26, 62, TEXT), (18, 46, CORAL_SOFT), (22, 58, (246, 200, 120)))):
        b.append(f'<rect x="{536 + i * 36}" y="{1040 - h_}" width="{w_}" height="{h_}" rx="3" fill="{hexc(c)}" opacity="0.8"/>')
    b.append(f'<rect x="530" y="1120" width="150" height="110" rx="6" fill="{hexc(mix(CORAL_DEEP, WALL_JO, 0.4))}"/>')
    b.append(f'<path d="M548 1210 L590 1150 L620 1185 L640 1165 L664 1210 Z" fill="{hexc(mix(CORAL, WALL_JO, 0.35))}"/>')
    # big plant in the corner
    for k, (dx, dy) in enumerate(((-30, -110), (0, -140), (28, -112), (-48, -70), (46, -76))):
        b.append(f'<path d="M940 1330 Q{940 + dx * 0.4} {1330 + dy * 0.5} {940 + dx} {1330 + dy}" stroke="{hexc(GRASS)}" stroke-width="16" fill="none" stroke-linecap="round"/>')
    b.append(f'<path d="M912 1318 L968 1318 L960 1362 L920 1362 Z" fill="{hexc(WOOD_DARK)}"/>')
    # desk Jo
    b.append(f'<rect x="110" y="{DESK_JO_Y}" width="380" height="18" rx="5" fill="{hexc(WOOD)}"/>')
    b.append(f'<rect x="126" y="{DESK_JO_Y + 18}" width="14" height="{1360 - DESK_JO_Y - 18}" fill="{hexc(WOOD_DARK)}"/>')
    b.append(f'<rect x="460" y="{DESK_JO_Y + 18}" width="14" height="{1360 - DESK_JO_Y - 18}" fill="{hexc(WOOD_DARK)}"/>')
    mx0, my0, mx1, my1 = MON_JO
    b.append(f'<rect x="{mx0 - 12}" y="{my0 - 12}" width="{mx1 - mx0 + 24}" height="{my1 - my0 + 24}" rx="12" fill="#0b0816"/>')
    b.append(f'<rect x="{(mx0 + mx1) / 2 - 10}" y="{my1 + 12}" width="20" height="{DESK_JO_Y - my1 - 12}" fill="#0b0816"/>')
    b.append(f'<rect x="{(mx0 + mx1) / 2 - 50}" y="{DESK_JO_Y - 6}" width="100" height="8" rx="3" fill="#0b0816"/>')
    b.append(f'<rect x="370" y="{DESK_JO_Y - 8}" width="110" height="8" rx="3" fill="#2a2440"/>')
    b.append(f'<rect x="130" y="{DESK_JO_Y - 34}" width="28" height="34" rx="5" fill="{hexc(CORAL_SOFT)}"/>')
    # wires: from each desk into the slab (static cable; the pulses ride on top)
    b.append(f'<path d="M{WIRE_SAM_X} {DESK_SAM_Y + 18} V700" stroke="#120e22" stroke-width="7" fill="none"/>')
    b.append(f'<path d="M{WIRE_JO_X} {DESK_JO_Y} V990" stroke="#120e22" stroke-width="7" fill="none"/>')
    return svg(b)


def figure_svg(who, pose, expr):
    """Seated figure. Sam faces right (teal hoodie, short hair, glasses); Jo faces left (coral sweater, ponytail)."""
    if who == "sam":
        (hx_, hy_), f = HIP_SAM, 1
        top, top_hi, hair, skin, pants = TEAL_DEEP, TEAL, (40, 30, 34), (214, 170, 132), (40, 42, 70)
    else:
        (hx_, hy_), f = HIP_JO, -1
        top, top_hi, hair, skin, pants = CORAL_DEEP, CORAL, (122, 56, 40), (238, 196, 160), (52, 40, 72)
    floor = 660 if who == "sam" else 1360
    X = lambda dx: hx_ + f * dx  # noqa: E731
    b = ["<defs>", f'<linearGradient id="top{who}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{hexc(top_hi)}"/><stop offset="1" stop-color="{hexc(top)}"/></linearGradient>', "</defs>"]
    chair = hexc((34, 26, 52))
    b += [f'<rect x="{min(X(-64), X(-46))}" y="{hy_ - 150}" width="18" height="160" rx="8" fill="{chair}"/>',
          f'<rect x="{min(X(-70), X(50))}" y="{hy_}" width="120" height="16" rx="7" fill="{chair}"/>',
          f'<rect x="{X(-8) - 7}" y="{hy_ + 16}" width="14" height="{floor - hy_ - 26}" fill="{chair}"/>',
          f'<path d="M{X(-50)} {floor - 6} L{X(40)} {floor - 6}" stroke="{chair}" stroke-width="10" stroke-linecap="round"/>']
    lean = {"typing": 14, "phone": 0, "slumped": 0, "up": -6, "happy": -4}[pose]
    if pose == "slumped":
        torso = f'<path d="M{X(-8)} {hy_ + 8} Q{X(20)} {hy_ - 90} {X(92)} {hy_ - 82} L{X(104)} {hy_ - 50} Q{X(40)} {hy_ - 52} {X(26)} {hy_ + 8} Z" fill="url(#top{who})"/>'
        hc = (X(112), hy_ - 82)
        arm = f'<path d="M{X(56)} {hy_ - 62} L{X(150)} {hy_ - 50}" stroke="url(#top{who})" stroke-width="24" stroke-linecap="round" fill="none"/>'
        hand = (X(158), hy_ - 50)
    else:
        torso = (f'<path d="M{X(-14)} {hy_ + 8} L{X(-6 + lean * 0.2)} {hy_ - 150} Q{X(26 + lean)} {hy_ - 172} {X(66 + lean)} {hy_ - 140} '
                 f'L{X(38 + lean * 0.5)} {hy_ + 8} Z" fill="url(#top{who})"/>')
        hc = (X(34 + lean), hy_ - 200)
        if pose == "typing":
            arm = f'<path d="M{X(30 + lean)} {hy_ - 124} Q{X(80)} {hy_ - 70} {X(140)} {hy_ - 38}" stroke="url(#top{who})" stroke-width="24" stroke-linecap="round" fill="none"/>'
            hand = (X(146), hy_ - 36)
        elif pose == "phone":
            arm = f'<path d="M{X(30)} {hy_ - 122} Q{X(70)} {hy_ - 60} {X(80)} {hy_ - 150}" stroke="url(#top{who})" stroke-width="24" stroke-linecap="round" fill="none"/>'
            hand = (X(82), hy_ - 154)
        else:
            arm = f'<path d="M{X(28 + lean)} {hy_ - 124} Q{X(60)} {hy_ - 60} {X(96)} {hy_ - 38}" stroke="url(#top{who})" stroke-width="24" stroke-linecap="round" fill="none"/>'
            hand = (X(102), hy_ - 36)
    hx, hy = hc
    b += [f'<path d="M{X(0)} {hy_ + 2} L{X(92)} {hy_ + 2} L{X(92)} {floor - 12}" stroke="{hexc(pants)}" stroke-width="30" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
          f'<ellipse cx="{X(104)}" cy="{floor - 8}" rx="24" ry="9" fill="{hexc(TEXT)}"/>',
          torso, arm]
    if pose == "phone":
        px, py = hand
        b.append(f'<rect x="{px - 11 + f * 6}" y="{py - 24}" width="22" height="38" rx="5" fill="#0b0816" stroke="{hexc(mix(OWNER[who][0], (255, 255, 255), 0.5))}" stroke-width="2"/>')
    b.append(f'<circle cx="{hand[0]}" cy="{hand[1]}" r="11" fill="{hexc(skin)}"/>')
    b.append(f'<circle cx="{hx}" cy="{hy}" r="34" fill="{hexc(skin)}"/>')
    # hair
    if who == "sam":
        b.append(f'<path d="M{hx - f * 36} {hy + 6} Q{hx - f * 40} {hy - 44} {hx + f * 4} {hy - 38} Q{hx + f * 36} {hy - 40} {hx + f * 34} {hy - 12} '
                 f'Q{hx + f * 14} {hy - 24} {hx - f * 4} {hy - 20} Q{hx - f * 22} {hy - 6} {hx - f * 36} {hy + 6} Z" fill="{hexc(hair)}"/>')
        b.append(f'<path d="M{hx - f * 30} {hy - 28} L{hx - f * 20} {hy - 46} L{hx - f * 8} {hy - 34} L{hx + f * 6} {hy - 48} L{hx + f * 16} {hy - 34}" fill="{hexc(hair)}"/>')
    else:
        b.append(f'<path d="M{hx - f * 36} {hy + 14} Q{hx - f * 42} {hy - 42} {hx + f * 2} {hy - 38} Q{hx + f * 34} {hy - 38} {hx + f * 34} {hy - 10} '
                 f'Q{hx + f * 10} {hy - 26} {hx - f * 10} {hy - 18} Q{hx - f * 26} {hy - 4} {hx - f * 36} {hy + 14} Z" fill="{hexc(hair)}"/>')
        b.append(f'<path d="M{hx - f * 34} {hy - 14} Q{hx - f * 70} {hy - 6} {hx - f * 64} {hy + 44} Q{hx - f * 50} {hy + 20} {hx - f * 40} {hy + 6} Z" fill="{hexc(hair)}"/>')
        b.append(f'<circle cx="{hx - f * 36}" cy="{hy - 12}" r="7" fill="{hexc(CORAL)}"/>')
    # face
    ex, ey = hx + f * 18, hy - 4
    eye = hexc((30, 22, 34))
    b.append(f'<circle cx="{ex}" cy="{ey}" r="4" fill="{eye}"/>')
    if who == "sam":
        b.append(f'<circle cx="{ex}" cy="{ey}" r="11" fill="none" stroke="{eye}" stroke-width="3"/>')
        b.append(f'<path d="M{ex - f * 11} {ey - 2} L{hx - f * 30} {ey - 6}" stroke="{eye}" stroke-width="3"/>')
    brow = {"neutral": (0, 0), "baffled": (-10, 6), "offended": (6, -8), "sad": (-4, 8), "happy": (-6, 2)}[expr]
    b.append(f'<path d="M{ex - f * 10} {ey - 16 + brow[0] * 0.3} Q{ex} {ey - 20 + brow[0] * 0.5} {ex + f * 10} {ey - 16 - brow[1] * 0.4}" stroke="{eye}" stroke-width="3" fill="none" stroke-linecap="round"/>')
    mx_, my_ = hx + f * 20, hy + 16
    if expr == "baffled":
        b.append(f'<ellipse cx="{mx_}" cy="{my_ + 2}" rx="4" ry="6" fill="{eye}"/>')
    elif expr == "offended":
        b.append(f'<path d="M{mx_ - f * 8} {my_ + 2} L{mx_ + f * 6} {my_ - 1}" stroke="{eye}" stroke-width="3" stroke-linecap="round"/>')
    elif expr == "sad":
        b.append(f'<path d="M{mx_ - f * 7} {my_ + 4} Q{mx_} {my_ - 2} {mx_ + f * 7} {my_ + 4}" stroke="{eye}" stroke-width="3" fill="none" stroke-linecap="round"/>')
    elif expr == "happy":
        b.append(f'<path d="M{mx_ - f * 9} {my_} Q{mx_} {my_ + 9} {mx_ + f * 8} {my_}" stroke="{eye}" stroke-width="3" fill="none" stroke-linecap="round"/>')
    else:
        b.append(f'<path d="M{mx_ - f * 6} {my_ + 1} L{mx_ + f * 5} {my_ + 1}" stroke="{eye}" stroke-width="3" stroke-linecap="round"/>')
    return svg(b)


_static = {}


def static(key):
    if key not in _static:
        if key == "house":
            _static[key] = render_svg(house_svg())
        else:
            who, pose, expr = key
            _static[key] = render_svg(figure_svg(who, pose, expr))
    return _static[key]


# ---------------------------------------------------------------- text helpers (record boxes for QA)
REC = None


def on_screen(box):
    return box[2] > 0 and box[0] < W and box[3] > 0 and box[1] < H


def record(name, text, lines, box, role="body"):
    if REC is not None and on_screen(box):
        REC.append(dict(name=name, type="text", role=role, text=text, lines=lines, bbox=tuple(int(v) for v in box)))


def wrap(text, fnt, maxw):
    """Fewest lines that fit, then balanced so no line is left with a lone word."""
    d = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    if d.textlength(text, font=fnt) <= maxw:
        return [text]
    words = text.split()
    for k in range(1, len(words)):
        # two sentences that each fit: break between them
        if words[k - 1].endswith((".", "?", "!")):
            a, b = " ".join(words[:k]), " ".join(words[k:])
            if d.textlength(a, font=fnt) <= maxw and d.textlength(b, font=fnt) <= maxw:
                return [a, b]
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        wa, wb = d.textlength(a, font=fnt), d.textlength(b, font=fnt)
        if wa <= maxw and wb <= maxw and (best is None or max(wa, wb) < best[0]):
            best = (max(wa, wb), [a, b])
    if best:
        return best[1]
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if d.textlength(trial, font=fnt) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    return lines


# ---------------------------------------------------------------- daylight
def daylight(tg):
    """1 = morning, 0 = night."""
    sid, t = scene_at(tg)
    if sid == "hook":
        return 1.0
    if sid == "setup":
        a, b = CUE["rewind"]
        return 1 - smooth((t - a) / (b - a))
    if sid == "problem":
        v = 0.0
        for a, b in (CUE["morning1"], CUE["morning2"]):
            v = max(v, win(t, a, b, 0.22, 0.25))
        return v
    if sid in ("switch", "fix"):
        return 0.0
    if sid == "payoff":
        return smooth(t / 0.7)
    return 1.0


def draw_sky(img, dl, tg):
    """Sky behind the house and in the windows: night with moon and stars, morning with a low sun."""
    top = mix((10, 8, 26), (120, 160, 220), dl)
    bot = mix((34, 24, 66), (250, 200, 160), dl)
    arr = np.zeros((H, W, 3), np.float32)
    g = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    arr[:] = (np.array(top, np.float32) * (1 - g) + np.array(bot, np.float32) * g)[:, None, :].reshape(H, 1, 3)
    sky = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(sky, "RGBA")
    rnd = random.Random(9)
    for _ in range(120):
        x, y = rnd.uniform(0, W), rnd.uniform(0, 1400)
        a = int(200 * (1 - dl) * (0.5 + 0.5 * math.sin(tg * rnd.uniform(1, 3) + x)))
        r = rnd.choice((1, 1, 1.5, 2))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, max(0, a)))
    # moon (night) and sun (morning) drift across behind the windows
    if dl < 0.98:
        for cx, cy in ((250, 380), (880, 1110)):
            put_glow(sky, cx, cy, 120, (220, 220, 255), 0.35 * (1 - dl))
            d.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), fill=(238, 236, 255, int(255 * (1 - dl))))
            d.ellipse((cx - 18, cy - 40, cx + 46, cy + 24), fill=top + (int(255 * (1 - dl)),))
    if dl > 0.02:
        for cx, cy in ((200, 500), (900, 1225)):
            put_glow(sky, cx, cy, 200, (255, 210, 140), 0.6 * dl)
            d.ellipse((cx - 40, cy - 40, cx + 40, cy + 40), fill=(255, 226, 160, int(255 * dl)))
    img.alpha_composite(sky)


_glow = {}


def put_glow(img, sx, sy, radius, col, alpha):
    if alpha <= 0.01 or radius < 2:
        return
    k = (col, 256)
    if k not in _glow:
        yy, xx = np.mgrid[0:256, 0:256].astype(np.float32)
        r = np.hypot(xx - 128, yy - 128) / 128
        a = np.clip(1 - r, 0, 1) ** 2.2
        arr = np.zeros((256, 256, 4), np.uint8)
        arr[..., :3] = col
        arr[..., 3] = (a * 255).astype(np.uint8)
        _glow[k] = Image.fromarray(arr, "RGBA")
    r = int(radius)
    spr = _glow[k].resize((2 * r, 2 * r), Image.BILINEAR)
    if alpha < 1:
        spr.putalpha(spr.split()[3].point(lambda v: int(v * clamp(alpha))))
    img.alpha_composite(spr, (int(sx - r), int(sy - r)))


# ---------------------------------------------------------------- the story state
def poses(tg):
    sid, t = scene_at(tg)
    if sid == "hook":
        return ("phone", "baffled"), ("phone", "offended" if t > CUE["hook_jo"] - 0.2 else "neutral")
    if sid in ("setup", "problem"):
        sam_e = "neutral"
        jo_e = "neutral"
        if sid == "problem":
            if t > CUE["p_jo_bills"] + 0.9 and t < CUE["morning1"][1] + 0.2:
                sam_e = "baffled"
            if t > CUE["p_sam_chores"] + 0.9:
                jo_e = "offended"
        return ("typing", sam_e), ("typing", jo_e)
    if sid == "switch":
        a, _ = CUE["type"]
        return (("slumped", "sad") if t < a - 0.15 else ("typing", "neutral")), ("slumped", "sad")
    if sid == "fix":
        return ("typing", "neutral"), ("typing", "neutral")
    return ("up", "happy"), ("up", "happy")


def tile_states(tg):
    """For each tile: list of layers (owner, build progress 0..1, crumple 0..1)."""
    sid, t = scene_at(tg)
    st = [[], [], []]
    if sid == "hook":
        st[0] = [("jo", 1.0, 0.0)]
        st[1] = [("sam", 1.0, 0.0)]
        return st
    if sid == "setup":
        a, b = CUE["rewind"]
        p = 1 - smooth((t - a) / (b - a) * 1.3)
        if p > 0:
            st[0] = [("jo", p, 0.0)]
            st[1] = [("sam", p, 0.0)]
        return st
    if sid == "problem":
        def built(at):
            return smooth((t - at - 0.65) / 0.45)

        def crum(at):
            return smooth((t - at - 0.65) / 0.55)
        bills = []
        if t >= CUE["p_sam_bills"] + 0.65:
            bills.append(["sam", built(CUE["p_sam_bills"]), 0.0])
        if t >= CUE["p_jo_bills"] + 0.65:
            bills[-1][2] = crum(CUE["p_jo_bills"])
            bills.append(["jo", built(CUE["p_jo_bills"]), 0.0])
        if t >= CUE["p_sam_bills2"] + 0.65:
            bills[-1][2] = crum(CUE["p_sam_bills2"])
            bills.append(["sam", built(CUE["p_sam_bills2"]), 0.0])
        chores = []
        if t >= CUE["p_jo_chores"] + 0.65:
            chores.append(["jo", built(CUE["p_jo_chores"]), 0.0])
        if t >= CUE["p_sam_chores"] + 0.65:
            chores[-1][2] = crum(CUE["p_sam_chores"])
            chores.append(["sam", built(CUE["p_sam_chores"]), 0.0])
        st[0] = [tuple(x) for x in bills if x[2] < 1]
        st[1] = [tuple(x) for x in chores if x[2] < 1]
        return st
    if sid == "switch":
        st[0] = [("sam", 1.0, 0.0)]
        a, d = CUE["map"]
        # as the map unfolds, Chores is handed back to Jo, whose agent picks it up again
        q = smooth((t - a - d * 0.4) / (d * 0.5))
        st[1] = [("sam", 1.0, q)] + ([("jo", 0.25 * q, 0.0)] if q > 0 else [])
        return st
    if sid == "fix":
        a, d = CUE["f_build"]
        st[0] = [("sam", 1.0, 0.0)]
        st[1] = [("jo", lerp(0.25, 1.0, smooth((t - a) / d)), 0.0)]
        st[2] = [("sam", smooth((t - CUE["f_sam"] - 0.6) / (CUE["g_end"] - CUE["f_sam"] - 0.6)), 0.0)] if t > CUE["f_sam"] + 0.6 else []
        return st
    st[0] = [("sam", 1.0, 0.0)]
    st[1] = [("jo", 1.0, 0.0)]
    st[2] = [("sam", 1.0, 0.0)]
    return st


def redone_count(tg):
    sid, t = scene_at(tg)
    if sid != "problem":
        return 3 if sid == "switch" else 0
    n = 0
    for k in ("p_jo_bills", "p_sam_chores", "p_sam_bills2"):
        if t >= CUE[k] + 0.9:
            n += 1
    return n


def map_amount(tg):
    sid, t = scene_at(tg)
    if sid == "switch":
        a, d = CUE["map"]
        return smooth((t - a) / d)
    return 1.0 if sid in ("fix", "payoff", "end") else 0.0


def pulses(tg):
    """(owner, tile index, progress 0..1) for every pulse in flight."""
    sid, t = scene_at(tg)
    out = []
    if sid == "problem":
        for k, owner, tile in (("p_sam_bills", "sam", 0), ("p_jo_bills", "jo", 0), ("p_jo_chores", "jo", 1),
                               ("p_sam_chores", "sam", 1), ("p_sam_bills2", "sam", 0)):
            p = (t - CUE[k]) / 0.65
            if 0 <= p <= 1:
                out.append((owner, tile, p))
    if sid == "fix":
        a, d = CUE["f_build"]
        for owner, tile, t0 in (("jo", 1, CUE["f_jo"]), ("sam", 2, CUE["f_sam"])):
            if t >= t0:
                # a steady stream of small pulses while each agent builds its own page
                end = a + d if owner == "jo" else CUE["g_end"] - 0.6
                k = 0
                while True:
                    s0 = t0 + k * 0.55
                    if s0 > min(t, end):
                        break
                    p = (t - s0) / 0.65
                    if 0 <= p <= 1:
                        out.append((owner, tile, p))
                    k += 1
    return out


def wire_path(owner, tile):
    """Screen polyline from the owner's desk to the tile."""
    tx = (TILES[tile][0] + TILES[tile][2]) / 2
    if owner == "sam":
        return [(WIRE_SAM_X, DESK_SAM_Y + 18), (WIRE_SAM_X, BAND[1] - 8), (tx, BAND[1] - 8), (tx, TILES[tile][1] + 10)]
    return [(WIRE_JO_X, DESK_JO_Y), (WIRE_JO_X, BAND[3] + 8), (tx, BAND[3] + 8), (tx, TILES[tile][3] - 10)]


def along(pts, p):
    seg = [math.dist(a, b) for a, b in zip(pts[:-1], pts[1:])]
    L = sum(seg) * clamp(p)
    for (a, b), s in zip(zip(pts[:-1], pts[1:]), seg):
        if L <= s:
            u = L / s if s else 0
            return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
        L -= s
    return pts[-1]


# ---------------------------------------------------------------- drawing: band, tiles, map
def draw_band(img, tg, dim=1.0):
    d = ImageDraw.Draw(img, "RGBA")
    m = map_amount(tg)
    x0, y0, x1, y1 = BAND
    bg = mix(BAND_BG, (30, 16, 62), m)
    if m > 0:
        put_glow(img, (x0 + x1) / 2, (y0 + y1) / 2, 560 * (0.6 + 0.4 * m), PURPLE, 0.45 * m)
    d.rounded_rectangle((x0, y0, x1, y1), radius=26, fill=bg + (255,), outline=mix((70, 60, 100), PURPLE_LIGHT, m) + (255,), width=4)
    # header strip: three dots on the left, the redone counter on the right; with Dandy, the hat
    for i in range(3):
        d.ellipse((x0 + 24 + i * 20, y0 + 22, x0 + 36 + i * 20, y0 + 34), fill=(90, 80, 120, int(255 * (1 - m))))
    if m > 0.05:
        hat = hat_img(30)
        hat.putalpha(hat.split()[3].point(lambda v: int(v * m)))
        img.alpha_composite(hat, (x0 + 24, y0 + 12))
    n = redone_count(tg)
    if n > 0 and m < 0.5:
        s = f"redone {n}"
        f = font("Inter-Bold.otf", 30)
        a = 1 - m * 2
        d.text((x1 - 26, y0 + 24), s, font=f, fill=(255, 170, 150, int(255 * a * dim)), anchor="rm")
        if a * dim > 0.5:
            record("redone counter", s, [s], d.textbbox((x1 - 26, y0 + 24), s, font=f, anchor="rm"))
    # map links between the cards (Dandy)
    if m > 0:
        for a_, b_ in ((0, 1), (1, 2)):
            ax, ay = TILES[a_][2], (TILES[a_][1] + TILES[a_][3]) / 2
            bx, by = TILES[b_][0], ay
            q = smooth((m - 0.2 * a_) / 0.6)
            d.line(((ax, ay), (lerp(ax, bx, q), by)), fill=PURPLE_LIGHT + (int(230 * q),), width=4)
    states = tile_states(tg)
    for i in range(3):
        draw_tile(img, i, states[i], m, tg, dim)


def draw_tile(img, i, layers, m, tg, dim):
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = TILES[i]
    built_owner = next((o for o, p, c in reversed(layers) if p > 0.5 and c < 0.5), None)
    # frame: dashed when nothing is there; map cards get a purple outline
    if not layers:
        dash = 16
        col = mix((110, 100, 140), PURPLE_LIGHT, m) + (int(200 * dim),)
        for x in range(x0, x1, dash * 2):
            d.line(((x, y0), (min(x + dash, x1), y0)), fill=col, width=3)
            d.line(((x, y1), (min(x + dash, x1), y1)), fill=col, width=3)
        for y in range(y0, y1, dash * 2):
            d.line(((x0, y), (x0, min(y + dash, y1))), fill=col, width=3)
            d.line(((x1, y), (x1, min(y + dash, y1))), fill=col, width=3)
    else:
        d.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=(34, 28, 56, int(255 * dim)), outline=mix((110, 100, 140), PURPLE_LIGHT, m) + (int(255 * dim),), width=3)
    # content layers: an old one crumpling away under a new one building in
    for owner, p, c in layers:
        if p <= 0:
            continue
        col, deep, soft = OWNER[owner]
        lay = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay, "RGBA")
        lw, lh = lay.size
        rows = [(16, 64, 0.82), (16, 98, 0.64), (16, 128, 0.72)]
        ld.rounded_rectangle((8, 8, lw - 8, lh - 8), radius=10, fill=deep + (150,))
        for k, (px, py, wf) in enumerate(rows):
            q = clamp(p * 3 - k * 0.6)
            if q > 0:
                ld.rounded_rectangle((px, py, px + (lw - 2 * px) * wf * q, py + 16), radius=7, fill=soft + (230,))
        ld.ellipse((lw - 44, 60, lw - 18, 86), fill=col + (int(255 * clamp(p * 2 - 1)),))
        if c > 0:
            ang = c * 28 * (1 if i % 2 else -1)
            sc = 1 - 0.65 * c
            lay = lay.rotate(ang, resample=Image.BILINEAR, expand=False)
            lay = lay.resize((max(1, int(lw * sc)), max(1, int(lh * sc))), Image.BILINEAR)
            lay.putalpha(lay.split()[3].point(lambda v: int(v * (1 - c) * dim)))
            ox = x0 + (lw - lay.width) // 2
            oy = y0 + (lh - lay.height) // 2 + int(60 * c * c)
            img.alpha_composite(lay, (ox, oy))
        else:
            if dim < 1:
                lay.putalpha(lay.split()[3].point(lambda v: int(v * dim)))
            img.alpha_composite(lay, (x0, y0))
    # label
    f = font("Inter-Bold.otf", 30)
    d.text((x0 + 18, y0 + 34), TILE_NAMES[i], font=f, fill=TEXT + (int(255 * dim),), anchor="lm")
    if dim > 0.5:
        record(f"tile {TILE_NAMES[i]}", TILE_NAMES[i], [TILE_NAMES[i]], d.textbbox((x0 + 18, y0 + 34), TILE_NAMES[i], font=f, anchor="lm"))
    # map: owner dot on each built card, a live dot where an agent is working
    if m > 0.3 and built_owner is None and layers:
        built_owner = layers[-1][0]
    if m > 0.3 and built_owner:
        col = OWNER[built_owner][0]
        sid, t = scene_at(tg)
        live = sid == "fix" and ((i == 1 and t < CUE["f_build"][0] + CUE["f_build"][1]) or (i == 2 and CUE["f_sam"] < t < CUE["g_end"]))
        r = 11 * (1 + (0.3 * math.sin(tg * 7) if live else 0))
        cx, cy = x1 - 28, y0 + 30
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (int(255 * m),))
        if live:
            put_glow(img, cx, cy, 46, col, 0.7)
    sid, t = scene_at(tg)
    if sid == "fix" and i == 2:
        c0, cd = CUE["catch"]
        la = win(t, c0 + cd * 0.8, CUE["catch_say"][1], 0.15, 0.4)
        if la > 0:
            # Dandy turns Jo's agent away: a purple bar across the card's lower edge and a lock on the card
            flash = 1 + 0.6 * math.exp(-max(0, t - c0 - cd * 0.8) * 5)
            d.rounded_rectangle((x0 + 8, y1 - 8, x1 - 8, y1 + 8), radius=8, fill=PURPLE_LIGHT + (int(230 * la),))
            put_glow(img, (x0 + x1) / 2, y1, 170 * flash, PURPLE, 0.6 * la)
            lx, ly = (x0 + x1) / 2, (y0 + y1) / 2 + 14
            d.rounded_rectangle((lx - 22, ly - 4, lx + 22, ly + 30), radius=6, fill=PURPLE + (int(255 * la),))
            d.arc((lx - 15, ly - 28, lx + 15, ly + 4), 180, 360, fill=PURPLE_LIGHT + (int(255 * la),), width=6)
            d.ellipse((lx - 5, ly + 6, lx + 5, ly + 16), fill=INK + (int(255 * la),))
        r0, rd = CUE["review"]
        if r0 <= t <= r0 + rd + 0.2:
            # Jo's agent reviews Sam's page: a coral magnifier sweeps across it
            u = ease_io((t - r0) / rd)
            a_ = win(t, r0, r0 + rd, 0.15, 0.2)
            mx_, my_ = lerp(x0 + 50, x1 - 70, u), (y0 + y1) / 2 + 18 + 12 * math.sin(u * math.pi * 2)
            put_glow(img, mx_, my_, 70, CORAL, 0.5 * a_)
            d.ellipse((mx_ - 26, my_ - 26, mx_ + 26, my_ + 26), outline=CORAL + (int(255 * a_),), width=6)
            d.line(((mx_ + 18, my_ + 18), (mx_ + 40, my_ + 40)), fill=CORAL + (int(255 * a_),), width=8)
        q = ease_out((t - r0 - rd - 0.05) / 0.35)
        if q > 0:
            cx, cy = x1 - 30, y1 - 30
            put_glow(img, cx, cy, 60, TEXT, 0.4 * q * math.exp(-max(0, t - r0 - rd) * 2))
            d.line(((cx - 12, cy), (cx - 3, cy + 9), (cx + 14, cy - 10)), fill=TEXT + (int(255 * q),), width=5, joint="curve")
    if sid in ("payoff", "end") and layers:
        cx, cy = x1 - 30, y1 - 30
        q = ease_out((t - 0.2 - 0.15 * i) / 0.4) if sid == "payoff" else 1
        if q > 0:
            d.line(((cx - 12, cy), (cx - 3, cy + 9), (cx + 14, cy - 10)), fill=TEXT + (int(255 * q),), width=5, joint="curve")


_hat = {}


def hat_img(h):
    if h not in _hat:
        hat = Image.open(os.path.join(ROOT, "motifs", "logo-hat-light.png")).convert("RGBA")
        _hat[h] = hat.resize((int(hat.width * h / hat.height), h), Image.LANCZOS)
    return _hat[h].copy()


def draw_wires(img, tg):
    d = ImageDraw.Draw(img, "RGBA")
    m = map_amount(tg)
    # the runs inside the slab along the band edges
    for owner, y in (("sam", BAND[1] - 8), ("jo", BAND[3] + 8)):
        col = mix(OWNER[owner][1], (40, 34, 60), 0.55)
        d.line(((TILES[0][0] + 60, y), (TILES[2][2] - 60, y)), fill=col + (255,), width=6)
        for k in range(3):
            tx = (TILES[k][0] + TILES[k][2]) / 2
            d.line(((tx, y), (tx, TILES[k][1] if owner == "sam" else TILES[k][3])), fill=col + (255,), width=6)
    sid, t = scene_at(tg)
    if sid == "fix":
        c0, cd = CUE["catch"]
        q = (t - c0) / cd
        if 0 <= q <= 1.7:
            pts = wire_path("jo", 2)
            p = 0.92 * ease_out(q / 0.8) if q < 0.8 else 0.92 - 0.25 * ease_out((q - 0.8) / 0.9)
            a_ = 1 - smooth((q - 1.1) / 0.6)
            x, y = along(pts, p)
            put_glow(img, x, y, 44, CORAL, 0.9 * a_)
            d.rounded_rectangle((x - 13, y - 16, x + 13, y + 16), radius=4, fill=CORAL_SOFT + (int(255 * a_),), outline=CORAL + (int(255 * a_),), width=2)
    for owner, tile, p in pulses(tg):
        pts = wire_path(owner, tile)
        x, y = along(pts, ease_io(p))
        col = OWNER[owner][0]
        put_glow(img, x, y, 44, col, 0.9)
        d.rounded_rectangle((x - 13, y - 16, x + 13, y + 16), radius=4, fill=OWNER[owner][2] + (255,), outline=col + (255,), width=2)
        for k in range(3):
            d.line(((x - 7, y - 8 + k * 7), (x + 7 - (k == 2) * 5, y - 8 + k * 7)), fill=OWNER[owner][1] + (255,), width=2)


# ---------------------------------------------------------------- monitors, callouts and texts
def monitor(img, who, tg, lines_n, typing=None, dandy=False):
    """A small Claude Code chat: owner messages on the right, agent replies on the left as grey bars."""
    x0, y0, x1, y1 = MON_SAM if who == "sam" else MON_JO
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((x0, y0, x1, y1), radius=6, fill=SCREEN_BG + (255,))
    col = OWNER[who][0]
    d.rectangle((x0, y0, x1, y0 + 20), fill=(30, 24, 50, 255))
    for i, c in enumerate(((255, 107, 107), (245, 197, 66), (120, 200, 120))):
        d.ellipse((x0 + 8 + i * 14, y0 + 6, x0 + 16 + i * 14, y0 + 14), fill=c + (255,))
    y = y0 + 30
    rnd = random.Random(7 if who == "sam" else 8)
    for k in range(lines_n):
        mine = k % 2 == 0
        wf = rnd.uniform(0.35, 0.7)
        bw = (x1 - x0 - 30) * wf
        if mine:
            d.rounded_rectangle((x1 - 12 - bw, y, x1 - 12, y + 14), radius=6, fill=col + (220,))
        else:
            d.rounded_rectangle((x0 + 12, y, x0 + 12 + bw, y + 14), radius=6, fill=(110, 100, 140, 220))
        y += 22
        if y > y1 - 36:
            break
    if typing:
        d.rounded_rectangle((x0 + 10, y1 - 28, x1 - 10, y1 - 8), radius=6, outline=col + (200,), width=2)
    if dandy:
        d.line(((x1 - 70, y0 + 24), (x1 - 70, y1 - 4)), fill=PURPLE + (255,), width=2)
        hat = hat_img(18)
        img.alpha_composite(hat, (int(x1 - 58), int(y0 + 28)))
        for k in range(3):
            c = (TEAL, CORAL, TEAL)[k]
            d.rounded_rectangle((x1 - 60, y0 + 56 + k * 26, x1 - 10, y0 + 74 + k * 26), radius=4, outline=PURPLE_LIGHT + (255,), width=2)
            d.ellipse((x1 - 22, y0 + 61 + k * 26, x1 - 14, y0 + 69 + k * 26), fill=c + (255,))
    # screen glow into the room at night
    put_glow(img, (x0 + x1) / 2, (y0 + y1) / 2, 260, mix(col, (200, 210, 255), 0.5), 0.18)


def callout(img, who, text, t, at, until, name, typed=False):
    """An agent's reply (or the owner's typed line) shown large above the monitor."""
    a = win(t, at, until, 0.25, 0.3)
    if a <= 0.01:
        return
    x0, y0, x1, y1 = MON_SAM if who == "sam" else MON_JO
    f = font("Inter-SemiBold.otf", 34)
    shown = text
    if typed:
        n = int((t - at) / 0.045)
        shown = text[:max(0, n)]
    lines = wrap(text, f, 640)
    shown_lines = wrap(shown, f, 640) if shown else [""]
    d = ImageDraw.Draw(img, "RGBA")
    lh = 44
    tw = max(d.textlength(l, font=f) for l in lines)
    bw, bh = tw + 76, len(lines) * lh + 30
    cx = (x0 + x1) / 2 if who == "sam" else (x0 + x1) / 2 + 120
    cx = min(max(cx, SAFE[0] + bw / 2), SAFE[2] - bw / 2)
    by1 = y0 - 26
    by0 = by1 - bh
    bx0 = cx - bw / 2
    lift = (1 - ease_out((t - at) / 0.3)) * 14
    by0 += lift
    by1 += lift
    col = OWNER[who][0]
    d.rounded_rectangle((bx0, by0, bx0 + bw, by1), radius=18, fill=(14, 10, 26, int(235 * a)), outline=col + (int(255 * a),), width=3)
    # tail toward the monitor
    tx = min(max((x0 + x1) / 2, bx0 + 40), bx0 + bw - 40)
    d.polygon([(tx - 14, by1 - 2), (tx + 14, by1 - 2), (tx, by1 + 16)], fill=(14, 10, 26, int(235 * a)))
    # a prompt glyph in the owner's colour: typed lines get ">", agent replies get a small square
    gx, gy = bx0 + 26, by0 + 15 + lh / 2
    if typed:
        d.text((gx, gy), ">", font=f, fill=col + (int(255 * a),), anchor="lm")
    else:
        d.rounded_rectangle((gx - 2, gy - 9, gx + 16, gy + 9), radius=4, fill=col + (int(255 * a),))
    for k, line in enumerate(shown_lines):
        d.text((bx0 + 54, by0 + 15 + k * lh), line, font=f, fill=TEXT + (int(255 * a),))
    if typed and int(t * 2.5) % 2 == 0 and len(shown) < len(text):
        last = shown_lines[-1]
        cxp = bx0 + 54 + d.textlength(last, font=f) + 2
        cy0 = by0 + 15 + (len(shown_lines) - 1) * lh
        d.line(((cxp, cy0 + 4), (cxp, cy0 + 38)), fill=col + (int(255 * a),), width=3)
    if a > 0.5:
        record(name, text, lines, (bx0 + 54, by0 + 15, bx0 + 54 + tw, by0 + 15 + len(lines) * lh))


def text_bubble(img, who, text, t, at, until, name):
    """A phone text, in the sender's colour, beside their head."""
    a = win(t, at, until, 0.2, 0.3)
    if a <= 0.01:
        return
    f = font("Inter-SemiBold.otf", 36)
    lines = wrap(text, f, 470)
    d = ImageDraw.Draw(img, "RGBA")
    lh = 46
    tw = max(d.textlength(l, font=f) for l in lines)
    bw, bh = tw + 48, len(lines) * lh + 26
    if who == "sam":
        hx, hy = HIP_SAM[0] + 34, HIP_SAM[1] - 200
        bx0 = hx + 70
        by0 = hy - 160
    else:
        hx, hy = HIP_JO[0] - 34, HIP_JO[1] - 200
        bx0 = hx - 40 - bw
        by0 = BAND[3] + 22
    bx0 = min(max(bx0, SAFE[0]), SAFE[2] - bw)
    pop = spring(clamp((t - at) / 0.35))
    s = 0.6 + 0.4 * pop
    cxb, cyb = bx0 + bw / 2, by0 + bh / 2
    col = OWNER[who][0]
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay, "RGBA")
    ld.rounded_rectangle((bx0, by0, bx0 + bw, by0 + bh), radius=24, fill=col + (255,))
    tx = bx0 + 30 if who == "sam" else bx0 + bw - 30
    ld.polygon([(tx - 12, by0 + bh - 4), (tx + 12, by0 + bh - 4), (tx + (-16 if who == "sam" else 16), by0 + bh + 18)], fill=col + (255,))
    for k, line in enumerate(lines):
        ld.text((bx0 + 24, by0 + 13 + k * lh), line, font=f, fill=INK + (255,))
    if abs(s - 1) > 0.01:
        lay = lay.resize((int(W * s), int(H * s)), Image.BILINEAR)
        ox, oy = int(cxb - cxb * s), int(cyb - cyb * s)
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        canvas.alpha_composite(lay, (max(0, ox), max(0, oy)))
        lay = canvas
    if a < 1:
        lay.putalpha(lay.split()[3].point(lambda v: int(v * a)))
    img.alpha_composite(lay)
    if a > 0.5 and pop > 0.9:
        record(name, text, lines, (bx0 + 24, by0 + 13, bx0 + 24 + tw, by0 + 13 + len(lines) * lh))


# ---------------------------------------------------------------- frame assembly
def lamp_glow(img, dl):
    a = 1 - dl
    put_glow(img, 356, 410, 260, (255, 210, 150), 0.42 * a)
    put_glow(img, 330, 1080, 240, (255, 190, 150), 0.0)
    put_glow(img, 600, 1035, 220, (255, 196, 140), 0.32 * a)   # string-light shelf glow downstairs


def night_tint(img, dl):
    """Rooms are darker at night (multiplied), lit by lamps and screens afterwards."""
    a = (1 - dl) * 0.42
    if a <= 0.01:
        return img
    arr = np.asarray(img, np.float32)
    tint = np.array([0.72, 0.68, 1.0], np.float32)
    arr[..., :3] = arr[..., :3] * (1 - a) + arr[..., :3] * tint * 0.5 * a
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def compose(tg):
    sid, t = scene_at(tg)
    dl = daylight(tg)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    draw_sky(img, dl, tg)
    img.alpha_composite(static("house"))
    (sp, se), (jp, je) = poses(tg)
    img.alpha_composite(static(("sam", sp, se)))
    img.alpha_composite(static(("jo", jp, je)))
    img = night_tint(img, dl)
    lamp_glow(img, dl)
    # monitors
    if sid in ("setup", "problem", "switch", "fix"):
        n_sam = 2 + int(max(0, tg - START["setup"]) * 0.9) % 6
        n_jo = 2 + int(max(0, tg - START["setup"] - 0.4) * 0.9) % 6
        dandy = map_amount(tg) > 0.6
        monitor(img, "sam", tg, n_sam, typing=sid == "switch", dandy=dandy)
        monitor(img, "jo", tg, n_jo, dandy=dandy)
    else:
        for who in ("sam", "jo"):
            x0, y0, x1, y1 = MON_SAM if who == "sam" else MON_JO
            ImageDraw.Draw(img, "RGBA").rounded_rectangle((x0, y0, x1, y1), radius=6, fill=(26, 22, 44, 255))
    dim = 0.38 if sid == "hook" else 1.0
    draw_wires(img, tg)
    draw_band(img, tg, dim)
    # story beats
    if sid == "hook":
        text_bubble(img, "sam", "did you delete my bills page??", t, CUE["hook_sam"], 99, "sam text")
        text_bubble(img, "jo", "no?? you rebuilt my chores page", t, CUE["hook_jo"], 99, "jo text")
    elif sid == "problem":
        callout(img, "sam", "Bills page done.", t, CUE["p_sam_bills"] + 0.75, CUE["p_jo_bills"] - 0.15, "sam agent 1")
        callout(img, "jo", "No bills page found. Building one.", t, CUE["p_jo_bills"] - 0.1, CUE["p_jo_bills"] + 1.15, "jo agent 1")
    elif sid == "switch":
        a, d = CUE["type"]
        callout(img, "sam", "point it at Dandy", t, a, 99, "sam types", typed=True)
    elif sid == "fix":
        callout(img, "sam", "Jo's agent is working on Chores. I'll take Groceries.", t, CUE["f_say"], CUE["f_say"] + 4.2, "sam agent 2")
        callout(img, "jo", "Groceries already has a writer. Picking another page.", t, CUE["catch_say"][0], CUE["catch_say"][1], "jo agent 2")
    elif sid == "payoff":
        text_bubble(img, "jo", "ok who built groceries, it's good", t, CUE["pay_jo"], 99, "jo text 2")
        text_bubble(img, "sam", "we did", t, CUE["pay_sam"], 99, "sam text 2")
    # the rewind: tape streaks across the frame
    if sid == "setup":
        a, b = CUE["rewind"]
        r = win(t, a - 0.01, b - 0.15, 0.05, 0.2)
        if r > 0:
            arr = np.asarray(img).copy()
            rnd = np.random.default_rng(int(tg * 1000))
            for _ in range(int(14 * r)):
                y0 = int(rnd.integers(0, H - 40))
                hgt = int(rnd.integers(6, 40))
                arr[y0:y0 + hgt] = np.roll(arr[y0:y0 + hgt], int(rnd.integers(-90, 90) * r), axis=1)
            img = Image.fromarray(arr)
            d = ImageDraw.Draw(img, "RGBA")
            for k in range(2):
                x = W / 2 - 40 + k * 46
                d.polygon([(x + 40, H * 0.3 - 30), (x + 40, H * 0.3 + 30), (x, H * 0.3)], fill=(255, 255, 255, int(200 * r)))
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
    a = ease_out((t - 0.45) / 0.6)
    if a > 0:
        hh = int(H * 0.11)
        hat = hat_img(hh)
        hat.putalpha(hat.split()[3].point(lambda v: int(v * a)))
        hy = H * 0.34 + (1 - a) * 40
        bg.alpha_composite(hat, (int(W / 2 - hat.width / 2), int(hy)))
        fh = font("Inter-Bold.otf", int(sizes["headline"] * 1.5))
        tw = d.textlength("Dandy", font=fh)
        ty = H * 0.34 + hh + 40
        d.text((W / 2 - tw / 2, ty), "Dandy", font=fh, fill=rgb(PAL["text"]) + (int(255 * a),))
        yy = ty + fh.size * 1.1 + 60
        for i, line in enumerate(CONTRACT["copy_rules"]["end_card_lines"]):
            b = ease_out((t - 0.85 - 0.25 * i) / 0.5)
            fl = font("Inter-Medium.otf", sizes["body" if i == 0 else "caption"])
            lw = d.textlength(line, font=fl)
            d.text((W / 2 - lw / 2, yy), line, font=fl, fill=(rgb(PAL["accent_gold"]) if i == 1 else rgb(PAL["soft"])) + (int(255 * b),))
            yy += fl.size * 1.1 + 50
    return bg


def caption_layout(text):
    fnt = font("Inter-Bold.otf", int(CONTRACT["type"]["vertical"]["body"] * 0.92))
    d = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    maxw = SAFE[2] - SAFE[0] - 40
    if d.textlength(text, font=fnt) <= maxw:
        lines = [text]
    else:
        words, best = text.split(), None
        for k in range(1, len(words)):
            a, b = " ".join(words[:k]), " ".join(words[k:])
            wa, wb = d.textlength(a, font=fnt), d.textlength(b, font=fnt)
            if wa <= maxw and wb <= maxw and (best is None or max(wa, wb) < best[0]):
                best = (max(wa, wb), [a, b])
        lines = best[1] if best else wrap(text, fnt, maxw)
    lh, pad = fnt.size * 1.18, 20
    y = SAFE[3] - len(lines) * (lh + pad * 0.6) - 6
    boxes = []
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=fnt)
        boxes.append((line, W / 2 - tw / 2, y + i * (lh + pad * 0.6), tw, lh))
    return fnt, boxes, pad


def draw_caption(img, tg):
    cue = next((c for c in CAPTIONS if c[0] <= tg < c[1]), None)
    if cue is None:
        return
    a = min(1.0, (tg - cue[0]) / 0.2, (cue[1] - tg) / 0.18)
    fnt, boxes, pad = caption_layout(cue[2])
    d = ImageDraw.Draw(img, "RGBA")
    for line, x, yy, tw, lh in boxes:
        d.rounded_rectangle((x - pad, yy - pad * 0.55, x + tw + pad, yy + lh + pad * 0.3), radius=14, fill=(8, 6, 16, int(190 * a)))
        d.text((x, yy), line, font=fnt, fill=TEXT + (int(255 * a),))


def caption_box(tg):
    cue = next((c for c in CAPTIONS if c[0] <= tg < c[1]), None)
    if cue is None:
        return None
    fnt, boxes, pad = caption_layout(cue[2])
    return dict(name="caption", type="caption", role="body", text=cue[2], lines=[b[0] for b in boxes],
                bbox=(min(b[1] for b in boxes) - pad, boxes[0][2] - pad * 0.55, max(b[1] + b[3] for b in boxes) + pad, boxes[-1][2] + boxes[-1][4] + pad * 0.3))


_last = {}


def frame(tg):
    sid, t = scene_at(tg)
    if sid == "end":
        if "last" not in _last:
            _last["last"] = compose(START["end"] - 1 / FPS)
        img = end_card(_last["last"], t)
        fr = finish(img, t, tg, bloom=0.3, grain=2.0, vignette=0.3, drift=0.0, zoom=1.0)
    else:
        img = compose(tg)
        fr = finish(img, t, tg, bloom=0.32, grain=2.4, vignette=0.32, drift=0.35, zoom=1.0)
    draw_caption(fr, tg)
    return fr.convert("RGB")


# ---------------------------------------------------------------- QA
QA_TIMES = {"hook": [3.6], "setup": [3.0, 5.5], "problem": [2.0, 3.4, 4.6, 6.8], "switch": [2.0, 3.4], "fix": [2.5, 4.8, 7.6, 9.5, 12.4, 14.2], "payoff": [2.6, 4.3]}


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
            compose(tg)
            els = list(REC)
            cb = caption_box(tg)
            if cb:
                els.append(cb)
            REC = None
            scenes.append(dict(id=f"{sid}@{ts}", type="cutaway", duration=dur, laid_out=els))
    problems = [f"{s}: {m}" for s, m in run_all(scenes, CONTRACT["canvases"]["vertical"], CONTRACT)]
    rules = CONTRACT["copy_rules"]
    for _, _, tx in CAPTIONS:
        for ch in rules["banned_characters"]:
            if ch in tx:
                problems.append(f"caption: banned character in {tx!r}")
        for ph in rules["banned_phrases"] + ["state layer"]:
            if ph in tx.lower():
                problems.append(f"caption: banned phrase {ph!r} in {tx!r}")
        if len(tx.split()) > CONTRACT["type"]["max_words_on_screen"] + 2:
            problems.append(f"caption: too many words in {tx!r}")
    return problems


# ---------------------------------------------------------------- sound (effects only; Charlie brings the music)
SR = 48000
_rng = np.random.default_rng(15)


def _band(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x).astype(np.float32)


def _n(x, g):
    return x / (np.abs(x).max() + 1e-9) * g


def snd_chime(g=0.3, f0=1320):
    n = int(SR * 0.5)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f0 * t) * np.exp(-t * 9) + 0.6 * np.sin(2 * np.pi * f0 * 1.5 * t) * np.exp(-t * 12) * (t > 0.07)
    return _n(x * (1 - np.exp(-t * 400)), g)


def snd_tick(g=0.12):
    n = int(SR * 0.03)
    t = np.arange(n) / SR
    return _n(_band(_rng.normal(0, 1, n), 2000, 8000) * np.exp(-t * 300), g)


def snd_whoosh(g=0.3, dur=0.6, lo=200, hi=2500):
    n = int(SR * dur)
    t = np.arange(n) / SR
    return _n(_band(_rng.normal(0, 1, n), lo, hi) * np.sin(np.pi * t / dur) ** 2, g)


def snd_rewind(g=0.32, dur=0.85):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 300 + 1800 * (t / dur) ** 0.5
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3 + _band(_rng.normal(0, 1, n), 800, 6000) * 0.7
    return _n(x * np.sin(np.pi * t / dur) ** 0.5, g)


def snd_blip(g=0.2, f=880):
    n = int(SR * 0.3)
    t = np.arange(n) / SR
    return _n(np.sin(2 * np.pi * f * t) * np.exp(-t * 12) * (1 - np.exp(-t * 300)), g)


def snd_crumple(g=0.35, dur=0.5):
    n = int(SR * dur)
    t = np.arange(n) / SR
    env = (_rng.random(n) > 0.985).astype(np.float32)
    env = np.convolve(env, np.exp(-np.arange(400) / 60), mode="same")
    return _n(_band(_rng.normal(0, 1, n), 1500, 8000) * env * np.exp(-t * 3), g)


def snd_thud(g=0.25):
    n = int(SR * 0.3)
    t = np.arange(n) / SR
    return _n(np.sin(2 * np.pi * (90 + 40 * np.exp(-t * 30)) * t) * np.exp(-t * 14), g)


def snd_denied(g=0.26):
    n = int(SR * 0.42)
    t = np.arange(n) / SR
    x = np.sign(np.sin(2 * np.pi * 220 * t)) * (t < 0.18) + np.sign(np.sin(2 * np.pi * 175 * t)) * (t >= 0.2)
    x = sosfilt(butter(2, 1400, btype="low", fs=SR, output="sos"), x).astype(np.float32)
    return _n(x * np.exp(-((t % 0.2) * 6)), g)


def snd_chord(g=0.22, root=261.6, dur=2.2):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * root * r * t) * np.exp(-t * 1.8) for r in (1, 1.26, 1.5, 2.0))
    return _n(x * (1 - np.exp(-t * 60)), g)


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
    put(snd_chime(0.32, 1320), S["hook"] + CUE["hook_sam"], -0.2)
    put(snd_chime(0.32, 1175), S["hook"] + CUE["hook_jo"], 0.2)
    put(snd_rewind(0.34, CUE["rewind"][1]), S["setup"] + CUE["rewind"][0], 0.0)
    # typing through the night scenes
    rnd = random.Random(3)
    for sid in ("setup", "problem", "fix"):
        t = S[sid] + (1.0 if sid == "setup" else 0.2)
        end = S[sid] + dict(SCENES)[sid] - 0.2
        while t < end:
            put(snd_tick(0.05), t, rnd.choice((-0.4, 0.4)))
            t += rnd.uniform(0.08, 0.22)
    for k, owner in (("p_sam_bills", "sam"), ("p_jo_bills", "jo"), ("p_jo_chores", "jo"), ("p_sam_chores", "sam"), ("p_sam_bills2", "sam")):
        put(snd_whoosh(0.14, 0.65, 400, 3000), S["problem"] + CUE[k], -0.3 if owner == "sam" else 0.3)
        put(snd_blip(0.16, 660 if owner == "sam" else 520), S["problem"] + CUE[k] + 0.68, 0.0)
    for k in ("p_jo_bills", "p_sam_chores", "p_sam_bills2"):
        put(snd_crumple(0.3), S["problem"] + CUE[k] + 0.65, 0.0)
        put(snd_thud(0.12), S["problem"] + CUE[k] + 0.9, 0.0)
    a, d = CUE["type"]
    t = S["switch"] + a
    while t < S["switch"] + a + d:
        put(snd_tick(0.07), t, -0.3)
        t += 0.07
    put(snd_chord(0.2, 261.6), S["switch"] + CUE["map"][0], 0.0)
    put(snd_whoosh(0.12, 1.0, 300, 3000), S["switch"] + CUE["map"][0] - 0.1, 0.0)
    put(snd_blip(0.14, 740), S["fix"] + CUE["f_say"], -0.3)
    for owner, t0 in (("jo", CUE["f_jo"]), ("sam", CUE["f_sam"])):
        k = 0
        while t0 + k * 0.55 < CUE["f_build"][0] + CUE["f_build"][1]:
            put(snd_blip(0.06, 520 if owner == "jo" else 660), S["fix"] + t0 + k * 0.55 + 0.65, 0.3 if owner == "jo" else -0.3)
            k += 1
    put(snd_whoosh(0.14, 0.6, 400, 3000), S["fix"] + CUE["catch"][0], 0.3)
    put(snd_denied(0.26), S["fix"] + CUE["catch"][0] + CUE["catch"][1] * 0.8, 0.0)
    put(snd_whoosh(0.1, CUE["review"][1], 900, 5000), S["fix"] + CUE["review"][0], 0.0)
    put(snd_chime(0.26, 1568), S["fix"] + CUE["review"][0] + CUE["review"][1] + 0.05, 0.0)
    put(snd_chime(0.3, 1175), S["payoff"] + CUE["pay_jo"], 0.2)
    put(snd_chime(0.3, 1320), S["payoff"] + CUE["pay_sam"], -0.2)
    put(snd_chord(0.18, 329.6, 2.6), S["end"] + 0.4, 0.0)
    peak = max(np.abs(L).max(), np.abs(R).max(), 1e-6)
    st = np.stack([L, R], 1)[:int(SR * TOTAL)] / peak * 0.6
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- timing file and render loop
def apply_timing():
    p = os.path.join(VIDEO, "voiceover", "cutaway.json")
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
    out = os.path.join(VIDEO, "out")
    os.makedirs(out, exist_ok=True)
    problems = qa()
    with open(os.path.join(out, "qa-cutaway-vertical.json"), "w") as f:
        json.dump(dict(canvas="vertical", look="apartment cutaway", duration=TOTAL, problems=problems,
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
    tmp = tempfile.mkdtemp(prefix="dandy-roommates-")
    jobs = [(k, i / FPS, os.path.join(tmp, f"f{k:06d}.png")) for k, i in enumerate(range(0, n_frames, step))]
    with Pool(workers) as pool:
        for done, _ in enumerate(pool.imap_unordered(_work, jobs, chunksize=4)):
            if done % 150 == 0:
                print(f"  {done}/{len(jobs)} frames", flush=True)
    wav = os.path.join(out, "cutaway-bed.wav")
    build_bed(wav)
    mp4 = os.path.join(out, "15-roommates-vertical.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS // step), "-i", os.path.join(tmp, "f%06d.png"), "-i", wav]
    if vo and vo.get("file") and not preview:
        fade = vo.get("fade_s", 1.0)
        fc = (f"[2:a]atrim=start={vo.get('offset_s', 0)},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
              f"volume={vo.get('voice_db', 0)}dB,apad=whole_dur={TOTAL},asplit=2[v][vk];[1:a]volume={vo.get('bed_db', -4)}dB[b];"
              f"[b][vk]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350[bd];"
              f"[v][bd]amix=inputs=2:normalize=0:duration=longest,atrim=0:{TOTAL},afade=t=out:st={TOTAL - fade}:d={fade},alimiter=limit=0.89:level=0[a]")
        cmd += ["-i", os.path.join(ROOT, vo["file"]), "-filter_complex", fc, "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18" if final else "21", "-preset", "slow" if final else "medium",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    if vo and vo.get("file") and not preview and vo.get("loudness_lufs"):
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

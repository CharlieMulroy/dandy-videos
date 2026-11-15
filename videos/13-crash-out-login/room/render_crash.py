"""Video 13, crash-out: "We already have a login page". The night room from video 02, with a new builder at the desk.

Usage:  python3 videos/13-crash-out-login/room/render_crash.py [--preview] [--stills] [--final]

Cold open mid-meltdown (the agent has just built a third login page), a smash cut in close, head on the desk. Then
Dandy Man walks in from the right and brings the purple light with him: the agent's light wanders because it cannot
see what is built, a map of the project blooms over the wall, the agent reads it, skips Login and starts on Payments.
End card with Dandy Man.

The wall, window, board and rug are video 02's back layer (videos/02-maya/lofi/layers/back.svg). The builder, the desk
and the monitor are drawn here, with the desk kept left of centre so Dandy Man has the right of the frame. Dandy Man,
the map, the agent's light, captions, the end card, the sound bed and the render loop come from render/stage.py, so
all four shared checks run before a frame is drawn.

Timings are placeholders until Charlie records; they move to voiceover/stage.json ("durations", "file", "lines").
"""
import argparse
import io
import math
import os
import random
import sys

import cairosvg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "render"))
import stage as S  # noqa: E402
from stage import clamp, ease_out, smooth, lerp, mix, font  # noqa: E402

W, H = S.W, S.H
PAL = S.PAL
BACK_SVG = os.path.join(ROOT, "videos", "02-maya", "lofi", "layers", "back.svg")

# ---------------------------------------------------------------- the room (video 02's coordinates, lifted 48 px)
LIFT_Y = 48                          # the whole room sits 48 px higher so captions clear the floor line
FLOOR, DESK_Y = 1420, 1180
HIP = (270, 1250)
SCREEN = (508, 926, 758, 1096)       # the monitor's screen
WINDOW = (640, 300, 1000, 760)
BOARD = (80, 330, 580, 780)
WOOD, WOOD_DARK = "#4A3566", "#33234A"
HOOD, HOOD_DARK, SKIN, SKIN_DARK, HAIR, PANTS = "#3F8E6A", "#2C6A50", "#C98F68", "#A9744F", "#1B1226", "#51468A"
FLOOR_RGB = (18, 10, 32)
CLOSE = (1.35, 115, 240)             # the smash-cut framing: zoom, then the crop's left and top
WIDE = (1.0, 0, 0)


def svg(body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">\n' + "\n".join(body) + "\n</svg>\n"


def sky_svg():
    x0, y0, x1, y1 = WINDOW
    rnd = random.Random(5)
    stars = [f'<circle cx="{rnd.uniform(x0 + 10, x1 - 10):.0f}" cy="{rnd.uniform(y0 + 10, y1 - 60):.0f}" r="{rnd.uniform(1.5, 3.2):.1f}" fill="#F3EEFF" opacity="{rnd.uniform(0.4, 0.9):.2f}"/>'
             for _ in range(26)]
    return svg(['<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0E0A1F"/><stop offset="1" stop-color="#1C1440"/></linearGradient></defs>',
                f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="url(#sky)"/>', *stars,
                f'<circle cx="{x1 - 90}" cy="{y0 + 110}" r="34" fill="#F3EEFF" opacity="0.85"/>',
                f'<circle cx="{x1 - 74}" cy="{y0 + 100}" r="30" fill="#141032"/>'])


def notes_svg():
    """A messy board: sticky notes and a few strings, so the room looks like a project that got away from someone."""
    bx0, by0, bx1, by1 = BOARD
    rnd = random.Random(11)
    cols = [PAL["soft"], PAL["highlight"], PAL["accent_gold"], PAL["soft"], PAL["highlight"], PAL["soft"], PAL["soft"]]
    b = []
    spots = [(110, 360), (250, 350), (400, 372), (130, 520), (290, 500), (430, 540), (220, 650)]
    for (x, y), c in zip(spots, cols):
        r = rnd.uniform(-9, 9)
        b.append(f'<g transform="rotate({r:.1f} {x + 55} {y + 50})"><rect x="{x}" y="{y}" width="112" height="100" rx="4" fill="{c}" opacity="0.55"/>'
                 + "".join(f'<rect x="{x + 12}" y="{y + 20 + k * 22}" width="{rnd.uniform(40, 86):.0f}" height="7" rx="3" fill="#1A0F2E" opacity="0.5"/>' for k in range(3))
                 + f'<circle cx="{x + 56}" cy="{y + 8}" r="6" fill="#F3EEFF" opacity="0.8"/></g>')
    for a, c in ((0, 4), (4, 2), (1, 5), (3, 6)):
        (xa, ya), (xb, yb) = spots[a], spots[c]
        b.append(f'<line x1="{xa + 56}" y1="{ya + 8}" x2="{xb + 56}" y2="{yb + 8}" stroke="{PAL["warning"]}" stroke-width="3" opacity="0.45"/>')
    return svg(b)


def front_svg():
    sx0, sy0, sx1, sy1 = SCREEN
    mx = (sx0 + sx1) / 2
    return svg([
        f'<rect x="340" y="{DESK_Y}" width="460" height="34" rx="10" fill="{WOOD}"/>',
        f'<rect x="360" y="{DESK_Y + 34}" width="26" height="{FLOOR - DESK_Y - 34}" fill="{WOOD_DARK}"/>',
        f'<rect x="754" y="{DESK_Y + 34}" width="26" height="{FLOOR - DESK_Y - 34}" fill="{WOOD_DARK}"/>',
        f'<rect x="360" y="{DESK_Y + 120}" width="420" height="14" fill="{WOOD_DARK}"/>',
        f'<rect x="{mx - 16}" y="{sy1 + 16}" width="32" height="{DESK_Y - 16 - sy1 - 16}" fill="{WOOD_DARK}"/>',
        f'<rect x="{mx - 90}" y="{DESK_Y - 16}" width="180" height="16" rx="6" fill="{WOOD_DARK}"/>',
        f'<rect x="{sx0 - 16}" y="{sy0 - 16}" width="{sx1 - sx0 + 32}" height="{sy1 - sy0 + 32}" rx="14" fill="#120A20"/>',
        f'<rect x="380" y="{DESK_Y - 14}" width="116" height="14" rx="5" fill="{PAL["background_lift"]}"/>',
        f'<rect x="{sx1 - 34}" y="{sy0 - 10}" width="48" height="48" rx="3" fill="{PAL["accent_gold"]}" transform="rotate(8 {sx1 - 10} {sy0 + 14})" opacity="0.85"/>',
    ])


# pose: head centre, head tilt (degrees, clockwise), torso, near arm, far arm, face
def builder_svg(pose):
    hx0, hy0 = HIP
    b = [
        f'<rect x="{hx0 - 120}" y="1040" width="34" height="240" rx="14" fill="{WOOD}"/>',
        f'<rect x="{hx0 - 110}" y="1255" width="190" height="30" rx="12" fill="{WOOD}"/>',
        f'<rect x="{hx0 - 28}" y="1285" width="26" height="110" fill="{WOOD}"/>',
        f'<path d="M{hx0 - 100} 1400 L{hx0 + 70} 1400" stroke="{WOOD}" stroke-width="18" stroke-linecap="round"/>',
    ]
    upright = f'M{hx0 - 20} 1270 L{hx0 - 8} 1000 Q{hx0 + 40} 960 {hx0 + 110} 1010 L{hx0 + 60} 1270 Z'
    folded = f'M{hx0 - 10} 1270 Q{hx0 + 30} 1130 {hx0 + 120} 1140 L{hx0 + 150} 1196 Q{hx0 + 60} 1200 {hx0 + 30} 1280 Z'
    far = near = ""
    hands = []
    if pose == "hair":         # both hands in the hair, elbows out
        torso, head, tilt, face = upright, (hx0 + 55, 928), -6, "yell"
        far = f'M{hx0 + 30} 1050 L{hx0 - 52} 985 L{hx0 + 24} 880'
        near = f'M{hx0 + 58} 1052 L{hx0 + 152} 1000 L{hx0 + 96} 882'
        hands = [(hx0 + 22, 874), (hx0 + 94, 876)]
    elif pose == "shout":      # arms thrown up
        torso, head, tilt, face = upright, (hx0 + 50, 926), -16, "shout"
        far = f'M{hx0 + 30} 1050 L{hx0 - 56} 838'
        near = f'M{hx0 + 58} 1052 L{hx0 + 158} 842'
        hands = [(hx0 - 60, 826), (hx0 + 162, 830)]
    elif pose in ("desk", "peek"):
        torso = folded
        head, tilt, face = ((hx0 + 165, 1128), 82, "none") if pose == "desk" else ((hx0 + 156, 1094), 46, "wary")
        near = f'M{hx0 + 108} 1168 L{hx0 + 112} 1318'
        hands = [(hx0 + 112, 1332)]
    elif pose == "watch":      # sitting up, looking up at the map
        torso, head, tilt, face = upright, (hx0 + 56, 930), -14, "oh"
        near = f'M{hx0 + 50} 1070 Q{hx0 + 120} 1120 {hx0 + 190} 1166'
        hands = [(hx0 + 200, 1168)]
    else:                      # "up": calm, hands back on the keyboard
        torso, head, tilt, face = upright, (hx0 + 60, 930), 0, "smile"
        near = f'M{hx0 + 50} 1070 Q{hx0 + 120} 1120 {hx0 + 190} 1166'
        hands = [(hx0 + 200, 1168)]
    hx, hy = head
    arm = 'stroke-width="42" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    b += [f'<path d="M{hx0} 1262 L{hx0 + 150} 1262 L{hx0 + 150} 1400" stroke="{PANTS}" stroke-width="52" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
          f'<ellipse cx="{hx0 + 168}" cy="1408" rx="40" ry="16" fill="{PAL["text"]}"/>']
    if far:
        b.append(f'<path d="{far}" stroke="{HOOD_DARK}" {arm}/>')
    b.append(f'<path d="{torso}" fill="{HOOD}"/>')
    dark = "#2A0E1C"
    f = [f'<circle cx="{hx}" cy="{hy}" r="54" fill="{SKIN}"/>',
         f'<path d="M{hx - 56} {hy + 12} Q{hx - 64} {hy - 64} {hx} {hy - 60} Q{hx + 50} {hy - 58} {hx + 52} {hy - 14} Q{hx + 22} {hy - 36} {hx - 18} {hy - 22} Q{hx - 40} {hy - 8} {hx - 56} {hy + 12} Z" fill="{HAIR}"/>',
         *[f'<circle cx="{hx + dx}" cy="{hy + dy}" r="17" fill="{HAIR}"/>' for dx, dy in ((-46, -30), (-28, -52), (0, -60), (28, -52), (46, -34))],
         f'<circle cx="{hx - 8}" cy="{hy + 6}" r="10" fill="{SKIN_DARK}"/>']
    if face != "none":
        f += [f'<circle cx="{hx + 30}" cy="{hy - 2}" r="15" fill="none" stroke="{PAL["text"]}" stroke-width="4"/>',
              f'<line x1="{hx + 15}" y1="{hy - 4}" x2="{hx - 4}" y2="{hy}" stroke="{PAL["text"]}" stroke-width="4"/>']
    if face in ("yell", "shout"):
        ry = 13 if face == "yell" else 21
        f += [f'<path d="M{hx + 23} {hy - 9} L{hx + 37} {hy - 2} L{hx + 23} {hy + 5}" stroke="{HAIR}" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
              f'<path d="M{hx + 12} {hy - 30} L{hx + 44} {hy - 20}" stroke="{HAIR}" stroke-width="6" stroke-linecap="round"/>',
              f'<ellipse cx="{hx + 30}" cy="{hy + 28}" rx="{ry * 0.7:.0f}" ry="{ry}" fill="{dark}"/>']
    elif face == "wary":
        f += [f'<circle cx="{hx + 32}" cy="{hy - 4}" r="5" fill="{HAIR}"/>',
              f'<path d="M{hx + 16} {hy - 24} L{hx + 44} {hy - 28}" stroke="{HAIR}" stroke-width="5" stroke-linecap="round"/>',
              f'<path d="M{hx + 24} {hy + 26} L{hx + 42} {hy + 26}" stroke="{HAIR}" stroke-width="4" stroke-linecap="round"/>']
    elif face == "oh":
        f += [f'<circle cx="{hx + 32}" cy="{hy - 5}" r="6" fill="{HAIR}"/>',
              f'<path d="M{hx + 14} {hy - 30} Q{hx + 30} {hy - 38} {hx + 44} {hy - 30}" stroke="{HAIR}" stroke-width="5" fill="none" stroke-linecap="round"/>',
              f'<ellipse cx="{hx + 34}" cy="{hy + 28}" rx="7" ry="9" fill="{dark}"/>']
    elif face == "smile":
        f += [f'<circle cx="{hx + 31}" cy="{hy - 3}" r="5" fill="{HAIR}"/>',
              f'<path d="M{hx + 16} {hy - 26} Q{hx + 30} {hy - 32} {hx + 42} {hy - 25}" stroke="{HAIR}" stroke-width="5" fill="none" stroke-linecap="round"/>',
              f'<path d="M{hx + 18} {hy + 22} Q{hx + 32} {hy + 36} {hx + 44} {hy + 20}" stroke="{HAIR}" stroke-width="4" fill="none" stroke-linecap="round"/>']
    b.append(f'<g transform="rotate({tilt} {hx} {hy})">' + "".join(f) + "</g>")
    if near:
        b.append(f'<path d="{near}" stroke="{HOOD}" {arm}/>')
    b += [f'<circle cx="{x}" cy="{y}" r="20" fill="{SKIN}"/>' for x, y in hands]
    return svg(b)


_layers = {}


def layer(name, z):
    key = (name, z)
    if key not in _layers:
        kw = dict(output_width=int(W * z), output_height=int(H * z))
        if name == "back":
            png = cairosvg.svg2png(url=BACK_SVG, **kw)
        else:
            src = {"sky": sky_svg, "notes": notes_svg, "front": front_svg}.get(name)
            png = cairosvg.svg2png(bytestring=(src() if src else builder_svg(name)).encode(), **kw)
        _layers[key] = Image.open(io.BytesIO(png)).convert("RGBA")
    return _layers[key]


def to_out(x, y, cam=WIDE):
    """A point in room coordinates, as output pixels under a camera."""
    z, ox, oy = cam
    return x * z - ox, (y - LIFT_Y) * z - oy


# ---------------------------------------------------------------- the monitor
FILES = ["login", "login_new", "login_final"]


def draw_screen(z, mode, t, n_files=3, garble=0, new_at=None):
    """The screen at zoom z. mode: chat (the agent's cheerful message), files (the list that keeps growing), work."""
    w, h = int((SCREEN[2] - SCREEN[0]) * z), int((SCREEN[3] - SCREEN[1]) * z)
    scr = Image.new("RGB", (w, h), S.BG)
    d = ImageDraw.Draw(scr, "RGBA")
    u = lambda v: v * z  # noqa: E731
    d.rectangle((0, 0, w, u(18)), fill=S.BG_LIFT)
    for i, c in enumerate(((255, 107, 107), (245, 197, 66), (124, 77, 255))):
        d.ellipse((u(7 + i * 12), u(5), u(15 + i * 12), u(13)), fill=c)
    if mode == "chat":
        for k, (x0, wd) in enumerate(((120, 110), (14, 150))):
            d.rounded_rectangle((u(x0), u(28 + k * 30), u(x0 + wd), u(50 + k * 30)), radius=u(6), fill=S.PURPLE if k == 0 else S.BG_LIFT)
        d.rounded_rectangle((u(14), u(92), u(214), u(150)), radius=u(8), fill=S.BG_LIFT, outline=S.PURPLE_HI, width=max(1, int(u(2))))
        d.ellipse((u(24), u(104), u(46), u(126)), fill=S.PURPLE_HI)
        d.line((u(29), u(115), u(34), u(120), u(41), u(109)), fill=(255, 255, 255), width=max(2, int(u(3))))
        for k, wd in enumerate((130, 96)):
            d.rounded_rectangle((u(56), u(104 + k * 18), u(56 + wd), u(112 + k * 18)), radius=u(4), fill=S.SOFT)
    elif mode == "files":
        fnt = font("Inter-SemiBold.otf", u(21))
        for i, name in enumerate(FILES[:n_files]):
            y = 26 + i * 40
            newest = new_at is not None and i == n_files - 1
            p = ease_out((t - new_at) / 0.18) if newest else 1.0
            col = S.WARN if (i == 2) else S.SOFT
            d.rounded_rectangle((u(10), u(y), u(240), u(y + 34)), radius=u(6), fill=S.BG_LIFT + (int(255 * p),),
                                outline=col + (int((255 if i == 2 else 120) * p),), width=max(1, int(u(2))))
            d.rounded_rectangle((u(18), u(y + 7), u(34), u(y + 27)), radius=u(3), fill=S.SOFT + (int(255 * p),))
            d.text((u(44), u(y + 4)), name, font=fnt, fill=S.TEXT + (int(255 * p),))
        if garble:
            fg = font("Inter-Medium.otf", u(15))
            d.text((u(12), u(150)), GARBLE[:garble], font=fg, fill=S.SOFT)
    else:  # work: the agent getting on with the right piece
        d.rounded_rectangle((u(14), u(30), u(214), u(88)), radius=u(8), fill=S.BG_LIFT, outline=S.PURPLE_HI, width=max(1, int(u(2))))
        for k, wd in enumerate((160, 120)):
            d.rounded_rectangle((u(26), u(44 + k * 18), u(26 + wd), u(52 + k * 18)), radius=u(4), fill=S.SOFT)
        d.rounded_rectangle((u(14), u(108), u(236), u(124)), radius=u(8), fill=S.BG_LIFT)
        d.rounded_rectangle((u(14), u(108), u(14 + 222 * clamp(0.15 + 0.12 * t)), u(124)), radius=u(8), fill=S.GOLD)
    return scr


GARBLE = "jkjkjhjkkjhjkjk"

_scrims = {}


def scrim(kind):
    if kind not in _scrims:
        im = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(im)
        if kind == "wall":     # darkens the wall so the map reads
            d.rectangle((0, 0, W, 800), fill=255)
            im = im.filter(ImageFilter.GaussianBlur(60))
        elif kind == "top":    # behind the shouted line
            d.rectangle((0, 0, W, 560), fill=255)
            im = im.filter(ImageFilter.GaussianBlur(80))
        else:                  # the whole room, a touch dimmer before Dandy Man arrives
            im = Image.new("L", (W, H), 255)
        _scrims[kind] = im
    return _scrims[kind]


def darken(img, kind, a):
    if a <= 0:
        return
    img.paste((6, 3, 14), (0, 0), scrim(kind).point(lambda v: int(v * a)))


def room(t, pose, screen, cam=WIDE, shake=(0, 0), nudge=(0, 0), dim=0.1, purple=0.0, wall=0.0):
    """One frame of the room. screen: kwargs for draw_screen. nudge: the builder's own offset (trembling, the head drop)."""
    z, ox, oy = cam
    ox, oy = ox + shake[0], oy + shake[1]
    img = Image.new("RGB", (W, H), FLOOR_RGB)
    at = (int(-ox), int(-LIFT_Y * z - oy))
    for name in ("sky", "back", "notes"):
        lay = layer(name, z)
        img.paste(lay, at, lay)
    tw = ImageDraw.Draw(img, "RGBA")
    for i in range(10):       # the fairy lights breathe
        cx, cy = to_out(60 + i * 108, 150 + (60 if i % 2 else 10) + (i % 3) * 8, (z, ox, oy))
        r = 16 * z
        tw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=S.GOLD + (int(60 * (0.5 + 0.5 * math.sin(t * 2.2 + i * 1.7))),))
    b = layer(pose, z)
    img.paste(b, (at[0] + int(nudge[0] * z), at[1] + int(nudge[1] * z)), b)
    f = layer("front", z)
    img.paste(f, at, f)
    sx, sy = to_out(SCREEN[0], SCREEN[1], (z, ox, oy))
    img.paste(draw_screen(z, t=t, **screen), (int(sx), int(sy)))
    mx, my = to_out((SCREEN[0] + SCREEN[2]) / 2, (SCREEN[1] + SCREEN[3]) / 2, (z, ox, oy))
    S.put_sprite(img, S.GLOW_P, mx - 40 * z, my + 20 * z, scale=1.5 * z, alpha=0.3 * (0.9 + 0.1 * math.sin(t * 7.3)))
    darken(img, "room", dim)
    darken(img, "wall", wall)
    if purple > 0:            # Dandy Man's light, spilling in from the right
        S.put_sprite(img, S.GLOW_P, 1130, 1010, scale=4.6, alpha=0.62 * purple)
        S.put_sprite(img, S.GLOW_P, 900, 1380, scale=1.6, alpha=0.4 * purple)
    return img


# ---------------------------------------------------------------- overlays
def callout_layout(lines, box, size=44):
    fnt = font("Inter-Bold.otf", size)
    return fnt, [(box[0] + 88, box[1] + 26 + i * size * 1.3) for i in range(len(lines))]


def callout(img, box, lines, tip, t, alpha=1.0, pop=1.0, size=44):
    """The agent's message, lifted out of the monitor: a card with its little light and a tail down to the screen."""
    if alpha <= 0:
        return
    x0, y0, x1, y1 = box
    dy = (1 - pop) * 18
    y0, y1 = y0 + dy, y1 + dy
    d = ImageDraw.Draw(img, "RGBA")
    a = int(255 * alpha)
    d.rounded_rectangle((x0 + 4, y0 + 10, x1 + 4, y1 + 12), radius=26, fill=(0, 0, 0, int(110 * alpha)))
    d.polygon([(tip[0] - 26, y1 - 2), (tip[0] + 26, y1 - 2), (tip[0], tip[1] + dy)], fill=S.CARD + (a,))
    d.rounded_rectangle((x0, y0, x1, y1), radius=26, fill=S.CARD + (int(250 * alpha),), outline=S.SOFT + (int(170 * alpha),), width=3)
    S.orb(img, x0 + 50, (y0 + y1) / 2, t, alpha=alpha * 0.9)
    fnt, pos = callout_layout(lines, (x0, y0, x1, y1), size)
    d = ImageDraw.Draw(img, "RGBA")
    for line, (x, y) in zip(lines, pos):
        d.text((x, y), line, font=fnt, fill=S.TEXT + (a,))


SHOUT = ["WE ALREADY HAVE", "A LOGIN PAGE"]
SHOUT_SIZE = 92
SHOUT_Y = (300, 418)
_shout = {}


def shout_boxes():
    fnt = font("Inter-ExtraBold.otf", SHOUT_SIZE)
    return [(W / 2 - fnt.getlength(s) / 2, y, W / 2 + fnt.getlength(s) / 2, y + SHOUT_SIZE * 1.1) for s, y in zip(SHOUT, SHOUT_Y)]


def shout_sprite(i):
    if i not in _shout:
        fnt = font("Inter-ExtraBold.otf", SHOUT_SIZE)
        tw = int(fnt.getlength(SHOUT[i])) + 40
        im = Image.new("RGBA", (tw, int(SHOUT_SIZE * 1.4)), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.text((24, 14), SHOUT[i], font=fnt, fill=(0, 0, 0, 170))
        d.text((20, 8), SHOUT[i], font=fnt, fill=S.TEXT + (255,))
        _shout[i] = im
    return _shout[i]


FLAT = "that's the third one."
FLAT_POS, FLAT_SIZE = (100, 812), 52


def flat_box():
    fnt = font("Inter-Medium.otf", FLAT_SIZE)
    return (FLAT_POS[0], FLAT_POS[1], FLAT_POS[0] + fnt.getlength(FLAT), FLAT_POS[1] + FLAT_SIZE * 1.2)


# ---------------------------------------------------------------- Dandy Man, standing on the floor at the right
DM_H = 580
DM_X0, DM_Y0 = 747, FLOOR - LIFT_Y - DM_H


def dm_box(*poses):
    """The drawn figure's box across the poses a scene uses."""
    bs = [S.dm_sprite(p, DM_H).getbbox() for p in poses]
    return (DM_X0 + min(b[0] for b in bs), DM_Y0 + min(b[1] for b in bs), DM_X0 + max(b[2] for b in bs), DM_Y0 + max(b[3] for b in bs))


def dandy(img, tg, pose, x=DM_X0, dip=0.0, alpha=1.0):
    S.draw_dm(img, tg, pose, x0=x, y0=DM_Y0 + dip, height=DM_H, alpha=alpha, bob=False)


# ---------------------------------------------------------------- the map over the wall
P = {"Login": (86, 290), "Calendar": (405, 290), "Bookings": (724, 290), "Payments": (724, 478)}
EDGES = [("Login", "Calendar"), ("Calendar", "Bookings"), ("Bookings", "Payments")]
STATES = {"Login": "done", "Calendar": "done", "Bookings": "done", "Payments": "next"}
BLOOM = [("Login", 0.35), ("Calendar", 0.65), ("Bookings", 0.95), ("Payments", 1.25)]
READ = [("Login", 1.9), ("Calendar", 2.3), ("Bookings", 2.7), ("Payments", 3.2)]
BUILD_AT, SAY_AT = 3.6, 3.9
SAY = ["Login's done.", "Building payments."]
SAY_BOX = (268, 656, 762, 800)
MON_TIP = (633, 846)
DONE_BOX = (420, 632, 944, 792)
DONE = ["Done! I built you", "a login page."]


def center(name):
    x, y = P[name]
    return x + S.NODE_W / 2, y + S.NODE_H / 2


def path(t, keys):
    if t <= keys[0][0]:
        return keys[0][1], keys[0][2]
    for (t0, x0, y0), (t1, x1, y1) in zip(keys, keys[1:]):
        if t <= t1:
            q = smooth((t - t0) / (t1 - t0))
            return lerp(x0, x1, q), lerp(y0, y1, q)
    return keys[-1][1], keys[-1][2]


def draw_map(img, t, building=None):
    S.put_sprite(img, S.GLOW_P, 540, 440, scale=2.2, alpha=0.4 * ease_out((t - BLOOM[0][1]) / 1.2))
    for (a, b), (_, at) in zip(EDGES, BLOOM[1:]):
        S.edge(img, S.node_box(*P[a]), S.node_box(*P[b]), p=ease_out((t - at + 0.1) / 0.35))
    for name, at in BLOOM:
        a = ease_out((t - at) / 0.3)
        pulse = (1 - clamp((t - at) / 0.5)) if t >= at else 0
        rd = dict(READ)[name]
        if t >= rd:
            pulse = max(pulse, 1 - clamp((t - rd) / 0.45))
        st, sa = STATES[name], 1.0
        if name == "Payments" and building is not None and t >= building:
            st, sa = "building", ease_out((t - building) / 0.3)
            pulse = max(pulse, 0.25 + 0.2 * math.sin((t - building) * 4))
        S.node(img, *P[name], name, alpha=a, slide=(1 - a) * 16, state=st, state_alpha=sa, pulse=pulse)


# ---------------------------------------------------------------- scenes
def jitter(seed, amp):
    rnd = random.Random(seed)
    return rnd.uniform(-amp, amp), rnd.uniform(-amp, amp)


def s_open(t, dur, tg):
    """Cold open, already mid-meltdown. The agent's message sits there, cheerful."""
    img = room(t, "hair", dict(mode="chat"), nudge=jitter(int(t * 30), 2.5))
    callout(img, DONE_BOX, DONE, MON_TIP, t, pop=ease_out(t / 0.2 + 0.6))
    return img


FILE_AT = [0.0, 0.75, 1.35]


def s_smash(t, dur, tg):
    """Smash cut in close. The line slams on; behind it the list of login pages keeps growing."""
    hit = math.exp(-t * 7)
    sx, sy = jitter(int(t * 30) + 100, 22 * hit + 1.5)
    n = sum(1 for a in FILE_AT if t >= a)
    img = room(t, "shout", dict(mode="files", n_files=n, new_at=FILE_AT[n - 1]), cam=CLOSE, shake=(sx, sy), nudge=jitter(int(t * 30) + 7, 3))
    darken(img, "top", 0.55)
    for i, box in enumerate(shout_boxes()):
        at = 0.02 + 0.22 * i
        if t < at:
            continue
        p = clamp((t - at) / 0.12)
        sc = lerp(1.7, 1.0, ease_out(p))
        jx, jy = jitter(int(t * 30) * 3 + i, 5)
        S.put_sprite(img, shout_sprite(i), W / 2 + jx, box[1] + SHOUT_SIZE * 0.62 + jy, scale=sc, alpha=min(1.0, p * 2))
    return img


DROP = 0.2


def s_thud(t, dur, tg):
    """Head on the desk. Silence."""
    if t < DROP:
        return room(t, "shout", dict(mode="files"), cam=CLOSE, nudge=(0, 30 * (t / DROP) ** 2))
    k = t - DROP
    bump = 16 * math.exp(-k * 9) * math.cos(k * 40)
    img = room(t, "desk", dict(mode="files", garble=int(clamp(k / 0.5) * len(GARBLE))), cam=CLOSE, shake=(0, -bump))
    a = ease_out((t - 0.75) / 0.3)
    if a > 0:
        d = ImageDraw.Draw(img, "RGBA")
        d.text(FLAT_POS, FLAT, font=font("Inter-Medium.otf", FLAT_SIZE), fill=S.SOFT + (int(255 * a),))
    return img


WALK = (0.35, 1.25)
TIP_AT, PEEK_AT = 1.35, 1.0


def s_enter(t, dur, tg):
    """A polite cough. Purple light from the right, and Dandy Man walks in and tips his hat."""
    purple = smooth((t - 0.1) / 0.8)
    img = room(t, "peek" if t >= PEEK_AT else "desk", dict(mode="files", garble=len(GARBLE)), purple=purple)
    if t >= WALK[0]:
        q = clamp((t - WALK[0]) / (WALK[1] - WALK[0]))
        x = lerp(1100, DM_X0, ease_out(q))
        if q < 1:
            pose, dip = ("walk-1", "walk-2")[int(t / 0.15) % 2], -6 * abs(math.sin(t * math.pi / 0.15))
        else:
            pose, dip = ("hat-tip" if t >= TIP_AT else "idle"), 0
        dandy(img, tg, pose, x=x, dip=dip)
    return img


def wander(t):
    return path(t, [(0.0, 633, 915), (0.6, 600, 740), (1.3, 330, 600), (2.0, 210, 400), (2.8, 520, 350), (3.6, 800, 520), (4.6, 640, 690), (6.0, 420, 560)])


def s_why(t, dur, tg):
    """The agent's light drifts around the room, looking at nothing in particular."""
    img = room(t, "peek", dict(mode="files", garble=len(GARBLE)), purple=1.0, wall=0.25 * smooth(t / 0.6))
    ox, oy = wander(t)
    S.orb(img, ox + 10 * math.sin(t * 2.3), oy + 8 * math.cos(t * 1.9), t, alpha=ease_out((t - 0.15) / 0.4), dim=0.5)
    dandy(img, tg, "pointing", dip=3 * math.sin(tg * 1.7))
    return img


WATCH_AT = 0.9


def map_frame(t, tg, pose, dm_pose, dip=0.0, lead=0.0):
    """Scenes 6 and 7 share this: the map over the wall, the agent on Payments, the message on the monitor."""
    img = room(t, pose, dict(mode="work" if t >= BUILD_AT else "files", garble=len(GARBLE) if t < BUILD_AT else 0),
               purple=1.0, wall=lerp(0.25, 0.78, smooth(t / 0.5)))
    draw_map(img, t, building=BUILD_AT)
    wx, wy = wander(4.6 + lead)
    keys = [(0.0, wx, wy), (READ[0][1] - 0.5, wx - 60, wy - 20)] + [(at, *center(n)) for n, at in READ] + [(99, *center("Payments"))]
    ox, oy = path(t, keys)
    wig = 9 * math.sin(t * 26) if t > BUILD_AT + 0.1 else 0
    S.orb(img, ox + wig, oy - 6, t, dim=0.5 * (1 - smooth((t - 1.2) / 0.5)))
    callout(img, SAY_BOX, SAY, MON_TIP, t, alpha=ease_out((t - SAY_AT) / 0.25), pop=ease_out((t - SAY_AT) / 0.3), size=38)
    dandy(img, tg, dm_pose, dip=dip)
    return img


def s_map(t, dur, tg):
    """He taps the cane once and the project blooms over the wall. The agent reads it, skips Login, starts Payments."""
    tap = 10 * math.sin(clamp(t / 0.3) * math.pi)
    return map_frame(t, tg, "watch" if t >= WATCH_AT else "peek", "pointing" if t > 0.3 else "idle", dip=tap)


BETTER_TIP = 0.55


def s_better(t, dur, tg):
    """The builder sits up. Dandy Man tips his hat."""
    return map_frame(50 + t, tg, "up" if t >= 0.2 else "watch", "hat-tip" if t >= BETTER_TIP else "idle")


SCENES = [("open", 1.6, s_open), ("smash", 2.6, s_smash), ("thud", 2.0, s_thud), ("enter", 2.6, s_enter), ("why", 4.6, s_why),
          ("map", 5.8, s_map), ("better", 2.2, s_better), ("end", 3.0, None)]
_st, _acc = {}, 0.0
for _sid, _d, _ in SCENES:
    _st[_sid] = _acc
    _acc += _d
CAPTIONS = [
    (_st["enter"] + 1.4, _st["enter"] + 2.5, "Rough night?"),
    (_st["why"] + 0.2, _st["why"] + 1.9, "Your agent isn't careless."),
    (_st["why"] + 2.0, _st["why"] + 3.2, "It just can't see"), (_st["why"] + 3.25, _st["why"] + 4.5, "what's already built."),
    (_st["map"] + 0.2, _st["map"] + 1.3, "Dandy shows it:"), (_st["map"] + 1.35, _st["map"] + 2.9, "every piece of your project,"),
    (_st["map"] + 2.95, _st["map"] + 4.1, "and where it stands,"), (_st["map"] + 4.15, _st["map"] + 5.6, "before it writes a line."),
    (_st["better"] + 0.4, _st["better"] + 2.0, "There. Much better."),
]
assert all(len(S.caption_lines(c[2])) == 1 for c in CAPTIONS), [c[2] for c in CAPTIONS if len(S.caption_lines(c[2])) > 1]


def qa_scenes(starts, durs, captions):
    """The settled layout of every scene, for render/checks.py run_all (layout, copy, gold, end card)."""
    bg = dict(name="room", type="art", background=True, bbox=(0, 0, W, H))

    def caps(sid):
        return S.caption_els(captions, starts[sid], durs[sid])

    def files():
        return [dict(name=f"file {n}", type="text", role="body", text=n, lines=[n]) for n in FILES]   # on the monitor

    sb = shout_boxes()
    nodes = []
    for n in P:
        nodes.append(S.text_el(f"node {n}", n, S.node_box(*P[n])))
        nodes.append(dict(name=f"chip {n}", type="text", role="body", text=STATES[n], lines=[STATES[n]], gold=False))
    nodes[-1].update(text="building", lines=["building"], gold=True)      # Payments goes from next to building
    say = S.text_el("agent message", " ".join(SAY), SAY_BOX, lines=SAY, enter_at=SAY_AT)
    return [
        dict(id="open", type="room", duration=durs["open"], laid_out=[bg, S.text_el("agent message", " ".join(DONE), DONE_BOX, lines=DONE)]),
        dict(id="smash", type="room", duration=durs["smash"], laid_out=[bg, S.text_el("shout", " ".join(SHOUT), (min(b[0] for b in sb), sb[0][1], max(b[2] for b in sb), sb[1][3]),
                                                                                    role="headline", lines=SHOUT)] + files()),
        dict(id="thud", type="room", duration=durs["thud"], laid_out=[bg, S.text_el("aside", FLAT, flat_box(), enter_at=0.75)] + files()),
        dict(id="enter", type="room", duration=durs["enter"], laid_out=[bg, dict(name="dandy_man", type="sprite", bbox=dm_box("idle", "hat-tip"))] + files() + caps("enter")),
        dict(id="why", type="room", duration=durs["why"], laid_out=[bg, dict(name="dandy_man", type="sprite", bbox=dm_box("pointing"))] + files() + caps("why")),
        dict(id="map", type="room", duration=durs["map"], laid_out=[bg, dict(name="dandy_man", type="sprite", bbox=dm_box("idle", "pointing")), say] + nodes + caps("map")),
        dict(id="better", type="room", duration=durs["better"], laid_out=[bg, dict(name="dandy_man", type="sprite", bbox=dm_box("idle", "hat-tip")),
                                                                          dict(say, enter_at=0)] + nodes + caps("better")),
        S.end_card_scene(durs["end"]),
    ]


# ---------------------------------------------------------------- sound
def snd_slam(gain=0.5):
    n = int(S.SR * 0.7)
    t = np.arange(n) / S.SR
    low = np.sin(2 * np.pi * (48 + 60 * np.exp(-t * 18)) * t) * np.exp(-t * 6)
    hit = S._band(np.random.default_rng(3).normal(0, 1, n), 150, 2500) * np.exp(-t * 40)
    return S._norm(low + 0.6 * hit, gain)


def snd_thud(gain=0.45):
    n = int(S.SR * 0.4)
    t = np.arange(n) / S.SR
    low = np.sin(2 * np.pi * (62 + 40 * np.exp(-t * 30)) * t) * np.exp(-t * 14)
    knock = S._band(np.random.default_rng(4).normal(0, 1, n), 250, 900) * np.exp(-t * 70)
    return S._norm(low + 0.5 * knock, gain)


S.SOUNDS.update(slam=snd_slam, thud=snd_thud)


def events(starts, durs):
    o, sm, th, en, wh, mp, be = (starts[k] for k in ("open", "smash", "thud", "enter", "why", "map", "better"))
    ev = [(o + 0.05, "chime", dict(gain=0.3, f0=1319), 0.2), (sm, "slam", dict(gain=0.55), 0.0)]
    ev += [(sm + a, "pop", dict(gain=0.28, f=520 - 70 * i), 0.3) for i, a in enumerate(FILE_AT) if a > 0]
    ev += [(th + DROP, "thud", dict(gain=0.5), -0.1)]
    ev += [(th + DROP + 0.06 + 0.06 * k, "tick", dict(gain=0.12), -0.1) for k in range(7)]
    ev += [(en + 0.05, "pop", dict(gain=0.2, f=300), 0.6), (en + 0.25, "pop", dict(gain=0.22, f=260), 0.6),      # the polite cough
           (en + 0.3, "whoosh", dict(gain=0.3, dur=0.9), 0.5), (en + TIP_AT, "chime", dict(gain=0.3, f0=880), 0.5),
           (wh + 0.2, "zip", dict(gain=0.16), 0.1), (mp + 0.12, "tick", dict(gain=0.3), 0.6), (mp + 0.2, "whoosh", dict(gain=0.25), 0.0)]
    for i, (n, at) in enumerate(BLOOM):
        ev.append((mp + at, "pop", dict(gain=0.3, f=523 * 2 ** (i * 2 / 12)), (P[n][0] - 420) / 500))
    ev += [(mp + at, "tick", dict(gain=0.25), (P[n][0] - 420) / 500) for n, at in READ]
    ev += [(mp + BUILD_AT, "chime", dict(gain=0.3, f0=1047), 0.4), (mp + SAY_AT, "pop", dict(gain=0.3, f=784), 0.1),
           (be + BETTER_TIP, "chime", dict(gain=0.3, f0=880), 0.5), (starts["end"] + 0.3, "chime", dict(gain=0.32, f0=660), 0.0)]
    return ev


SPEC = dict(video_dir=VIDEO, slug="13-crash-out-login", look_tag="room", look="night room with Dandy Man", scenes=SCENES, captions=CAPTIONS,
            qa_scenes=qa_scenes, events=events, still_s=0.0, thumbnail=False, voiceover=os.path.join(VIDEO, "voiceover", "stage.json"))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if S.render_video(SPEC, a.preview, a.stills, a.final) else 1)

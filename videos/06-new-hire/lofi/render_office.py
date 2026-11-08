"""Renderer for video 06, The New Hire: the Maya lofi look (video 02) in an office. Vertical only.

Usage:  python3 videos/06-new-hire/lofi/render_office.py [--preview] [--final] [--stills]

Same pipeline as videos/02-maya/lofi/render_lofi.py: SVG layers from gen_office.py are rasterised once at
SCALE x the 1080x1920 room, every frame is composed in room coordinates, then a camera (cx, cy, zoom) crops
and resizes to 1080x1920. Shots are near-still: one small motion each (steam, a drawing arrow, scrolling code,
a page flip, a ticking second hand, light and dust). The room is a plain office; brand purple appears only in
the Dandy panel on the monitor and on the end card. The turn ("This is your AI agent") is a grade change on the
same shot: the room desaturates and dims, the hire stays in full colour.
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

import cairosvg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "render"))
import gen_office as G  # noqa: E402
from finish import finish  # noqa: E402

with open(os.path.join(ROOT, "style", "contract.json")) as f:
    CONTRACT = json.load(f)
PAL = CONTRACT["palette"]
FONT_DIR = "/usr/share/fonts/opentype/inter"
FPS = CONTRACT["motion"]["fps"]
W, H = 1080, 1920
SCALE = 2
SAFE = (int(W * 0.08), CONTRACT["layout"]["vertical_safe_top_px"], W - int(W * 0.08), H - CONTRACT["layout"]["vertical_safe_bottom_px"])
NOTE = (255, 233, 168)       # sticky-note yellow (paler than the contract gold)
INK = {"blue": (47, 111, 214), "red": (214, 69, 69), "dark": (40, 46, 62)}


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, p):
    return a + (b - a) * p


def mix(c1, c2, p):
    return tuple(int(lerp(c1[i], c2[i], p)) for i in range(3))


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(size))


def S(v):
    return int(v * SCALE)


_layers = {}


def layer(name):
    if name not in _layers:
        png = cairosvg.svg2png(url=os.path.join(HERE, "layers", name + ".svg"), output_width=W * SCALE)
        _layers[name] = Image.open(io.BytesIO(png)).convert("RGBA")
    return _layers[name]


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


_hat = {}


def hat_img(h):
    if h not in _hat:
        im = Image.open(os.path.join(ROOT, "motifs", "logo-hat-light.png")).convert("RGBA")
        _hat[h] = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
    return _hat[h]


# ---------- room details drawn per frame (room coords x SCALE) ----------
def draw_sky(canvas, day):
    x0, y0, x1, y1 = (S(v) for v in G.WINDOW)
    top, bot = ((246, 227, 196), (201, 216, 234)) if day == 1 else ((232, 222, 206), (186, 204, 228))
    sky = Image.new("RGBA", (x1 - x0, y1 - y0))
    d = ImageDraw.Draw(sky)
    for i in range(0, y1 - y0, 4):
        d.rectangle((0, i, x1 - x0, i + 4), fill=mix(top, bot, i / (y1 - y0)) + (255,))
    canvas.alpha_composite(sky, (x0, y0))


def draw_beams(canvas, t, day):
    """Morning light through the blinds, falling down and to the left across the wall, desk and floor."""
    x0, y0, x1, y1 = G.WINDOW
    g = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    shift = 0 if day == 1 else 40
    breathe = 0.85 + 0.15 * math.sin(t * 0.7)
    for k in range(5):
        a = x0 + 40 + k * 70
        poly = [(S(a), S(y0 + 20)), (S(a + 46), S(y0 + 20)), (S(a + 46 - 420 - shift), S(1700)), (S(a - 420 - shift), S(1700))]
        d.polygon(poly, fill=(246, 222, 180, int(22 * breathe)))
    canvas.alpha_composite(g.filter(ImageFilter.GaussianBlur(S(14))))
    # dust motes drifting slowly in the light
    d = ImageDraw.Draw(canvas)
    rnd = random.Random(5)
    for _ in range(30):
        by = rnd.uniform(440, 1150)
        bx = rnd.uniform(680, 1000) - (by - 300) * 0.42
        sp = rnd.uniform(4, 10)
        px = bx + math.sin(t * 0.3 + bx) * 18 - t * sp * 0.6
        py = by + t * sp * 0.4 + math.sin(t * 0.5 + by) * 10
        r = rnd.uniform(1.5, 3.2)
        a = int(70 * (0.5 + 0.5 * math.sin(t * 1.3 + bx)))
        d.ellipse((S(px - r), S(py - r), S(px + r), S(py + r)), fill=(250, 236, 210, a))


def draw_clock(canvas, t, minute=0.0):
    cx, cy, r = G.CLOCK
    d = ImageDraw.Draw(canvas)
    hour = 9 + minute / 60
    for ang, ln, wd, col in ((hour / 12 * 360, r * 0.5, 6, (40, 46, 62)), (minute / 60 * 360, r * 0.78, 4, (40, 46, 62)),
                             ((int(t) % 60) / 60 * 360, r * 0.84, 2, (214, 69, 69))):
        a = math.radians(ang - 90)
        d.line([(S(cx), S(cy)), (S(cx + math.cos(a) * ln), S(cy + math.sin(a) * ln))], fill=col + (255,), width=S(wd / 2) + 1)
    d.ellipse((S(cx - 4), S(cy - 4), S(cx + 4), S(cy + 4)), fill=(40, 46, 62, 255))


BOXES = {"app": (250, 380, 410, 440), "auth": (110, 520, 250, 580), "api": (400, 520, 540, 580),
         "db": (300, 660, 420, 720), "billing": (440, 660, 570, 720)}
ARROWS = [("app", "auth", "dark"), ("app", "api", "dark"), ("api", "db", "blue"), ("auth", "db", "blue"), ("api", "billing", "red")]


def draw_board(canvas, mode, t=0.0, draw_at=None):
    """mode: 'full' diagram, 'drawing' (last arrow draws itself from draw_at), 'wiped' (grey smears), None."""
    if mode is None:
        return
    d = ImageDraw.Draw(canvas)
    fb = font("Inter-Bold.otf", S(22))
    if mode == "wiped":
        sm = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sm)
        rnd = random.Random(9)
        for _ in range(9):
            x, y = rnd.uniform(110, 470), rnd.uniform(370, 700)
            sd.rounded_rectangle((S(x), S(y), S(x + rnd.uniform(90, 160)), S(y + rnd.uniform(18, 34))), radius=S(14), fill=(150, 158, 175, 60))
        sd.rounded_rectangle((S(258), S(388), S(402), S(432)), radius=S(4), outline=(150, 158, 175, 70), width=S(3))
        canvas.alpha_composite(sm.filter(ImageFilter.GaussianBlur(S(6))))
        return
    for name, (x0, y0, x1, y1) in BOXES.items():
        col = INK["blue"] if name in ("db", "billing") else INK["dark"]
        d.rounded_rectangle((S(x0), S(y0), S(x1), S(y1)), radius=S(6), outline=col + (255,), width=S(3))
        tw = d.textlength(name, font=fb)
        d.text((S((x0 + x1) / 2) - tw / 2, S((y0 + y1) / 2 - 14)), name, font=fb, fill=col + (255,))
    for i, (a, b, ink) in enumerate(ARROWS):
        ax0, ay0, ax1, ay1 = BOXES[a]
        bx0, by0, bx1, by1 = BOXES[b]
        p0 = ((ax0 + ax1) / 2, ay1)
        p1 = ((bx0 + bx1) / 2, by0)
        prog = 1.0
        if mode == "drawing" and i == len(ARROWS) - 1:
            prog = ease((t - draw_at) / 0.7) if t >= draw_at else 0.0
        if prog <= 0:
            continue
        pe = (lerp(p0[0], p1[0], prog), lerp(p0[1], p1[1], prog))
        d.line([(S(p0[0]), S(p0[1] + 4)), (S(pe[0]), S(pe[1] - 4))], fill=INK[ink] + (255,), width=S(3))
        if prog >= 1:
            ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
            for s in (-1, 1):
                d.line([(S(p1[0]), S(p1[1] - 4)), (S(p1[0] - 14 * math.cos(ang + s * 0.45)), S(p1[1] - 4 - 14 * math.sin(ang + s * 0.45)))],
                       fill=INK[ink] + (255,), width=S(3))


def draw_code(canvas, scr, t, speed=22.0, seed=1):
    x0, y0, x1, y1 = (S(v) for v in scr)
    im = Image.new("RGBA", (x1 - x0, y1 - y0), (15, 20, 36, 255))
    d = ImageDraw.Draw(im)
    rnd = random.Random(seed)
    lines = [(rnd.randint(0, 3), [(rnd.randint(2, 9), rnd.choice(((158, 211, 154), (242, 194, 122), (233, 237, 243), (127, 178, 240))))
                                  for _ in range(rnd.randint(1, 4))]) for _ in range(80)]
    lh = S(13)
    off = (t * speed * SCALE) % (lh * 40)
    for i, (indent, toks) in enumerate(lines):
        y = S(8) + i * lh - off
        if y < -lh or y > im.height:
            continue
        x = S(8) + indent * S(10)
        for ln, col in toks:
            w = ln * S(5)
            d.rounded_rectangle((x, y, x + w, y + S(6)), radius=S(2), fill=col + (220,))
            x += w + S(5)
    canvas.alpha_composite(im, (x0, y0))


def draw_screen(canvas, t, msgs=(), dandy=None):
    """Main monitor: a chat window. dandy = (at, title, rows[(label, state, turn_done_at)]) slides in as a purple panel."""
    x0, y0, x1, y1 = (S(v) for v in G.SCREEN)
    scr = Image.new("RGBA", (x1 - x0, y1 - y0), (18, 22, 36, 255))
    d = ImageDraw.Draw(scr)
    sw, sh = scr.size
    hdr = S(22)
    d.rectangle((0, 0, sw, hdr), fill=(34, 40, 58, 255))
    for i, c in enumerate(((255, 107, 107), (245, 197, 66), (120, 200, 120))):
        d.ellipse((S(7) + i * S(12), S(7), S(14) + i * S(12), S(14)), fill=c + (255,))
    f = font("Inter-Regular.otf", S(12))
    fb = font("Inter-Bold.otf", S(13))
    panel_p = ease((t - dandy[0]) / 0.5) if dandy and t >= dandy[0] else 0.0
    chat_w = int(lerp(sw, sw * 0.46, panel_p))
    y = hdr + S(10)
    pad = S(8)
    for who, text, at in msgs:
        if t < at:
            continue
        p = ease((t - at) / 0.35)
        lines = wrap(text, f, chat_w - S(24) - pad * 2, d)
        bw = max(d.textlength(l, font=f) for l in lines) + pad * 2
        bh = len(lines) * S(16) + pad * 1.3
        bx0 = S(10) if who == "agent" else chat_w - S(10) - bw
        col = (52, 60, 84) if who == "agent" else (70, 92, 140)
        by0 = y + (1 - p) * S(6)
        d.rounded_rectangle((bx0, by0, bx0 + bw, by0 + bh), radius=S(7), fill=col + (int(255 * p),))
        for i, l in enumerate(lines):
            d.text((bx0 + pad, by0 + pad * 0.5 + i * S(16)), l, font=f, fill=rgb(PAL["text"]) + (int(255 * p),))
        y += bh + S(6)
    if panel_p > 0:
        px0 = int(lerp(sw, sw * 0.46, panel_p))
        d.rectangle((px0, hdr, sw, sh), fill=rgb(PAL["background_lift"]) + (255,))
        d.line([(px0, hdr), (px0, sh)], fill=rgb(PAL["highlight"]) + (255,), width=S(2))
        if sw - px0 > S(60):
            hat = hat_img(S(14))
            scr.alpha_composite(hat, (px0 + S(8), hdr + S(7)))
            d.text((px0 + S(28), hdr + S(6)), "Dandy", font=fb, fill=rgb(PAL["text"]) + (255,))
            d.text((px0 + S(8), hdr + S(28)), dandy[1], font=fb, fill=rgb(PAL["soft"]) + (255,))
            yy = hdr + S(52)
            for label, state, done_at in dandy[2]:
                if done_at is not None and t >= done_at:
                    state = "done"
                col = {"done": rgb(PAL["highlight"]), "next": rgb(PAL["accent_gold"]), "decided": rgb(PAL["soft"])}[state]
                d.rounded_rectangle((px0 + S(8), yy, sw - S(8), yy + S(24)), radius=S(5), outline=col + (255,), width=S(2), fill=col + (50,))
                d.text((px0 + S(14), yy + S(5)), label, font=f, fill=rgb(PAL["text"]) + (255,))
                mw = d.textlength(state, font=f)
                d.text((sw - S(14) - mw, yy + S(5)), state, font=f, fill=col + (255,))
                yy += S(30)
    canvas.alpha_composite(scr, (x0, y0))


def draw_screen_glow(canvas, strength):
    """Purple light from the Dandy panel spilling onto the bezel and desk."""
    if strength <= 0:
        return
    x0, y0, x1, y1 = (S(v) for v in G.SCREEN)
    g = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((x0 - S(120), y0 - S(90), x1 + S(120), y1 + S(160)), fill=rgb(PAL["highlight"]) + (int(70 * strength),))
    canvas.alpha_composite(g.filter(ImageFilter.GaussianBlur(S(50))))


NOTES = [("the project = budget app", (-60, -40), -7), ("auth is DONE", (230, -36), 6)]   # offsets from the main bezel corner


def draw_notes(canvas, t, notes_at=None, peel=None):
    if notes_at is None:
        return
    fn = font("Inter-Medium.otf", S(12))
    sx0, sy0, sx1, sy1 = G.SCREEN
    for i, (text, (ox, oy), ang) in enumerate(NOTES):
        if t < notes_at[i]:
            continue
        q = ease((t - peel[i]) / 0.5) if peel and t >= peel[i] else 0.0
        if q >= 1:
            continue
        nw = nh = S(78)
        note = Image.new("RGBA", (nw + S(20), nh + S(20)), (0, 0, 0, 0))
        nd = ImageDraw.Draw(note)
        nd.rectangle((S(10), S(10), S(10) + nw, S(10) + nh), fill=NOTE + (245,))
        for k, l in enumerate(wrap(text, fn, nw - S(14), nd)):
            nd.text((S(17), S(17) + k * S(15)), l, font=fn, fill=(60, 52, 40, 255))
        note = note.rotate(ang + q * 50 * (1 if i else -1), expand=True, resample=Image.BICUBIC)
        note.putalpha(note.split()[3].point(lambda v: int(v * (1 - q))))
        cx, cy = S(sx0 + ox + 80), S(sy0 + oy + 40)
        canvas.alpha_composite(note, (int(cx - note.width / 2 + q * S(40) * (1 if i else -1)), int(cy - note.height / 2 + q * S(160))))


def draw_thought(canvas, t, at):
    if t < at:
        return
    p = ease((t - at) / 0.4)
    hx, hy = G.HEAD["confused"]
    d = ImageDraw.Draw(canvas)
    bob = math.sin(t * 2.2) * 4
    for (dx, dy, r) in ((60, -70, 9), (82, -100, 14)):
        d.ellipse((S(hx + dx - r), S(hy + dy - r + bob), S(hx + dx + r), S(hy + dy + r + bob)), fill=(233, 237, 243, int(235 * p)))
    cx, cy, r = hx + 120, hy - 160 + bob, 48
    d.ellipse((S(cx - r), S(cy - r), S(cx + r), S(cy + r)), fill=(233, 237, 243, int(235 * p)))
    fq = font("Inter-Bold.otf", S(56))
    tw = d.textlength("?", font=fq)
    d.text((S(cx) - tw / 2, S(cy - 36)), "?", font=fq, fill=(40, 46, 62, int(255 * p)))


def draw_steam(canvas, t):
    x, y = (S(v) for v in G.MUG)
    d = ImageDraw.Draw(canvas)
    for k in range(3):
        ph = t * 0.9 + k * 2.1
        pts = [(x + S(-12 + k * 12) + math.sin(ph + u * 5) * S(9) * (0.3 + u), y - S(8) - u * S(100)) for u in (i / 11 for i in range(12))]
        a = int(110 * (0.6 + 0.4 * math.sin(ph)))
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=(240, 242, 248, int(a * (1 - i / len(pts)))), width=S(4))


def draw_page_flip(canvas, t, at):
    """One page lifting off the lower half and turning to the upper half, seen edge-on as a curving white line."""
    if t < at or t > at + 0.6:
        return
    q = smooth((t - at) / 0.6)
    (x, y), tp, bt = G.BINDER, G.BINDER_TOP, G.BINDER_BOT
    end = (lerp(bt[0], tp[0], q) + 30 * math.sin(q * math.pi) * -1, lerp(bt[1], tp[1], q))
    mid = (lerp(x, end[0], 0.5) - 26 * math.sin(q * math.pi), lerp(y, end[1], 0.5))
    pts = [(S(x - 6), S(y)), (S(mid[0]), S(mid[1])), (S(end[0]), S(end[1]))]
    ImageDraw.Draw(canvas).line(pts, fill=(250, 251, 253, 255), width=S(5), joint="curve")


# ---------- composing a frame ----------
def room_frame(t, o):
    """o: dict of shot options. Returns the camera view at 1080x1920 (RGBA)."""
    day = o.get("day", 1)
    canvas = Image.new("RGBA", (W * SCALE, H * SCALE), (30, 36, 52, 255))
    draw_sky(canvas, day)
    canvas.alpha_composite(layer("back"))
    draw_clock(canvas, t + o.get("clock_t", 0), o.get("minute", 0.0))
    draw_board(canvas, o.get("board", "full"), t, o.get("draw_at"))
    pose = o.get("pose", "typing")
    standing = pose == "board"
    bob = int(math.sin(t * 2 * math.pi / 2.4) * S(2)) if pose == "typing" else 0
    fig = layer("hire-" + pose)
    if not standing:
        canvas.alpha_composite(fig, (0, bob))
    canvas.alpha_composite(layer("front"))
    for scr, sp, seed in ((G.SCREEN_L, 16, 3), (G.SCREEN_R, 12, 4)):
        draw_code(canvas, scr, t + o.get("code_t", 0), speed=sp * o.get("code_speed", 1.0), seed=seed)
    if o.get("main") == "code":
        draw_code(canvas, G.SCREEN, t, speed=26 * o.get("code_speed", 1.0), seed=2)
    else:
        draw_screen(canvas, t, o.get("msgs", ()), o.get("dandy"))
    draw_screen_glow(canvas, o.get("glow", 0.0) * (ease((t - o["dandy"][0]) / 0.6) if o.get("dandy") else 0.0))
    draw_notes(canvas, t, o.get("notes_at"), o.get("peel"))
    if pose == "binder":
        canvas.alpha_composite(layer("binder"))
        draw_page_flip(canvas, t, o.get("flip_at", 1.0))
    if standing:
        canvas.alpha_composite(fig)
    if o.get("steam", True):
        draw_steam(canvas, t)
    draw_beams(canvas, t, day)
    if o.get("thought_at") is not None:
        draw_thought(canvas, t, o["thought_at"])
    # the turn: desaturate and dim the room, keep the hire in full colour
    g = o.get("grade_at")
    if g is not None and t >= g:
        q = smooth((t - g) / 0.6)
        arr = np.asarray(canvas).astype(np.float32)
        lum = (arr[..., :3] * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
        grey = (arr[..., :3] * (1 - 0.85 * q) + lum * 0.85 * q) * (1 - 0.45 * q)
        fa = np.asarray(fig).astype(np.float32)[..., 3:4] / 255.0
        if not standing:
            fa = np.roll(fa, bob, axis=0) * (1 - np.asarray(layer("front")).astype(np.float32)[..., 3:4] / 255.0)
        out = arr[..., :3] * fa + grey * (1 - fa)
        canvas = Image.fromarray(np.concatenate([np.clip(out, 0, 255), arr[..., 3:4]], -1).astype(np.uint8), "RGBA")
    cx, cy, z = o["cam"]
    if o.get("cam_to"):
        tx, ty, tz, dur = o["cam_to"]
        q = smooth(t / dur)
        cx, cy, z = lerp(cx, tx, q), lerp(cy, ty, q), lerp(z, tz, q)
    cw, ch = W * SCALE / z, H * SCALE / z
    x0 = min(max(0, cx * SCALE - cw / 2), W * SCALE - cw)
    y0 = min(max(0, cy * SCALE - ch / 2), H * SCALE - ch)
    return canvas.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)


def title(frame, text, t_local, y, role="headline", align="left", exit_at=None, t_abs=None, scale=1.0):
    if t_local < 0:
        return
    a = ease(t_local / 0.4)
    if exit_at is not None and t_abs is not None and t_abs >= exit_at:
        a = min(a, 1 - ease((t_abs - exit_at) / 0.3))
    if a <= 0:
        return
    sizes = CONTRACT["type"]["vertical"]
    fnt = font({"headline": "Inter-Bold.otf", "body": "Inter-Medium.otf", "caption": "Inter-Medium.otf"}[role], sizes[role] * scale)
    d = ImageDraw.Draw(frame)
    lines = wrap(text, fnt, SAFE[2] - SAFE[0], d)
    lh = fnt.size * 1.18
    yy = y * H - (1 - a) * 20
    for l in lines:
        lw = d.textlength(l, font=fnt)
        x = SAFE[0] if align == "left" else W / 2 - lw / 2
        d.text((x + 2, yy + 3), l, font=fnt, fill=(0, 0, 0, int(150 * a)))
        d.text((x, yy), l, font=fnt, fill=rgb(PAL["text"]) + (int(255 * a),))
        yy += lh


def draw_cue(frame, cues, t_global):
    cue = next((c for c in cues if c["start"] <= t_global < c["end"]), None)
    if cue is None:
        return
    fnt = font("Inter-Bold.otf", int(CONTRACT["type"]["vertical"]["body"] * 0.95))
    d = ImageDraw.Draw(frame)
    lh = fnt.size * 1.15
    pad = 18
    for i, line in enumerate(wrap(cue["text"], fnt, SAFE[2] - SAFE[0], d)):
        tw = d.textlength(line, font=fnt)
        x, yy = W / 2 - tw / 2, 0.80 * H + i * (lh + pad * 0.8)
        d.rounded_rectangle((x - pad, yy - pad * 0.6, x + tw + pad, yy + lh + pad * 0.4), radius=14, fill=(14, 18, 30, 200))
        d.text((x, yy), line, font=fnt, fill=rgb(PAL["text"]) + (255,))


END_LINES = ("Unlock their full potential.", "Use Dandy.")


def end_card(room, t):
    """Soft end card, no Dandy Man: the room blurs under the brand dark; the line, the hat, the wordmark, the URL and the trial."""
    p = ease(t / 1.0)
    bg = room.filter(ImageFilter.GaussianBlur(int(14 * p)))
    bg.alpha_composite(Image.new("RGBA", bg.size, rgb(PAL["background"]) + (int(215 * p),)))
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W * 0.1, H * 0.3, W * 0.9, H * 0.75), fill=rgb(PAL["primary"]) + (int(110 * p),))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(bg)
    sizes = CONTRACT["type"]["vertical"]
    title(bg, END_LINES[0], t - 0.4, 0.17, role="headline", align="center")
    title(bg, END_LINES[1], t - 0.9, 0.17 + 2 * 96 * 1.18 / H + 0.012, role="body", align="center")
    a = ease((t - 1.3) / 0.6)
    if a > 0:
        hat = hat_img(int(H * 0.10)).copy()
        hat.putalpha(hat.split()[3].point(lambda v: int(v * a)))
        hy = H * 0.43
        bg.alpha_composite(hat, (int(W / 2 - hat.width / 2), int(hy)))
        fh = font("Inter-Bold.otf", int(sizes["headline"] * 1.3))
        tw = d.textlength("Dandy", font=fh)
        ty = hy + hat.height + 30
        d.text((W / 2 - tw / 2, ty), "Dandy", font=fh, fill=rgb(PAL["text"]) + (int(255 * a),))
        yy = ty + fh.size * 1.1 + 50
        for i, line in enumerate(CONTRACT["copy_rules"]["end_card_lines"]):
            b = ease((t - 1.7 - 0.25 * i) / 0.5)
            fl = font("Inter-Medium.otf", sizes["body" if i == 0 else "caption"])
            lw = d.textlength(line, font=fl)
            d.text((W / 2 - lw / 2, yy), line, font=fl, fill=(rgb(PAL["accent_gold"]) if i == 1 else rgb(PAL["soft"])) + (int(255 * b),))
            yy += fl.size * 1.1 + 40
    return bg


# ---------- the shots ----------
WIDE = (540, 960, 1.0)
BOARD_CAM = (440, 680, 1.6)
CODE_CAM = (770, 1010, 1.9)
DOCS_CAM = (420, 1010, 1.75)
SCREEN_CAM = (790, 995, 2.2)
CHAT_DAY2 = [("agent", "Morning! So, what are we working on?", 1.4)]
CHAT_DANDY = [("agent", "Reading Dandy. Auth is done, billing is next. Starting there.", 1.3),
              ("agent", "Billing added. Writing it back.", 5.0)]
DANDY = (0.4, "Budget app", [("Auth", "done", None), ("Billing", "next", 5.4), ("Postgres", "decided", None)])

SCENES = [
    dict(id="s1-hire", dur=4.0, lines="Meet your new hire. He can do anything.",
         o=dict(pose="typing", board="full", main="code", cam=WIDE, cam_to=(500, 1000, 1.1, 4.0))),
    dict(id="s2-design", dur=2.4, lines="Designs the whole system before lunch.",
         o=dict(pose="board", board="drawing", draw_at=0.7, main="code", cam=BOARD_CAM, cam_to=(450, 680, 1.66, 2.4))),
    dict(id="s3-build", dur=2.3, lines="Builds it after.",
         o=dict(pose="typing", board="full", main="code", code_speed=2.2, cam=CODE_CAM, cam_to=(780, 1010, 1.95, 2.3))),
    dict(id="s4-docs", dur=2.3, lines="Reads every document you have in seconds.",
         o=dict(pose="binder", board="full", main="code", flip_at=0.8, cam=DOCS_CAM, cam_to=(420, 1000, 1.8, 2.3))),
    dict(id="s5-day2", dur=7.0, lines="He has one flaw. Every morning, he forgets. The project, the plan, what he built yesterday. All of it.",
         o=dict(pose="confused", day=2, board="wiped", msgs=CHAT_DAY2, notes_at=(0, 0), thought_at=2.6, minute=0.0, cam=WIDE, cam_to=(520, 980, 1.06, 7.0))),
    dict(id="s6-turn", dur=7.0, lines="That employee is your AI agent. Extremely powerful. And starting from zero every single session.",
         o=dict(pose="confused", day=2, board="wiped", msgs=CHAT_DAY2, notes_at=(0, 0), clock_t=7.0, minute=0.0, grade_at=0.2, thought_at=-1.0,
                cam=(520, 980, 1.06), cam_to=(430, 1020, 1.22, 7.0))),
    dict(id="s7-dandy", dur=8.0, lines="Don't let that limit what they can do. Dandy holds the state of your project. The agent reads it before it starts, and writes back what it changed. Nothing is forgotten.",
         o=dict(pose="typing", day=2, board="wiped", msgs=CHAT_DANDY, dandy=DANDY, glow=1.0, steam=False, notes_at=(0, 0), peel=(2.4, 3.0),
                cam=SCREEN_CAM, cam_to=(790, 990, 2.35, 8.0))),
    dict(id="end", dur=5.0, lines="Unlock their full potential. Use Dandy.", end=True),
]
TITLES = [  # (scene id, text, at, y, role, align, exit_at)
    ("s1-hire", "the new hire", 0.6, 0.70, "headline", "left", None),
    ("s2-design", "designs it before lunch", 0.2, 0.70, "body", "left", None),
    ("s3-build", "builds it after", 0.2, 0.70, "body", "left", None),
    ("s4-docs", "reads everything you have", 0.2, 0.70, "body", "left", None),
    ("s5-day2", "day 2", 0.3, 0.70, "headline", "left", None),
    ("s6-turn", "This is your AI agent", 0.7, 0.16, "headline", "center", None),
    ("s6-turn", "Powerful. And starting from zero every session.", 2.6, 0.31, "body", "center", None),
    ("s7-dandy", "reads the state first", 1.2, 0.70, "body", "left", 4.6),
    ("s7-dandy", "writes back what changed", 4.9, 0.70, "body", "left", None),
]


def copy_qa():
    rules = CONTRACT["copy_rules"]
    texts = [x[1] for x in TITLES] + [n[0] for n in NOTES] + [m[1] for m in CHAT_DAY2 + CHAT_DANDY] + list(END_LINES)
    problems = []
    for tx in texts:
        for ch in rules["banned_characters"]:
            if ch in tx:
                problems.append(("copy", f"banned character in {tx!r}"))
        for ph in rules["banned_phrases"]:
            if ph in tx.lower():
                problems.append(("copy", f"banned phrase {ph!r} in {tx!r}"))
        if len(tx.split()) > CONTRACT["type"]["max_words_on_screen"]:
            problems.append(("copy", f"more than {CONTRACT['type']['max_words_on_screen']} words: {tx!r}"))
    return problems


def apply_timing():
    path = os.path.join(VIDEO, "voiceover", "office.json")
    if os.path.exists(path):
        with open(path) as f:
            timing = json.load(f).get("durations", {})
        for sc in SCENES:
            if sc["id"] in timing:
                sc["dur"] = float(timing[sc["id"]])


def audio_chain(path):
    out = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "info", "-i", path, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = json.loads(out[out.rfind("{"):out.rfind("}") + 1])
    return f"volume={-16.0 - float(m['input_i']):.2f}dB,alimiter=limit=0.84:attack=5:release=60:level=0,apad"


def render(preview=False, final=False, stills=False):
    apply_timing()
    out = os.path.join(VIDEO, "out")
    os.makedirs(out, exist_ok=True)
    problems = copy_qa()
    with open(os.path.join(out, "qa-office-vertical.json"), "w") as f:
        json.dump(dict(canvas="vertical", look="lofi-office", problems=[list(p) for p in problems],
                       scenes=[dict(id=s["id"], duration=s["dur"]) for s in SCENES]), f, indent=2)
    if problems:
        print("QA FAILED:", problems)
        return False
    cues = None
    cap_path = os.path.join(VIDEO, "captions.json")
    if os.path.exists(cap_path) and not preview:
        with open(cap_path) as f:
            cues = json.load(f)["cues"]
    tmp = tempfile.mkdtemp(prefix="dandy-office-")
    n, offset, last_room, contact = 0, 0.0, None, []
    for sc in SCENES:
        frames = int(round(sc["dur"] * FPS))
        picks = {int(1.0 * FPS), frames - int(0.5 * FPS)}
        for i in range(frames):
            if preview and i % 3:
                continue
            if stills and i not in picks:
                continue
            t = i / FPS
            if sc.get("end"):
                fr = finish(end_card(last_room, t), t, offset + t, bloom=0.5, grain=2.5, vignette=0.3, drift=0.5)
            else:
                fr = room_frame(t, sc["o"])
                last_room = fr
                fr = finish(fr, t, offset + t, bloom=0.3, grain=2.5, vignette=0.3, drift=0.5, zoom=1.02)
            for cid, text, at, y, role, align, exit_at in TITLES:
                if cid == sc["id"]:
                    title(fr, text, t - at, y, role=role, align=align, exit_at=exit_at, t_abs=t)
            if cues:
                draw_cue(fr, cues, offset + t)
            if stills:
                fr.convert("RGB").save(os.path.join(out, f"office-{sc['id']}-{t:04.1f}.png"))
                continue
            fr.convert("RGB").save(os.path.join(tmp, f"f{n:06d}.png"), compress_level=1)
            n += 1
            if i == max(k for k in range(frames) if not (preview and k % 3)):
                contact.append(fr.convert("RGB"))
        offset += sc["dur"]
    if stills:
        print("stills in", out)
        return True
    mp4 = os.path.join(out, f"06-new-hire-vertical{'-final' if final else ''}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS // 3 if preview else FPS), "-i", os.path.join(tmp, "f%06d.png")]
    audio_path = os.path.join(VIDEO, "voiceover", "office.json")
    if os.path.exists(audio_path) and not preview:
        with open(audio_path) as f:
            audio = json.load(f)
        total = sum(s["dur"] for s in SCENES)
        cmd += ["-ss", str(audio.get("offset_s", 0)), "-i", os.path.join(ROOT, audio["file"]),
                "-af", audio_chain(os.path.join(ROOT, audio["file"])), "-t", str(total), "-c:a", "aac", "-b:a", "160k"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"] + (["-preset", "slow", "-crf", "17", "-movflags", "+faststart"] if final else ["-crf", "20"]) + [mp4]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    th = 480
    thumbs = [im.resize((int(im.width * th / im.height), th)) for im in contact]
    sheet = Image.new("RGB", (len(thumbs) * (thumbs[0].width + 24) + 24, th + 48), (30, 36, 52))
    for i, im in enumerate(thumbs):
        sheet.paste(im, (24 + i * (thumbs[0].width + 24), 24))
    sheet.save(os.path.join(out, "contact-office-vertical.png"))
    print(f"rendered {mp4} ({n} frames)")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--stills", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if render(a.preview, a.final, a.stills) else 1)

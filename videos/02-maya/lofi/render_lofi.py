"""Renderer for video 02's own look (the cozy room). Vertical only.

Usage:  python3 videos/02-maya/lofi/render_lofi.py [--preview] [--final] [--stills]

Layers (SVG, from gen_room.py) are rasterised once at SCALE x the 1080x1920 room; every frame is
composed in room coordinates at that scale, then the camera crops a window and resizes it to
1080x1920, so push-ins stay crisp. Rain, sky, steam, the chat on the monitor, the bulletin board
and the fairy lights are drawn per frame. Narration captions and the end card are drawn in output
coordinates inside the contract's safe zone. The end card is the soft variant: no Dandy Man
(invariants 4 and 5), the room dims and the hat, wordmark and the two contract lines fade in.
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
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "render"))
import gen_room as G  # noqa: E402
import checks  # noqa: E402

with open(os.path.join(ROOT, "style", "contract.json")) as f:
    CONTRACT = json.load(f)
PAL = CONTRACT["palette"]
FONT_DIR = "/usr/share/fonts/opentype/inter"
FPS = CONTRACT["motion"]["fps"]
W, H = 1080, 1920
SCALE = 2  # room raster scale; the camera can zoom up to SCALE x without blur
SAFE = (int(W * 0.08), CONTRACT["layout"]["vertical_safe_top_px"], W - int(W * 0.08), H - CONTRACT["layout"]["vertical_safe_bottom_px"])


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def lerp(a, b, p):
    return a + (b - a) * p


def mix(c1, c2, p):
    return tuple(int(lerp(c1[i], c2[i], p)) for i in range(3))


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(size))


_layers = {}


def layer(name):
    if name not in _layers:
        png = cairosvg.svg2png(url=os.path.join(HERE, "layers", name + ".svg"), output_width=W * SCALE)
        _layers[name] = Image.open(io.BytesIO(png)).convert("RGBA")
    return _layers[name]


def S(v):
    return int(v * SCALE)


# ---------- per-frame room drawing (all in room coords, scaled by S) ----------
NIGHT = (rgb("#0E0A1F"), rgb("#1C1440"))
DAWN = (rgb("#3A2A6E"), rgb("#C98A8A"))
DAY = (rgb("#6E86C8"), rgb("#CFE0F5"))


def sky_colors(phase):
    """phase 0 = night, 0.5 = day, 1 = night again."""
    p = (1 - math.cos(phase * 2 * math.pi)) / 2  # 0 night -> 1 day -> 0
    if p < 0.5:
        q = p / 0.5
        return mix(NIGHT[0], DAWN[0], q), mix(NIGHT[1], DAWN[1], q), p
    q = (p - 0.5) / 0.5
    return mix(DAWN[0], DAY[0], q), mix(DAWN[1], DAY[1], q), p


def draw_sky(canvas, phase, rain, t):
    x0, y0, x1, y1 = (S(v) for v in G.WINDOW)
    top, bottom, dayness = sky_colors(phase)
    sky = Image.new("RGBA", (x1 - x0, y1 - y0))
    d = ImageDraw.Draw(sky)
    hgt = y1 - y0
    for i in range(0, hgt, 4):
        d.rectangle((0, i, x1 - x0, i + 4), fill=mix(top, bottom, i / hgt) + (255,))
    rnd = random.Random(7)
    if dayness < 0.6:  # stars
        for _ in range(40):
            sx, sy = rnd.random() * (x1 - x0), rnd.random() * hgt * 0.7
            a = int(200 * (1 - dayness / 0.6) * (0.5 + 0.5 * math.sin(t * 2 + sx)))
            d.ellipse((sx - 2, sy - 2, sx + 2, sy + 2), fill=rgb(PAL["text"]) + (max(0, a),))
    # moon by night, sun by day, both ride the phase
    mx = (x1 - x0) * 0.68
    my = hgt * (0.22 + 0.5 * abs(0.5 - phase) * 2 * 0.6)
    if dayness < 0.5:
        a = int(255 * (1 - dayness * 2))
        d.ellipse((mx - S(34), my - S(34), mx + S(34), my + S(34)), fill=rgb(PAL["accent_gold"]) + (a,))
        d.ellipse((mx - S(14), my - S(44), mx + S(40), my + S(14)), fill=mix(top, bottom, 0.2) + (a,))
    else:
        a = int(255 * (dayness - 0.5) * 2)
        d.ellipse((mx - S(40), my - S(40), mx + S(40), my + S(40)), fill=rgb(PAL["accent_gold"]) + (a,))
    # distant skyline
    rnd2 = random.Random(3)
    bx = 0
    while bx < x1 - x0:
        bw, bh = S(rnd2.randint(30, 70)), S(rnd2.randint(60, 180))
        d.rectangle((bx, hgt - bh, bx + bw, hgt), fill=mix(top, (10, 6, 24), 0.7) + (255,))
        for wy in range(hgt - bh + S(12), hgt - S(8), S(18)):
            for wx in range(bx + S(6), bx + bw - S(6), S(14)):
                if rnd2.random() < (0.35 if dayness < 0.5 else 0.08):
                    d.rectangle((wx, wy, wx + S(5), wy + S(7)), fill=rgb(PAL["accent_gold"]) + (150,))
        bx += bw + S(rnd2.randint(6, 18))
    if rain > 0:
        rnd3 = random.Random(11)
        for _ in range(70):
            rx = rnd3.random() * (x1 - x0)
            speed = S(900) * (0.8 + rnd3.random() * 0.5)
            ry = (rnd3.random() * hgt + t * speed) % (hgt + S(60)) - S(60)
            ln = S(rnd3.randint(26, 50))
            d.line([(rx, ry), (rx - ln * 0.18, ry + ln)], fill=rgb(PAL["soft"]) + (int(110 * rain),), width=S(1.5))
    canvas.alpha_composite(sky, (x0, y0))


def draw_steam(canvas, t, strength=1.0):
    if strength <= 0:
        return
    x, y = (S(v) for v in G.MUG)
    d = ImageDraw.Draw(canvas)
    for k in range(3):
        pts = []
        ph = t * 0.9 + k * 2.1
        for i in range(12):
            u = i / 11
            px = x + S(-14 + k * 14) + math.sin(ph + u * 5) * S(10) * (0.3 + u)
            py = y - S(8) - u * S(110)
            pts.append((px, py))
        a = int(120 * strength * (0.6 + 0.4 * math.sin(ph)))
        for i in range(len(pts) - 1):
            fade = 1 - i / len(pts)
            d.line([pts[i], pts[i + 1]], fill=rgb(PAL["text"]) + (int(a * fade),), width=S(4))


def draw_lights(canvas, t):
    d = ImageDraw.Draw(canvas)
    for i in range(10):
        cx = 60 + i * 108
        cy = 150 + (60 if i % 2 else 10) + (i % 3) * 8
        tw = 0.5 + 0.5 * math.sin(t * 2.2 + i * 1.7)
        r = S(16)
        d.ellipse((S(cx) - r, S(cy) - r, S(cx) + r, S(cy) + r), fill=rgb(PAL["accent_gold"]) + (int(70 * tw),))


def draw_glow(canvas, t, strength=1.0):
    """Cool light from the monitor on Maya and the desk, flickering gently."""
    x0, y0, x1, y1 = (S(v) for v in G.SCREEN)
    g = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    a = int(60 * strength * (0.85 + 0.15 * math.sin(t * 7.3)))
    ImageDraw.Draw(g).ellipse((x0 - S(260), y0 - S(120), x1 + S(80), y1 + S(220)), fill=rgb(PAL["highlight"]) + (a,))
    canvas.alpha_composite(g.filter(ImageFilter.GaussianBlur(S(60))))


# ---------- the chat on the monitor ----------
def draw_screen(canvas, msgs, t, dandy=None, typing=None):
    """msgs: list of (who, text, at). dandy: (at, title, nodes[(label, state)]) side panel. typing: (at, text) being typed by Maya."""
    x0, y0, x1, y1 = (S(v) for v in G.SCREEN)
    scr = Image.new("RGBA", (x1 - x0, y1 - y0), rgb(PAL["background"]) + (255,))
    d = ImageDraw.Draw(scr)
    sw, sh = scr.size
    hdr = S(26)
    d.rectangle((0, 0, sw, hdr), fill=rgb(PAL["background_lift"]) + (255,))
    for i, c in enumerate(((255, 107, 107), (245, 197, 66), (124, 77, 255))):
        d.ellipse((S(8) + i * S(14), S(8), S(16) + i * S(14), S(16)), fill=c + (255,))
    f = font("Inter-Regular.otf", S(15))
    fb = font("Inter-Medium.otf", S(15))
    chat_w = sw if dandy is None or t < dandy[0] else int(sw * 0.56)
    y = hdr + S(14)
    pad = S(10)
    for who, text, at in msgs:
        if t < at:
            continue
        p = ease((t - at) / 0.35)
        lines = wrap(text, f, chat_w - S(30) - pad * 2, d)
        bw = max(d.textlength(l, font=f) for l in lines) + pad * 2
        bh = len(lines) * S(20) + pad * 1.4
        if who == "maya":
            bx0 = chat_w - S(12) - bw
            col = rgb(PAL["primary"])
        else:
            bx0 = S(12)
            col = rgb(PAL["background_lift"])
        by0 = y + (1 - p) * S(8)
        d.rounded_rectangle((bx0, by0, bx0 + bw, by0 + bh), radius=S(8), fill=col + (int(255 * p),))
        for i, l in enumerate(lines):
            d.text((bx0 + pad, by0 + pad * 0.6 + i * S(20)), l, font=f, fill=rgb(PAL["text"]) + (int(255 * p),))
        y += bh + S(8)
    sent_at = min((m[2] for m in msgs if m[0] == "maya"), default=None)
    if typing and t >= typing[0] and (sent_at is None or t < sent_at):
        n = int((t - typing[0]) / 0.035)
        shown = typing[1][:n]
        bx0 = S(12)
        d.rounded_rectangle((bx0, sh - S(34), chat_w - S(12), sh - S(10)), radius=S(8), fill=rgb(PAL["background_lift"]) + (255,), outline=rgb(PAL["soft"]) + (160,), width=S(1))
        cursor = "|" if int(t * 2) % 2 == 0 and n < len(typing[1]) else ""
        d.text((bx0 + pad, sh - S(29)), shown + cursor, font=f, fill=rgb(PAL["text"]) + (255,))
    if dandy is not None and t >= dandy[0]:
        p = ease((t - dandy[0]) / 0.5)
        px0 = sw - int(sw * 0.44 * p)
        if sw - px0 < S(60):
            canvas.alpha_composite(scr, (x0, y0))
            return
        d.rectangle((px0, hdr, sw, sh), fill=rgb(PAL["background_lift"]) + (255,))
        d.line([(px0, hdr), (px0, sh)], fill=rgb(PAL["highlight"]) + (255,), width=S(2))
        hat = hat_img(S(16))
        scr.alpha_composite(hat, (px0 + S(10), hdr + S(8)))
        d.text((px0 + S(32), hdr + S(8)), "Dandy", font=fb, fill=rgb(PAL["accent_gold"]) + (255,))
        d.text((px0 + S(10), hdr + S(32)), dandy[1], font=fb, fill=rgb(PAL["text"]) + (255,))
        yy = hdr + S(60)
        for label, state in dandy[2]:
            col = {"done": rgb(PAL["highlight"]), "next": rgb(PAL["accent_gold"]), "todo": rgb(PAL["soft"])}[state]
            d.rounded_rectangle((px0 + S(10), yy, sw - S(10), yy + S(26)), radius=S(5), outline=col + (255,), width=S(2),
                                fill=(col + (60,)) if state != "todo" else (0, 0, 0, 0))
            d.text((px0 + S(18), yy + S(3)), label, font=f, fill=rgb(PAL["text"]) + (255,))
            mark = {"done": "done", "next": "next", "todo": ""}[state]
            if mark:
                mw = d.textlength(mark, font=f)
                d.text((sw - S(16) - mw, yy + S(4)), mark, font=f, fill=col + (255,))
            yy += S(32)
    canvas.alpha_composite(scr, (x0, y0))


_hat = {}


def hat_img(h):
    if h not in _hat:
        im = Image.open(os.path.join(ROOT, "motifs", "logo-hat-light.png")).convert("RGBA")
        _hat[h] = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
    return _hat[h]


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


# ---------- the bulletin board ----------
PROJECTS = [("Budget tracker", 0.6), ("Workout log", 0.45), ("Side business site", 0.3)]


def draw_board(canvas, t, cards_at, notes=None, done=None, progress_to=None, pins_only=False):
    """cards_at: per-card enter time. notes: list of (text, at, peel_at or None). done: per-card time the card turns done.
    progress_to: per-card (at, value) progress bar fill."""
    bx0, by0, bx1, by1 = (S(v) for v in G.BOARD)
    d = ImageDraw.Draw(canvas)
    ft = font("Inter-Bold.otf", S(20))
    fs = font("Inter-Medium.otf", S(15))
    fn = font("Inter-Medium.otf", S(17))
    card_w, card_h = (bx1 - bx0) - S(60), S(96)
    for i, (title, prog) in enumerate(PROJECTS):
        at = cards_at[i]
        if t < at:
            continue
        p = ease((t - at) / 0.4)
        cx0 = bx0 + S(30)
        cy0 = by0 + S(30) + i * (card_h + S(34)) - (1 - p) * S(10)
        is_done = done is not None and done[i] is not None and t >= done[i]
        dp = ease((t - done[i]) / 0.5) if is_done else 0.0
        card_col = rgb(PAL["text"])
        d.rounded_rectangle((cx0, cy0, cx0 + card_w, cy0 + card_h), radius=S(6), fill=card_col + (int(255 * p),))
        d.ellipse((cx0 + card_w / 2 - S(7), cy0 - S(7), cx0 + card_w / 2 + S(7), cy0 + S(7)), fill=rgb(PAL["warning"]) + (int(255 * p),))
        d.text((cx0 + S(16), cy0 + S(14)), title, font=ft, fill=rgb(PAL["background"]) + (int(255 * p),))
        # progress bar
        val = prog
        if progress_to is not None and progress_to[i] and t >= progress_to[i][0]:
            val = lerp(prog, progress_to[i][1], ease((t - progress_to[i][0]) / 1.2))
        pb = (cx0 + S(16), cy0 + S(58), cx0 + card_w - S(16), cy0 + S(72))
        d.rounded_rectangle(pb, radius=S(7), fill=rgb(PAL["soft"]) + (int(120 * p),))
        d.rounded_rectangle((pb[0], pb[1], pb[0] + (pb[2] - pb[0]) * val, pb[3]), radius=S(7), fill=rgb(PAL["highlight"]) + (int(255 * p),))
        lab = f"{int(val * 100)}%"
        d.text((cx0 + card_w - S(16) - d.textlength(lab, font=fs), cy0 + S(14)), lab, font=fs, fill=rgb(PAL["background_lift"]) + (int(255 * p),))
        if is_done:
            # "done" stamp slaps on, slightly rotated
            stamp = Image.new("RGBA", (S(120), S(50)), (0, 0, 0, 0))
            sd = ImageDraw.Draw(stamp)
            sd.rounded_rectangle((S(3), S(3), S(117), S(47)), radius=S(8), outline=rgb(PAL["highlight"]) + (255,), width=S(4))
            sd.text((S(22), S(11)), "DONE", font=font("Inter-Bold.otf", S(22)), fill=rgb(PAL["highlight"]) + (255,))
            stamp = stamp.rotate(-8, expand=True, resample=Image.BICUBIC)
            sc = 1.6 - 0.6 * dp
            st = stamp.resize((int(stamp.width * sc), int(stamp.height * sc)))
            st.putalpha(st.split()[3].point(lambda v: int(v * dp)))
            canvas.alpha_composite(st, (int(cx0 + card_w - S(150) - st.width / 2 + S(60)), int(cy0 + S(40) - st.height / 2)))
    if notes:
        for i, (text, at, peel) in enumerate(notes):
            if t < at:
                continue
            p = ease((t - at) / 0.35)
            if peel is not None and t >= peel:
                q = ease((t - peel) / 0.45)
                if q >= 1:
                    continue
            else:
                q = 0.0
            cy0 = by0 + S(30) + i * (card_h + S(34))
            nw, nh = S(150), S(84)
            nx = bx1 - S(30) - nw + S(8)
            ny = cy0 + S(6)
            note = Image.new("RGBA", (nw + S(20), nh + S(20)), (0, 0, 0, 0))
            nd = ImageDraw.Draw(note)
            nd.rectangle((S(10), S(10), S(10) + nw, S(10) + nh), fill=rgb(PAL["warning"]) + (235,))
            nd.polygon([(S(10) + nw - S(18), S(10) + nh), (S(10) + nw, S(10) + nh - S(18)), (S(10) + nw, S(10) + nh)], fill=rgb(PAL["background"]) + (90,))
            lines = wrap(text, fn, nw - S(20), nd)
            for k, l in enumerate(lines):
                nd.text((S(20), S(20) + k * S(21)), l, font=fn, fill=rgb(PAL["background"]) + (255,))
            ang = (-6, 5, -4)[i % 3] + q * 40
            note = note.rotate(ang, expand=True, resample=Image.BICUBIC)
            a = p * (1 - q)
            note.putalpha(note.split()[3].point(lambda v: int(v * a)))
            canvas.alpha_composite(note, (int(nx - (note.width - nw) / 2 + q * S(60)), int(ny - (note.height - nh) / 2 - (1 - p) * S(10) + q * S(120))))


# ---------- scenes ----------
def room_frame(t, pose, phase, rain, steam, screen, board, cam, zoom_to=None, glow=1.0):
    """Compose the room at SCALE, then crop with the camera (cx, cy, zoom) in room coords."""
    canvas = Image.new("RGBA", (W * SCALE, H * SCALE), rgb(PAL["background"]) + (255,))
    draw_sky(canvas, phase, rain, t)
    canvas.alpha_composite(layer("back"))
    draw_lights(canvas, t)
    if board:
        draw_board(canvas, t, **board)
    bob = int(math.sin(t * 2 * math.pi / 2.6) * S(2)) if pose == "typing" else 0
    canvas.alpha_composite(layer("maya-" + pose), (0, bob))
    canvas.alpha_composite(layer("front"))
    if screen:
        draw_screen(canvas, t=t, **screen)
    draw_glow(canvas, t, glow)
    draw_steam(canvas, t, steam)
    cx, cy, z = cam
    if zoom_to:
        z = lerp(z, zoom_to[0], ease(t / zoom_to[1]))
    cw, ch = W * SCALE / z, H * SCALE / z
    x0 = min(max(0, cx * SCALE - cw / 2), W * SCALE - cw)
    y0 = min(max(0, cy * SCALE - ch / 2), H * SCALE - ch)
    return canvas.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)


def caption(frame, text, t_local, y=0.68, role="body", align="left", exit_at=None, t_abs=None):
    if t_local < 0:
        return
    a = ease(t_local / 0.4)
    if exit_at is not None and t_abs is not None and t_abs >= exit_at:
        a = min(a, 1 - ease((t_abs - exit_at) / 0.3))
    if a <= 0:
        return
    sizes = CONTRACT["type"]["vertical"]
    fnt = font({"headline": "Inter-Bold.otf", "body": "Inter-Regular.otf", "caption": "Inter-Medium.otf"}[role], sizes[role])
    d = ImageDraw.Draw(frame)
    lines = wrap(text, fnt, SAFE[2] - SAFE[0], d)
    lh = fnt.size * 1.2
    yy = y * H - (1 - a) * 20
    for l in lines:
        lw = d.textlength(l, font=fnt)
        x = SAFE[0] if align == "left" else W / 2 - lw / 2
        d.text((x + 2, yy + 3), l, font=fnt, fill=(0, 0, 0, int(140 * a)))
        d.text((x, yy), l, font=fnt, fill=rgb(PAL["text"]) + (int(255 * a),))
        yy += lh


def draw_cue(frame, cues, t_global):
    """Burned-in narration captions, same style as render.py: bold, centred, on a dark pill."""
    cue = next((c for c in cues if c["start"] <= t_global < c["end"]), None)
    if cue is None:
        return
    sizes = CONTRACT["type"]["vertical"]
    fnt = font("Inter-Bold.otf", int(sizes["body"] * 0.95))
    d = ImageDraw.Draw(frame)
    lines = wrap(cue["text"], fnt, SAFE[2] - SAFE[0], d)
    lh = fnt.size * 1.15
    y = 0.80 * H
    pad = 18
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=fnt)
        x = W / 2 - tw / 2
        yy = y + i * (lh + pad * 0.8)
        d.rounded_rectangle((x - pad, yy - pad * 0.6, x + tw + pad, yy + lh + pad * 0.4), radius=14, fill=rgb(PAL["background"]) + (200,))
        d.text((x, yy), line, font=fnt, fill=rgb(PAL["text"]) + (255,))


def end_card(frame_room, t, dur):
    """Soft end card: the room darkens and blurs under the hat, wordmark and the two contract lines."""
    p = ease(t / 1.2)
    bg = frame_room.filter(ImageFilter.GaussianBlur(int(14 * p)))
    dark = Image.new("RGBA", bg.size, rgb(PAL["background"]) + (int(200 * p),))
    bg.alpha_composite(dark)
    d = ImageDraw.Draw(bg)
    sizes = CONTRACT["type"]["vertical"]
    fh = font("Inter-Bold.otf", int(sizes["headline"] * 1.5))
    a = ease((t - 0.6) / 0.6)
    if a > 0:
        hat = hat_img(int(H * 0.11))
        hy = H * 0.36
        hat2 = hat.copy()
        hat2.putalpha(hat2.split()[3].point(lambda v: int(v * a)))
        bg.alpha_composite(hat2, (int(W / 2 - hat.width / 2), int(hy)))
        tw = d.textlength("Dandy", font=fh)
        ty = hy + hat.height + 40
        d.text((W / 2 - tw / 2, ty), "Dandy", font=fh, fill=rgb(PAL["text"]) + (int(255 * a),))
        yy = ty + fh.size * 1.1 + 60
        for i, line in enumerate(CONTRACT["copy_rules"]["end_card_lines"]):
            b = ease((t - 1.0 - 0.25 * i) / 0.5)
            fl = font("Inter-Regular.otf" if i == 0 else "Inter-Medium.otf", sizes["body" if i == 0 else "caption"])
            lw = d.textlength(line, font=fl)
            col = rgb(PAL["accent_gold"]) if i == 1 else rgb(PAL["soft"])
            d.text((W / 2 - lw / 2, yy), line, font=fl, fill=col + (int(255 * b),))
            yy += fl.size * 1.1 + 60
    return bg


WIDE = (540, 960, 1.0)
BOARD_CAM = (330, 560, 1.9)
SCREEN_CAM = (640, 1030, 1.75)
CHAT_INTRO = [("maya", "build me a budget tracker: income, spending, a chart", 0.0),
              ("agent", "Done. Income and spending are in. Want the chart next?", 1.4)]
CHAT_FORGOT = [("maya", "add the chart to the budget tracker", 1.5),
               ("agent", "Which budget tracker? I have no context on that.", 2.2)]
CHAT_DANDY = [("agent", "Reading Dandy. Budget tracker: income and spending done, chart is next. Starting there.", 0.9),
              ("maya", "yes", 3.3),
              ("agent", "Chart added. Writing it back to Dandy.", 4.4)]
DANDY_PANEL = (0.0, "Budget tracker", [("Income", "done"), ("Spend", "done"), ("Chart", "next")])
NOTES = [("where was I?", 1.4, None), ("rebuilt it. again.", 1.9, None), ("explained it 4 times", 2.4, None)]
NOTES_PEEL = [("where was I?", 0.0, 0.2), ("rebuilt it. again.", 0.0, 0.9), ("explained it 4 times", 0.0, 1.6)]

SCENES = [
    # id, duration, narration (for captions.json later), frame function
    dict(id="s1-room", dur=5.3, lines="Maya isn't a coder. She builds things with Claude Code anyway.",
         frame=lambda t: room_frame(t, "typing", 0.0, 1.0, 1.0, dict(msgs=CHAT_INTRO), dict(cards_at=[0, 0, 0]), WIDE, zoom_to=(1.1, 5.3))),
    dict(id="s2-board", dur=4.4, lines="Three projects. None finished.",
         frame=lambda t: room_frame(t, "typing", 0.0, 1.0, 0.8, dict(msgs=CHAT_INTRO), dict(cards_at=[0.3, 0.7, 1.1], notes=NOTES), BOARD_CAM)),
    dict(id="s3-forgot", dur=3.6, lines="",
         frame=lambda t: room_frame(t, "typing" if t < 2.8 else "slumped", 0.0, 1.0, 0.6, dict(msgs=CHAT_FORGOT, typing=(0.2, "add the chart to the budget tracker")), dict(cards_at=[0, 0, 0], notes=[(n[0], 0, None) for n in NOTES]), SCREEN_CAM)),
    dict(id="s4-dandy", dur=6.0, lines="Then she put them in Dandy. Now every session starts from what's actually true.",
         frame=lambda t: room_frame(t, "slumped" if t < 0.6 else ("up" if t < 2.6 else "typing"), 0.02, 0.6, 0.4, dict(msgs=CHAT_DANDY, dandy=DANDY_PANEL), dict(cards_at=[0, 0, 0], notes=[(n[0], 0, None) for n in NOTES]), SCREEN_CAM)),
    dict(id="s5-weeks", dur=2.0, lines="Three weeks later.",
         frame=lambda t: room_frame(t, "typing", (t / 2.0) % 1.0, max(0.0, 1 - t / 0.8), 0.8, dict(msgs=CHAT_DANDY, dandy=DANDY_PANEL), dict(cards_at=[0, 0, 0], notes=[(n[0], 0, None) for n in NOTES]), WIDE, zoom_to=(1.08, 2.0))),
    dict(id="s6-done", dur=4.5, lines="Same Maya. Same agent.",
         frame=lambda t: room_frame(t, "typing", 0.0, 0.0, 1.0, dict(msgs=CHAT_DANDY, dandy=DANDY_PANEL),
                                    dict(cards_at=[0, 0, 0], notes=NOTES_PEEL, done=[1.0, 1.8, 2.6], progress_to=[(0.6, 1.0), (1.4, 1.0), (2.2, 1.0)]), BOARD_CAM)),
    dict(id="end", dur=4.5, lines="Finish what you started.", end=True),
]
CAPTIONS = [  # on-screen text, drawn in output coords; (scene id, text, at, y, role, align, exit_at)
    ("s1-room", "Maya. Not a coder.", 1.0, 0.74, "headline", "left", 4.6),
    ("s2-board", "Started 3. Finished 0.", 2.6, 0.745, "body", "left", None),
    ("s5-weeks", "3 weeks later", 0.2, 0.74, "headline", "left", None),
    ("s6-done", "Finished 3.", 3.2, 0.745, "body", "left", None),
    ("end", "Finish what you started.", 1.0, 0.74, "body", "center", None),
]


def copy_qa():
    """Invariant 3 on the on-screen copy (captions, notes, chat); layout is by construction inside the safe zone."""
    rules = CONTRACT["copy_rules"]
    problems = []
    texts = [c[1] for c in CAPTIONS] + [n[0] for n in NOTES] + [m[1] for m in CHAT_INTRO + CHAT_FORGOT + CHAT_DANDY]
    for tx in texts:
        for ch in rules["banned_characters"]:
            if ch in tx:
                problems.append(("copy", f"banned character in {tx!r}"))
        for ph in rules["banned_phrases"]:
            if ph in tx.lower():
                problems.append(("copy", f"banned phrase {ph!r} in {tx!r}"))
    return problems


def apply_timing():
    """voiceover/lofi.json may carry {"durations": {scene_id: seconds}} from the aligner."""
    path = os.path.join(VIDEO, "voiceover", "lofi.json")
    if not os.path.exists(path):
        return
    with open(path) as f:
        timing = json.load(f).get("durations", {})
    for sc in SCENES:
        if sc["id"] in timing:
            sc["dur"] = float(timing[sc["id"]])


def render(preview=False, final=False, stills=False):
    apply_timing()
    out = os.path.join(VIDEO, "out")
    os.makedirs(out, exist_ok=True)
    problems = copy_qa()
    report = dict(canvas="vertical", look="lofi-room", problems=[list(p) for p in problems],
                  scenes=[dict(id=s["id"], duration=s["dur"]) for s in SCENES])
    with open(os.path.join(out, "qa-lofi-vertical.json"), "w") as f:
        json.dump(report, f, indent=2)
    if problems:
        print("QA FAILED:", problems)
        return False
    tmp = tempfile.mkdtemp(prefix="dandy-lofi-")
    cues = None
    cap_path = os.path.join(VIDEO, "captions.json")
    if os.path.exists(cap_path) and not preview:
        with open(cap_path) as f:
            cues = json.load(f)["cues"]
    n, offset, contact = 0, 0.0, []
    step = 1.0 / FPS
    last_room = None
    for sc in SCENES:
        frames = int(sc["dur"] * FPS)
        for i in range(frames):
            if preview and i % 3:
                continue
            if stills and i not in (int(1.0 * FPS), int((sc["dur"] - 0.6) * FPS)):
                continue
            t = i * step
            if sc.get("end"):
                fr = end_card(last_room, t, sc["dur"])
            else:
                fr = sc["frame"](t)
                last_room = fr
            for cid, text, at, y, role, align, exit_at in CAPTIONS:
                if cid == sc["id"] and not cues:  # on-screen titles only when there is no narration track
                    caption(fr, text, t - at, y=y, role=role, align=align, exit_at=exit_at, t_abs=t)
            if cues:
                draw_cue(fr, cues, offset + t)
            if stills:
                if i in (int(1.0 * FPS), int((sc["dur"] - 0.6) * FPS)):
                    fr.convert("RGB").save(os.path.join(out, f"lofi-{sc['id']}-{t:04.1f}.png"))
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
    mp4 = os.path.join(out, f"02-maya-lofi-vertical{'-final' if final else ''}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "f%06d.png")]
    audio_path = os.path.join(VIDEO, "voiceover", "lofi.json")
    if os.path.exists(audio_path) and not preview:
        with open(audio_path) as f:
            audio = json.load(f)
        total = sum(s["dur"] for s in SCENES)
        cmd += ["-ss", str(audio.get("offset_s", 0)), "-i", os.path.join(ROOT, audio["file"]),
                "-af", "highpass=f=80,afftdn=nf=-28,loudnorm=I=-16:TP=-1.5:LRA=11,apad", "-t", str(total), "-c:a", "aac", "-b:a", "160k"]
    if final:
        cmd += ["-c:v", "libx264", "-preset", "slow", "-pix_fmt", "yuv420p", "-crf", "17", "-movflags", "+faststart", mp4]
    else:
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", mp4]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    th = 480
    thumbs = [im.resize((int(im.width * th / im.height), th)) for im in contact]
    sheet = Image.new("RGB", (len(thumbs) * (thumbs[0].width + 24) + 24, th + 48), rgb(PAL["background_lift"]))
    for i, im in enumerate(thumbs):
        sheet.paste(im, (24 + i * (thumbs[0].width + 24), 24))
    sheet.save(os.path.join(out, "contact-lofi-vertical.png"))
    print(f"rendered {mp4} ({n} frames)")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--stills", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if render(a.preview, a.final, a.stills) else 1)

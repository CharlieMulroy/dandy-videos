"""The Void Stage look, shared by the pinned series (10 What is Dandy?, 11 How does Dandy work?, 12 Why use Dandy?).

Dandy Man floats bottom right in a dark purple void and points up at the visuals, which float in the open space
above him. One short key phrase sits bottom left; captions are burned in under both. Every video in the series
opens on a still title card (the thumbnail) and closes on the shared end card with Dandy Man.

A video file supplies its scenes and calls render_video(spec); see videos/10-what-is-dandy/render_what.py.
All four shared checks (render/checks.py run_all) run on the declared layout before any frame is drawn.
"""
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

import cairosvg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from finish import finish, spring  # noqa: E402,F401
from checks import run_all  # noqa: E402

with open(os.path.join(ROOT, "style", "contract.json")) as f:
    CONTRACT = json.load(f)
PAL = CONTRACT["palette"]
W, H = 1080, 1920
FPS = CONTRACT["motion"]["fps"]
FONT_DIR = "/usr/share/fonts/opentype/inter"
MARGIN = int(W * CONTRACT["layout"]["outer_margin_pct_of_short_edge"])
SAFE = (MARGIN, CONTRACT["layout"]["vertical_safe_top_px"], W - MARGIN, H - CONTRACT["layout"]["vertical_safe_bottom_px"])


def _hex(k):
    return tuple(int(PAL[k][i:i + 2], 16) for i in (1, 3, 5))


BG, BG_LIFT, PURPLE, PURPLE_HI, SOFT, TEXT, GOLD, WARN = (_hex(k) for k in (
    "background", "background_lift", "primary", "highlight", "soft", "text", "accent_gold", "warning"))
VOID = (14, 8, 28)
CARD = (38, 24, 66)
ORB = (226, 214, 255)

# ---------------------------------------------------------------- layout slots
STAGE = (SAFE[0], 270, SAFE[2], 840)                 # where the visuals float
DM_H = 480                                           # Dandy Man in his corner
DM_X0, DM_Y0 = 791, 895                              # sprite top-left; the figure's right edge sits on the margin
DM_BOX = (847, DM_Y0, SAFE[2], DM_Y0 + DM_H)         # the drawn figure, widest pose
PHRASE_X, PHRASE_Y, PHRASE_W = SAFE[0], 1010, 713    # key phrase block, bottom left
PHRASE_SIZE = 72
TITLE_DM_H = 680
TITLE_DM_X0, TITLE_DM_Y0 = 344, 790
CAP_SIZE = 44                                        # one line per cue, so captions clear Dandy Man


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
    return tuple(int(lerp(c1[i], c2[i], clamp(p))) for i in range(3))


def wrap(text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if fnt.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    return lines


# ---------------------------------------------------------------- sprites
def _radial(size, color, power=2.0, alpha=255):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.sqrt((xx - size / 2) ** 2 + (yy - size / 2) ** 2) / (size / 2)
    a = np.clip(1 - r, 0, 1) ** power * alpha
    arr = np.zeros((size, size, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = a.astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


HALO = _radial(240, ORB, 2.2, 160)
CORE = _radial(36, (255, 255, 255), 1.2, 255)
GLOW_P = _radial(480, PURPLE_HI, 1.9, 150)
GLOW_G = _radial(300, GOLD, 2.2, 120)


def put_sprite(img, spr, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    s = spr if scale == 1.0 else spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if alpha < 1:
        s = s.copy()
        s.putalpha(s.split()[3].point(lambda v: int(v * alpha)))
    img.paste(s, (int(cx - s.width / 2), int(cy - s.height / 2)), s)


_dm_master, _dm_cache = {}, {}


def dm_sprite(pose, height):
    height = int(round(height / 4) * 4)
    key = (pose, height)
    if key not in _dm_cache:
        if pose not in _dm_master:
            png = cairosvg.svg2png(url=os.path.join(ROOT, "cast", "dandy-man", pose + ".svg"), output_height=1000)
            _dm_master[pose] = Image.open(io.BytesIO(png)).convert("RGBA")
        m = _dm_master[pose]
        _dm_cache[key] = m.resize((int(m.width * height / m.height), height), Image.LANCZOS)
    return _dm_cache[key]


def draw_dm(img, tg, pose="idle", x0=DM_X0, y0=DM_Y0, height=DM_H, alpha=1.0, bob=True):
    """Dandy Man, floating: a slow bob and a soft purple glow under his feet."""
    dy = (7 * math.sin(tg * 1.7) if bob else 0) * height / DM_H
    spr = dm_sprite(pose, height)
    cx = x0 + spr.width * 0.505
    put_sprite(img, GLOW_P, cx, y0 + height + 6 + dy * 0.3, scale=height / 620, alpha=0.55 * alpha)
    if alpha < 1:
        spr = spr.copy()
        spr.putalpha(spr.split()[3].point(lambda v: int(v * alpha)))
    img.paste(spr, (int(x0), int(y0 + dy)), spr)


def dm_place(p):
    """Dandy Man's slot between the title card (p=0) and his corner (p=1)."""
    q = smooth(p)
    return dict(x0=lerp(TITLE_DM_X0, DM_X0, q), y0=lerp(TITLE_DM_Y0, DM_Y0, q), height=lerp(TITLE_DM_H, DM_H, q))


# ---------------------------------------------------------------- the void
_void = None
_specks = None


def void(tg):
    global _void, _specks
    if _void is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - 560) / 900) ** 2 + ((yy - 700) / 1150) ** 2)
        lift = np.clip(1 - r, 0, 1) ** 1.6
        arr = np.array(VOID, np.float32) + lift[..., None] * (np.array(BG_LIFT, np.float32) - np.array(VOID, np.float32)) * 0.9
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
        neb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        nd = ImageDraw.Draw(neb)
        nd.ellipse((-200, 180, 620, 900), fill=PURPLE + (46,))
        nd.ellipse((560, 900, 1300, 1700), fill=PURPLE_HI + (30,))
        nd.ellipse((300, 1300, 900, 2100), fill=PURPLE + (34,))
        im.alpha_composite(neb.filter(ImageFilter.GaussianBlur(150)))
        _void = im.convert("RGB")
        rnd = random.Random(21)
        _specks = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(6, 22), rnd.uniform(1.0, 2.6), rnd.uniform(0, 6.28),
                    rnd.randint(40, 130)) for _ in range(90)]
    img = _void.copy()
    d = ImageDraw.Draw(img, "RGBA")
    for x, y, v, r, ph, a in _specks:
        yy = (y - tg * v) % H
        xx = x + 10 * math.sin(tg * 0.4 + ph)
        tw = 0.6 + 0.4 * math.sin(tg * 1.3 + ph)
        d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=SOFT + (int(a * tw),))
    return img


# ---------------------------------------------------------------- pieces of the visuals
def orb(img, x, y, t, alpha=1.0, dim=0.0):
    put_sprite(img, HALO, x, y, scale=0.85 * (1 - 0.3 * dim) * (1 + 0.05 * math.sin(t * 5)), alpha=alpha * (1 - 0.45 * dim))
    put_sprite(img, CORE, x, y, scale=1.35, alpha=alpha * (1 - 0.3 * dim))


def pill_box(cx, cy, text, size=38):
    fnt = font("Inter-SemiBold.otf", size)
    tw = fnt.getlength(text)
    return (cx - tw / 2 - size * 0.8, cy - size * 0.95, cx + tw / 2 + size * 0.8, cy + size * 0.95)


def pill(img, cx, cy, text, alpha=1.0, size=38):
    if alpha <= 0:
        return
    d = ImageDraw.Draw(img, "RGBA")
    b = pill_box(cx, cy, text, size)
    d.rounded_rectangle(b, radius=(b[3] - b[1]) / 2, fill=PURPLE + (int(210 * alpha),), outline=PURPLE_HI + (int(255 * alpha),), width=2)
    fnt = font("Inter-SemiBold.otf", size)
    d.text((cx - fnt.getlength(text) / 2, cy - size * 0.62), text, font=fnt, fill=TEXT + (int(255 * alpha),))


def card(img, box, text, alpha=1.0, slide=0.0, size=48):
    """A floating card with one line of text (the question cards)."""
    if alpha <= 0:
        return
    x0, y0, x1, y1 = box
    y0, y1 = y0 + slide, y1 + slide
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((x0 + 4, y0 + 10, x1 + 4, y1 + 12), radius=22, fill=(0, 0, 0, int(90 * alpha)))
    d.rounded_rectangle((x0, y0, x1, y1), radius=22, fill=CARD + (int(245 * alpha),), outline=SOFT + (int(150 * alpha),), width=2)
    fnt = font("Inter-Bold.otf", size)
    tw = fnt.getlength(text)
    d.text(((x0 + x1) / 2 - tw / 2, (y0 + y1) / 2 - size * 0.62), text, font=fnt, fill=TEXT + (int(255 * alpha),))


NODE_W, NODE_H = 270, 130
STATE_COL = {"done": PURPLE_HI, "building": GOLD, "next": SOFT}


def node_box(x, y):
    return (x, y, x + NODE_W, y + NODE_H)


def node(img, x, y, title, alpha=1.0, state=None, pulse=0.0, slide=0.0, state_alpha=1.0):
    """One piece of the project map: a title, and optionally where it stands (done, building, next)."""
    if alpha <= 0:
        return
    y = y + slide
    cx, cy = x + NODE_W / 2, y + NODE_H / 2
    if pulse > 0:
        put_sprite(img, GLOW_P, cx, cy, scale=0.75, alpha=0.8 * pulse * alpha)
    if state == "building" and state_alpha > 0:
        put_sprite(img, GLOW_G, cx, cy, scale=0.9, alpha=0.5 * state_alpha * alpha)
    d = ImageDraw.Draw(img, "RGBA")
    edge = SOFT
    if state in STATE_COL:
        edge = mix(SOFT, STATE_COL[state], state_alpha)
    edge = mix(edge, (255, 255, 255), 0.6 * pulse)
    d.rounded_rectangle((x + 4, y + 10, x + NODE_W + 4, y + NODE_H + 12), radius=20, fill=(0, 0, 0, int(100 * alpha)))
    d.rounded_rectangle((x, y, x + NODE_W, y + NODE_H), radius=20, fill=mix(CARD, PURPLE, 0.25 * pulse) + (int(250 * alpha),),
                        outline=edge + (int(255 * alpha),), width=3)
    ft = font("Inter-Bold.otf", 40)
    tw = ft.getlength(title)
    ty = y + (22 if state else 40)
    d.text((cx - tw / 2, ty), title, font=ft, fill=TEXT + (int(255 * alpha),))
    if state:
        fs = font("Inter-SemiBold.otf", 28)
        sw = fs.getlength(state)
        a = int(255 * alpha * state_alpha)
        col = STATE_COL[state]
        ix, iy = cx - (sw + 34) / 2 + 11, y + 96
        if state == "done":
            d.ellipse((ix - 12, iy - 12, ix + 12, iy + 12), fill=col + (a,))
            d.line((ix - 6, iy, ix - 1, iy + 5, ix + 6, iy - 5), fill=(255, 255, 255, a), width=3)
        elif state == "building":
            d.ellipse((ix - 11, iy - 11, ix + 11, iy + 11), fill=col + (a,))
        else:
            d.ellipse((ix - 11, iy - 11, ix + 11, iy + 11), outline=col + (a,), width=3)
        d.text((ix + 23, iy - 18), state, font=fs, fill=mix(col, TEXT, 0.35) + (a,))


def anchors(a, b):
    """Where a line leaves node a and meets node b (boxes): straight across a row or down a column."""
    ax, ay = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
    bx, by = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    if abs(ay - by) < abs(ax - bx):
        return ((a[2], ay), (b[0], by)) if bx > ax else ((a[0], ay), (b[2], by))
    return ((ax, a[3]), (bx, b[1])) if by > ay else ((ax, a[1]), (bx, b[3]))


def edge(img, a, b, p=1.0, alpha=1.0, hot=0.0):
    """A connection drawn from box a to box b; p is how much of it has been drawn."""
    if p <= 0 or alpha <= 0:
        return
    (x0, y0), (x1, y1) = anchors(a, b)
    ex, ey = lerp(x0, x1, p), lerp(y0, y1, p)
    d = ImageDraw.Draw(img, "RGBA")
    col = mix(SOFT, (255, 255, 255), hot)
    d.line((x0, y0, ex, ey), fill=PURPLE_HI + (int((70 + 110 * hot) * alpha),), width=12)
    d.line((x0, y0, ex, ey), fill=col + (int(235 * alpha),), width=4)
    if p >= 0.98:
        d.ellipse((x1 - 7, y1 - 7, x1 + 7, y1 + 7), fill=col + (int(255 * alpha),))


def map_glow(img, alpha=1.0):
    put_sprite(img, GLOW_P, 540, 560, scale=2.4, alpha=0.42 * alpha)


def phrase_lines(text):
    return wrap(text, font("Inter-Bold.otf", PHRASE_SIZE), PHRASE_W - 34)


def phrase_box(text):
    fnt = font("Inter-Bold.otf", PHRASE_SIZE)
    lines = phrase_lines(text)
    w = max(fnt.getlength(l) for l in lines)
    return (PHRASE_X, PHRASE_Y, PHRASE_X + 34 + w, PHRASE_Y + len(lines) * PHRASE_SIZE * 1.2)


def phrase(img, text, t, at=0.0, until=1e9):
    """The key phrase, bottom left: an accent bar and up to three bold lines."""
    a = ease_out((t - at) / 0.35) * (1 - ease_out((t - until + 0.25) / 0.25))
    if a <= 0:
        return
    fnt = font("Inter-Bold.otf", PHRASE_SIZE)
    lines = phrase_lines(text)
    d = ImageDraw.Draw(img, "RGBA")
    dx = (1 - a) * -24
    hgt = len(lines) * PHRASE_SIZE * 1.2
    d.rounded_rectangle((PHRASE_X + dx, PHRASE_Y + 6, PHRASE_X + 10 + dx, PHRASE_Y + hgt - 6), radius=5, fill=PURPLE_HI + (int(255 * a),))
    for i, line in enumerate(lines):
        d.text((PHRASE_X + 34 + dx, PHRASE_Y + i * PHRASE_SIZE * 1.2), line, font=fnt, fill=TEXT + (int(255 * a),))


TITLE_SIZE = 150


def title_boxes(lines):
    fnt = font("Inter-ExtraBold.otf", TITLE_SIZE)
    out, y = [], 380
    for line in lines:
        w = fnt.getlength(line)
        out.append((W / 2 - w / 2, y, W / 2 + w / 2, y + TITLE_SIZE * 1.12))
        y += TITLE_SIZE * 1.12
    return out


def title_card(img, lines, tg, out=0.0, accent_last=True):
    """The thumbnail: the question in large type over Dandy Man. `out` (0..1) lifts the title away."""
    fnt = font("Inter-ExtraBold.otf", TITLE_SIZE)
    a = 1 - ease_out(out)
    if a <= 0:
        return
    put_sprite(img, GLOW_P, W / 2, 520, scale=2.2, alpha=0.5 * a)
    d = ImageDraw.Draw(img, "RGBA")
    for i, (line, b) in enumerate(zip(lines, title_boxes(lines))):
        col = SOFT if (accent_last and i == len(lines) - 1) else TEXT
        d.text((b[0], b[1] - 90 * ease_out(out)), line, font=fnt, fill=mix(col, TEXT, 0.25) + (int(255 * a),))


# ---------------------------------------------------------------- captions and end card
def caption_lines(text):
    return wrap(text, font("Inter-Bold.otf", CAP_SIZE), SAFE[2] - SAFE[0] - 40)


def caption_box(text):
    fnt = font("Inter-Bold.otf", CAP_SIZE)
    lines = caption_lines(text)
    lh, pad = fnt.size * 1.18, 20
    y = SAFE[3] - len(lines) * (lh + pad * 0.6) - 10
    w = max(fnt.getlength(l) for l in lines)
    return (W / 2 - w / 2 - pad, y - pad * 0.55, W / 2 + w / 2 + pad, y + (len(lines) - 1) * (lh + pad * 0.6) + lh + pad * 0.3)


def draw_caption(img, captions, tg):
    cue = next((c for c in captions if c[0] <= tg < c[1]), None)
    if cue is None:
        return
    a = min(1.0, (tg - cue[0]) / 0.2, (cue[1] - tg) / 0.2)
    fnt = font("Inter-Bold.otf", CAP_SIZE)
    d = ImageDraw.Draw(img, "RGBA")
    lines = caption_lines(cue[2])
    lh, pad = fnt.size * 1.18, 20
    y = SAFE[3] - len(lines) * (lh + pad * 0.6) - 10
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=fnt)
        x, yy = W / 2 - tw / 2, y + i * (lh + pad * 0.6)
        d.rounded_rectangle((x - pad, yy - pad * 0.55, x + tw + pad, yy + lh + pad * 0.3), radius=14, fill=(8, 5, 16, int(200 * a)))
        d.text((x, yy), line, font=fnt, fill=TEXT + (int(255 * a),))


END_DM_H = int(H * 0.32)


def end_card_layout():
    """The shared end card with Dandy Man, laid out as render/render.py does for the house style."""
    spr = dm_sprite("idle", END_DM_H)
    x, y = MARGIN, H * 0.5 - spr.height / 2
    cx = (x + spr.width + (W - MARGIN)) / 2
    sizes = CONTRACT["type"]["vertical"]
    fh = font("Inter-Bold.otf", int(sizes["headline"] * 1.5))
    tw = fh.getlength("Dandy")
    hat_h = int(H * 0.09)
    ty = H * 0.5 - sizes["headline"] * 0.9
    hy = ty - hat_h - CONTRACT["layout"]["spacing_unit_px"] * 2
    lay = dict(dm=(x, y), cx=cx, hat_h=hat_h, hy=hy, ty=ty, fh=fh, tw=tw, lines=[])
    yy = ty + fh.size * 1.1 + CONTRACT["layout"]["spacing_unit_px"] * 3
    for i, line in enumerate(CONTRACT["copy_rules"]["end_card_lines"]):
        fb = font("Inter-Medium.otf", sizes["body" if i == 0 else "caption"])
        lay["lines"].append((line, fb, yy, i == 1))
        yy += fb.size * 1.1 + CONTRACT["layout"]["spacing_unit_px"] * 3
    return lay


_hat = {}


def hat(h):
    if h not in _hat:
        im = Image.open(os.path.join(ROOT, "motifs", "logo-hat-light.png")).convert("RGBA")
        _hat[h] = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
    return _hat[h]


def end_card(last, t, tg):
    p = ease_out(t / 0.7)
    bg = last.convert("RGBA").filter(ImageFilter.GaussianBlur(int(18 * p)))
    bg.alpha_composite(Image.new("RGBA", bg.size, BG + (int(232 * p),)))
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W * 0.2, H * 0.3, W * 1.0, H * 0.7), fill=PURPLE + (int(120 * p),))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(130)))
    bg = bg.convert("RGB")
    lay = end_card_layout()
    a = ease_out((t - 0.3) / 0.5)
    if a > 0:
        draw_dm(bg, tg, "idle", x0=lay["dm"][0], y0=lay["dm"][1], height=END_DM_H, alpha=a)
        d = ImageDraw.Draw(bg, "RGBA")
        hh = hat(lay["hat_h"]).copy()
        hh.putalpha(hh.split()[3].point(lambda v: int(v * a)))
        bg.paste(hh, (int(lay["cx"] - hh.width / 2), int(lay["hy"])), hh)
        d.text((lay["cx"] - lay["tw"] / 2, lay["ty"]), "Dandy", font=lay["fh"], fill=TEXT + (int(255 * a),))
        for i, (line, fb, yy, gold) in enumerate(lay["lines"]):
            b = ease_out((t - 0.6 - 0.2 * i) / 0.45)
            lw = fb.getlength(line)
            d.text((lay["cx"] - lw / 2, yy), line, font=fb, fill=(GOLD if gold else SOFT) + (int(255 * b),))
    return bg


def end_card_scene(duration):
    """The end card as a checks.py scene (type end_card, one gold line)."""
    lay = end_card_layout()
    spr = dm_sprite("idle", END_DM_H)
    x, y = lay["dm"]
    hw = hat(lay["hat_h"]).width
    laid = [dict(name="dandy_man", type="sprite", bbox=(x + spr.width * 0.2, y, x + spr.width * 0.8, y + spr.height)),
            dict(name="logo_hat", type="sprite", bbox=(lay["cx"] - hw / 2, lay["hy"], lay["cx"] + hw / 2, lay["hy"] + lay["hat_h"])),
            dict(name="wordmark", type="text", role="headline", text="Dandy", lines=["Dandy"],
                 bbox=(lay["cx"] - lay["tw"] / 2, lay["ty"], lay["cx"] + lay["tw"] / 2, lay["ty"] + lay["fh"].size * 1.1))]
    for i, (line, fb, yy, gold) in enumerate(lay["lines"]):
        lw = fb.getlength(line)
        laid.append(dict(name=f"end_line_{i}", type="text", role="body", text=line, lines=[line], gold=gold,
                         bbox=(lay["cx"] - lw / 2, yy, lay["cx"] + lw / 2, yy + fb.size * 1.1)))
    return dict(id="end", type="end_card", duration=duration, laid_out=laid)


def text_el(name, text, bbox, role="body", lines=None, **kw):
    return dict(name=name, type="text", role=role, text=text, lines=lines or [text], bbox=bbox, **kw)


def caption_els(captions, start, dur):
    """Caption cues that fall inside a scene, as non-text layout boxes (they are checked for position, not word count)."""
    out = []
    for i, (s, e, tx) in enumerate(captions):
        t0, t1 = s - start, e - start
        if t1 > 0 and t0 < dur:
            out.append(dict(name=f"caption {i}", type="caption", bbox=caption_box(tx), enter_at=max(0, t0), exit_at=min(dur, t1)))
    return out


# ---------------------------------------------------------------- sound: soft, bright, a little playful
SR = 48000
_rng = np.random.default_rng(31)


def _norm(x, gain):
    return (x / (np.abs(x).max() + 1e-9) * gain).astype(np.float32)


def _band(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x).astype(np.float32)


def snd_pop(gain=0.3, f=660):
    n = int(SR * 0.16)
    t = np.arange(n) / SR
    return _norm(np.sin(2 * np.pi * (f + 500 * np.exp(-t * 60)) * t) * np.exp(-t * 34), gain)


def snd_chime(gain=0.3, f0=880):
    n = int(SR * 1.6)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f0 * m * t) * np.exp(-t * (2.5 + 2 * k)) / (k + 1) for k, m in enumerate((1.0, 2.0, 3.01, 4.2)))
    return _norm(x, gain)


def snd_whoosh(gain=0.35, dur=0.55):
    n = int(SR * dur)
    t = np.arange(n) / SR
    return _norm(_band(_rng.normal(0, 1, n), 400, 4000) * np.sin(np.pi * t / dur) ** 2, gain)


def snd_zip(gain=0.2):
    n = int(SR * 0.3)
    t = np.arange(n) / SR
    return _norm(np.sin(2 * np.pi * (300 + 1400 * t / 0.3) * t) * np.sin(np.pi * t / 0.3) ** 2, gain)


def snd_tick(gain=0.2):
    n = int(SR * 0.05)
    t = np.arange(n) / SR
    return _norm(_band(_rng.normal(0, 1, n), 2500, 9000) * np.exp(-t * 150), gain)


SOUNDS = dict(pop=snd_pop, chime=snd_chime, whoosh=snd_whoosh, zip=snd_zip, tick=snd_tick)


def build_bed(path, total, events):
    """events: (time_s, sound name, kwargs for the sound, pan -1..1)."""
    n = int(SR * total) + SR
    L = np.zeros(n, np.float32)
    R = np.zeros(n, np.float32)
    t = np.arange(n) / SR
    pad = (np.sin(2 * np.pi * 110 * t) + 0.6 * np.sin(2 * np.pi * 164.8 * t) + 0.4 * np.sin(2 * np.pi * 220.4 * t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t))
    pad = _norm(pad, 0.035)
    L += pad
    R += np.roll(pad, 600)
    for at, name, kw, pan in events:
        x = SOUNDS[name](**kw)
        i = int(at * SR)
        if 0 <= i < n:
            x = x[:n - i]
            L[i:i + len(x)] += x * math.cos((pan + 1) * math.pi / 4) * 1.41
            R[i:i + len(x)] += x * math.sin((pan + 1) * math.pi / 4) * 1.41
    peak = max(np.abs(L).max(), np.abs(R).max(), 1e-6)
    st = np.stack([L, R], 1)[:int(SR * total)] / peak * 0.55
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- render
def render_video(spec, preview=False, stills=False, final=False):
    """spec: video_dir, slug, look_tag, scenes [(id, dur, fn(t, dur, tg) or None for the end card)], captions,
    qa_scenes(starts) -> checks.py scenes, events(starts) -> sound events, still_s (how long frame one holds),
    voiceover (path to the timing json, optional)."""
    scenes, captions = spec["scenes"], spec["captions"]
    vo = None
    vp = spec.get("voiceover")
    if vp and os.path.exists(vp):
        with open(vp) as f:
            vo = json.load(f)
        scenes = [(sid, float(vo.get("durations", {}).get(sid, dur)), fn) for sid, dur, fn in scenes]
        if "lines" in vo:
            captions = [(s - 0.05, e + 0.3, tx) for s, e, tx in vo["lines"]]
    out = os.path.join(spec["video_dir"], "out")
    os.makedirs(out, exist_ok=True)
    starts, acc = {}, 0.0
    for sid, dur, _ in scenes:
        starts[sid] = acc
        acc += dur
    total = acc
    durs = {sid: dur for sid, dur, _ in scenes}
    qa = spec["qa_scenes"](starts, durs, captions)
    problems = [f"{s}: {m}" for s, m in run_all(qa, CONTRACT["canvases"]["vertical"], CONTRACT)]
    with open(os.path.join(out, f"qa-{spec['look_tag']}-vertical.json"), "w") as f:
        json.dump(dict(canvas="vertical", look="void stage", duration=total, problems=problems,
                       checks=["check_layout", "check_copy", "check_gold", "check_end_card"],
                       end_card="with Dandy Man", scenes=[dict(id=s, start=round(starts[s], 2), duration=d) for s, d, _ in scenes]), f, indent=2)
    if problems:
        print("QA FAILED:")
        for p in problems:
            print("  ", p)
        return False
    mp4 = os.path.join(out, f"{spec['slug']}-vertical.mp4")
    wav = os.path.join(out, f"{spec['look_tag']}-bed.wav")
    step = 3 if preview else 1
    tmp = tempfile.mkdtemp(prefix="dandy-stage-")
    n, last = 0, None
    still_s = spec.get("still_s", 0.5)
    for sid, dur, fn in scenes:
        frames = int(round(dur * FPS))
        picks = {0, int(frames * 0.3), int(frames * 0.62), frames - 2}
        for i in range(frames):
            if i % step or (stills and i not in picks):
                continue
            t = i / FPS
            tg = starts[sid] + t
            img = end_card(last, t, tg) if fn is None else fn(t, dur, tg)
            if fn is not None:
                last = img
            held = tg < still_s          # frame one holds perfectly still: no drift, no grain shimmer
            fr = finish(img.convert("RGBA"), t, 0.0 if held else tg - still_s, bloom=0.5, grain=0.0 if held else 2.0, vignette=0.34,
                        drift=0.0 if held else 0.35 * smooth((tg - still_s) / 1.2), zoom=1.03)
            fr = fr.convert("RGB")
            draw_caption(fr, captions, tg)
            if n == 0 and not stills:
                fr.save(os.path.join(out, f"{spec['slug'].split('-')[0]}-thumbnail.png"))
            if stills:
                fr.convert("RGB").save(os.path.join(out, f"still-{sid}-{t:04.1f}.png"))
                continue
            fr.convert("RGB").save(os.path.join(tmp, f"f{n:06d}.png"), compress_level=1)
            n += 1
    if stills:
        print("stills in", out)
        return True
    build_bed(wav, total, spec["events"](starts, durs))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS // step), "-i", os.path.join(tmp, "f%06d.png"), "-i", wav]
    if vo and vo.get("file") and not preview:
        hp = "" if vo.get("mixed") else "highpass=f=70,"
        fc = (f"[2:a]atrim=start={vo.get('offset_s', 0)},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
              f"{hp}volume={vo.get('voice_db', 3)}dB,apad=whole_dur={total},asplit=2[v][vk];[1:a]volume={vo.get('bed_db', -6)}dB[b];"
              f"[b][vk]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350[bd];"
              f"[v][bd]amix=inputs=2:normalize=0:duration=longest,atrim=0:{total},afade=t=out:st={total - 1.0}:d=1.0,alimiter=limit=0.89:level=0[a]")
        cmd += ["-i", os.path.join(ROOT, vo["file"]), "-filter_complex", fc, "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18" if final else "21", "-preset", "slow" if final else "medium",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    print(f"rendered {mp4} ({total:.1f} s)")
    return True

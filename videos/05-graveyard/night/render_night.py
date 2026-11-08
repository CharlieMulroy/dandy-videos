"""Renderer for video 05's own look: a graveyard of dead side projects at night, with the reaper of context rot.
Vertical only.

Usage:  python3 videos/05-graveyard/night/render_night.py [--preview] [--final] [--stills]

v2 (Nov 7, after Charlie's notes on the first preview): a perspective camera instead of a sideways pan. The field
is a grid of stones (12 columns, 40 rows) in world units; the camera starts wide and high, pushes forward through
the columns past the named stones, pulls back to reveal the reaper walking the rows, holds while the reaper
closes in week by week, and then a rider on horseback carries the purple light in and the reaper retreats.
Drawing helpers live in night_lib.py; sound in sfx_night.py; the shared finish pass in render/finish.py.
Scene durations can be overridden by voiceover/night.json; narration captions come from captions.json.
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
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "render"))
import env  # noqa: E402
import sfx_night  # noqa: E402
from rider import draw_rider, rider_glass_estimate  # noqa: E402
from finish import finish  # noqa: E402
from night_lib import (F_SCALE, PX, project, CONTRACT, EYES, FOG, FPS, GOLD, H, HORIZON, NIGHT, PURPLE, SAFE, TEXT, W, alpha_mul, chat_panel, display,  # noqa: E402
                       draw_fog, draw_landscape, draw_moon, draw_reaper, ease, font, lerp, mix, sky, smooth, stone_image, wrap)

def cam_at(x, z, k):
    return dict(x=x, z=z, k=k)


# ---------- the field ----------
COLS = [-13.0, -10.8, -8.6, -6.4, -4.2, -2.0, 2.0, 4.2, 6.4, 8.6, 10.8, 13.0]
ROW_STEP = 1.8
ROWS = [2.0 + ROW_STEP * i for i in range(28)]
NAMED = {
    # (col x, row z): (kind, name, epitaph). These are the stones the push passes close.
    (-2.0, 2.0): ("round", "Budget App", "Started with a prompt.\nBuried in a tab."),
    (2.0, 5.6): ("slab", "Portfolio Site v3", "Rebuilt the login twice.\nDid not survive the third."),
    (-2.0, 9.2): ("round", "Discord Bot", "Last words:\n\"as I mentioned earlier\""),
    (2.0, 12.8): ("slab", "Recipe Scraper", "2026 to 2026"),
    (-2.0, 16.4): ("round", "Habit Tracker", "Explained eleven times.\nFinished zero."),
    (4.2, 7.4): ("slab", "Inventory Tool", "Cause of death:\n\"let me catch you up\""),
    (-4.2, 11.0): ("round", "The Newsletter Thing", "Session ended.\nSo did it."),
    (4.2, 14.6): ("round", "Side Project #14", "Beloved for a weekend."),
}
KINDS = ("round", "slab", "cross", "round", "slab")


def field():
    out = []
    rnd = random.Random(8)
    for z in ROWS:
        for x in COLS:
            if any(abs(x - tx) < 1.4 and abs(z - tz) < 1.4 for (tx, tz, *_) in env.YARD_TREES):
                continue
            if (x, z) in NAMED:
                kind, name, ep = NAMED[(x, z)]
            else:
                if rnd.random() < 0.18:  # gaps in the rows
                    continue
                kind, name, ep = rnd.choice(KINDS), "", ""
            jitter = rnd.uniform(-0.18, 0.18)
            out.append((x + jitter, z + rnd.uniform(-0.25, 0.25), kind, name, ep))
    return out


FIELD = field()
_resized = {}
_shaded = {}


def stone_at_scale(img, scale, haze_k, tint_k):
    key = (id(img), round(scale, 2), round(haze_k, 2), round(tint_k, 2))
    if key in _shaded:
        return _shaded[key]
    rk = (id(img), round(scale, 2))
    if rk not in _resized:
        if len(_resized) > 600:
            _resized.clear()
        w, h = max(2, int(img.width * scale)), max(2, int(img.height * scale))
        _resized[rk] = img.resize((w, h), Image.LANCZOS if scale < 1 else Image.BILINEAR)
    im = _resized[rk]
    if haze_k > 0.01 or tint_k > 0.01:
        arr = np.asarray(im).astype(np.float32)
        if haze_k > 0.01:
            arr[..., :3] = arr[..., :3] * (1 - haze_k) + np.array(mix(NIGHT, FOG, 0.25), np.float32) * haze_k
        if tint_k > 0.01:
            arr[..., :3] = arr[..., :3] * (1 - tint_k * 0.7) + np.array(mix(PURPLE, (255, 255, 255), 0.25), np.float32) * tint_k * 0.7 + np.array(PURPLE, np.float32) * tint_k * 0.35
            arr[..., :3] = np.clip(arr[..., :3], 0, 255)
        im = Image.fromarray(arr.astype(np.uint8), "RGBA")
    if len(_shaded) > 900:
        _shaded.clear()
    _shaded[key] = im
    return im


def draw_field(frame, cam, light=None, extra=(), max_d=42.0, actors=()):
    """Project every stone, sort far to near, draw with atmospheric haze and (optionally) the lantern's light.
    light = (x, z, strength) in world units. extra = list of (x, z, img, rise_px) drawn in depth order too.
    actors = list of (z, draw_fn) interleaved by depth so stones in front of a figure occlude it."""
    items = []
    for (x, z, kind, name, ep) in FIELD:
        pr = project(x, z, cam)
        if pr is None or pr[3] > max_d:
            continue
        sx, gy, s, d = pr
        if d < 0.5:  # passing through the camera: already faded out, skip the giant resize
            continue
        half = 270 * s
        if sx < -half or sx > W + half or gy < HORIZON - 10:
            continue
        items.append((d, sx, gy, s, stone_image(kind, name, ep), 0.0, x, z))
    for (x, z, img, rise) in extra:
        pr = project(x, z, cam)
        if pr is not None:
            sx, gy, s, d = pr
            items.append((d, sx, gy, s, img, rise, x, z))
    items.sort(key=lambda it: -it[0])
    actors = list(actors) + env.actors(cam, 0.0, light)
    pending = sorted(((z - cam["z"], fn) for z, fn in actors), key=lambda a: -a[0])
    for d, sx, gy, s, img, rise, x, z in items:
        while pending and pending[0][0] > d:
            pending.pop(0)[1](frame)
        haze_k = min(0.8, max(0.0, (d - 2.0) / 14) * 0.9)
        tint_k = 0.0
        if light is not None:
            lx, lz, ls = light
            dist2 = (x - lx) ** 2 + (z - lz) ** 2 * 0.6
            tint_k = min(0.3, 0.6 * ls / (1 + dist2 * 1.1))
        im = stone_at_scale(img, s, haze_k, tint_k)
        fade = 1.0 if d > 0.9 else max(0.0, (d - 0.5) / 0.4)
        y = int(gy - im.height * 0.94 + rise)
        # ground shadow
        if d < 12:
            sw, sh = im.width + 40, int(40 * s) + 24
            shd = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
            ImageDraw.Draw(shd).ellipse((20, 8, sw - 20, sh - 8), fill=(0, 0, 0, int(140 * fade)))
            frame.alpha_composite(shd.filter(ImageFilter.GaussianBlur(8 + 6 * s)), (int(sx - sw / 2), int(gy - sh / 2)))
        if rise > 0:
            im = im.crop((0, 0, im.width, max(1, int(gy + 6 - y))))
        frame.alpha_composite(alpha_mul(im, fade), (int(sx - im.width / 2), y))
    for _, fn in pending:
        fn(frame)


# ---------- the rider ----------
def rot(px, py, cx, cy, ang):
    c, s = math.cos(ang), math.sin(ang)
    return cx + (px - cx) * c - (py - cy) * s, cy + (px - cx) * s + (py - cy) * c


def ellipse_pts(cx, cy, rx, ry, ang=0.0, n=28):
    return [rot(cx + math.cos(a) * rx, cy + math.sin(a) * ry, cx, cy, ang) for a in (2 * math.pi * k / n for k in range(n))]


def lantern_glow(frame, xy, radius, strength, t):
    """The purple light in screen space: a soft radial glow plus a lit patch of ground."""
    if strength <= 0:
        return
    x, y = xy
    flick = 0.92 + 0.08 * math.sin(t * 9.0) * math.sin(t * 4.3)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, al in ((radius * 1.0, 28), (radius * 0.6, 55), (radius * 0.32, 95), (radius * 0.14, 150)):
        gd.ellipse((x - r, y - r, x + r, y + r), fill=PURPLE + (int(al * strength * flick),))
    frame.alpha_composite(glow.filter(ImageFilter.GaussianBlur(radius * 0.18)))


# ---------- end card ----------
_hat = {}


def hat_img(h):
    if h not in _hat:
        im = Image.open(os.path.join(ROOT, "motifs", "logo-hat-light.png")).convert("RGBA")
        _hat[h] = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
    return _hat[h]


def end_card(t):
    fr = sky()
    draw_landscape(fr, 0)
    draw_fog(fr, t + 40, 0, strength=0.9)
    # the purple light lingers from the rider, then settles behind the card
    lantern_glow(fr, (W * 0.5, H * 0.62), 900, 0.6 * (1 - 0.5 * ease(t / 1.5)), t)
    fr.alpha_composite(Image.new("RGBA", (W, H), NIGHT + (int(200 * ease(t / 1.0)),)))
    sizes = CONTRACT["type"]["vertical"]
    d = ImageDraw.Draw(fr, "RGBA")
    display(fr, "Revive your old projects.", H * 0.20, t, 0.3, size=92, glow=PURPLE)
    a = ease((t - 1.0) / 0.6)
    if a > 0:
        hat = hat_img(int(H * 0.10))
        hy = H * 0.42
        fr.alpha_composite(alpha_mul(hat, a), (int(W / 2 - hat.width / 2), int(hy)))
        fh = font("Inter-Bold.otf", int(sizes["headline"] * 1.4))
        tw = d.textlength("Dandy", font=fh)
        ty = hy + hat.height + 36
        d.text((W / 2 - tw / 2, ty), "Dandy", font=fh, fill=TEXT + (int(255 * a),))
        yy = ty + fh.size * 1.1 + 50
        for i, line in enumerate(CONTRACT["copy_rules"]["end_card_lines"]):
            b = ease((t - 1.4 - 0.25 * i) / 0.5)
            fl = font("Inter-Regular.otf" if i == 0 else "Inter-Medium.otf", sizes["body" if i == 0 else "caption"])
            lw = d.textlength(line, font=fl)
            col = GOLD if i == 1 else (200, 190, 220)
            d.text((W / 2 - lw / 2, yy), line, font=fl, fill=col + (int(255 * b),))
            yy += fl.size * 1.1 + 50
    return fr


# ---------- scenes ----------
def base(t, cam):
    fr = sky()
    draw_moon(fr, t, cam["x"] * 60)
    draw_landscape(fr, cam["x"] * 60 + cam["z"] * 2)
    env.draw_far(fr, cam, t)
    env.draw_ground(fr, cam, t)
    return fr


def s1(t, dur):
    # wide and high: the whole field under the moon, fog over everything; the push starts slowly
    z = -14 + 10 * (t / dur) ** 2.2
    k = 6000 - 1400 * (t / dur) ** 2
    cam = cam_at(0.0, z, k)
    fr = base(t, cam)
    draw_fog(fr, t, cam["x"], strength=0.5, push=z)
    draw_field(fr, cam, max_d=72.0)
    draw_fog(fr, t + 3, cam["x"], strength=0.7, push=z)
    return fr


PUSH_V = 1.65


def s2(t, dur):
    # the push: down the centre aisle at a steady walk, the named stones passing close on either side
    z = -4 + PUSH_V * t
    k = lerp(4600, 900, smooth(t / (dur * 0.55)))
    # weave toward each named stone: Budget App (left, z=2) is passed at distance 2 when the camera is at z=0
    period = 2 * 3.6 / PUSH_V
    t_pass = 4.0 / PUSH_V
    x = -0.9 * math.cos(2 * math.pi * (t - t_pass) / period) * smooth(t / 2.0)
    cam = cam_at(x, z, k)
    fr = base(t + 5, cam)
    draw_fog(fr, t + 5, x, strength=0.45, push=z)
    draw_field(fr, cam)
    draw_fog(fr, t + 8, x, strength=0.5, push=z)
    return fr


def s3(t, dur):
    # pull back and up to a wide view; the reaper is walking the rows
    q = smooth(min(1.0, t / 3.2))
    z = lerp(-4 + PUSH_V * 11.0, 5.4, q)
    k = lerp(900, 1300, q)
    cam = cam_at(0.0, z, k)
    fr = base(t + 16, cam)
    draw_fog(fr, t + 16, 0, strength=0.5, push=z)
    rx = lerp(-3.2, 1.4, smooth(t / dur))
    rz = 11.5

    def reaper(frame):
        pr = project(rx, rz, cam)
        if pr:
            sx, gy, s, d = pr
            draw_reaper(frame, sx, gy, 760 * s, t, eyes=min(1.0, max(0.0, (t - 1.0) / 1.5)), step=(t * 0.9) % 1, fade=min(1.0, max(0.0, (t - 0.6) / 1.2)))
    draw_field(fr, cam, actors=[(rz, reaper)])
    draw_fog(fr, t + 19, 0, strength=0.75, push=z)
    display(fr, "CONTEXT ROT", H * 0.24, t, 4.6, size=150, glow=(60, 90, 80))
    return fr


S4_PHASES = (0.0, 4.6, 9.2)
S4_Z = (11.5, 9.0, 7.0)


def s4(t, dur):
    # the weeks: the camera holds, the reaper is nearer each week, the chat window types at the lower right
    cam = cam_at(0.0, 5.4, 1300)
    fr = base(t + 24, cam)
    phase = 0 if t < S4_PHASES[1] else (1 if t < S4_PHASES[2] else 2)
    since = t - S4_PHASES[phase]
    draw_fog(fr, t + 24, 0, strength=0.5 + 0.12 * phase, push=cam["z"])
    rz = S4_Z[phase] - 0.35 * smooth(since / 4.4)
    rx = (-1.0, -0.9, -0.75)[phase]

    def reaper(frame):
        pr = project(rx, rz, cam)
        if pr:
            sx, gy, s, d = pr
            draw_reaper(frame, sx, gy, 760 * s, t, eyes=1.0, fade=min(1.0, since / 0.5 + (1.0 if phase == 0 else 0.0)))
    extra = []
    if t > 10.6:
        q = smooth((t - 10.6) / 2.4)
        img = stone_image("round", "", "", blank=True)
        extra.append((0.7, 8.6, img, (1 - q) * img.height * 0.9 * (F_SCALE / 3.2)))
    draw_field(fr, cam, extra=extra, actors=[(rz, reaper)])
    pulse = 0.0
    for ph in S4_PHASES[1:]:
        if ph - 0.5 < t < ph + 0.9:
            pulse = max(pulse, 1 - abs(t - ph - 0.2) / 0.7)
    draw_fog(fr, t + 27, 0, strength=0.75 + 0.15 * phase + 0.9 * pulse, push=cam["z"])
    chat_panel(fr, t, 0.3, 4.4, "so the project is a budget app, it tracks my spending by category and")
    chat_panel(fr, t, 4.9, 9.0, "ok so, again, the project is a budget app that")
    chat_panel(fr, t, 9.5, 12.8, "", blank=True)
    display(fr, "week 1: you explain it", H * 0.27, t, 0.9, size=62, slam=False, exit_at=4.3, weight="Inter-Bold.otf")
    display(fr, "week 3: you explain it again", H * 0.27, t, 5.4, size=62, slam=False, exit_at=8.9, weight="Inter-Bold.otf")
    display(fr, "week 6:", H * 0.27, t, 10.0, size=62, slam=False, exit_at=13.4, weight="Inter-Bold.otf")
    return fr


RIDER_X0, RIDER_V0, RIDER_VMIN = 8.6, 2.4, 0.1


def rider_motion(t):
    """World x, gait phase and stride size at time t. Speed falls from a gallop to a slow canter between 1 s and
    6 s; the stride rate follows the ground speed so the hooves do not skate."""
    def vf(u):
        return RIDER_VMIN + (1 - RIDER_VMIN) * (1 - smooth(min(1.0, max(0.0, (u - 1.0) / 5.0))))
    n = max(1, int(t * 60))
    us = np.linspace(0, t, n + 1)
    v = np.array([vf(u) for u in us])
    dist = np.trapezoid(v, us) * RIDER_V0 if t > 0 else 0.0
    phase = 2 * math.pi * np.trapezoid(0.8 + 1.4 * v, us) if t > 0 else 0.0
    return RIDER_X0 - dist, phase, 0.3 + 0.7 * v[-1]


def s5(t, dur):
    # the rider: purple light before the horse, the horse canters in from the right and slows, the reaper retreats
    cam = cam_at(0.0, 5.4, 1300)
    fr = base(t + 38, cam)
    draw_fog(fr, t + 38, 0, strength=0.55, push=cam["z"])
    # rider path in world units: gallops in from off the right, eases to a slow canter and keeps moving left
    rx_w, gait, speed = rider_motion(t)
    arrive = smooth(min(1.0, max(0.0, (t - 1.0) / 5.0)))
    rz_w = 8.3
    light_strength = ease((t - 0.3) / 1.6)
    light = (rx_w - 0.4, rz_w, 1.3 * light_strength)
    # reaper: near-left, then backs off into the fog once the light reaches him
    retreat = smooth(min(1.0, max(0.0, (t - 2.0) / 4.5)))
    gz = lerp(6.8, 19.0, retreat)
    gx = lerp(-0.8, -7.0, retreat)
    lantern_xy = []

    def reaper(frame):
        pr = project(gx, gz, cam)
        if pr:
            sx, gy, s, d = pr
            draw_reaper(frame, sx, gy, 760 * s, t, eyes=1.0 - retreat, step=((t * 0.8) % 1) if 0 < retreat < 1 else 0, fade=1.0 - smooth((t - 5.2) / 2.6))

    def rider(frame):
        pr = project(rx_w, rz_w, cam)
        if pr:
            sx, gy, s, d = pr
            xy = draw_rider(frame, sx, gy, 680 * s, gait, t, speed=speed, lantern=light_strength)
            if xy:
                lantern_xy.append(xy)
    pr = project(rx_w, rz_w, cam)
    if pr:  # the wide light sits behind the figures; only a small hot core goes over the lantern
        sx, gy, s, d = pr
        lantern_glow(fr, rider_glass_estimate(sx, gy, 680 * s), 820, 0.75 * light_strength, t)
    draw_field(fr, cam, light=light, actors=[(gz, reaper), (rz_w, rider)])
    draw_fog(fr, t + 41, 0, strength=0.42, color=mix(FOG, PURPLE, 0.25 * light_strength), push=cam["z"])
    if lantern_xy:
        lantern_glow(fr, lantern_xy[0], 150, light_strength, t)
    display(fr, "unless the truth rides in with you", H * 0.26, t, 2.4, size=70, slam=False, exit_at=6.2, weight="Inter-Bold.otf")
    display(fr, "written down, read first, every session", H * 0.26, t, 6.7, size=70, slam=False, exit_at=dur - 0.3, weight="Inter-Bold.otf")
    return fr


SCENES = [
    dict(id="s1-wide", dur=5.0, frame=s1),
    dict(id="s2-push", dur=11.0, frame=s2),
    dict(id="s3-reveal", dur=8.0, frame=s3),
    dict(id="s4-weeks", dur=14.0, frame=s4),
    dict(id="s5-rider", dur=10.0, frame=s5),
    dict(id="end", dur=6.0, frame=lambda t, d: end_card(t)),
]

ON_SCREEN = ["HERE LIES", "CONTEXT ROT", "week 1: you explain it", "week 3: you explain it again", "week 6:", "unless the truth rides in with you",
             "written down, read first, every session", "Revive your old projects.", "new session", "What is this project?"] + [v[1] for v in NAMED.values()] + [v[2] for v in NAMED.values()]


def apply_timing():
    path = os.path.join(VIDEO, "voiceover", "night.json")
    if os.path.exists(path):
        with open(path) as f:
            timing = json.load(f).get("durations", {})
        for sc in SCENES:
            if sc["id"] in timing:
                sc["dur"] = float(timing[sc["id"]])


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
        d.rounded_rectangle((x - pad, yy - pad * 0.6, x + tw + pad, yy + lh + pad * 0.4), radius=14, fill=NIGHT + (210,))
        d.text((x, yy), line, font=fnt, fill=TEXT + (255,))


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
    with open(os.path.join(out, "qa-night-vertical.json"), "w") as f:
        json.dump(dict(canvas="vertical", look="night", problems=[list(p) for p in problems], scenes=[dict(id=s["id"], duration=s["dur"]) for s in SCENES]), f, indent=2)
    if problems:
        print("QA FAILED:", problems)
        return False
    cues = None
    cap_path = os.path.join(VIDEO, "captions.json")
    if os.path.exists(cap_path) and not preview:
        with open(cap_path) as f:
            cues = json.load(f)["cues"]
    tmp = tempfile.mkdtemp(prefix="dandy-night-")
    n, offset, contact = 0, 0.0, []
    step = 1.0 / FPS
    for sc in SCENES:
        frames = int(sc["dur"] * FPS)
        for i in range(frames):
            if preview and i % 3:
                continue
            if stills and i not in (int(0.5 * FPS), int((sc["dur"] * 0.5) * FPS), int((sc["dur"] - 0.6) * FPS)):
                continue
            t = i * step
            fr = sc["frame"](t, sc["dur"])
            shake = 7.0 * max(0.0, 1 - (t - 4.6) / 0.35) if sc["id"] == "s3-reveal" and t >= 4.6 else 0.0
            fr = finish(fr, t, offset + t, shake=shake, bloom=0.8, grain=1.6, vignette=0.45, drift=0.5)
            if cues:
                draw_cue(fr, cues, offset + t)
            if stills:
                fr.convert("RGB").save(os.path.join(out, f"night-{sc['id']}-{t:04.1f}.png"))
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
    mp4 = os.path.join(out, f"05-graveyard-vertical{'-final' if final else ''}.mp4")
    total = sum(s["dur"] for s in SCENES)
    bed = sfx_night.build_bed([(s["id"], s["dur"]) for s in SCENES], os.path.join(out, "sfx-bed.wav"))
    cmd = ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "f%06d.png"), "-i", bed]
    apath = os.path.join(VIDEO, "voiceover", "night.json")
    audio = {}
    if os.path.exists(apath):
        with open(apath) as f:
            audio = json.load(f)
    voice = audio.get("file") if not preview else None
    music = audio.get("music")
    parts, mixn, idx = ["[1:a]volume=0.9[sfx]"], ["[sfx]"], 2
    if voice:
        cmd += ["-ss", str(audio.get("offset_s", 0)), "-i", os.path.join(ROOT, voice)]
        parts.append(f"[{idx}:a]{audio_chain(os.path.join(ROOT, voice), bool(audio.get('mixed')))}[voice]")
        idx += 1
    if music:
        cmd += ["-stream_loop", "-1", "-i", os.path.join(ROOT, music)]
        parts.append(f"[{idx}:a]volume={audio.get('music_db', -14)}dB[m0]")
        if voice:
            parts.append("[voice]asplit[v1][v2]")
            parts.append("[m0][v2]sidechaincompress=threshold=0.05:ratio=6:attack=40:release=500[mduck]")
            mixn = ["[v1]", "[sfx]", "[mduck]"]
        else:
            mixn = ["[sfx]", "[m0]"]
    elif voice:
        mixn = ["[voice]", "[sfx]"]
    fc = ";".join(parts) + ";" + "".join(mixn) + f"amix=inputs={len(mixn)}:normalize=0:duration=first,alimiter=limit=0.89:level=0[aout]"
    cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]", "-t", str(total), "-c:a", "aac", "-b:a", "192k"]
    if final:
        cmd += ["-c:v", "libx264", "-preset", "slow", "-pix_fmt", "yuv420p", "-crf", "17", "-movflags", "+faststart", mp4]
    else:
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", mp4]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    th = 480
    thumbs = [im.resize((int(im.width * th / im.height), th)) for im in contact]
    sheet = Image.new("RGB", (len(thumbs) * (thumbs[0].width + 24) + 24, th + 48), NIGHT)
    for i, im in enumerate(thumbs):
        sheet.paste(im, (24 + i * (thumbs[0].width + 24), 24))
    sheet.save(os.path.join(out, "contact-night-vertical.png"))
    print(f"rendered {mp4} ({n} frames)")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--stills", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if render(a.preview, a.final, a.stills) else 1)

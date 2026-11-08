"""The rider for video 05: a painted puppet cut from assets/rider-source.png by cut_rider.py.

draw_rider(frame, sx, gy, L, phase, t, speed=1.0, lantern=1.0, fade=1.0) -> screen (x, y) of the lantern glass.
  sx, gy  where the figure's centre stands on the ground in screen pixels
  L       horse body length in screen pixels (chest to buttock)
  phase   gait phase in radians (the caller integrates it so the stride matches the ground speed)
  speed   0..1, scales the stride, the bob and the cloak's flutter

The rig: four legs rotate about pivots hidden under the body (hind legs lead, forelegs follow half a stride
later), the body bobs and pitches with the stride, the cloak, tail and mane ripple through a displacement warp
that is zero where they attach and grows toward their free ends, and the lantern swings from the hand. The figure
is composited a touch softer and flatter than the source so it sits in the scene instead of on it. The lantern
glass is the only purple; the light it throws is drawn by the caller. rider_silhouette.py is the old code-drawn
rider, kept as a fallback.
"""
import json
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(HERE, "assets", "rider")
with open(os.path.join(PARTS, "rig.json")) as f:
    RIG = json.load(f)
SW, SH = RIG["size"]
LEG_ORDER = ("fl_far", "hl_far", "hl_near", "fl_near")      # all behind the body: the body hides the joints
# gait: (amplitude in degrees, phase offset). Hind legs lead; forelegs follow about half a stride later.
GAIT = dict(hl_far=(13.0, 0.0), hl_near=(12.0, 0.55), fl_far=(15.0, math.pi), fl_near=(17.0, math.pi + 0.55))
BODY_CENTRE = (640.0, 640.0)   # pitch pivot, source px (under the saddle)
FOOT_X = 640.0                 # the source x placed at sx

_src = None
_scaled = {}


def _load():
    global _src
    if _src is None:
        _src = {n: Image.open(os.path.join(PARTS, f"{n}.png")).convert("RGBA") for n in ("body", "lantern") + LEG_ORDER}
    return _src


def _at_scale(ws):
    key = round(ws, 3)
    if key not in _scaled:
        if len(_scaled) > 6:
            _scaled.clear()
        src = _load()
        size = (max(2, int(SW * ws)), max(2, int(SH * ws)))
        parts = {n: im.resize(size, Image.LANCZOS) for n, im in src.items()}
        # warp weights for the body layer, in source units then scaled
        yy, xx = np.mgrid[0:size[1], 0:size[0]].astype(np.float32)
        X, Y = xx / ws, yy / ws
        cloak = np.clip((X - 690) / 660, 0, 1) ** 1.6 * np.clip((540 - Y) / 60, 0, 1)
        tail = np.clip((X - 1040) / 380, 0, 1) ** 1.4 * np.clip((Y - 440) / 30, 0, 1)
        mane = 0.35 * np.clip((Y - 262) / 12, 0, 1) * np.clip((338 - Y) / 30, 0, 1) * np.clip((X - 170) / 60, 0, 1) * np.clip((470 - X) / 60, 0, 1)
        _scaled[key] = dict(parts=parts, xx=xx, yy=yy, X=X, cloak=cloak, tail=tail, mane=mane, size=size)
    return _scaled[key]


def _rot(pt, centre, deg):
    a = math.radians(-deg)  # PIL rotates counter-clockwise on screen for positive angles
    x, y = pt[0] - centre[0], pt[1] - centre[1]
    return centre[0] + x * math.cos(a) - y * math.sin(a), centre[1] + x * math.sin(a) + y * math.cos(a)


def draw_rider(frame, sx, gy, L, phase, t, speed=1.0, lantern=1.0, fade=1.0):
    if fade <= 0 or L < 8:
        return None
    ws = L / RIG["body_len"]
    sc = _at_scale(ws)
    parts, size = sc["parts"], sc["size"]
    s = max(0.0, min(1.0, speed))
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    # legs, behind the body
    for name in LEG_ORDER:
        amp, off = GAIT[name]
        ang = amp * s * math.sin(phase + off)
        pv = RIG["parts"][name]["pivot"]
        leg = parts[name].rotate(ang, resample=Image.BICUBIC, center=(pv[0] * ws, pv[1] * ws))
        canvas.alpha_composite(leg)
    # body with cloak, tail and mane rippling
    flutter = 0.35 + 0.65 * s
    X = sc["X"]
    dy = (sc["cloak"] * 20 * math.sqrt(flutter) * np.sin(X / 95.0 - t * 9.0)
          + sc["tail"] * 15 * flutter * np.sin(X / 70.0 - t * 11.0 + 0.7)
          + sc["mane"] * 6 * flutter * np.sin(X / 40.0 - t * 13.0))
    dx = sc["cloak"] * 8 * flutter * np.sin(X / 140.0 - t * 7.0 + 1.1) + sc["tail"] * 6 * flutter * np.cos(X / 90.0 - t * 10.0)
    body = np.asarray(parts["body"])
    warped = cv2.remap(body, sc["xx"] - (dx * ws).astype(np.float32), sc["yy"] - (dy * ws).astype(np.float32),
                       interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    canvas.alpha_composite(Image.fromarray(warped, "RGBA"))
    # lantern swings from the hand: a slow pendulum plus a jolt each stride
    swing = 3.0 * math.sin(t * 3.1) * (0.5 + 0.5 * s) + 5.0 * s * math.sin(phase + 1.0)
    lp = RIG["parts"]["lantern"]["pivot"]
    canvas.alpha_composite(parts["lantern"].rotate(swing, resample=Image.BICUBIC, center=(lp[0] * ws, lp[1] * ws)))
    glass = _rot(RIG["glass"], lp, swing)
    # the stride: the body rises in the suspension phase and pitches nose-down on landing
    bob = -0.03 * s * max(0.0, math.sin(phase + 0.6)) * RIG["body_len"]
    pitch = 2.2 * s * math.sin(phase + 1.2)
    canvas = canvas.rotate(pitch, resample=Image.BICUBIC, center=(BODY_CENTRE[0] * ws, BODY_CENTRE[1] * ws))
    glass = _rot(glass, BODY_CENTRE, pitch)
    # sit it into the scene: a little softer and flatter than the painting
    arr = np.asarray(canvas.filter(ImageFilter.GaussianBlur(max(0.4, 0.9 * ws)))).astype(np.float32)
    arr[..., :3] = arr[..., :3] * 0.9 + 4
    if fade < 1:
        arr[..., 3] *= fade
    fig = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    ox = sx - FOOT_X * ws
    oy = gy - RIG["ground_y"] * ws + bob * ws
    # a faint shadow: the horse is mostly airborne at the gallop
    shd = Image.new("RGBA", (int(L * 1.1), int(L * 0.08) + 16), (0, 0, 0, 0))
    ImageDraw.Draw(shd).ellipse((8, 6, shd.width - 8, shd.height - 6), fill=(0, 0, 0, int(110 * fade)))
    frame.alpha_composite(shd.filter(ImageFilter.GaussianBlur(10)), (int(sx - shd.width / 2), int(gy - shd.height / 2)))
    frame.alpha_composite(fig, (int(ox), int(oy)))
    return (ox + glass[0] * ws, oy + glass[1] * ws)


def rider_glass_estimate(sx, gy, L):
    """Where the lantern glass sits for a figure at (sx, gy) of length L, ignoring swing and stride."""
    ws = L / RIG["body_len"]
    return sx + (RIG["glass"][0] - FOOT_X) * ws, gy + (RIG["glass"][1] - RIG["ground_y"]) * ws

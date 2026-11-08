"""The reaper for video 05: a painted puppet from assets/reaper-source.png (Charlie's ChatGPT generation, Nov 7,
transparent background). Replaces the code-drawn reaper in night_lib.draw_reaper, with the same call:

draw_reaper(frame, sx, ground_y, height, t, eyes=1.0, sway=1.0, step=0.0, fade=1.0)
  sx, ground_y  where the hem's centre meets the ground, screen px
  height        hood top to ground, screen px
  eyes          0..1 glow of the two eye lights in the empty hood (added here, so they can fade on the retreat)
  step          0..1 phase of a walking stride (0 = still); the reaper glides, so a step is a heavier sway
  fade          0..1 overall opacity

Rig: the staff, blade and bony hands are a rigid layer on top; the robe beneath ripples through a displacement
warp that is zero near the shoulders and the staff and grows toward the hem and the tattered sides; the whole
figure sways a little about its base and breathes. Composited slightly softer, like the rider.
"""
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "assets", "reaper-source.png")
HOOD_TOP, GROUND = 85, 1062        # source px
BASE_X = 700                       # hem centre
EYES_AT = ((684, 182), (718, 182))  # inside the hood
EYE_RGB = (184, 255, 217)
STAFF = ((520, 30), (612, 1045))   # the staff's centre line, top to bottom
RIGID = [  # blade, staff top and both hands stay rigid
    [(498, 10), (600, 18), (760, 40), (880, 95), (940, 170), (905, 165), (820, 95), (700, 58), (560, 52), (540, 110), (500, 110)],
    [(500, 200), (575, 200), (580, 300), (500, 300)],
    [(548, 440), (645, 440), (645, 520), (548, 520)],
]

_src = None
_scaled = {}


def _load():
    global _src
    if _src is None:
        _src = Image.open(SRC).convert("RGBA")
    return _src


def _at_scale(ws):
    key = round(ws, 3)
    if key not in _scaled:
        if len(_scaled) > 8:
            _scaled.clear()
        src = _load()
        size = (max(2, int(src.width * ws)), max(2, int(src.height * ws)))
        full = src.resize(size, Image.LANCZOS)
        yy, xx = np.mgrid[0:size[1], 0:size[0]].astype(np.float32)
        X, Y = xx / ws, yy / ws
        # distance from the staff line, source px
        (x0, y0), (x1, y1) = STAFF
        dx, dy = x1 - x0, y1 - y0
        dist = np.abs(dy * (X - x0) - dx * (Y - y0)) / math.hypot(dx, dy)
        rigid = Image.new("L", size, 0)
        rd = ImageDraw.Draw(rigid)
        for poly in RIGID:
            rd.polygon([(px * ws, py * ws) for px, py in poly], fill=255)
        staff_band = (dist < 20) & (Y < 1050)
        rigid_m = np.maximum(np.asarray(rigid), (staff_band * 255).astype(np.uint8))
        rigid_soft = np.asarray(Image.fromarray(rigid_m).filter(ImageFilter.GaussianBlur(max(0.6, 1.2 * ws)))).astype(np.float32) / 255
        arr = np.asarray(full).astype(np.float32)
        top = arr.copy()
        top[..., 3] *= rigid_soft
        # robe ripple weight: zero near the shoulders, staff and hands; grows down the robe and out to the sides
        down = np.clip((Y - 330) / 700, 0, 1) ** 1.3
        side = np.clip((np.abs(X - BASE_X) - 160) / 260, 0, 1) * np.clip((Y - 260) / 200, 0, 1)
        keep_off = np.clip((dist - 30) / 60, 0, 1) * (1 - rigid_soft)
        wgt = np.clip(down + 0.6 * side, 0, 1.2) * keep_off
        _scaled[key] = dict(robe=np.ascontiguousarray(arr.astype(np.uint8)), top=Image.fromarray(top.astype(np.uint8), "RGBA"),
                            xx=xx, yy=yy, X=X, Y=Y, w=wgt.astype(np.float32), size=size)
    return _scaled[key]


def draw_reaper(frame, sx, ground_y, height, t, eyes=1.0, sway=1.0, step=0.0, fade=1.0):
    if fade <= 0 or height < 8:
        return
    ws = height / (GROUND - HOOD_TOP)
    sc = _at_scale(ws)
    X, Y, w = sc["X"], sc["Y"], sc["w"]
    walk = math.sin(step * math.pi * 2) if step else 0.0
    # robe: a slow wave running down and across, stronger at the hem and the tattered edges
    dxs = w * (9 * np.sin(Y / 85.0 - t * 2.2 + X / 210.0) + 5 * walk * np.sin(Y / 140.0))
    dys = w * 3.5 * np.sin(X / 70.0 - t * 2.8)
    robe = cv2.remap(sc["robe"], sc["xx"] - (dxs * ws).astype(np.float32), sc["yy"] - (dys * ws).astype(np.float32),
                     interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    fig = Image.fromarray(robe, "RGBA")
    fig.alpha_composite(sc["top"])
    # eyes: two cold points in the hood with a soft glow
    if eyes > 0:
        flick = 0.85 + 0.15 * math.sin(t * 7.0) * math.sin(t * 3.1)
        glow = Image.new("RGBA", fig.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        er = max(1.5, 5.5 * ws)
        for ex, ey in EYES_AT:
            gd.ellipse((ex * ws - er * 4, ey * ws - er * 4, ex * ws + er * 4, ey * ws + er * 4), fill=EYE_RGB + (int(110 * eyes * flick),))
        glow = glow.filter(ImageFilter.GaussianBlur(er * 1.8))
        gd = ImageDraw.Draw(glow)
        for ex, ey in EYES_AT:
            gd.ellipse((ex * ws - er, ey * ws - er * 0.65, ex * ws + er, ey * ws + er * 0.65), fill=EYE_RGB + (int(255 * eyes * flick),))
        fig.alpha_composite(glow)
    # sway about the base and a slow breath
    ang = (0.8 * math.sin(t * 0.9) + 1.6 * walk) * sway
    fig = fig.rotate(ang, resample=Image.BICUBIC, center=(BASE_X * ws, GROUND * ws))
    arr = np.asarray(fig.filter(ImageFilter.GaussianBlur(max(0.4, 0.8 * ws)))).astype(np.float32)
    arr[..., :3] = arr[..., :3] * 0.92 + 3
    if fade < 1:
        arr[..., 3] *= fade
    fig = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    bob = -abs(walk) * 0.008 * height + math.sin(t * 1.1) * 0.004 * height
    # ground shadow
    shd = Image.new("RGBA", (int(height * 0.9), int(height * 0.07) + 16), (0, 0, 0, 0))
    ImageDraw.Draw(shd).ellipse((8, 6, shd.width - 8, shd.height - 6), fill=(0, 0, 0, int(150 * fade)))
    frame.alpha_composite(shd.filter(ImageFilter.GaussianBlur(10)), (int(sx - shd.width / 2), int(ground_y - shd.height / 2)))
    frame.alpha_composite(fig, (int(sx - BASE_X * ws), int(ground_y - GROUND * ws + bob)))

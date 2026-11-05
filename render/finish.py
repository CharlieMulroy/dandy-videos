"""The shared finish pass: camera drift with a slow zoom (and an optional impact shake), bloom on bright
pixels, film grain and a vignette. Declared on Dandy's Renderer node (finish_options); first built for
04's void look, lifted here on Nov 5 so every renderer applies the same pass.

    from finish import finish
    frame = finish(frame, t_scene, t_global, shake=0.0, bloom=1.0, grain=4.5, vignette=0.38, drift=1.0)

frame is an RGBA PIL image at the output size; the result is RGBA at the same size.
"""
import math
import random

import numpy as np
from PIL import Image, ImageFilter

_vig = {}


def spring(t):
    """Overshooting ease: arrives fast, overshoots a little, settles."""
    t = max(0.0, min(1.0, t))
    return 1 - math.exp(-6.5 * t) * math.cos(8.0 * t) if t < 1 else 1.0


def finish(frame, t, t_global, shake=0.0, bloom=1.0, grain=4.5, vignette=0.38, drift=1.0, zoom=1.03):
    W, H = frame.size
    z = zoom + 0.025 * drift * math.sin(t_global * 0.23)
    ox = (math.sin(t_global * 0.31) * 14 + random.uniform(-1, 1) * shake) * drift
    oy = (math.cos(t_global * 0.27) * 10 + random.uniform(-1, 1) * shake) * drift
    nw, nh = int(W * z), int(H * z)
    big = frame.resize((nw, nh), Image.BILINEAR)
    x0 = max(0, min(nw - W, int((nw - W) / 2 + ox)))
    y0 = max(0, min(nh - H, int((nh - H) / 2 + oy)))
    fr = big.crop((x0, y0, x0 + W, y0 + H)).convert("RGB")
    arr = np.asarray(fr).astype(np.float32)
    if bloom > 0:
        small = fr.resize((W // 4, H // 4), Image.BILINEAR)
        sa = np.asarray(small).astype(np.float32)
        lum = sa.mean(axis=2, keepdims=True)
        bright = np.clip((lum - 150) / 105, 0, 1) * sa
        bl = Image.fromarray(np.clip(bright, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR)
        arr = arr + np.asarray(bl).astype(np.float32) * 0.55 * bloom
    if vignette > 0:
        key = (W, H, vignette)
        if key not in _vig:
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            v = np.sqrt(((xx - W / 2) / (W * 0.72)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
            _vig[key] = np.clip(1 - v * vignette, 1 - vignette * 1.05, 1.0)[..., None]
        arr = arr * _vig[key]
    if grain > 0:
        noise = np.random.default_rng(int(t_global * 1000) % 100000).normal(0, grain, (H // 2, W // 2, 1)).astype(np.float32)
        arr = arr + np.repeat(np.repeat(noise, 2, axis=0), 2, axis=1)[:H, :W]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")

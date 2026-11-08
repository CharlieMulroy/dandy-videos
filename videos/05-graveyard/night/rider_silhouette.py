"""The rider for video 05: a galloping horse with a cloaked rider holding a lantern out ahead (Paul Revere, in
silhouette). Side view, facing left. Drawn as polygons in horse units (L = body length, chest to buttock),
then shaded: the side facing the lantern takes a faint purple rim light; the rest is near-black.

draw_rider(frame, sx, gy, L, phase, t, speed, lantern, fade) -> screen (x, y) of the lantern's glass.
phase is the gait phase in radians; speed 0..1 scales the stride (0 = standing)."""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIL = (10, 8, 18, 255)
PURPLE = (124, 77, 255)


def _smooth_closed(pts, n=6):
    """Chaikin smoothing on a closed polygon so the horse reads as flesh, not facets."""
    for _ in range(n):
        out = []
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            out.append((0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]))
            out.append((0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1]))
        pts = out
    return pts


def _limb(d, joints, widths, fill):
    """A tapered limb through a list of joints, drawn as quads plus round joints."""
    for i in range(len(joints) - 1):
        (x0, y0), (x1, y1) = joints[i], joints[i + 1]
        w0, w1 = widths[i] / 2, widths[i + 1] / 2
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) + 1e-6
        nx, ny = -dy / ln, dx / ln
        d.polygon([(x0 + nx * w0, y0 + ny * w0), (x1 + nx * w1, y1 + ny * w1), (x1 - nx * w1, y1 - ny * w1), (x0 - nx * w0, y0 - ny * w0)], fill=fill)
        d.ellipse((x0 - w0, y0 - w0, x0 + w0, y0 + w0), fill=fill)
    x, y = joints[-1]
    w = widths[-1] / 2
    d.ellipse((x - w, y - w, x + w, y + w), fill=fill)


def _leg(d, P, L, root, lengths, angles, widths, hoof_dir):
    """Chain of segments from root. angles are absolute, measured from straight down, positive = toward the head (-x)."""
    pts = [P(*root)]
    x, y = root
    for ln, a in zip(lengths, angles):
        x, y = x - math.sin(a) * ln, y + math.cos(a) * ln
        pts.append(P(x, y))
    _limb(d, pts, [w * L for w in widths], SIL)
    # hoof: a small wedge at the end
    hx, hy = pts[-1]
    hw = widths[-1] * L * 0.9
    d.polygon([(hx - hw, hy - hw * 0.2), (hx + hw * 0.6, hy - hw * 0.2), (hx + hw * 0.8, hy + hw * 0.7), (hx - hw * 1.1, hy + hw * 0.7)], fill=SIL)


def draw_rider(frame, sx, gy, L, phase, t, speed=1.0, lantern=1.0, fade=1.0):
    if fade <= 0:
        return None
    layer = Image.new("RGBA", (int(L * 2.4), int(L * 2.0)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ox, oy = layer.width * 0.52, layer.height - 10
    # gallop: the body rises and pitches with the stride
    bob = -0.035 * L * speed * max(0.0, math.sin(phase + 0.6))
    pitch = 0.06 * speed * math.sin(phase + 1.2)

    def P(x, y):
        # rotate about the body centre for the pitch, then place
        cx, cy = 0.0, -0.75
        dx, dy = x - cx, y - cy
        rx = cx + dx * math.cos(pitch) - dy * math.sin(pitch)
        ry = cy + dx * math.sin(pitch) + dy * math.cos(pitch)
        return ox + rx * L, oy + bob + ry * L

    s = speed
    # ---- far legs (drawn first) ----
    # hind: hip at (0.40,-0.74); stifle, hock, fetlock. In the gallop the hinds reach far forward then thrust back.
    hind_a = 0.75 * s * math.sin(phase)                      # upper leg swing
    hind_b = 0.55 * s * max(0.0, math.sin(phase + 0.5)) + 0.35 * s   # hock fold (always a little flexed)
    front_a = 0.8 * s * math.sin(phase + math.pi * 0.9)
    front_b = 1.1 * s * max(0.0, math.sin(phase + math.pi * 0.9 + 0.9))
    hind_far = [hind_a - 0.35 * s, hind_a - 0.35 * s + hind_b * 0.6, hind_a - 0.35 * s + hind_b * 0.6 - hind_b * 1.3]
    front_far = [front_a - 0.3 * s, front_a - 0.3 * s - front_b, front_a - 0.3 * s - front_b * 0.6]
    _leg(d, P, L, (0.40, -0.70), (0.26, 0.26, 0.10), hind_far, (0.14, 0.09, 0.06, 0.05), -1)
    _leg(d, P, L, (-0.36, -0.70), (0.24, 0.26, 0.10), front_far, (0.12, 0.08, 0.055, 0.05), -1)
    # ---- tail, streaming back ----
    tail = []
    for k in range(9):
        q = k / 8
        tail.append(P(0.52 + q * 0.42, -0.84 + q * 0.10 + 0.05 * math.sin(t * 10 - q * 5) * (0.3 + s)))
    tail_w = [0.09 * L * (1 - q * 0.75) for q in (k / 8 for k in range(9))]
    _limb(d, tail, tail_w, SIL)
    # ---- body, then neck, then head (separate polygons so the thin parts keep their shape) ----
    body = [(-0.32, -0.97), (-0.10, -0.95), (0.12, -0.93), (0.30, -0.97), (0.44, -0.94), (0.52, -0.82), (0.53, -0.70), (0.46, -0.58), (0.34, -0.53), (0.20, -0.54), (0.0, -0.52), (-0.20, -0.55), (-0.36, -0.60), (-0.47, -0.72), (-0.50, -0.84), (-0.44, -0.96)]
    d.polygon([P(*p) for p in _smooth_closed(body, 2)], fill=SIL)
    neck = [(-0.30, -0.99), (-0.44, -0.97), (-0.50, -0.86), (-0.72, -1.04), (-0.84, -1.16), (-0.86, -1.30), (-0.74, -1.37), (-0.60, -1.27), (-0.44, -1.12)]
    d.polygon([P(*p) for p in _smooth_closed(neck, 2)], fill=SIL)
    head = [(-0.86, -1.30), (-0.86, -1.12), (-0.94, -1.06), (-1.06, -1.00), (-1.12, -1.04), (-1.10, -1.12), (-1.00, -1.22), (-0.90, -1.34), (-0.80, -1.40), (-0.74, -1.38)]
    d.polygon([P(*p) for p in _smooth_closed(head, 2)], fill=SIL)
    # ears
    d.polygon([P(-0.80, -1.38), P(-0.80, -1.52), P(-0.74, -1.39)], fill=SIL)
    d.polygon([P(-0.74, -1.38), P(-0.71, -1.51), P(-0.67, -1.37)], fill=SIL)
    # mane: one flowing shape along the crest, streaming back with the gallop
    mane = [(-0.74, -1.38)]
    for k in range(6):
        q = k / 5
        mane.append((-0.70 + q * 0.42 + 0.02 * math.sin(t * 12 + k), -1.36 + q * 0.34 - 0.10 - 0.05 * math.sin(t * 9 + k) * (0.3 + s)))
    mane += [(-0.28, -0.99), (-0.42, -1.12), (-0.56, -1.26)]
    d.polygon([P(*p) for p in _smooth_closed(mane, 2)], fill=SIL)
    # ---- near legs ----
    hind_near = [hind_a + 0.35 * s, hind_a + 0.35 * s + hind_b * 0.6, hind_a + 0.35 * s + hind_b * 0.6 - hind_b * 1.3]
    front_near = [front_a + 0.3 * s, front_a + 0.3 * s - front_b, front_a + 0.3 * s - front_b * 0.6]
    _leg(d, P, L, (0.36, -0.72), (0.26, 0.26, 0.10), hind_near, (0.15, 0.10, 0.065, 0.055), -1)
    _leg(d, P, L, (-0.32, -0.72), (0.24, 0.26, 0.10), front_near, (0.13, 0.085, 0.06, 0.055), -1)
    # ---- rider ----
    # near leg: thigh forward, knee bent, boot in the stirrup
    _limb(d, [P(-0.02, -0.98), P(-0.20, -0.84), P(-0.16, -0.60)], [0.11 * L, 0.08 * L, 0.07 * L], SIL)
    d.polygon([P(-0.22, -0.62), P(-0.10, -0.62), P(-0.08, -0.55), P(-0.26, -0.55)], fill=SIL)  # boot
    # torso leaning into the ride
    torso = [(0.06, -0.98), (-0.10, -0.98), (-0.20, -1.26), (-0.14, -1.34), (-0.02, -1.34), (0.02, -1.26)]
    d.polygon([P(*p) for p in torso], fill=SIL)
    # cloak streaming behind, edge rippling
    rip = lambda k: 0.03 * math.sin(t * 11 + k * 1.7) * (0.4 + s)  # noqa: E731
    cloak = [(-0.08, -1.33), (0.04, -1.32), (0.24, -1.30 + rip(0)), (0.46 + 0.10 * s, -1.22 + rip(1)), (0.64 + 0.16 * s, -1.06 + rip(2)), (0.58 + 0.14 * s, -0.98 + rip(3)), (0.40 + 0.06 * s, -1.02 + rip(4)), (0.22, -1.06), (0.08, -1.04), (0.02, -1.10)]
    d.polygon([P(*p) for p in _smooth_closed(cloak, 3)], fill=SIL)
    # head and tricorn
    d.polygon([P(-0.12, -1.30), P(-0.04, -1.30), P(-0.06, -1.38), P(-0.14, -1.38)], fill=SIL)
    hx, hy = P(-0.12, -1.41)
    d.ellipse((hx - 0.07 * L, hy - 0.07 * L, hx + 0.07 * L, hy + 0.07 * L), fill=SIL)
    d.polygon([P(-0.32, -1.44), P(-0.24, -1.54), P(-0.10, -1.58), P(0.04, -1.54), P(0.10, -1.44), P(-0.02, -1.47), P(-0.22, -1.47)], fill=SIL)
    # rein hand and reins
    d.line((P(-0.22, -1.20), P(-0.88, -1.12)), fill=(30, 26, 40, 220), width=max(1, int(0.012 * L)))
    # lantern arm held out and up ahead
    _limb(d, [P(-0.16, -1.28), P(-0.36, -1.36), P(-0.52, -1.34)], [0.09 * L, 0.07 * L, 0.06 * L], SIL)
    lx, ly = P(-0.54, -1.34)
    lw, lh = 0.085 * L, 0.13 * L
    d.line((lx, ly, lx, ly + 0.04 * L), fill=(40, 36, 32, 255), width=max(1, int(0.012 * L)))
    top = ly + 0.04 * L
    d.polygon([(lx - lw * 0.45, top + lh * 0.12), (lx + lw * 0.45, top + lh * 0.12), (lx + lw * 0.3, top), (lx - lw * 0.3, top)], fill=(22, 20, 18, 255))
    d.rounded_rectangle((lx - lw / 2, top + lh * 0.1, lx + lw / 2, top + lh), radius=int(0.01 * L), fill=(22, 20, 18, 255), outline=(70, 62, 56, 255), width=2)
    glass = (int(PURPLE[0] * 0.5 + 128), int(PURPLE[1] * 0.5 + 128), int(PURPLE[2] * 0.5 + 128), int(255 * lantern))
    d.rounded_rectangle((lx - lw * 0.34, top + lh * 0.22, lx + lw * 0.34, top + lh * 0.9), radius=int(0.008 * L), fill=glass)

    # ---- shading: purple rim light from the lantern side (front/top), black elsewhere ----
    alpha = np.asarray(layer.split()[3]).astype(np.float32) / 255
    h, w = alpha.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lxp, lyp = lx, top + lh * 0.5
    dist = np.sqrt((xx - lxp) ** 2 + (yy - lyp) ** 2) / L
    light = np.clip(1.0 - dist / 1.5, 0, 1) ** 1.5 * 0.9 * lantern
    # edge-only: erode the mask and light the rim
    inner = np.asarray(Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(max(3, int(L * 0.03) | 1)))).astype(np.float32) / 255
    rim = np.clip(alpha - inner, 0, 1)
    arr = np.asarray(layer).astype(np.float32)
    tint = np.array(PURPLE, np.float32)
    k = (light * (0.10 + 0.9 * rim))[..., None]
    arr[..., :3] = arr[..., :3] * (1 - k) + tint * k
    arr[..., :3] = np.clip(arr[..., :3], 0, 255)
    layer = Image.fromarray(arr.astype(np.uint8), "RGBA")
    if fade < 1:
        layer.putalpha(layer.split()[3].point(lambda v: int(v * fade)))
    # ground shadow
    shd = Image.new("RGBA", (int(L * 1.3), int(L * 0.09) + 16), (0, 0, 0, 0))
    ImageDraw.Draw(shd).ellipse((8, 6, shd.width - 8, shd.height - 6), fill=(0, 0, 0, int(150 * fade)))
    frame.alpha_composite(shd.filter(ImageFilter.GaussianBlur(10)), (int(sx - shd.width / 2), int(gy - shd.height / 2)))
    frame.alpha_composite(layer, (int(sx - ox), int(gy - oy)))
    return (sx - ox + lxp, gy - oy + lyp)

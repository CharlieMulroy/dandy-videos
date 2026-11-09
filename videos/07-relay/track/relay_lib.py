"""Drawing for video 07, The Relay: a night track meet, all in code.

Side view: a dark sky with floodlight towers, empty stands, a barrier, and a wet track whose lanes recede in
perspective; the floodlights streak down the wet surface. Layers are pre-rendered as tileable strips and scrolled
at their own parallax, so a tracking shot only slices arrays. Runners are a jointed silhouette (side view, facing +x)
filled near black, with a cold rim light from the floodlights and a blurred, rippled reflection in the wet track.
Overhead: the oval from above with eight lanes, light pools from the towers, and tiny top-down runners.

Colours keep to a cold night family; brand purple is reserved for the baton (BATON) and the end card.
"""
import math
import os
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FONT_DIR = "/usr/share/fonts/opentype/inter"

SKY_TOP, SKY_BOT = (4, 6, 12), (12, 17, 32)
STAND_A, STAND_B = (14, 17, 26), (19, 23, 34)
SEAT = (40, 46, 62)
BARRIER = (10, 12, 18)
TRACK_FAR, TRACK_NEAR = (44, 22, 22), (66, 30, 27)
LANE = (190, 196, 210)
BODY, BODY_FAR = (7, 9, 15), (17, 21, 32)
RIM = (205, 225, 255)
LAMP = (255, 252, 240)
BATON, BATON_CORE = (124, 77, 255), (214, 196, 255)
WARN = (255, 107, 107)

HORIZON = 1090                                                        # top of the track in side view
LANE_Y = [1090, 1106, 1126, 1152, 1186, 1232, 1296, 1390, 1530, 1745]  # lane lines, far to near
NEAR_FOOT = 1660                                                       # where feet land in the near lane


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(size))


def lerp(a, b, p):
    return a + (b - a) * p


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def mixc(c1, c2, p):
    return tuple(int(lerp(c1[i], c2[i], p)) for i in range(3))


def comp(frame, color, alpha, x0=0, y0=0):
    """Blend a solid colour into frame (H, W, 3 uint8) through alpha (h, w float 0..1) placed at x0, y0."""
    h, w = alpha.shape
    fx0, fy0 = max(0, x0), max(0, y0)
    fx1, fy1 = min(frame.shape[1], x0 + w), min(frame.shape[0], y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    a = alpha[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0, None]
    reg = frame[fy0:fy1, fx0:fx1].astype(np.float32)
    frame[fy0:fy1, fx0:fx1] = (reg * (1 - a) + np.array(color, np.float32) * a).astype(np.uint8)


def add_light(frame, light, x0=0, y0=0):
    """Additive light: light is (h, w, 3) float."""
    h, w = light.shape[:2]
    fx0, fy0 = max(0, x0), max(0, y0)
    fx1, fy1 = min(frame.shape[1], x0 + w), min(frame.shape[0], y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    reg = frame[fy0:fy1, fx0:fx1].astype(np.float32) + light[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
    frame[fy0:fy1, fx0:fx1] = np.clip(reg, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- side-view strips
TOWER_GAP = 1400
STRIP_W = TOWER_GAP * 2
_strips = {}


def _sky_strip():
    s = np.zeros((HORIZON, STRIP_W, 3), np.float32)
    yy = np.linspace(0, 1, HORIZON)[:, None, None]
    s[:] = np.array(SKY_TOP) * (1 - yy) + np.array(SKY_BOT) * yy
    light = np.zeros((HORIZON, STRIP_W, 3), np.float32)
    for k in range(2):
        cx = TOWER_GAP * k + TOWER_GAP // 2
        # pole and lamp bank
        cv2.rectangle(s, (cx - 7, 400), (cx + 7, HORIZON), (9, 11, 17), -1)
        cv2.rectangle(s, (cx - 92, 330), (cx + 92, 420), (14, 16, 24), -1)
        for r in range(3):
            for c in range(6):
                lx, ly = cx - 75 + c * 30, 345 + r * 26
                cv2.circle(light, (lx, ly), 9, (255, 250, 236), -1, cv2.LINE_AA)
        # glow and haze cone downwards
        g = np.zeros((HORIZON, STRIP_W), np.float32)
        cv2.circle(g, (cx, 375), 160, 1.0, -1)
        g = cv2.GaussianBlur(g, (0, 0), 90)
        cone = np.zeros((HORIZON, STRIP_W), np.float32)
        pts = np.array([[cx - 90, 420], [cx + 90, 420], [cx + 520, HORIZON], [cx - 520, HORIZON]], np.int32)
        cv2.fillPoly(cone, [pts], 1.0)
        cone = cv2.GaussianBlur(cone, (0, 0), 60) * np.linspace(0.6, 0.15, HORIZON)[:, None]
        light += (g * 70)[..., None] * np.array([1.0, 0.98, 0.92]) + (cone * 22)[..., None] * np.array([0.8, 0.86, 1.0])
    return np.clip(s, 0, 255), light


def _stands_strip():
    """Empty tiered stands with a roofline, faint seat rows and a dark barrier, tileable across 1200 px."""
    w = 1200
    top, bot = 640, HORIZON
    a = np.zeros((bot - top, w), np.float32)
    col = np.zeros((bot - top, w, 3), np.float32)
    a[:] = 1.0
    rows = 14
    for r in range(rows):
        y0 = int(30 + r * (bot - top - 80) / rows)
        y1 = int(30 + (r + 1) * (bot - top - 80) / rows)
        col[y0:y1] = STAND_A if r % 2 else STAND_B
        rnd = random.Random(r)
        for x in range(0, w, 22):
            if rnd.random() < 0.92:
                cv2.rectangle(col, (x + 3, y1 - 9), (x + 15, y1 - 4), [c * 0.9 for c in SEAT], -1)
    col[:30] = (8, 10, 15)
    col[bot - top - 50:] = BARRIER
    for x in range(0, w, 300):  # stair aisles
        cv2.rectangle(col, (x + 140, 30), (x + 156, bot - top - 50), (11, 13, 20), -1)
    # thin barrier ad boards, unlit
    for x in range(0, w, 240):
        cv2.rectangle(col, (x + 10, bot - top - 42), (x + 226, bot - top - 12), (16, 19, 28), -1)
    return col, a, top


def _track_strip():
    """Wet track base for the side view: gradient, lane lines and a tileable fleck texture (parallax 1)."""
    h = H - HORIZON
    base = np.zeros((h, W, 3), np.float32)
    yy = np.linspace(0, 1, h)[:, None, None] ** 0.8
    base[:] = np.array(TRACK_FAR) * (1 - yy) + np.array(TRACK_NEAR) * yy
    for i, ly in enumerate(LANE_Y):
        th = max(1, int(1 + 5 * (ly - HORIZON) / (H - HORIZON)))
        cv2.line(base, (0, ly - HORIZON), (W, ly - HORIZON), [c * (0.55 + 0.45 * i / len(LANE_Y)) for c in LANE], th, cv2.LINE_AA)
    fw = 2048
    fl = np.zeros((h, fw), np.float32)
    rnd = np.random.default_rng(4)
    for _ in range(2600):
        y = int(rnd.uniform(0, h) ** 1.0)
        depth = (y / h)
        x = int(rnd.uniform(0, fw))
        ln = int(4 + 40 * depth)
        cv2.line(fl, (x, y), (min(fw - 1, x + ln), y), float(rnd.uniform(0.15, 0.6)), 1 + int(2 * depth))
    puddle = np.zeros((h, fw), np.float32)
    for _ in range(40):
        y = int(rnd.uniform(0.1, 1.0) * h)
        x = int(rnd.uniform(0, fw))
        cv2.ellipse(puddle, (x, y), (int(60 + 160 * y / h), int(4 + 18 * y / h)), 0, 0, 360, 1.0, -1)
    puddle = cv2.GaussianBlur(puddle, (0, 0), 6)
    return base, fl, puddle


def _reflect_strip(sky_light):
    """The floodlights streaked down the wet track: vertical pillars under each lamp bank."""
    h = H - HORIZON
    r = np.zeros((h, STRIP_W, 3), np.float32)
    for k in range(2):
        cx = TOWER_GAP * k + TOWER_GAP // 2
        col = np.zeros((h, STRIP_W), np.float32)
        cv2.rectangle(col, (cx - 70, 0), (cx + 70, h), 1.0, -1)
        col = cv2.GaussianBlur(col, (0, 0), 28)
        fade = np.linspace(0.9, 0.25, h)[:, None]
        r += (col * fade * 120)[..., None] * np.array([1.0, 0.95, 0.85])
    return r


def strips():
    if not _strips:
        sky, sky_light = _sky_strip()
        st_col, st_a, st_top = _stands_strip()
        base, fl, puddle = _track_strip()
        _strips.update(sky=sky, sky_light=sky_light, st_col=st_col, st_a=st_a, st_top=st_top, track=base, flecks=fl,
                       puddle=puddle, refl=_reflect_strip(sky_light))
    return _strips


def _tile(strip, off, width):
    """Slice `width` columns from a tileable strip starting at off (wraps)."""
    sw = strip.shape[1]
    off = int(off) % sw
    if off + width <= sw:
        return strip[:, off:off + width]
    return np.concatenate([strip[:, off:], strip[:, :width - (sw - off)]], axis=1)


def side_background(cam_x, t):
    """The side-view stadium for a camera at world x (zoom 1). Parallax: towers 0.35, stands 0.5, track 1."""
    S = strips()
    fr = np.zeros((H, W, 3), np.float32)
    fr[:HORIZON] = _tile(S["sky"], cam_x * 0.35, W)
    fr[:HORIZON] += _tile(S["sky_light"], cam_x * 0.35, W) * (0.92 + 0.08 * math.sin(t * 9.1))
    top = S["st_top"]
    fr[top:HORIZON] = _tile(S["st_col"], cam_x * 0.5, W)
    fr[HORIZON:] = S["track"]
    fl = _tile(S["flecks"], cam_x, W)
    fr[HORIZON:] += fl[..., None] * np.array([28, 18, 16])
    pud = _tile(S["puddle"], cam_x, W)
    refl = _tile(S["refl"], cam_x * 0.35, W)
    ripple = 0.75 + 0.25 * np.sin(np.linspace(0, 40, H - HORIZON)[:, None] + t * 3.0)
    fr[HORIZON:] += refl * (0.35 + 0.65 * pud[..., None]) * ripple[..., None]
    # cold glow of the haze over the stands
    return np.clip(fr, 0, 255).astype(np.uint8)


VANISH_X, VANISH_Y = W / 2, 1000


def _persp_x(x_near, y):
    """A line across the lanes recedes toward the vanishing point: its x at row y given its x at the near feet row."""
    return VANISH_X + (x_near - VANISH_X) * (y - VANISH_Y) / (NEAR_FOOT - VANISH_Y)


def lane_marks(frame, cam_x, marks):
    """Exchange-zone ticks (near lane only) and the finish line across every lane, in perspective.
    marks = [(world_x, kind)] with kind 'zone' or 'finish'."""
    for wx, kind in marks:
        x = wx - cam_x + W / 2
        if x < -600 or x > W + 600:
            continue
        if kind == "finish":
            y0, y1 = LANE_Y[0], H
            hw0, hw1 = 1.5, 22 * (y1 - VANISH_Y) / (NEAR_FOOT - VANISH_Y)
            pts = np.array([[_persp_x(x, y0) - hw0, y0], [_persp_x(x, y0) + hw0, y0], [_persp_x(x, y1) + hw1, y1], [_persp_x(x, y1) - hw1, y1]], np.int32)
            lay = np.zeros(frame.shape[:2], np.float32)
            cv2.fillPoly(lay, [pts], 1.0, cv2.LINE_AA)
            comp(frame, (226, 230, 238), lay * 0.85)
        else:
            y0, y1 = LANE_Y[-2] + 3, LANE_Y[-1] - 3
            pts = np.array([[_persp_x(x, y0) - 3, y0], [_persp_x(x, y0) + 3, y0], [_persp_x(x, y1) + 6, y1], [_persp_x(x, y1) - 6, y1]], np.int32)
            cv2.fillPoly(frame, [pts], (176, 186, 204), cv2.LINE_AA)


# ---------------------------------------------------------------- runner
L_THIGH, L_SHIN, L_FOOT, L_TORSO, L_UA, L_FA = 0.25, 0.25, 0.075, 0.30, 0.17, 0.16
HEAD_R = 0.058


def pose_sprint(phase, lean=0.24):
    p = 2 * math.pi * phase
    def leg(q):
        hip = 0.18 + 0.86 * math.sin(q)
        knee = 0.15 + 1.8 * max(0.0, math.cos(q - 0.3)) ** 1.4
        return hip, knee
    hA, kA = leg(p)
    hB, kB = leg(p + math.pi)
    return dict(lean=lean, hA=hA, kA=kA, hB=hB, kB=kB, sA=-0.95 * math.sin(p), eA=1.45 + 0.25 * math.sin(p),
                sB=0.95 * math.sin(p), eB=1.45 - 0.25 * math.sin(p), head=0.0)


def pose_stand(arms=0.05):
    return dict(lean=0.02, hA=0.04, kA=0.06, hB=-0.04, kB=0.06, sA=arms, eA=0.15, sB=-arms, eB=0.15, head=0.0)


def pose_look_up():
    p = pose_stand()
    p.update(head=-0.5, lean=-0.06)
    return p


def pose_crouch():
    """In the blocks: hips up, near knee forward and down, far leg back, hands on the line."""
    return dict(lean=1.25, hA=1.55, kA=2.25, hB=0.55, kB=1.5, sA=1.45, eA=0.0, sB=1.4, eB=0.0, head=-0.6)


def pose_reach(phase, hand_forward=True):
    """Running with the near arm out straight forward (the hand-off)."""
    p = pose_sprint(phase, lean=0.18)
    if hand_forward:
        p.update(sA=1.45, eA=0.08)
    return p


def pose_receive(phase):
    """Running, near arm stretched straight back, palm open (a receiver who is already moving)."""
    p = pose_sprint(phase, lean=0.2)
    p.update(sA=-1.25, eA=0.05, head=0.0)
    return p


def pose_stumble(q):
    """q 0..1: pitch forward, arms out, then upright and still, hands on hips."""
    a = math.sin(q * math.pi)
    return dict(lean=0.24 + 0.55 * a - 0.2 * q, hA=0.5 * a + 0.05, kA=0.5 * a + 0.1, hB=-0.4 * a, kB=0.4 * a + 0.1,
                sA=0.9 * a + 0.3 * (1 - a) * q, eA=0.6 + 1.0 * q, sB=-0.6 * a, eB=0.5 + 1.0 * q, head=0.2 * a)


def pose_blend(a, b, q):
    return {k: lerp(a[k], b[k], q) for k in a}


def joints(p):
    """Forward kinematics in body units, y up, x forward, hip at (0, 0) before grounding."""
    J = {"hip": (0.0, 0.0)}
    lean = p["lean"]
    sh = (math.sin(lean) * L_TORSO, math.cos(lean) * L_TORSO)
    J["shoulder"] = sh
    J["head"] = (sh[0] + math.sin(lean + p["head"] * 0.5) * 0.11 + 0.01, sh[1] + math.cos(lean + p["head"] * 0.5) * 0.11)
    for side in ("A", "B"):
        h, k = p["h" + side], p["k" + side]
        knee = (math.sin(h) * L_THIGH, -math.cos(h) * L_THIGH)
        sa = h - k
        ankle = (knee[0] + math.sin(sa) * L_SHIN, knee[1] - math.cos(sa) * L_SHIN)
        fa = sa + 1.45
        toe = (ankle[0] + math.sin(fa) * L_FOOT, ankle[1] - math.cos(fa) * L_FOOT)
        J["knee" + side], J["ankle" + side], J["toe" + side] = knee, ankle, toe
        s, e = p["s" + side], p["e" + side]
        elbow = (sh[0] + math.sin(s) * L_UA, sh[1] - math.cos(s) * L_UA)
        wrist = (elbow[0] + math.sin(s + e) * L_FA, elbow[1] - math.cos(s + e) * L_FA)
        J["elbow" + side], J["wrist" + side] = elbow, wrist
    low = min(J[k][1] for k in ("ankleA", "ankleB", "toeA", "toeB"))
    return {k: (v[0], v[1] - low + 0.012) for k, v in J.items()}


def draw_runner(frame, x, ground_y, s, pose, facing=1, hand=None, baton=0.0, reflect=True, rim=1.0, tone=1.0):
    """Silhouette with rim light and wet reflection. x, ground_y: screen point under the body; s: px per body unit.
    hand: None, 'open' or 'closed' (draws fingers on the near hand). baton: 0..1 visibility of the purple baton
    in the near hand. Returns the near wrist position on screen."""
    J = joints(pose)
    pad = int(s * 0.9)
    bx0, by0 = int(x - pad), int(ground_y - s * 1.25)
    bw, bh = pad * 2, int(s * 1.25) + 4
    if bx0 > W or bx0 + bw < 0 or by0 > H:
        return None
    near = np.zeros((bh, bw), np.uint8)
    far = np.zeros((bh, bw), np.uint8)
    fist = np.zeros((bh, bw), np.uint8)       # the fist around the baton, drawn after it so the hand holds it

    def P(k):
        jx, jy = J[k]
        return (int((x + facing * jx * s - bx0) * 4), int((ground_y - jy * s - by0) * 4))

    def taper(img, a, b, w0, w1):
        (ax, ay), (bx, by) = P(a), P(b)
        dx, dy = bx - ax, by - ay
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        r0, r1 = w0 * s * 2, w1 * s * 2       # half widths in shifted (x4) units
        poly = np.array([[ax + nx * r0, ay + ny * r0], [bx + nx * r1, by + ny * r1], [bx - nx * r1, by - ny * r1], [ax - nx * r0, ay - ny * r0]], np.int32)
        cv2.fillPoly(img, [poly], 255, cv2.LINE_AA, shift=2)
        cv2.circle(img, (int(ax), int(ay)), int(r0), 255, -1, cv2.LINE_AA, shift=2)
        cv2.circle(img, (int(bx), int(by)), int(r1), 255, -1, cv2.LINE_AA, shift=2)

    def limbs(img, side):
        taper(img, "hip", "knee" + side, 0.105, 0.068)
        taper(img, "knee" + side, "ankle" + side, 0.066, 0.036)
        taper(img, "ankle" + side, "toe" + side, 0.04, 0.018)

    def arm(img, side):
        taper(img, "shoulder", "elbow" + side, 0.062, 0.044)
        taper(img, "elbow" + side, "wrist" + side, 0.044, 0.032)

    limbs(far, "B")
    arm(far, "B")
    # torso: hips to a broader chest, leaning with the pose
    taper(near, "hip", "shoulder", 0.13, 0.165)
    nk = J["shoulder"]
    hd = J["head"]
    J["neck"] = (lerp(nk[0], hd[0], 0.45), lerp(nk[1], hd[1], 0.45))
    taper(near, "shoulder", "neck", 0.06, 0.05)
    hx, hy = P("head")
    cv2.ellipse(near, (hx, hy), (int(HEAD_R * s * 4), int(HEAD_R * 1.15 * s * 4)), math.degrees(-pose["lean"]) * facing, 0, 360, 255, -1, cv2.LINE_AA, shift=2)
    limbs(near, "A")
    arm(near, "A")
    wx, wy = J["wristA"]
    ex, ey = J["elbowA"]
    ang = math.atan2(wy - ey, (wx - ex) * facing)
    sw = (x + facing * wx * s, ground_y - wy * s)
    if hand:
        # palm plus fingers along the forearm direction; open spreads them, closed curls them into a fist
        dx, dy = math.cos(ang), -math.sin(ang)
        px, py = sw[0] + dx * 0.02 * s, sw[1] + dy * 0.02 * s
        cv2.circle(near, (int((px - bx0) * 4), int((py - by0) * 4)), int(0.03 * s * 4), 255, -1, cv2.LINE_AA, shift=2)
        if hand == "open":
            for k, spread in enumerate((-0.35, -0.12, 0.1, 0.32)):
                a2 = ang + spread
                fx, fy = px + math.cos(a2) * 0.075 * s * facing, py - math.sin(a2) * 0.075 * s
                cv2.line(near, (int((px - bx0) * 4), int((py - by0) * 4)), (int((fx - bx0) * 4), int((fy - by0) * 4)), 255,
                         max(1, int(0.014 * s)), cv2.LINE_AA, shift=2)
            tx, ty = px + math.cos(ang + 1.1) * 0.05 * s * facing, py - math.sin(ang + 1.1) * 0.05 * s
            cv2.line(near, (int((px - bx0) * 4), int((py - by0) * 4)), (int((tx - bx0) * 4), int((ty - by0) * 4)), 255,
                     max(1, int(0.016 * s)), cv2.LINE_AA, shift=2)
        else:
            fist_img = fist if baton > 0 else near
            cv2.circle(fist_img, (int((px + dx * 0.02 * s - bx0) * 4), int((py + dy * 0.02 * s - by0) * 4)), int(0.036 * s * 4), 255, -1, cv2.LINE_AA, shift=2)
    nf = near.astype(np.float32) / 255
    ff = far.astype(np.float32) / 255
    fm = fist.astype(np.float32) / 255
    allm = np.maximum(np.maximum(nf, ff), fm)
    if reflect:
        gy = ground_y - by0
        rh = min(bh - 1, gy), int(s * 0.9)
        src = allm[max(0, gy - int(s * 1.1)):gy]
        if src.size:
            ref = src[::-1]
            ref = cv2.resize(ref, (bw, max(1, int(ref.shape[0] * 0.9))))
            k = ref.shape[0]
            rows = np.arange(k, dtype=np.float32)
            shift = (np.sin(rows * 0.18 + x * 0.01) * 0.012 * s).astype(np.float32)
            mapx = (np.arange(bw, dtype=np.float32)[None, :] + shift[:, None]).astype(np.float32)
            mapy = np.repeat(rows[:, None], bw, axis=1)
            ref = cv2.remap(ref, mapx, mapy, cv2.INTER_LINEAR)
            ref = cv2.GaussianBlur(ref, (0, 0), max(1.0, s * 0.012)) * np.linspace(0.42, 0.0, k)[:, None]
            comp(frame, (4, 4, 8), ref * 0.9 * tone, bx0, ground_y)
            if baton > 0:
                pass
    comp(frame, mixc(BODY_FAR, (40, 46, 62), 1 - tone), ff * (1 - nf), bx0, by0)
    comp(frame, mixc(BODY, (40, 46, 62), 1 - tone), nf, bx0, by0)
    if rim > 0:
        d = int(min(7, max(2, s * 0.011)))
        # lit where the light (behind and above the runner) reaches the edge: pixel in the body, its up-back neighbour not
        lit = np.clip(allm - np.roll(np.roll(allm, d, axis=0), facing * d, axis=1), 0, 1)
        rimm = cv2.GaussianBlur(lit, (0, 0), min(2.2, max(0.7, s * 0.0025))) * rim * tone
        comp(frame, RIM, np.clip(rimm * 1.25, 0, 1), bx0, by0)
    if baton > 0:
        draw_baton(frame, sw, ang, facing, s, baton)
        if fm.any():
            # the fist closes over the middle of the baton; its rim picks up the floodlight and a touch of purple
            comp(frame, BODY, fm, bx0, by0)
            d = int(min(7, max(2, s * 0.011)))
            lit = np.clip(fm - np.roll(np.roll(allm, d, axis=0), facing * d, axis=1), 0, 1)
            comp(frame, RIM, np.clip(cv2.GaussianBlur(lit, (0, 0), 1.0) * rim * tone * 1.2, 0, 1), bx0, by0)
            edge = np.clip(fm - cv2.erode(fm, np.ones((3, 3), np.uint8), iterations=max(1, d // 2)), 0, 1)
            comp(frame, BATON, np.clip(edge * 0.45 * baton, 0, 1), bx0, by0)
    return sw


def draw_baton(frame, wrist, ang, facing, s, vis, glow=1.0):
    """The baton held through the fist: a short capsule across the hand, brand purple with a hot core and a glow."""
    px, py = wrist
    dx, dy = math.cos(ang) * facing, -math.sin(ang)
    cx, cy = px + dx * 0.04 * s, py + dy * 0.04 * s
    # the baton sits across the fist, perpendicular to the forearm
    nx, ny = -dy, dx
    ln = 0.075 * s
    a = (cx - nx * ln, cy - ny * ln)
    b = (cx + nx * ln, cy + ny * ln)
    pad = int(0.5 * s)
    gw = np.zeros((pad * 2, pad * 2), np.float32)
    o = (int(cx) - pad, int(cy) - pad)
    cv2.line(gw, (int(a[0] - o[0]), int(a[1] - o[1])), (int(b[0] - o[0]), int(b[1] - o[1])), 1.0, max(2, int(0.03 * s)), cv2.LINE_AA)
    halo = cv2.GaussianBlur(gw, (0, 0), max(3, min(40, s * 0.04)))
    add_light(frame, (halo[..., None] * np.array(BATON, np.float32) * 1.6 * vis * glow), o[0], o[1])
    comp(frame, BATON, np.clip(gw * vis, 0, 1), o[0], o[1])
    core = np.zeros_like(gw)
    cv2.line(core, (int(a[0] - o[0]), int(a[1] - o[1])), (int(b[0] - o[0]), int(b[1] - o[1])), 1.0, max(1, int(0.011 * s)), cv2.LINE_AA)
    comp(frame, BATON_CORE, np.clip(core * vis, 0, 1), o[0], o[1])


# ---------------------------------------------------------------- overhead oval
OV_SCALE = 2                     # overhead base is drawn at 2x so the camera can start zoomed in
OV_CX, OV_CY = W // 2, H // 2
STRAIGHT = 760                   # straight length (vertical), zoom-1 px
R_IN = 230
LANE_W = 22
N_LANES = 8
_ov = {}


def lane_point(lane, d):
    """Point and heading on the centre of `lane` (0 inner) at distance d along it, zoom-1 px. Runs anticlockwise
    starting at the bottom of the right straight, going up."""
    r = R_IN + (lane + 0.5) * LANE_W
    curve = math.pi * r
    per = 2 * STRAIGHT + 2 * curve
    d = d % per
    hs = STRAIGHT / 2
    if d < STRAIGHT:                         # right straight, going up
        return (OV_CX + r, OV_CY + hs - d), -math.pi / 2
    d -= STRAIGHT
    if d < curve:                            # top bend, right to left
        a = d / r
        return (OV_CX + r * math.cos(a), OV_CY - hs - r * math.sin(a)), -math.pi / 2 - a
    d -= curve
    if d < STRAIGHT:                         # left straight, going down
        return (OV_CX - r, OV_CY - hs + d), math.pi / 2
    d -= STRAIGHT
    a = d / r                                # bottom bend, left to right
    return (OV_CX - r * math.cos(a), OV_CY + hs + r * math.sin(a)), math.pi / 2 - a


def lap_length(lane):
    r = R_IN + (lane + 0.5) * LANE_W
    return 2 * STRAIGHT + 2 * math.pi * r


def overhead_base():
    if "base" in _ov:
        return _ov["base"]
    S = OV_SCALE
    img = np.zeros((H * S, W * S, 3), np.float32)
    img[:] = (8, 10, 16)
    # stands ring: dark band with seat texture
    hs = STRAIGHT / 2
    def stadium(r_out, col):
        m = np.zeros((H * S, W * S), np.uint8)
        cv2.rectangle(m, (int((OV_CX - r_out) * S), int((OV_CY - hs) * S)), (int((OV_CX + r_out) * S), int((OV_CY + hs) * S)), 255, -1)
        cv2.circle(m, (OV_CX * S, int((OV_CY - hs) * S)), int(r_out * S), 255, -1, cv2.LINE_AA)
        cv2.circle(m, (OV_CX * S, int((OV_CY + hs) * S)), int(r_out * S), 255, -1, cv2.LINE_AA)
        return m
    r_track_out = R_IN + N_LANES * LANE_W
    outer = stadium(r_track_out + 150, 1)
    img[outer > 0] = STAND_A
    rnd = np.random.default_rng(3)
    seat = np.zeros((H * S, W * S), np.float32)
    for _ in range(9000):
        x, y = int(rnd.uniform(0, W * S)), int(rnd.uniform(0, H * S))
        if outer[y, x]:
            cv2.rectangle(seat, (x, y), (x + 5, y + 3), 1.0, -1)
    img += seat[..., None] * np.array([18, 20, 28]) * 0.6
    track = stadium(r_track_out + 6, 1)
    yy = np.linspace(0, 1, H * S)[:, None, None]
    tcol = np.array(TRACK_FAR) * (1 - yy) + np.array(TRACK_NEAR) * yy
    img = np.where(track[..., None] > 0, tcol, img)
    infield = stadium(R_IN - 4, 1)
    img[infield > 0] = (10, 22, 16)
    # infield texture: mown stripes
    for k in range(0, H * S, 120):
        band = np.zeros((H * S, W * S), np.float32)
        band[k:k + 60] = 1
        img += (band * (infield > 0))[..., None] * np.array([2, 5, 3])
    for i in range(N_LANES + 1):
        r = R_IN + i * LANE_W
        m = np.zeros((H * S, W * S), np.uint8)
        x0, x1 = int((OV_CX - r) * S), int((OV_CX + r) * S)
        y0, y1 = int((OV_CY - hs) * S), int((OV_CY + hs) * S)
        cv2.line(m, (x0, y0), (x0, y1), 255, 2, cv2.LINE_AA)
        cv2.line(m, (x1, y0), (x1, y1), 255, 2, cv2.LINE_AA)
        cv2.ellipse(m, (OV_CX * S, y0), (int(r * S), int(r * S)), 0, 180, 360, 255, 2, cv2.LINE_AA)
        cv2.ellipse(m, (OV_CX * S, y1), (int(r * S), int(r * S)), 0, 0, 180, 255, 2, cv2.LINE_AA)
        img = np.where(m[..., None] > 0, img * 0.3 + np.array(LANE) * 0.7 * (m[..., None] / 255), img)
    # exchange zones: a short bar across every lane at each quarter
    for lane in range(N_LANES):
        for q in range(4):
            (px, py), hd = lane_point(lane, lap_length(lane) * q / 4)
            nx, ny = -math.sin(hd), math.cos(hd)
            a = (int((px - nx * 10) * S), int((py - ny * 10) * S))
            b = (int((px + nx * 10) * S), int((py + ny * 10) * S))
            cv2.line(img, a, b, (150, 160, 178), 3, cv2.LINE_AA)
    # finish line across the right straight's top
    (px, py), _ = lane_point(0, 0)
    cv2.line(img, (int((OV_CX + R_IN) * S), int((OV_CY + hs) * S)), (int((OV_CX + r_track_out) * S), int((OV_CY + hs) * S)), (220, 224, 232), 4, cv2.LINE_AA)
    # light pools from four towers, and the wet sheen
    pools = np.zeros((H * S, W * S), np.float32)
    for cx, cy in ((OV_CX - 420, OV_CY - 640), (OV_CX + 420, OV_CY - 640), (OV_CX - 420, OV_CY + 640), (OV_CX + 420, OV_CY + 640)):
        cv2.circle(pools, (int(cx * S), int(cy * S)), int(520 * S), 1.0, -1)
    pools = cv2.GaussianBlur(pools, (0, 0), 160 * S)
    sheen = cv2.GaussianBlur(rnd.random((H * S // 8, W * S // 8)).astype(np.float32), (0, 0), 3)
    sheen = cv2.resize(sheen, (W * S, H * S)) * (track[..., None] > 0)[..., 0]
    img = img * (0.55 + 0.9 * pools[..., None]) + (np.clip(sheen - 0.5, 0, 1) * 70 * pools)[..., None] * np.array([1.0, 0.95, 0.9])
    for cx, cy in ((OV_CX - 470, OV_CY - 700), (OV_CX + 470, OV_CY - 700), (OV_CX - 470, OV_CY + 700), (OV_CX + 470, OV_CY + 700)):
        cv2.rectangle(img, (int((cx - 28) * S), int((cy - 10) * S)), (int((cx + 28) * S), int((cy + 10) * S)), (255, 250, 236), -1)
    _ov["base"] = np.clip(img, 0, 255).astype(np.uint8)
    return _ov["base"]


def overhead_runner(img, pos, heading, phase, S, state="run", tone=1.0, baton=0.0, K=2.0):
    """A runner seen from above at 2x base scale: shoulders, head, pumping arms and legs, rim on the lit side.
    K enlarges the figure beyond true scale so it reads in a wide shot."""
    x, y = pos[0] * S, pos[1] * S
    c, s_ = math.cos(heading), math.sin(heading)
    S = S * K
    def pt(f, r):  # forward, right offsets in zoom-1 px
        return (int((x + (f * c - r * s_) * S) * 4), int((y + (f * s_ + r * c) * S) * 4))
    col = mixc(BODY, (60, 66, 82), 1 - tone)
    sw = math.sin(phase * 2 * math.pi) if state == "run" else 0.0
    if state == "sit":
        cv2.line(img, pt(0, -2), pt(9, -2), col, int(2.2 * S), cv2.LINE_AA, shift=2)
        cv2.line(img, pt(0, 2), pt(9, 2), col, int(2.2 * S), cv2.LINE_AA, shift=2)
        cv2.ellipse(img, pt(-1, 0), (int(5 * S * 4), int(4 * S * 4)), math.degrees(heading), 0, 360, col, -1, cv2.LINE_AA, shift=2)
        cv2.circle(img, pt(-4, 0), int(3 * S * 4), col, -1, cv2.LINE_AA, shift=2)
        return
    for side, ph in ((-1, sw), (1, -sw)):
        cv2.line(img, pt(0, side * 2.5), pt(7 * ph, side * 2.5), col, int(2.0 * S), cv2.LINE_AA, shift=2)      # legs
        cv2.line(img, pt(1, side * 5.5), pt(1 - 6 * ph, side * 6.5), col, int(1.6 * S), cv2.LINE_AA, shift=2)  # arms
    cv2.ellipse(img, pt(0, 0), (int(3.4 * S * 4), int(6.5 * S * 4)), math.degrees(heading), 0, 360, col, -1, cv2.LINE_AA, shift=2)
    cv2.circle(img, pt(1, 0), int(3.0 * S * 4), mixc(col, (30, 34, 46), 0.4), -1, cv2.LINE_AA, shift=2)
    cv2.circle(img, pt(1.5, -1.2), int(1.2 * S * 4), mixc(RIM, col, 1 - 0.7 * tone), -1, cv2.LINE_AA, shift=2)

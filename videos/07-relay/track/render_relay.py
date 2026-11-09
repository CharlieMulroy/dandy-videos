"""Renderer for video 07, The Relay. Vertical 1080x1920 only.

Usage:  python3 videos/07-relay/track/render_relay.py [--preview] [--stills] [--final]

Timeline (global seconds, shot ids in SHOTS):
  s1a 0.0-1.3   feet at full speed, tight and low, splashes on the wet track
  s1b 1.3-2.15  tight on the outstretched hand: it closes on empty air
  s1c 2.15-3.0  wide: the next runner is off his mark, in the wrong lane, looking at the stands; the first stumbles
  s2  3.0-10.0  three legs: out of the blocks, faster each time, and each hand-off closes on air; the board's
                split drops while the leg counter never moves
  s3  10.0-20.0 overhead of the whole oval, every lane dropping hand-offs, one race abandoned
  s4a 20.0-22.0 the first runner's hand: the purple baton appears, the fist closes on it, pistol
  s4b 22.0-26.75 clean hand-off 1: the receiver already moving
  s4c 26.75-32.0 clean hand-off 2, quicker
  s5a 32.0-35.5 the anchor leg pulls away from the other lanes
  s5b 35.5-40.0 the finish: baton across the line, the clock stops
  end 40.0-44.5 end card without Dandy Man

Captions are the script's narration lines, burned in at fixed times until Charlie's voiceover is aligned
(voiceover/relay.json with "captions" or "file" then replaces them). Uses the shared finish pass from video 04.
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

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "render"))
import relay_lib as R  # noqa: E402
import sfx_relay  # noqa: E402
from finish import finish, spring  # noqa: E402

with open(os.path.join(ROOT, "style", "contract.json")) as f:
    CONTRACT = json.load(f)
PAL = CONTRACT["palette"]
W, H = R.W, R.H
FPS = CONTRACT["motion"]["fps"]
SAFE = (int(W * 0.08), CONTRACT["layout"]["vertical_safe_top_px"], W - int(W * 0.08), H - CONTRACT["layout"]["vertical_safe_bottom_px"])
S_SIDE = 600                  # px per body unit in a zoom-1 side shot (near lane)
V = 2300.0                    # sprint speed, px/s at zoom 1
CADENCE = 2.25                # stride cycles per second at full speed
VANISH = 1000                 # perspective vanishing row for the side view


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


# ---------------------------------------------------------------- motion helpers
def ramp_dist(t, v, tau=0.45):
    """Distance covered from standstill, accelerating to v with time constant tau."""
    if t <= 0:
        return 0.0
    return v * (t - tau * (1 - math.exp(-t / tau)))


def decel_dist(t, v, dur):
    """Distance while slowing from v to 0 over dur (quadratic)."""
    t = clamp(t, 0, dur)
    return v * (t - t * t / (2 * dur))


def lane_geom(lane):
    """Foot row and scale factor for a lane in the side view; lane 8 is the near lane, lower numbers are further."""
    y0, y1 = R.LANE_Y[lane], R.LANE_Y[lane + 1]
    foot = y0 + (y1 - y0) * 0.6 if lane < 8 else R.NEAR_FOOT
    return foot, (foot - VANISH) / (R.NEAR_FOOT - VANISH)


# ---------------------------------------------------------------- side shots
def side_shot(t, cam_x, actors, zoom=1.0, focus=None, marks=(), blur=0.0, board=None):
    """actors: dicts with X (world px), lane (8 = near), pose, facing, hand, baton, tone. Returns uint8 frame and the
    near-lane wrist positions keyed by actor name."""
    bg = R.side_background(cam_x, t)
    R.lane_marks(bg, cam_x, marks)
    if blur > 1:
        k = int(blur)
        bg[R.HORIZON - 460:] = cv2.blur(bg[R.HORIZON - 460:], (k, 1))
    wrists = {}
    for a in sorted(actors, key=lambda a: a.get("lane", 8)):
        lane = a.get("lane", 8)
        foot, k = lane_geom(lane)
        sx = (a["X"] - cam_x) * k + W / 2
        if zoom == 1.0:
            wr = R.draw_runner(bg, sx, int(foot), S_SIDE * k * a.get("scale", 1.0), a["pose"], facing=a.get("facing", 1),
                               hand=a.get("hand"), baton=a.get("baton", 0.0), tone=a.get("tone", 1.0) * (0.55 + 0.45 * k),
                               rim=a.get("rim", 1.0))
            if wr:
                wrists[a.get("name", "")] = wr
    fr = bg
    if zoom != 1.0:
        fx, fy = focus
        cw, ch = W / zoom, H / zoom
        x0 = clamp(fx - cw / 2, 0, W - cw)
        y0 = clamp(fy - ch / 2, 0, H - ch)
        crop = bg[int(y0):int(y0 + ch), int(x0):int(x0 + cw)]
        fr = cv2.resize(crop, (W, H), interpolation=cv2.INTER_LINEAR)
        fr = cv2.GaussianBlur(fr, (0, 0), 1.2 + zoom * 0.6)
        for a in sorted(actors, key=lambda a: a.get("lane", 8)):
            lane = a.get("lane", 8)
            foot, k = lane_geom(lane)
            sx = (a["X"] - cam_x) * k + W / 2
            ox, oy = (sx - x0) * zoom, (foot - y0) * zoom
            wr = R.draw_runner(fr, ox, int(oy), S_SIDE * k * zoom * a.get("scale", 1.0), a["pose"], facing=a.get("facing", 1),
                               hand=a.get("hand"), baton=a.get("baton", 0.0), tone=a.get("tone", 1.0), rim=a.get("rim", 1.0))
            if wr:
                wrists[a.get("name", "")] = wr
    if board:
        draw_board(fr, *board)
    return fr, wrists


def wrist_world(pose, X, facing=1):
    """Near-wrist position at zoom 1 in screen coords for a near-lane runner whose camera is at X (centre)."""
    J = R.joints(pose)
    wx, wy = J["wristA"]
    return W / 2 + facing * wx * S_SIDE, R.NEAR_FOOT - wy * S_SIDE


def draw_board(fr, left, right, flash=0.0, red=False):
    """The stadium board: a dark LED panel at the top of the frame, cold white digits; the leg label in red."""
    x0, y0, x1, y1 = 170, 462, 910, 582
    cv2.rectangle(fr, (x0 - 8, y0 - 8), (x1 + 8, y1 + 8), (20, 22, 30), -1)
    cv2.rectangle(fr, (x0, y0), (x1, y1), (6, 7, 11), -1)
    im = Image.fromarray(fr[y0:y1, x0:x1])
    d = ImageDraw.Draw(im)
    fl = R.font("Inter-Bold.otf", 50)
    fr_ = R.font("Inter-Bold.otf", 70)
    d.text((30, 34), left, font=fl, fill=(255, 92, 92) if not left.startswith("FINISH") else (240, 244, 255))
    col = (255, 120, 120) if red else (236, 242, 255)
    tw = d.textlength(right, font=fr_)
    d.text((x1 - x0 - 30 - tw, 22), right, font=fr_, fill=col)
    arr = np.asarray(im).astype(np.float32)
    # LED dot screen: darken a fine grid so the digits read as lamps
    grid = np.ones(arr.shape[:2], np.float32)
    grid[::4, :] = 0.55
    grid[:, ::4] = 0.55
    arr *= grid[..., None]
    fr[y0:y1, x0:x1] = arr.astype(np.uint8)
    glow = cv2.GaussianBlur(arr, (0, 0), 6) * (0.5 + 0.8 * flash)
    R.add_light(fr, glow * 0.6, x0, y0)


# ---------------------------------------------------------------- shot s1a: the feet
def shot_feet(t, dur):
    X = 400 + V * t
    phase = CADENCE * t
    cam = X + 80
    a = dict(name="A", X=X, pose=R.pose_sprint(phase), lane=8)
    fr, _ = side_shot(t, cam, [a], zoom=3.0, focus=(W / 2, 1560), blur=46)
    splashes(fr, t, phase, cam, X)
    return fr


def foot_strikes(phase_fn, t_now, look_back=0.6, step=1 / 120):
    """Times in the last look_back seconds when the grounded foot switched (a strike)."""
    out = []
    prev = None
    tt = max(0.0, t_now - look_back)
    while tt <= t_now:
        J = R.joints(R.pose_sprint(phase_fn(tt)))
        g = "A" if min(J["ankleA"][1], J["toeA"][1]) < min(J["ankleB"][1], J["toeB"][1]) else "B"
        if prev is not None and g != prev:
            out.append((tt, g))
        prev = g
        tt += step
    return out


def splashes(fr, t, phase, cam, X):
    """Droplets thrown back and up from each foot strike, catching the floodlight."""
    lay = np.zeros(fr.shape[:2], np.float32)
    for ts, g in foot_strikes(lambda u: CADENCE * u, t):
        age = t - ts
        J = R.joints(R.pose_sprint(CADENCE * ts))
        # the strike point in output coords: the toe at that moment, carried back by the camera since
        zoom, fy = 3.0, 1560
        y0 = fy - H / zoom / 2
        sx = (W / 2 + (X - V * age - cam) + J["toe" + g][0] * S_SIDE - (W / 2 - W / zoom / 2)) * zoom
        sy = (R.NEAR_FOOT - y0) * zoom
        rnd = random.Random(int(ts * 1000))
        for _ in range(26):
            vx, vy = rnd.uniform(-900, -200), rnd.uniform(500, 1500)
            px = sx + vx * age - V * zoom * age * 0.0
            py = sy - (vy * age - 2600 * age * age)
            if py > sy + 10:
                continue
            r = rnd.uniform(5, 14) * (1 - age / 0.6)
            cv2.circle(lay, (int(px), int(py)), max(1, int(r)), 1.0 * (1 - age / 0.6), -1, cv2.LINE_AA)
    lay = cv2.GaussianBlur(lay, (0, 0), 1.2)
    R.comp(fr, (215, 228, 255), np.clip(lay * 1.0, 0, 1))


# ---------------------------------------------------------------- shot s1b/s4a: the hand
def shot_hand(t, dur, baton_at=None):
    """Tight on the near hand reaching forward. Without a baton the hand closes on air; with one, the baton forms
    in the open hand (purple sparks converge) and the fist closes on it."""
    v = V * (0.55 - 0.25 * clamp(t / dur)) if baton_at is None else V * 0.5
    X = 2000 + v * t
    phase = CADENCE * 0.6 * t + 0.25
    close_at = dur * 0.55 if baton_at is None else baton_at + 0.55
    hand = "open" if t < close_at else "closed"
    pose = R.pose_reach(phase)
    pose["sA"], pose["eA"] = 1.42 + 0.03 * math.sin(t * 7), 0.06
    wx, wy = wrist_world(pose, X)
    zoom = 4.0
    bv = 0.0 if baton_at is None else clamp((t - baton_at) / 0.5)
    a = dict(name="A", X=X, pose=pose, lane=8, hand=hand, baton=bv if t >= close_at else 0.0)
    fr, wr = side_shot(t, X, [a], zoom=zoom, focus=(wx + 30, wy + 20), blur=10)
    if baton_at is not None and wr.get("A"):
        hx, hy = wr["A"]
        q = clamp((t - baton_at) / 0.6)
        if 0 < q < 1 or (t < close_at and t >= baton_at):
            # the baton forming in the open palm before the fist closes
            sparks(fr, (hx + 40, hy - 10), t - baton_at)
            if t >= baton_at and t < close_at:
                R.draw_baton(fr, (hx, hy), -0.05, 1, S_SIDE * zoom, clamp((t - baton_at) / 0.5))
    return fr


def sparks(fr, c, age):
    if age < 0 or age > 1.0:
        return
    lay = np.zeros(fr.shape[:2], np.float32)
    rnd = random.Random(5)
    for _ in range(60):
        ang = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(160, 420)
        q = clamp(age / rnd.uniform(0.4, 0.8))
        r = r0 * (1 - R.ease_out(q))
        x, y = c[0] + math.cos(ang) * r, c[1] + math.sin(ang) * r
        cv2.circle(lay, (int(x), int(y)), int(2 + 3 * (1 - q)), 1.0 - q * 0.8, -1, cv2.LINE_AA)
    lay = cv2.GaussianBlur(lay, (0, 0), 1.5)
    R.add_light(fr, lay[..., None] * np.array(R.BATON, np.float32) * 1.4)


# ---------------------------------------------------------------- shot s1c: the miss, wide
def shot_miss_wide(t, dur):
    X0 = 6000
    q = clamp(t / dur)
    X = X0 + decel_dist(t, V * 0.45, dur)
    pose = R.pose_stumble(clamp(t / (dur * 0.95)))
    a = dict(name="A", X=X, pose=pose, lane=8, hand="closed")
    b = dict(name="B", X=X0 + 900, lane=6, pose=R.pose_look_up(), facing=-1)
    zoom = 1.0 + 0.08 * R.smooth(q)
    fr, _ = side_shot(t, X0 + 380, [b, a], zoom=zoom, focus=(W / 2, 1180), marks=[(X0 - 60, "zone"), (X0 + 260, "zone")])
    return fr


# ---------------------------------------------------------------- s2: three legs that all start from zero
LEG_DUR = 7.0 / 3
SPLITS = (10.41, 10.32, 10.19)
RECEIVERS = ("turned", "blocks", "wrong_lane")
MISS_AT = 1.62


def leg_state(t, i):
    f = (1.0, 1.07, 1.14)[i]
    v = V * f
    base = 20000 + i * 9000
    out = 0.42
    if t < MISS_AT:
        X = base + ramp_dist(t - out * 0.4, v, 0.4)
    else:
        X = base + ramp_dist(MISS_AT - out * 0.4, v, 0.4) + decel_dist(t - MISS_AT, v * 0.9, LEG_DUR - MISS_AT)
    return X, v, base


def shot_leg(t, dur, i):
    X, v, base = leg_state(t, i)
    phase = CADENCE * (1.0 + 0.07 * i) * t
    if t < 0.42:
        pose = R.pose_blend(R.pose_crouch(), R.pose_sprint(phase), R.smooth(t / 0.42))
    elif t < MISS_AT - 0.3:
        pose = R.pose_sprint(phase)
    elif t < MISS_AT + 0.12:
        pose = R.pose_reach(phase)
    else:
        pose = R.pose_stumble(clamp((t - MISS_AT - 0.12) / (LEG_DUR - MISS_AT - 0.1)))
    hand = "open" if MISS_AT - 0.3 <= t < MISS_AT else ("closed" if t >= MISS_AT else None)
    zone = leg_state(MISS_AT, i)[0] + 150
    kind = RECEIVERS[i]
    if kind == "turned":
        recv = dict(name="B", X=zone + 240, lane=8, pose=R.pose_look_up(), facing=-1)
    elif kind == "blocks":
        rq = clamp((t - MISS_AT - 0.25) / 0.5)
        rp = R.pose_blend(R.pose_crouch(), R.pose_stand(), R.smooth(rq) * 0.5)
        recv = dict(name="B", X=zone + 330, lane=8, pose=rp)
    else:
        recv = dict(name="B", X=zone + 140, lane=6, pose=R.pose_stand(arms=0.25))
    lead = 160 if t < MISS_AT - 0.2 else 160 + 220 * R.smooth((t - MISS_AT + 0.2) / 0.5)
    cam = min(X + lead, zone + 260)
    # the board: the split runs, freezes red at the miss, then the counter stays on leg 1
    clock = SPLITS[i] * clamp(t / MISS_AT)
    board = ("LEG 1 OF 4", f"{clock:5.2f}", 1.0 if 0 <= t - MISS_AT < 0.4 else 0.0, t >= MISS_AT)
    speed_px = v / FPS if t < MISS_AT else 0
    fr, _ = side_shot(t, cam, [recv, dict(name="A", X=X, pose=pose, lane=8, hand=hand)], marks=[(zone - 400, "zone"), (zone + 90, "zone")],
                      blur=min(40, speed_px * 0.6), board=board)
    return fr


# ---------------------------------------------------------------- s3: overhead
OV_LANES = 8
ABANDONED = 5


def overhead_sim(lane, t):
    """State of one lane at time t in the overhead: a list of (d, state, phase, tone) for its visible runners and the
    times of failed hand-offs (for the red pulse)."""
    Q = R.lap_length(lane) / 4
    rnd = random.Random(lane * 7 + 3)
    v = rnd.uniform(380, 470)
    start_q = rnd.randint(0, 3)
    t0 = -rnd.uniform(0.0, 2.2)
    if lane == ABANDONED:
        d = Q * start_q + Q * 0.18
        return [(d, "sit", 0.0, 1.0), (Q * (start_q + 1), "stand", 0.0, 0.8)], []
    out, misses = [], []
    leg = 0
    T = t0
    while True:
        # arrival time of this leg: solve ramp_dist(T_a) = Q
        lo, hi = 0.0, 10.0
        for _ in range(30):
            mid = (lo + hi) / 2
            if ramp_dist(mid, v, 0.5) < Q:
                lo = mid
            else:
                hi = mid
        arrive = T + hi
        delay = rnd.uniform(0.8, 1.6)
        zone_d = Q * (start_q + leg)
        if t < arrive:
            out.append((zone_d + ramp_dist(t - T, v, 0.5), "run", (t - T) * 2.6, 1.0))
            out.append((zone_d + Q, "stand", 0.0, 0.85))
            return out, misses
        misses.append((arrive, zone_d + Q))
        if t < arrive + delay:
            out.append((zone_d + Q + 2, "stand", 0.0, 1.0))
            out.append((zone_d + Q + 18, "stand", 0.0, 0.85))
            return out, misses
        # the old runner lingers at the zone, fading
        if t < arrive + delay + 2.5:
            out.append((zone_d + Q - 4, "stand", 0.0, 1 - (t - arrive - delay) / 2.5))
        T = arrive + delay
        leg += 1


def shot_overhead(t, dur):
    S = R.OV_SCALE
    base = R.overhead_base()
    focus_lane = 3
    runs, _ = overhead_sim(focus_lane, 0.0)
    (fx, fy), _ = R.lane_point(focus_lane, runs[0][0])
    q = clamp(t / 2.4)
    z = 3.2 + (1.04 - 3.2) * spring(q)
    z = max(1.0, z)
    cx = R.lerp(fx, W / 2, R.smooth(q))
    cy = R.lerp(fy, H / 2, R.smooth(q))
    cw, ch = W / z, H / z
    x0 = clamp(cx - cw / 2, 0, W - cw)
    y0 = clamp(cy - ch / 2, 0, H - ch)
    crop = base[int(y0 * S):int((y0 + ch) * S), int(x0 * S):int((x0 + cw) * S)].copy()
    pulses = np.zeros(crop.shape[:2], np.float32)
    for lane in range(OV_LANES):
        items, misses = overhead_sim(lane, t + 4.0)
        for d, state, ph, tone in items:
            (px, py), hd = R.lane_point(lane, d)
            if state == "stand":
                hd += {0: 2.6, 1: -2.0, 2: 1.4}[lane % 3]       # standing turned every which way
            R.overhead_runner(crop, (px - x0, py - y0), hd, ph, S, state=state, tone=tone)
            if state == "run":
                (tx, ty), _ = R.lane_point(lane, d - 40)
                cv2.line(crop, (int((tx - x0) * S), int((ty - y0) * S)), (int((px - x0) * S), int((py - y0) * S)), (90, 100, 120), 2, cv2.LINE_AA)
        for at, md in misses:
            age = t + 4.0 - at
            if 0 <= age < 0.9:
                (px, py), _ = R.lane_point(lane, md)
                cv2.circle(pulses, (int((px - x0) * S), int((py - y0) * S)), int((8 + 30 * age) * S), 1.0 - age / 0.9, max(1, int(2 * S)), cv2.LINE_AA)
    fr = cv2.resize(crop, (W, H), interpolation=cv2.INTER_AREA if z < 2 else cv2.INTER_LINEAR)
    pul = cv2.resize(pulses, (W, H))
    R.comp(fr, R.WARN, np.clip(pul * 0.8, 0, 1))
    return fr


# ---------------------------------------------------------------- s4: clean hand-offs
def handoff_shot(t, dur, ex_at, leg_from, leg_to, base, show_from_baton=True):
    """Incoming runner (with baton) catches a receiver who is already running; the baton passes at ex_at."""
    vin = V * 1.02
    X_in = base + vin * t
    if t > ex_at:
        X_in = base + vin * ex_at + decel_dist(t - ex_at, vin, 1.6)
    # receiver: already moving, matched so they meet at ex_at, then accelerates past
    meet = base + vin * ex_at + 120
    vr = V * 0.82
    X_r = meet - vr * (ex_at - t) if t < ex_at else meet + vr * (t - ex_at) + 0.5 * 900 * (t - ex_at) ** 2
    ph_in = CADENCE * t
    ph_r = CADENCE * 0.95 * t + 0.4
    pin = R.pose_reach(ph_in) if ex_at - 0.45 < t < ex_at + 0.1 else (R.pose_sprint(ph_in) if t <= ex_at else R.pose_stumble(0.0))
    if t > ex_at + 0.1:
        pin = R.pose_blend(R.pose_sprint(ph_in), R.pose_stand(), R.smooth((t - ex_at) / 1.4))
    pr = R.pose_receive(ph_r) if ex_at - 0.6 < t < ex_at + 0.05 else R.pose_sprint(ph_r)
    has_in = 1.0 if t < ex_at else 0.0
    has_r = 1.0 if t >= ex_at else 0.0
    cam = R.lerp((X_in + X_r) / 2, X_r + 120, R.smooth((t - ex_at + 0.2) / 0.8))
    clock = (20.0 + base / 10000.0) if False else None
    tg = SHOT_START[current_shot[0]] + t
    race = race_clock(tg)
    board = (f"LEG {leg_from if t < ex_at else leg_to} OF 4", f"{race:5.2f}", 1.0 if 0 <= t - ex_at < 0.35 else 0.0, False)
    actors = [dict(name="R", X=X_r, pose=pr, lane=8, hand="open" if ex_at - 0.6 < t < ex_at else ("closed" if t >= ex_at else None), baton=has_r),
              dict(name="A", X=X_in, pose=pin, lane=8, hand="closed", baton=has_in if show_from_baton else 0.0)]
    fr, wr = side_shot(t, cam, actors, marks=[(meet - 350, "zone"), (meet + 300, "zone")], blur=24, board=board)
    if abs(t - ex_at) < 0.25 and wr.get("R"):
        flash = np.zeros(fr.shape[:2], np.float32)
        hx, hy = wr["R"]
        cv2.circle(flash, (int(hx), int(hy)), 40, 1.0, -1)
        flash = cv2.GaussianBlur(flash, (0, 0), 30) * (1 - abs(t - ex_at) / 0.25)
        R.add_light(fr, flash[..., None] * np.array(R.BATON, np.float32) * 1.2)
    return fr


def race_clock(tg):
    return 0.44 + (tg - 20.0) * 2.2


# ---------------------------------------------------------------- s5: away and home
def shot_away(t, dur):
    X = 90000 + V * 1.05 * t
    phase = CADENCE * 1.05 * t
    others = []
    for lane, vf, stop in ((7, 0.86, None), (6, 0.8, 1.6), (5, 0.9, None), (3, 0.78, None), (2, 0.84, 2.2)):
        x0 = 90000 - 260 + 30 * lane
        if stop is None or t < stop:
            Xo, po = x0 + V * vf * t, R.pose_sprint(CADENCE * vf * t + lane * 0.13)
        else:
            Xo = x0 + V * vf * stop + decel_dist(t - stop, V * vf, 0.9)
            po = R.pose_stumble(clamp((t - stop) / 1.2))
        others.append(dict(name=f"o{lane}", X=Xo, lane=lane, pose=po, tone=0.8))
    me = dict(name="D", X=X, lane=8, pose=R.pose_sprint(phase), hand="closed", baton=1.0)
    tg = SHOT_START["s5a"] + t
    board = ("LEG 4 OF 4", f"{race_clock(tg):5.2f}", 0.0, False)
    fr, _ = side_shot(t, X + 120, others + [me], blur=34, board=board)
    return fr


FINISH_CROSS = 1.5


def shot_finish(t, dur):
    FX = 200000
    v = V * 1.05
    X = FX - v * FINISH_CROSS + v * t if t < FINISH_CROSS else FX + decel_dist(t - FINISH_CROSS, v, 2.6)
    phase = CADENCE * 1.05 * t
    pose = R.pose_sprint(phase) if t < FINISH_CROSS else R.pose_blend(R.pose_sprint(phase), R.pose_stand(arms=0.3), R.smooth((t - FINISH_CROSS) / 1.6))
    tg = SHOT_START["s5b"] + t
    stop = race_clock(SHOT_START["s5b"] + FINISH_CROSS)
    if t < FINISH_CROSS:
        board = ("LEG 4 OF 4", f"{race_clock(tg):5.2f}", 0.0, False)
    else:
        board = ("FINISH", f"{stop:5.2f}", 1.0 if t - FINISH_CROSS < 0.5 else 0.25, False)
    q = R.smooth((t - FINISH_CROSS - 0.3) / 2.2)
    me = dict(name="D", X=X, lane=8, pose=pose, hand="closed", baton=1.0)
    others = [dict(name="o7", X=FX - 900 + V * 0.85 * t, lane=6, pose=R.pose_sprint(CADENCE * 0.85 * t), tone=0.7)]
    cam = X + 90                      # track the runner so the line slides in under the baton as the clock stops
    if q <= 0:
        fr, _ = side_shot(t, cam, others + [me], marks=[(FX, "finish")], board=board)
    else:
        J = R.joints(pose)
        wx = X - cam + W / 2 + J["wristA"][0] * S_SIDE
        wy = R.NEAR_FOOT - J["wristA"][1] * S_SIDE
        fr, _ = side_shot(t, cam, others + [me], zoom=1.0 + 1.1 * q, focus=(R.lerp(W / 2, wx, q), R.lerp(H / 2, wy, q)),
                          marks=[(FX, "finish")], board=board if q < 0.35 else None)
    return fr


# ---------------------------------------------------------------- end card
def end_card(last, t):
    p = R.ease_out(t / 1.0)
    bg = Image.fromarray(last).convert("RGBA").filter(ImageFilter.GaussianBlur(int(16 * p)))
    bg.alpha_composite(Image.new("RGBA", bg.size, rgb(PAL["background"]) + (int(220 * p),)))
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W * 0.12, H * 0.28, W * 0.88, H * 0.72), fill=rgb(PAL["primary"]) + (int(120 * p),))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(130)))
    d = ImageDraw.Draw(bg)
    sizes = CONTRACT["type"]["vertical"]
    a = R.ease_out((t - 0.5) / 0.6)
    if a > 0:
        hat = Image.open(os.path.join(ROOT, "motifs", "logo-hat-light.png")).convert("RGBA")
        hh = int(H * 0.11)
        hat = hat.resize((int(hat.width * hh / hat.height), hh), Image.LANCZOS)
        hat.putalpha(hat.split()[3].point(lambda v: int(v * a)))
        hy = H * 0.34
        bg.alpha_composite(hat, (int(W / 2 - hat.width / 2), int(hy)))
        fh = R.font("Inter-Bold.otf", int(sizes["headline"] * 1.5))
        tw = d.textlength("Dandy", font=fh)
        ty = hy + hh + 40
        d.text((W / 2 - tw / 2, ty), "Dandy", font=fh, fill=rgb(PAL["text"]) + (int(255 * a),))
        yy = ty + fh.size * 1.1 + 60
        for i, line in enumerate(CONTRACT["copy_rules"]["end_card_lines"]):
            b = R.ease_out((t - 0.9 - 0.25 * i) / 0.5)
            fl = R.font("Inter-Medium.otf", sizes["body" if i == 0 else "caption"])
            lw = d.textlength(line, font=fl)
            d.text((W / 2 - lw / 2, yy), line, font=fl, fill=(rgb(PAL["accent_gold"]) if i == 1 else rgb(PAL["soft"])) + (int(255 * b),))
            yy += fl.size * 1.1 + 50
    return np.asarray(bg.convert("RGB"))


# ---------------------------------------------------------------- timeline
SHOTS = [
    ("s1a", 1.3, lambda t, d: shot_feet(t, d)),
    ("s1b", 0.85, lambda t, d: shot_hand(t, d)),
    ("s1c", 0.85, lambda t, d: shot_miss_wide(t, d)),
    ("s2a", LEG_DUR, lambda t, d: shot_leg(t, d, 0)),
    ("s2b", LEG_DUR, lambda t, d: shot_leg(t, d, 1)),
    ("s2c", LEG_DUR, lambda t, d: shot_leg(t, d, 2)),
    ("s3", 10.0, lambda t, d: shot_overhead(t, d)),
    ("s4a", 2.0, lambda t, d: shot_hand(t, d, baton_at=0.45)),
    ("s4b", 4.75, lambda t, d: handoff_shot(t, d, 1.9, 1, 2, 120000)),
    ("s4c", 5.25, lambda t, d: handoff_shot(t, d, 1.5, 2, 3, 150000)),
    ("s5a", 3.5, lambda t, d: shot_away(t, d)),
    ("s5b", 4.5, lambda t, d: shot_finish(t, d)),
    ("end", 4.5, None),
]
SHOT_START = {}
_acc = 0.0
for _id, _d, _ in SHOTS:
    SHOT_START[_id] = _acc
    _acc += _d
TOTAL = _acc
current_shot = [None]

CAPTIONS = [(4.0, 6.6, "Every session is brilliant."), (6.8, 9.6, "Every session starts cold."),
            (11.0, 12.8, "Look at the whole track."), (13.0, 14.8, "Every lane drops it."), (15.0, 16.6, "Some stop running."),
            (16.8, 19.6, "Nobody is carrying what the last runner knew."), (21.4, 23.2, "Dandy is the baton."),
            (23.4, 27.4, "It holds where the project is, what changed, and what's next."),
            (27.6, 29.8, "So the next runner starts at speed."), (29.9, 31.8, "Not from the blocks."),
            (34.0, 38.8, "Stop restarting. Start handing off.")]
BOARD_TEXT = ["LEG 1 OF 4", "LEG 2 OF 4", "LEG 3 OF 4", "LEG 4 OF 4", "FINISH"]

# finish-pass settings per shot: (shake, bloom, grain, vignette, drift)
LOOK = dict(default=(0.0, 0.9, 3.2, 0.42, 0.8), s1a=(5.0, 1.0, 3.4, 0.45, 0.6), s1c=(3.0, 0.9, 3.2, 0.42, 0.8),
            s3=(0.0, 0.8, 3.0, 0.4, 0.5), s4a=(0.0, 1.1, 3.0, 0.45, 0.5), end=(0.0, 0.6, 2.6, 0.3, 0.4))


def draw_caption(img, tg):
    cue = next((c for c in CAPTIONS if c[0] <= tg < c[1]), None)
    if cue is None:
        return
    a = min(1.0, (tg - cue[0]) / 0.25, (cue[1] - tg) / 0.2)
    fnt = R.font("Inter-Bold.otf", int(CONTRACT["type"]["vertical"]["body"] * 0.95))
    d = ImageDraw.Draw(img)
    words, lines, cur = cue[2].split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if d.textlength(trial, font=fnt) <= SAFE[2] - SAFE[0] - 40 or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    lh = fnt.size * 1.18
    pad = 20
    y = SAFE[3] - len(lines) * (lh + pad * 0.6) - 10
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=fnt)
        x, yy = W / 2 - tw / 2, y + i * (lh + pad * 0.6)
        d.rounded_rectangle((x - pad, yy - pad * 0.55, x + tw + pad, yy + lh + pad * 0.3), radius=14, fill=(6, 8, 14, int(190 * a)))
        d.text((x, yy), line, font=fnt, fill=(243, 238, 255, int(255 * a)))


def copy_qa():
    rules = CONTRACT["copy_rules"]
    problems = []
    for tx in [c[2] for c in CAPTIONS] + BOARD_TEXT:
        for ch in rules["banned_characters"]:
            if ch in tx:
                problems.append(f"banned character in {tx!r}")
        for ph in rules["banned_phrases"] + ["state layer"]:
            if ph in tx.lower():
                problems.append(f"banned phrase {ph!r} in {tx!r}")
        if len(tx.split()) > CONTRACT["type"]["max_words_on_screen"]:
            problems.append(f"too many words: {tx!r}")
    return problems


def sound_plan():
    """Events and footfall runs, in global seconds, from the same timeline as the pictures."""
    st = SHOT_START
    ev = [(0.0, "pistol", 0.9, -0.2), (st["s1b"] + 0.85 * 0.55, "scuff", 0.35, 0.1), (st["s1c"] + 0.1, "scuff", 0.55, 0.0),
          (st["s1c"] + 0.4, "breath", 0.3, 0.0)]
    runs = [(0.05, st["s1b"], 4.5, 0.75), (st["s1b"], st["s1c"] + 0.4, 3.0, 0.4)]
    for i, sid in enumerate(("s2a", "s2b", "s2c")):
        s0 = st[sid]
        runs.append((s0 + 0.35, s0 + MISS_AT, 4.4 * (1 + 0.07 * i), 0.5))
        ev += [(s0 + MISS_AT + 0.05, "scuff", 0.45, 0.0), (s0 + MISS_AT + 0.35, "breath", 0.3, 0.1), (s0 + MISS_AT + 0.05, "beep", 0.12, 0.0)]
    ev += [(st["s3"] - 0.1, "whoosh", 0.4, 0.0)]
    runs.append((st["s3"], st["s4a"], 9.0, 0.08))
    ev += [(st["s4a"] + 0.45, "tone", 0.38, 0.0), (st["s4a"] + 1.2, "pistol", 0.75, 0.2)]
    runs += [(st["s4b"], st["s4b"] + 4.75, 8.8, 0.38), (st["s4c"], st["s4c"] + 5.25, 9.2, 0.4)]
    ev += [(st["s4b"] + 1.9, "slap", 0.55, 0.0), (st["s4c"] + 1.5, "slap", 0.55, 0.0)]
    for k in range(6):
        ev.append((st["s4b"] + 0.4 + k * 1.6, "breath", 0.12, 0.0))
    runs += [(st["s5a"], st["s5b"] + FINISH_CROSS, 4.7, 0.42), (st["s5b"] + FINISH_CROSS, st["s5b"] + FINISH_CROSS + 1.6, 3.0, 0.3)]
    ev += [(st["s5b"] + FINISH_CROSS, "beep", 0.4, 0.0), (st["s5b"] + FINISH_CROSS + 0.3, "breath", 0.28, 0.0),
           (st["end"] + 0.5, "tone", 0.25, 0.0)]
    return ev, runs


def render(preview=False, stills=False, final=False):
    out = os.path.join(VIDEO, "out")
    os.makedirs(out, exist_ok=True)
    problems = copy_qa()
    report = dict(canvas="vertical", look="night-track", duration=TOTAL, problems=problems,
                  shots=[dict(id=s[0], start=round(SHOT_START[s[0]], 2), duration=round(s[1], 2)) for s in SHOTS])
    with open(os.path.join(out, "qa-relay-vertical.json"), "w") as f:
        json.dump(report, f, indent=2)
    if problems:
        print("QA FAILED:", problems)
        return False
    tmp = tempfile.mkdtemp(prefix="dandy-relay-")
    step = 3 if preview else 1
    n = 0
    last = None
    for sid, dur, fn in SHOTS:
        current_shot[0] = sid
        frames = int(round(dur * FPS))
        picks = {int(frames * 0.25), int(frames * 0.7)}
        for i in range(frames):
            if i % step:
                continue
            if stills and i not in picks:
                continue
            t = i / FPS
            tg = SHOT_START[sid] + t
            if fn is None:
                fr = end_card(last, t)
            else:
                fr = fn(t, dur)
                last = fr
            sh, bl, gr, vg, dr = LOOK.get(sid, LOOK["default"])
            img = finish(Image.fromarray(fr).convert("RGBA"), t, tg, shake=sh * (1 if sid != "s1c" else max(0, 1 - t / 0.4)),
                         bloom=bl, grain=gr, vignette=vg, drift=dr, zoom=1.03)
            draw_caption(img, tg)
            if stills:
                img.convert("RGB").save(os.path.join(out, f"relay-{sid}-{t:04.2f}.png"))
                continue
            img.convert("RGB").save(os.path.join(tmp, f"f{n:06d}.png"), compress_level=1)
            n += 1
    if stills:
        print("stills in", out)
        return True
    wav = os.path.join(out, "relay-bed.wav")
    ev, runs = sound_plan()
    sfx_relay.build_bed(ev, runs, TOTAL, wav, crowd_swell=SHOT_START["s5b"] + FINISH_CROSS)
    mp4 = os.path.join(out, "07-relay-vertical.mp4")
    fps = FPS // step
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "f%06d.png"), "-i", wav,
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18" if final else "20", "-preset", "slow" if final else "medium",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    print(f"rendered {mp4} ({n} frames, {TOTAL:.1f} s)")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if render(a.preview, a.stills, a.final) else 1)

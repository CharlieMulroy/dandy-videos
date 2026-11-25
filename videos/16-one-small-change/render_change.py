"""Video 16, One Small Change: what propagation is, in the Void Stage look (render/stage.py).

First draft, kept for reference; the current look is city/render_city.py.

Usage:  python3 videos/16-one-small-change/render_change.py [--preview] [--stills] [--final]

Frame one is the thumbnail: a still title card (also saved as out/16-thumbnail.png). Then: the agent renames a
column on Bookings and leaves; the three pieces that were reading it quietly break; rewind; the same rename with
Dandy, where the change runs down each connection, the three pieces are updated and flagged, and the agent is
told what it touched; the flags clear while Dandy Man tips his hat; end card with Dandy Man.

The map is a corner of the booking app from videos 10 to 12: Bookings and the three pieces that read from it.
Timings below are placeholders; voiceover/stage.json ("durations", "file", "lines", "cues") replaces them once
Charlie records.
"""
import argparse
import math
import os
import sys

from PIL import ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "render"))
import stage as S  # noqa: E402
from stage import clamp, ease_out, smooth, lerp  # noqa: E402

STILL = 0.5
TITLE = ["One small", "change"]
TOP = "Bookings"
KIDS = ["Reminders", "Payments", "Reports"]
ORDER = [TOP] + KIDS
P = {"Bookings": (405, 290), "Reminders": (86, 560), "Payments": (405, 560), "Reports": (724, 560)}
OLD, NEW = "date", "start_time"
FS = 38                       # field tag size
OUT_TAG = (850, 355)          # the column Bookings puts out, beside it
IN_Y = 778                    # the column each piece below takes in, under it
BUS_Y = 490
TOLD = (221, 355, "3 touched")
PHRASES = {"b1": ("Done in ten seconds", 2.9), "b2": ("Nothing errors", 5.0), "b3": ("Propagation", 0.5),
           "b4": ("The change travels", 7.2), "b5": ("Nothing missed", 5.0), "b6": ("Nothing caught off guard", 1.4)}
TITLE_OUT = 2.1

# b1: the rename
B1_NODES, B1_EDGES, B1_TAG = [0.15, 0.45, 0.6, 0.75], 0.8, 1.0
B1_ARRIVE, B1_CH, B1_LEAVE = 1.6, 2.4, 3.5
# b2: what it didn't know
B2_IN = [1.4, 1.7, 2.0]
B2_BAD = [6.3, 6.6, 6.9]
B2_RED = 8.5
# b3: rewind
B3_BACK, B3_TAG = 0.4, 0.9
# b4: the same change, with Dandy
B4_IN, B4_OUT, B4_ARRIVE, B4_CH, B4_RIP, B4_LAND = 2.8, 4.1, 5.6, 6.2, 7.4, 8.2
# b5: updated or flagged, and the agent is told
B5_FLAG = [2.2, 2.45, 2.7]
B5_BACK, B5_TOLD = 3.8, 4.7
# b6: settled
B6_CLEAR = [0.5, 0.8, 1.1]
B6_TIP = 2.2

_vo = os.path.join(HERE, "voiceover", "stage.json")
if os.path.exists(_vo):
    import json as _json
    with open(_vo) as _f:
        _c = _json.load(_f).get("cues", {})
    TITLE_OUT = _c.get("title_out", TITLE_OUT)
    PHRASES = {k: (PHRASES[k][0], _c.get("phrases", {}).get(k, PHRASES[k][1])) for k in PHRASES}
    B1_TAG, B1_ARRIVE, B1_CH, B1_LEAVE = _c.get("b1", (B1_TAG, B1_ARRIVE, B1_CH, B1_LEAVE))
    B2_IN, B2_BAD, B2_RED = _c.get("b2_in", B2_IN), _c.get("b2_bad", B2_BAD), _c.get("b2_red", B2_RED)
    B3_BACK, B3_TAG = _c.get("b3", (B3_BACK, B3_TAG))
    B4_IN, B4_OUT, B4_ARRIVE, B4_CH, B4_RIP, B4_LAND = _c.get("b4", (B4_IN, B4_OUT, B4_ARRIVE, B4_CH, B4_RIP, B4_LAND))
    B5_FLAG = _c.get("b5_flag", B5_FLAG)
    B5_BACK, B5_TOLD = _c.get("b5", (B5_BACK, B5_TOLD))
    B6_CLEAR, B6_TIP = _c.get("b6_clear", B6_CLEAR), _c.get("b6_tip", B6_TIP)


# ---------------------------------------------------------------- geometry
def center(name):
    x, y = P[name]
    return x + S.NODE_W / 2, y + S.NODE_H / 2


def perch(name):
    return P[name][0] + 26, P[name][1] + 4


def in_tag(name):
    return center(name)[0], IN_Y


def tag_box(cx, cy, text):
    return S.pill_box(cx, cy, text, FS)


def route(name):
    """The connection from Bookings down to one of the pieces below: down, across, down."""
    cx = center(name)[0]
    tx = center(TOP)[0]
    return [(tx, P[TOP][1] + S.NODE_H), (tx, BUS_Y), (cx, BUS_Y), (cx, P[name][1])]


def _segs(pts):
    return [(a, b, math.hypot(b[0] - a[0], b[1] - a[1])) for a, b in zip(pts, pts[1:])]


def along(pts, u):
    segs = _segs(pts)
    left = clamp(u) * sum(s[2] for s in segs)
    for a, b, ln in segs:
        if left <= ln and ln > 0:
            return lerp(a[0], b[0], left / ln), lerp(a[1], b[1], left / ln)
        left -= ln
    return pts[-1]


def partial(pts, p):
    segs = _segs(pts)
    left = clamp(p) * sum(s[2] for s in segs)
    out = [pts[0]]
    for a, b, ln in segs:
        if ln == 0:
            continue
        if left >= ln:
            out.append(b)
            left -= ln
        else:
            out.append((lerp(a[0], b[0], left / ln), lerp(a[1], b[1], left / ln)))
            break
    return out


def path(t, keys):
    if t <= keys[0][0]:
        return keys[0][1], keys[0][2]
    for (t0, x0, y0), (t1, x1, y1) in zip(keys, keys[1:]):
        if t <= t1:
            q = smooth((t - t0) / (t1 - t0))
            return lerp(x0, x1, q), lerp(y0, y1, q)
    return keys[-1][1], keys[-1][2]


def bob(tg):
    return max(0.0, tg - STILL)


# ---------------------------------------------------------------- pieces drawn only here
def draw_route(img, name, p=1.0, hot=0.0, dim=0.0):
    if p <= 0:
        return
    pts = partial(route(name), p)
    if len(pts) < 2:
        return
    d = ImageDraw.Draw(img, "RGBA")
    col = S.mix(S.mix(S.SOFT, (255, 255, 255), hot), (96, 84, 120), dim)
    flat = [c for pt in pts for c in pt]
    d.line(flat, fill=S.PURPLE_HI + (int((70 + 110 * hot) * (1 - 0.6 * dim)),), width=12, joint="curve")
    d.line(flat, fill=col + (235,), width=4, joint="curve")
    if p >= 0.98:
        x1, y1 = pts[-1]
        d.ellipse((x1 - 7, y1 - 7, x1 + 7, y1 + 7), fill=col + (255,))


def route_pulse(img, name, u, color=(255, 255, 255)):
    if u <= 0 or u >= 1:
        return
    x, y = along(route(name), u)
    S.put_sprite(img, S.HALO, x, y, scale=0.34, alpha=0.95)
    ImageDraw.Draw(img, "RGBA").ellipse((x - 9, y - 9, x + 9, y + 9), fill=color + (255,))


def tag(img, cx, cy, text, alpha=1.0, glow=0.0, bad=0.0):
    """A column name as a small tag. glow lights it up; bad strikes it through (it no longer matches)."""
    if alpha <= 0.01:
        return
    if glow > 0:
        S.put_sprite(img, S.GLOW_P, cx, cy, scale=0.62, alpha=0.9 * glow * alpha)
    d = ImageDraw.Draw(img, "RGBA")
    b = tag_box(cx, cy, text)
    a = int(255 * alpha)
    outline = S.mix(S.mix(S.SOFT, (255, 255, 255), 0.7 * glow), S.WARN, bad)
    fill = S.mix(S.mix(S.VOID, S.CARD, 0.7), S.PURPLE, 0.45 * glow)
    d.rounded_rectangle(b, radius=(b[3] - b[1]) / 2, fill=fill + (int(240 * alpha),), outline=outline + (a,), width=3)
    fnt = S.font("Inter-SemiBold.otf", FS)
    tw = fnt.getlength(text)
    d.text((cx - tw / 2, cy - FS * 0.62), text, font=fnt, fill=S.mix(S.TEXT, (150, 136, 176), 0.8 * bad) + (a,))
    if bad > 0:
        x0 = cx - tw / 2 - 8
        d.line((x0, cy + 2, x0 + (tw + 16) * clamp(bad), cy + 2), fill=S.WARN + (a,), width=4)


def swap(img, cx, cy, old, new, t, at):
    """One tag turning into another at time `at`."""
    if t < at:
        tag(img, cx, cy, old)
        return
    tag(img, cx, cy, old, alpha=1 - ease_out((t - at) / 0.18))
    tag(img, cx, cy, new, alpha=ease_out((t - at - 0.06) / 0.25), glow=1 - clamp((t - at) / 0.9))


def crack(img, name, p, alpha=1.0):
    if p <= 0 or alpha <= 0:
        return
    x, y = P[name]
    pts = [(x + 248, y + 2), (x + 234, y + 38), (x + 256, y + 66), (x + 232, y + 98), (x + 246, y + 128)]
    pts = partial(pts, p)
    if len(pts) < 2:
        return
    d = ImageDraw.Draw(img, "RGBA")
    flat = [c for pt in pts for c in pt]
    d.line(flat, fill=S.VOID + (int(255 * alpha),), width=9, joint="curve")
    d.line(flat, fill=S.WARN + (int(210 * alpha),), width=3, joint="curve")


def draw_map(img, t, node_at=None, edge_at=None, pulses=None, flags=None, hot=None, jiggle=None, broken=None, red=0.0):
    """Bookings and the three pieces under it. broken[name] is 0..1: the piece dims and a crack runs down it."""
    pulses, flags, hot, jiggle, broken = pulses or {}, flags or {}, hot or {}, jiggle or {}, broken or {}
    node_at = node_at or [-9] * 4
    S.map_glow(img, alpha=ease_out((t - node_at[0]) / 1.5) * 0.9)
    for k in KIDS:
        draw_route(img, k, p=1.0 if edge_at is None else ease_out((t - edge_at) / 0.5), hot=hot.get(k, 0), dim=broken.get(k, 0))
    for name, at in zip(ORDER, node_at):
        a = ease_out((t - at) / 0.3)
        br = broken.get(name, 0)
        x, y = P[name]
        x += jiggle.get(name, 0)
        if br > 0 and red > 0:
            S.put_sprite(img, S.GLOW_W, *center(name), scale=1.15, alpha=0.75 * red * br)
        S.node(img, x, y, name, alpha=a * (1 - 0.42 * br), slide=(1 - a) * 16, pulse=pulses.get(name, 0), flag=flags.get(name, 0))
        if br > 0:
            crack(img, name, clamp(br * 1.4), alpha=br)
            if red > 0:
                d = ImageDraw.Draw(img, "RGBA")
                d.rounded_rectangle((x, y, x + S.NODE_W, y + S.NODE_H), radius=20, outline=S.WARN + (int(255 * red * br),), width=4)


# ---------------------------------------------------------------- scenes
def s_title(t, dur, tg):
    img = S.void(bob(tg))
    S.title_card(img, TITLE, tg, out=(t - TITLE_OUT) / 0.6)
    S.draw_dm(img, bob(tg), "idle", **S.dm_place((t - TITLE_OUT - 0.05) / 0.65))
    return img


def s_b1(t, dur, tg):
    img = S.void(bob(tg))
    done = t >= B1_CH
    pulses = {TOP: 1 - clamp((t - B1_CH) / 0.7)} if done else {}
    draw_map(img, t, node_at=B1_NODES, edge_at=B1_EDGES, pulses=pulses)
    if t < B1_CH:
        tag(img, *OUT_TAG, OLD, alpha=ease_out((t - B1_TAG) / 0.3))
    else:
        swap(img, *OUT_TAG, OLD, NEW, t, B1_CH)
    ox, oy = path(t, [(0.6, -60, 420), (B1_ARRIVE, *perch(TOP)), (B1_LEAVE, *perch(TOP)), (B1_LEAVE + 0.7, 1150, 330)])
    wig = 7 * math.sin(t * 26) if B1_ARRIVE + 0.15 < t < B1_CH else 0
    S.orb(img, ox + wig, oy, t, alpha=1 - clamp((t - B1_LEAVE - 0.4) / 0.3))
    S.phrase(img, PHRASES["b1"][0], t, at=PHRASES["b1"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def b2_state(t):
    broken = {k: ease_out((t - at) / 0.6) for k, at in zip(KIDS, B2_BAD) if t >= at}
    red = ease_out((t - B2_RED) / 0.25)
    return broken, red


def s_b2(t, dur, tg):
    img = S.void(bob(tg))
    broken, red = b2_state(t)
    hot = {k: 0.7 * (1 - clamp(abs(t - at - 0.1) / 0.5)) for k, at in zip(KIDS, B2_IN)}
    jig = {k: 6 * math.sin((t - B2_RED) * 44 + i) * max(0.0, 1 - (t - B2_RED) / 0.45) for i, k in enumerate(KIDS)} if t >= B2_RED else {}
    draw_map(img, t, hot=hot, broken=broken, red=red, jiggle=jig)
    tag(img, *OUT_TAG, NEW)
    for k, at, bad in zip(KIDS, B2_IN, B2_BAD):
        a = ease_out((t - at) / 0.3)
        tag(img, *in_tag(k), OLD, alpha=a, glow=(1 - clamp((t - at) / 0.8)) if t >= at else 0, bad=ease_out((t - bad) / 0.35))
    S.phrase(img, PHRASES["b2"][0], t, at=PHRASES["b2"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def s_b3(t, dur, tg):
    img = S.void(bob(tg))
    back = 1 - smooth((t - B3_BACK) / 0.9)
    draw_map(img, t, broken={k: back for k in KIDS}, red=back)
    swap(img, *OUT_TAG, NEW, OLD, t, B3_TAG)
    for k in KIDS:
        tag(img, *in_tag(k), OLD, bad=back)
    u = (t - B3_BACK) / 0.9          # the rewind: a band of light sweeps back across the map
    if 0 < u < 1:
        x = lerp(1040, 40, smooth(u))
        d = ImageDraw.Draw(img, "RGBA")
        for i in range(12):
            d.rectangle((x + i * 9, 270, x + i * 9 + 9, 830), fill=S.ORB + (int(70 * (1 - i / 12) * math.sin(math.pi * u)),))
    S.phrase(img, PHRASES["b3"][0], t, at=PHRASES["b3"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def s_b4(t, dur, tg):
    img = S.void(bob(tg))
    changed = t >= B4_CH
    lands = [B4_LAND + 0.12 * i for i in range(3)]
    pulses = {k: 1 - clamp((t - at) / 0.7) for k, at in zip(KIDS, lands) if t >= at}
    if changed:
        pulses[TOP] = 1 - clamp((t - B4_CH) / 0.8)
    jig = {TOP: 8 * math.sin((t - B4_CH) * 40) * max(0.0, 1 - (t - B4_CH) / 0.45)} if changed else {}
    hot = {k: 0.9 * (1 - clamp(abs(t - (B4_RIP + lands[i]) / 2) / 0.6)) for i, k in enumerate(KIDS)}
    draw_map(img, t, pulses=pulses, hot=hot, jiggle=jig)
    for i, k in enumerate(KIDS):
        route_pulse(img, k, (t - B4_RIP) / (lands[i] - B4_RIP))
    g_out = max(0.0, 1 - abs(t - B4_OUT - 0.25) / 0.7)
    if changed:
        swap(img, *OUT_TAG, OLD, NEW, t, B4_CH)
    else:
        tag(img, *OUT_TAG, OLD, glow=g_out)
    g_in = max(0.0, 1 - abs(t - B4_IN - 0.25) / 0.7)
    for k, at in zip(KIDS, lands):
        if t >= at:
            swap(img, *in_tag(k), OLD, NEW, t, at)
        else:
            tag(img, *in_tag(k), OLD, glow=g_in)
    ox, oy = path(t, [(B4_ARRIVE - 0.9, 1150, 330), (B4_ARRIVE, *perch(TOP)), (dur, *perch(TOP))])
    wig = 7 * math.sin(t * 26) if B4_ARRIVE + 0.1 < t < B4_CH else 0
    S.orb(img, ox + wig, oy, t, alpha=clamp((t - B4_ARRIVE + 0.9) / 0.3))
    S.phrase(img, PHRASES["b4"][0], t, at=PHRASES["b4"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def s_b5(t, dur, tg):
    img = S.void(bob(tg))
    flags = {k: ease_out((t - at) / 0.35) for k, at in zip(KIDS, B5_FLAG)}
    hot = {k: 0.8 * (1 - clamp(abs(t - B5_BACK - 0.4) / 0.6)) for k in KIDS}
    told = t >= B5_TOLD
    draw_map(img, t, flags=flags, hot=hot, pulses={TOP: 1 - clamp((t - B5_TOLD) / 0.8)} if told else {})
    for k in KIDS:
        route_pulse(img, k, 1 - (t - B5_BACK) / 0.8, color=S.WARN)
    tag(img, *OUT_TAG, NEW)
    for k in KIDS:
        tag(img, *in_tag(k), NEW)
    if told:
        a = ease_out((t - B5_TOLD) / 0.3) * (1 - ease_out((t - dur + 0.3) / 0.3))
        tag(img, TOLD[0], TOLD[1] + (1 - ease_out((t - B5_TOLD) / 0.3)) * 14, TOLD[2], alpha=a, glow=1 - clamp((t - B5_TOLD) / 1.0))
    S.orb(img, *perch(TOP), t)
    S.phrase(img, PHRASES["b5"][0], t, at=PHRASES["b5"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def s_b6(t, dur, tg):
    img = S.void(bob(tg))
    flags = {k: 1 - ease_out((t - at) / 0.3) for k, at in zip(KIDS, B6_CLEAR)}
    pulses = {k: 1 - clamp((t - at) / 0.7) for k, at in zip(KIDS, B6_CLEAR) if t >= at}
    if t >= B6_CLEAR[-1] + 0.5:
        w = 0.22 + 0.12 * math.sin((t - B6_CLEAR[-1]) * 3)
        pulses = {n: max(pulses.get(n, 0), w) for n in ORDER}
    draw_map(img, t, flags=flags, pulses=pulses)
    tag(img, *OUT_TAG, NEW)
    for k in KIDS:
        tag(img, *in_tag(k), NEW)
    S.orb(img, *perch(TOP), t)
    S.phrase(img, PHRASES["b6"][0], t, at=PHRASES["b6"][1], until=1e9)
    S.draw_dm(img, bob(tg), "hat-tip" if t >= B6_TIP else "pointing")
    return img


SCENES = [("title", 2.8, s_title), ("b1", 4.8, s_b1), ("b2", 9.8, s_b2), ("b3", 2.8, s_b3), ("b4", 9.8, s_b4), ("b5", 7.2, s_b5),
          ("b6", 3.8, s_b6), ("end", 3.0, None)]
# Placeholder cues, scene-relative; Charlie's recording replaces them through voiceover/stage.json "lines".
_CAPS = [
    ("title", 0.6, 1.6, "You ask your agent"), ("title", 1.65, 2.7, "for one small change."),
    ("b1", 0.4, 1.8, "Rename a column."), ("b1", 2.5, 4.3, "Done in ten seconds."),
    ("b2", 0.2, 1.2, "What it didn't know:"), ("b2", 1.25, 3.1, "three other parts of your project"), ("b2", 3.15, 4.6, "were reading that column."),
    ("b2", 5.0, 6.0, "Nothing errors."), ("b2", 6.2, 7.8, "They just quietly go wrong,"), ("b2", 7.9, 9.5, "and you find out next week."),
    ("b3", 0.4, 2.5, "That's what propagation fixes."),
    ("b4", 0.3, 2.2, "In Dandy, every piece of your project"), ("b4", 2.25, 3.6, "says what it takes in"), ("b4", 3.65, 5.0, "and what it puts out."),
    ("b4", 5.4, 7.0, "So when one piece changes,"), ("b4", 7.1, 9.3, "the change travels down the map."),
    ("b5", 0.3, 1.9, "Everything that depends on it"), ("b5", 1.95, 3.4, "gets updated or flagged,"),
    ("b5", 3.6, 4.9, "and your agent is told"), ("b5", 4.95, 6.7, "exactly what it just touched."),
    ("b6", 0.3, 1.2, "One change."), ("b6", 1.4, 3.3, "Nothing caught off guard."),
]
_st, _acc = {}, 0.0
for _sid, _d, _ in SCENES:
    _st[_sid] = _acc
    _acc += _d
CAPTIONS = [(round(_st[s] + a, 2), round(_st[s] + b, 2), tx) for s, a, b, tx in _CAPS]
assert all(len(S.caption_lines(c[2])) == 1 for c in CAPTIONS), [c[2] for c in CAPTIONS if len(S.caption_lines(c[2])) > 1]


def qa_scenes(starts, durs, captions):
    tb = S.title_boxes(TITLE)
    tspr = S.dm_sprite("idle", S.TITLE_DM_H)
    dm = dict(name="dandy_man", type="sprite", bbox=S.DM_BOX)

    def ph(key):
        text, at = PHRASES[key]
        return S.text_el("key phrase", text, S.phrase_box(text), lines=S.phrase_lines(text), enter_at=at)

    def caps(sid):
        return S.caption_els(captions, starts[sid], durs[sid])

    def nodes(at=None):
        return [S.text_el(f"node {n}", n, S.node_box(*P[n]), **({"enter_at": at[i]} if at else {})) for i, n in enumerate(ORDER)]

    def tg_el(name, cx, cy, text, **kw):
        return S.text_el(name, text, tag_box(cx, cy, text), **kw)

    def ins(text, **kw):
        return [tg_el(f"in {k}", *in_tag(k), text, **kw) for k in KIDS]

    out = [dict(id="title", type="title", duration=durs["title"], laid_out=[
        S.text_el("title", " ".join(TITLE), (min(b[0] for b in tb), tb[0][1], max(b[2] for b in tb), tb[-1][3]), role="headline", lines=TITLE, exit_at=TITLE_OUT),
        dict(name="dandy_man", type="sprite", exit_at=TITLE_OUT + 0.05,
             bbox=(S.TITLE_DM_X0 + tspr.width * 0.2, S.TITLE_DM_Y0, S.TITLE_DM_X0 + tspr.width * 0.8, S.TITLE_DM_Y0 + S.TITLE_DM_H))])]
    # A tag that flips is one element holding the wider of its two names, so the word count is what is on screen at once.
    out.append(dict(id="b1", type="stage", duration=durs["b1"], laid_out=nodes(B1_NODES) + [tg_el("out tag", *OUT_TAG, NEW, enter_at=B1_TAG), ph("b1"), dm] + caps("b1")))
    out.append(dict(id="b2", type="stage", duration=durs["b2"], laid_out=nodes() + [tg_el("out tag", *OUT_TAG, NEW)]
                    + [tg_el(f"in {k}", *in_tag(k), OLD, enter_at=at) for k, at in zip(KIDS, B2_IN)] + [ph("b2"), dm] + caps("b2")))
    out.append(dict(id="b3", type="stage", duration=durs["b3"], laid_out=nodes() + [tg_el("out tag", *OUT_TAG, NEW)] + ins(OLD) + [ph("b3"), dm] + caps("b3")))
    out.append(dict(id="b4", type="stage", duration=durs["b4"], laid_out=nodes() + [tg_el("out tag", *OUT_TAG, NEW)] + ins(NEW) + [ph("b4"), dm] + caps("b4")))
    out.append(dict(id="b5", type="stage", duration=durs["b5"], laid_out=nodes() + [tg_el("out tag", *OUT_TAG, NEW)] + ins(NEW)
                    + [tg_el("told", *TOLD, enter_at=B5_TOLD), ph("b5"), dm] + caps("b5")))
    out.append(dict(id="b6", type="stage", duration=durs["b6"], laid_out=nodes() + [tg_el("out tag", *OUT_TAG, NEW)] + ins(NEW) + [ph("b6"), dm] + caps("b6")))
    out.append(S.end_card_scene(durs["end"]))
    return out


def events(starts, durs):
    b1, b2, b3, b4, b5, b6 = (starts[k] for k in ("b1", "b2", "b3", "b4", "b5", "b6"))
    pan = {"Reminders": -0.6, "Payments": 0.0, "Reports": 0.6}
    ev = [(STILL, "whoosh", dict(gain=0.2), 0.0), (starts["title"] + TITLE_OUT, "whoosh", dict(gain=0.3), 0.3)]
    for i, at in enumerate(B1_NODES):
        ev.append((b1 + at, "pop", dict(gain=0.28, f=523 * 2 ** (i * 2 / 12)), 0.0))
    ev += [(b1 + B1_TAG, "pop", dict(gain=0.22, f=784), 0.5), (b1 + B1_ARRIVE - 0.5, "whoosh", dict(gain=0.18, dur=0.45), -0.5)]
    for k in range(4):
        ev.append((b1 + B1_ARRIVE + 0.2 + 0.15 * k, "tick", dict(gain=0.16), 0.0))
    ev += [(b1 + B1_CH, "chime", dict(gain=0.3, f0=1047), 0.4), (b1 + B1_LEAVE, "whoosh", dict(gain=0.2, dur=0.5), 0.5)]
    for k, at in zip(KIDS, B2_IN):
        ev.append((b2 + at, "pop", dict(gain=0.24, f=620), pan[k]))
    for k, at in zip(KIDS, B2_BAD):          # the breakage is nearly silent: a dry tick each, nothing more
        ev.append((b2 + at, "tick", dict(gain=0.2), pan[k]))
    ev += [(b2 + B2_RED, "pop", dict(gain=0.4, f=180), 0.0), (b2 + B2_RED + 0.06, "pop", dict(gain=0.3, f=150), 0.0),
           (b3 + B3_BACK, "zip", dict(gain=0.22), 0.0), (b3 + B3_BACK + 0.15, "whoosh", dict(gain=0.3, dur=0.8), 0.0),
           (b3 + B3_TAG + 0.4, "chime", dict(gain=0.24, f0=784), 0.0),
           (b4 + B4_IN, "pop", dict(gain=0.22, f=587), 0.0), (b4 + B4_OUT, "pop", dict(gain=0.22, f=784), 0.5),
           (b4 + B4_ARRIVE - 0.5, "whoosh", dict(gain=0.18, dur=0.45), 0.5),
           (b4 + B4_CH, "chime", dict(gain=0.3, f0=1047), 0.4), (b4 + B4_RIP, "zip", dict(gain=0.22), 0.0)]
    for i, k in enumerate(KIDS):
        ev.append((b4 + B4_LAND + 0.12 * i, "pop", dict(gain=0.3, f=660 * 2 ** (i * 2 / 12)), pan[k]))
    ev.append((b4 + B4_LAND + 0.4, "chime", dict(gain=0.22, f0=1319), 0.0))
    for k, at in zip(KIDS, B5_FLAG):
        ev.append((b5 + at, "pop", dict(gain=0.28, f=380), pan[k]))
    ev += [(b5 + B5_BACK, "zip", dict(gain=0.18), 0.0), (b5 + B5_TOLD, "chime", dict(gain=0.3, f0=988), -0.4), (b5 + B5_TOLD, "tick", dict(gain=0.3), -0.4)]
    for i, (k, at) in enumerate(zip(KIDS, B6_CLEAR)):
        ev.append((b6 + at, "pop", dict(gain=0.26, f=660 + 110 * i), pan[k]))
    ev += [(b6 + B6_TIP + 0.1, "chime", dict(gain=0.3, f0=880), 0.4), (starts["end"] + 0.3, "chime", dict(gain=0.32, f0=660), 0.0)]
    return ev


SPEC = dict(video_dir=HERE, slug="16-one-small-change", look_tag="stage", scenes=SCENES, captions=CAPTIONS, qa_scenes=qa_scenes,
            events=events, still_s=STILL, voiceover=os.path.join(HERE, "voiceover", "stage.json"))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if S.render_video(SPEC, a.preview, a.stills, a.final) else 1)

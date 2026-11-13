"""Video 10, What is Dandy? First of the pinned series, in the Void Stage look (render/stage.py).

Usage:  python3 videos/10-what-is-dandy/render_what.py [--preview] [--stills] [--final]

Frame one is the thumbnail: a still title card that holds for half a second (also saved as out/10-thumbnail.png).
Then: the agent starts a new session knowing nothing (three question cards); Dandy as a live map of an ordinary app;
the agent reads the map, marks a piece done and adds a new one; every piece shows where it stands and the agent goes
straight to the one in progress while Dandy Man tips his hat; end card with Dandy Man.

Timings move to voiceover/stage.json ("durations", "file", "lines") once Charlie records.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "render"))
import stage as S  # noqa: E402
from stage import clamp, ease_out, smooth, lerp  # noqa: E402

STILL = 0.5
TITLE = ["What is", "Dandy?"]
P = {"Sign up": (86, 290), "Calendar": (405, 290), "Bookings": (405, 480), "Payments": (724, 480), "Reminders": (86, 480),
     "Reviews": (405, 670)}
EDGES = [("Sign up", "Calendar"), ("Calendar", "Bookings"), ("Bookings", "Payments"), ("Bookings", "Reminders")]
ROW = {"Bookings": (86, 470), "Reviews": (405, 470), "Reminders": (724, 470)}
ROW_STATE = {"Bookings": "done", "Reviews": "building", "Reminders": "next"}

PILL = (540, 326, "New session")
ORB_HOME = (540, 452)
CARDS = [((86, 540, 516, 650), "What's built?", 2.6), ((564, 540, 994, 650), "What's decided?", 3.4), ((325, 700, 755, 810), "What's next?", 4.2)]
PHRASES = {"b1": ("Starting from zero", 1.0), "b2": ("A live map of your project", 2.6), "b3": ("Reads first. Writes back.", 0.8),
           "b4": ("Right where you left off", 1.2)}

B2_NODES = [("Sign up", 0.5), ("Calendar", 1.3), ("Bookings", 2.1), ("Payments", 2.9), ("Reminders", 3.7)]
B2_EDGES = [1.5, 2.3, 3.1, 3.9]
B3_READ = [("Sign up", 0.7), ("Calendar", 1.1), ("Bookings", 1.5), ("Payments", 1.9), ("Reminders", 2.3)]
B3_WORK, B3_DONE, B3_NEW, B3_NEW_EDGE = 2.9, 3.8, 4.4, 4.7
B4_SLIDE, B4_CHIPS, B4_ORB, B4_TIP = 0.8, (0.9, 1.2, 1.5), 2.0, 3.0


def center(name, table=P):
    x, y = table[name]
    return x + S.NODE_W / 2, y + S.NODE_H / 2


def path(t, keys):
    """Smooth travel through (time, x, y) keyframes."""
    if t <= keys[0][0]:
        return keys[0][1], keys[0][2]
    for (t0, x0, y0), (t1, x1, y1) in zip(keys, keys[1:]):
        if t <= t1:
            q = smooth((t - t0) / (t1 - t0))
            return lerp(x0, x1, q), lerp(y0, y1, q)
    return keys[-1][1], keys[-1][2]


def bob(tg):
    return max(0.0, tg - STILL)


def fade_out(t, dur, d=0.35):
    return 1 - ease_out((t - (dur - d)) / d)


def s_title(t, dur, tg):
    img = S.void(bob(tg))
    out = (t - 1.3) / 0.6
    S.title_card(img, TITLE, tg, out=out)
    S.draw_dm(img, bob(tg), "idle", **S.dm_place((t - 1.35) / 0.65))
    return img


def s_b1(t, dur, tg):
    img = S.void(bob(tg))
    fo = fade_out(t, dur)
    S.pill(img, *PILL, alpha=ease_out((t - 0.3) / 0.3) * fo)
    for box, text, at in CARDS:
        a = ease_out((t - at) / 0.3)
        S.card(img, box, text, alpha=a * fo, slide=(1 - a) * 16)
    ox, oy = path(t, [(0.0, 540, 200), (0.6, *ORB_HOME), (2.6, *ORB_HOME), (3.2, 300, 470), (3.9, 780, 470), (4.7, 540, 676), (5.6, *ORB_HOME)])
    lost = smooth((t - 2.6) / 0.6)
    S.orb(img, ox + 8 * math.sin(t * 2.3) * lost, oy + 6 * math.cos(t * 1.9), t, alpha=ease_out(t / 0.4) * fo, dim=0.5 * lost)
    S.phrase(img, PHRASES["b1"][0], t, at=PHRASES["b1"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def draw_map(img, t_nodes, t_edges, t, states=None, pulses=None, alpha=1.0, hot=None):
    states, pulses, hot = states or {}, pulses or {}, hot or {}
    S.map_glow(img, alpha=alpha * ease_out((t - t_nodes[0][1]) / 1.5))
    for (a, b), at in zip(EDGES, t_edges):
        S.edge(img, S.node_box(*P[a]), S.node_box(*P[b]), p=ease_out((t - at) / 0.4), alpha=alpha, hot=hot.get((a, b), 0))
    for name, at in t_nodes:
        a = ease_out((t - at) / 0.3)
        st = states.get(name)
        S.node(img, *P[name], name, alpha=a * alpha, slide=(1 - a) * 16, state=st[0] if st else None,
               state_alpha=st[1] if st else 1.0, pulse=pulses.get(name, 0))


def s_b2(t, dur, tg):
    img = S.void(bob(tg))
    pulses = {n: 1 - clamp((t - at) / 0.5) for n, at in B2_NODES if t >= at}
    draw_map(img, B2_NODES, B2_EDGES, t, pulses=pulses)
    S.phrase(img, PHRASES["b2"][0], t, at=PHRASES["b2"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


ALL_NOW = [(n, -9) for n, _ in B2_NODES]
EDGES_NOW = [-9] * 4


def s_b3(t, dur, tg):
    img = S.void(bob(tg))
    pulses = {n: 1 - clamp((t - at) / 0.45) for n, at in B3_READ if t >= at}
    states = {}
    if t >= B3_WORK:
        if t < B3_DONE:
            states["Bookings"] = ("building", ease_out((t - B3_WORK) / 0.3))
        else:
            states["Bookings"] = ("done", 1.0)
            pulses["Bookings"] = max(pulses.get("Bookings", 0), 1 - clamp((t - B3_DONE) / 0.6))
    draw_map(img, ALL_NOW, EDGES_NOW, t, states=states, pulses=pulses)
    S.edge(img, S.node_box(*P["Bookings"]), S.node_box(*P["Reviews"]), p=ease_out((t - B3_NEW_EDGE) / 0.4))
    a = ease_out((t - B3_NEW) / 0.3)
    S.node(img, *P["Reviews"], "Reviews", alpha=a, slide=(1 - a) * 16, pulse=1 - clamp((t - B3_NEW) / 0.6) if t >= B3_NEW else 0)
    keys = [(0.0, -40, 240)] + [(at, *center(n)) for n, at in B3_READ] + [(B3_WORK, *center("Bookings")), (B3_DONE + 0.2, *center("Bookings")),
                                                                         (B3_NEW + 0.1, *center("Reviews")), (dur, *center("Reviews"))]
    ox, oy = path(t, keys)
    wig = 10 * math.sin(t * 26) if B3_WORK + 0.2 < t < B3_DONE else 0
    S.orb(img, ox + wig, oy - 6, t)
    S.phrase(img, PHRASES["b3"][0], t, at=PHRASES["b3"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def s_b4(t, dur, tg):
    img = S.void(bob(tg))
    q = smooth(t / B4_SLIDE)
    S.map_glow(img)
    gone = 1 - ease_out(t / 0.45)
    # the pieces that leave, and the old connections
    for (a, b) in EDGES + [("Bookings", "Reviews")]:
        S.edge(img, S.node_box(*P[a]), S.node_box(*P[b]), alpha=gone)
    for name in ("Sign up", "Calendar", "Payments"):
        S.node(img, *P[name], name, alpha=gone)
    pos = {n: (lerp(P[n][0], ROW[n][0], q), lerp(P[n][1], ROW[n][1], q)) for n in ROW}
    order = ["Bookings", "Reviews", "Reminders"]
    for i, (a, b) in enumerate(zip(order, order[1:])):
        S.edge(img, S.node_box(*ROW[a]), S.node_box(*ROW[b]), p=ease_out((t - B4_SLIDE - 0.15 * i) / 0.4))
    for n, at in zip(order, B4_CHIPS):
        sa = ease_out((t - at) / 0.3)
        st = ROW_STATE[n] if (sa > 0 or n == "Bookings") else None
        pulse = (1 - clamp((t - at) / 0.5)) if t >= at else 0
        if n == "Reviews" and t >= B4_ORB:
            pulse = max(pulse, 0.35 + 0.25 * math.sin((t - B4_ORB) * 4))
        S.node(img, *pos[n], n, state=st, state_alpha=1.0 if (n == "Bookings" and sa <= 0) else sa, pulse=pulse)
    cx, cy = center("Reviews", ROW)
    ox, oy = path(t, [(0.0, *center("Reviews")), (B4_SLIDE, cx, cy - 150), (B4_ORB - 0.5, cx, cy - 150), (B4_ORB, cx, cy - 6), (dur, cx, cy - 6)])
    S.orb(img, ox, oy, t)
    S.phrase(img, PHRASES["b4"][0], t, at=PHRASES["b4"][1], until=1e9)
    S.draw_dm(img, bob(tg), "hat-tip" if t >= B4_TIP else "pointing")
    return img


SCENES = [("title", 2.0, s_title), ("b1", 7.0, s_b1), ("b2", 7.0, s_b2), ("b3", 6.0, s_b3), ("b4", 5.0, s_b4), ("end", 3.0, None)]
CAPTIONS = [
    (2.2, 3.6, "When you build with AI,"), (3.65, 5.4, "every new session starts from zero."),
    (5.5, 6.6, "Your agent doesn't know"), (6.65, 7.9, "what's built, what's decided,"), (7.95, 8.9, "or what's next."),
    (9.2, 11.6, "Dandy is where your project lives."),
    (11.8, 13.7, "A live map of every piece,"), (13.75, 15.8, "and how they connect."),
    (16.2, 18.8, "Your agent reads it before it starts,"), (18.85, 21.6, "and updates it when it's done."),
    (22.2, 23.8, "So every session picks up"), (23.85, 25.6, "right where the last one left off."),
    (25.7, 26.9, "That's Dandy."),
]
assert all(len(S.caption_lines(c[2])) == 1 for c in CAPTIONS), [c[2] for c in CAPTIONS if len(S.caption_lines(c[2])) > 1]


def qa_scenes(starts, durs, captions):
    """The settled layout of every scene, for render/checks.py run_all (layout, copy, gold, end card)."""
    tb = S.title_boxes(TITLE)
    tspr = S.dm_sprite("idle", S.TITLE_DM_H)
    dm = dict(name="dandy_man", type="sprite", bbox=S.DM_BOX)

    def ph(key):
        text, at = PHRASES[key]
        return S.text_el("key phrase", text, S.phrase_box(text), lines=S.phrase_lines(text), enter_at=at)

    def caps(sid):
        return S.caption_els(captions, starts[sid], durs[sid])

    out = [dict(id="title", type="title", duration=durs["title"], laid_out=[
        S.text_el("title", " ".join(TITLE), (min(b[0] for b in tb), tb[0][1], max(b[2] for b in tb), tb[-1][3]), role="headline", lines=TITLE, exit_at=1.3),
        dict(name="dandy_man", type="sprite", exit_at=1.35,
             bbox=(S.TITLE_DM_X0 + tspr.width * 0.2, S.TITLE_DM_Y0, S.TITLE_DM_X0 + tspr.width * 0.8, S.TITLE_DM_Y0 + S.TITLE_DM_H))])]
    b1 = [S.text_el("pill", PILL[2], S.pill_box(*PILL)), ph("b1"), dm]
    b1 += [S.text_el(f"card {tx}", tx, box, enter_at=at) for box, tx, at in CARDS]
    out.append(dict(id="b1", type="stage", duration=durs["b1"], laid_out=b1 + caps("b1")))
    nodes = [S.text_el(f"node {n}", n, S.node_box(*P[n]), enter_at=at) for n, at in B2_NODES]
    out.append(dict(id="b2", type="stage", duration=durs["b2"], laid_out=nodes + [ph("b2"), dm] + caps("b2")))
    nodes3 = [S.text_el(f"node {n}", n, S.node_box(*P[n])) for n, _ in B2_NODES] + [S.text_el("node Reviews", "Reviews", S.node_box(*P["Reviews"]), enter_at=B3_NEW)]
    chip = dict(name="status chip", type="text", role="body", text="building", lines=["building"], gold=True, enter_at=B3_WORK)   # then "done"; sits inside its node
    out.append(dict(id="b3", type="stage", duration=durs["b3"], laid_out=nodes3 + [chip, ph("b3"), dm] + caps("b3")))
    row = []
    for n in ROW:
        row.append(S.text_el(f"node {n}", n, S.node_box(*ROW[n]), enter_at=B4_SLIDE))
        row.append(dict(name=f"chip {n}", type="text", role="body", text=ROW_STATE[n], lines=[ROW_STATE[n]], gold=ROW_STATE[n] == "building"))
    out.append(dict(id="b4", type="stage", duration=durs["b4"], laid_out=row + [ph("b4"), dm] + caps("b4")))
    out.append(S.end_card_scene(durs["end"]))
    return out


def events(starts, durs):
    ev = [(STILL, "whoosh", dict(gain=0.2), 0.0), (starts["title"] + 1.3, "whoosh", dict(gain=0.3), 0.3)]
    b1, b2, b3, b4 = (starts[k] for k in ("b1", "b2", "b3", "b4"))
    ev.append((b1 + 0.3, "pop", dict(gain=0.25, f=520), 0.0))
    for i, (box, _, at) in enumerate(CARDS):
        ev.append((b1 + at, "pop", dict(gain=0.3, f=420 - 40 * i), (box[0] + box[2] - 1080) / 1080))
    ev.append((b2 - 0.2, "whoosh", dict(gain=0.3), 0.0))
    for i, (n, at) in enumerate(B2_NODES):
        ev.append((b2 + at, "pop", dict(gain=0.3, f=523 * 2 ** (i * 2 / 12)), (P[n][0] - 420) / 500))
    for at in B2_EDGES:
        ev.append((b2 + at, "zip", dict(gain=0.14), 0.0))
    for n, at in B3_READ:
        ev.append((b3 + at, "tick", dict(gain=0.25), (P[n][0] - 420) / 500))
    for k in range(4):
        ev.append((b3 + B3_WORK + 0.25 + 0.14 * k, "tick", dict(gain=0.16), 0.0))
    ev += [(b3 + B3_DONE, "chime", dict(gain=0.3, f0=1047), 0.0), (b3 + B3_NEW, "pop", dict(gain=0.3, f=784), 0.0),
           (b3 + B3_NEW_EDGE, "zip", dict(gain=0.14), 0.0), (b4, "whoosh", dict(gain=0.3), 0.0)]
    for i, at in enumerate(B4_CHIPS):
        ev.append((b4 + at, "pop", dict(gain=0.25, f=660 + 110 * i), -0.5 + 0.5 * i))
    ev += [(b4 + B4_ORB, "chime", dict(gain=0.22, f0=1319), 0.0), (b4 + B4_TIP + 0.1, "chime", dict(gain=0.3, f0=880), 0.4),
           (starts["end"] + 0.3, "chime", dict(gain=0.32, f0=660), 0.0)]
    return ev


SPEC = dict(video_dir=HERE, slug="10-what-is-dandy", look_tag="stage", scenes=SCENES, captions=CAPTIONS, qa_scenes=qa_scenes,
            events=events, still_s=STILL, voiceover=os.path.join(HERE, "voiceover", "stage.json"))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if S.render_video(SPEC, a.preview, a.stills, a.final) else 1)

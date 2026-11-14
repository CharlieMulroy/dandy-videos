"""Video 11, How does Dandy work? Second of the pinned series, in the Void Stage look (render/stage.py).

Usage:  python3 videos/11-how-dandy-works/render_how.py [--preview] [--stills] [--final]

Frame one is the thumbnail: a still title card that holds for half a second (also saved as out/11-thumbnail.png).
Then: the AI coding tool and Dandy plug together, once; "a booking app" becomes a map of pieces and connections;
the agent reads the map, builds one piece, and a second light checks it before it counts as done; one piece changes
and Dandy flags the pieces it touches; the map sits current while Dandy Man tips his hat; end card with Dandy Man.

The example app and its layout are the same as video 10, so the series reads as one explanation.
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
TITLE = ["How does", "Dandy work?"]
P = {"Sign up": (86, 290), "Calendar": (405, 290), "Bookings": (405, 480), "Payments": (724, 480), "Reminders": (86, 480)}
ORDER = ["Sign up", "Calendar", "Bookings", "Payments", "Reminders"]
EDGES = [("Sign up", "Calendar"), ("Calendar", "Bookings"), ("Bookings", "Payments"), ("Bookings", "Reminders")]
PHRASES = {"b1": ("Connect it once", 0.8), "b2": ("Your idea, mapped", 2.4), "b3": ("Read. Build. Check.", 0.8),
           "b4": ("Change one, flag the rest", 1.0), "b5": ("Always current", 1.0)}

# b1: the two tools plug together
TOOL_A, TOOL_B = (86, 400, 446, 720), (634, 400, 994, 720)
B1_CARDS, B1_CABLE, B1_JOIN = (0.3, 0.7), 1.6, 2.4
# b2: an idea becomes a map
IDEA = (540, 326, "a booking app")
B2_IDEA_OUT, B2_NODES, B2_EDGES, B2_FLOW = 2.0, [2.2, 2.7, 3.2, 3.7, 4.2], [2.9, 3.4, 3.9, 4.4], 5.0
# b3: read, build, check
B3_READ = [0.6, 1.0, 1.4, 1.8, 2.2]
B3_BUILD, B3_CHECK, B3_DONE, B3_LEAVE = 3.0, 4.8, 6.2, 6.7
# b4: one piece changes, Dandy flags what it touches
B4_CHANGE, B4_RIPPLE, B4_FLAG = 0.8, 1.5, 2.1
# b5: the map, current
B5_CHIPS = {"Sign up": 0.5, "Calendar": 0.7, "Bookings": 0.9}
B5_TIP = 2.6


def center(name):
    x, y = P[name]
    return x + S.NODE_W / 2, y + S.NODE_H / 2


def box(name):
    return S.node_box(*P[name])


def perch(name):
    """Where the agent's light rests on a piece: its top-left corner, clear of the title."""
    return P[name][0] + 26, P[name][1] + 4


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


def fade_out(t, dur, d=0.35):
    return 1 - ease_out((t - (dur - d)) / d)


def draw_map(img, t, node_at=None, edge_at=None, states=None, pulses=None, flags=None, hot=None, jiggle=None):
    """The booking app's map. node_at / edge_at give entry times (default: already there)."""
    states, pulses, flags, hot, jiggle = states or {}, pulses or {}, flags or {}, hot or {}, jiggle or {}
    node_at = node_at or [-9] * 5
    edge_at = edge_at or [-9] * 4
    S.map_glow(img, alpha=ease_out((t - node_at[0]) / 1.5))
    for (a, b), at in zip(EDGES, edge_at):
        S.edge(img, box(a), box(b), p=ease_out((t - at) / 0.4), hot=hot.get((a, b), 0))
    for name, at in zip(ORDER, node_at):
        a = ease_out((t - at) / 0.3)
        st = states.get(name)
        x, y = P[name]
        S.node(img, x + jiggle.get(name, 0), y, name, alpha=a, slide=(1 - a) * 16, state=st[0] if st else None,
               state_alpha=st[1] if st else 1.0, pulse=pulses.get(name, 0), flag=flags.get(name, 0))


def s_title(t, dur, tg):
    img = S.void(bob(tg))
    S.title_card(img, TITLE, tg, out=(t - 1.3) / 0.6)
    S.draw_dm(img, bob(tg), "idle", **S.dm_place((t - 1.35) / 0.65))
    return img


def s_b1(t, dur, tg):
    img = S.void(bob(tg))
    fo = fade_out(t, dur)
    joined = t >= B1_JOIN
    lit = (0.5 + 0.3 * math.sin((t - B1_JOIN) * 5)) * smooth((t - B1_JOIN) / 0.3) if joined else 0
    S.cable(img, TOOL_A, TOOL_B, p=smooth((t - B1_CABLE) / (B1_JOIN - B1_CABLE)), spark=(1 - clamp((t - B1_JOIN) / 0.5)) if joined else 0, alpha=fo)
    for bx, label, icon, at in ((TOOL_A, "Your AI coding tool", "orb", B1_CARDS[0]), (TOOL_B, "Dandy", "hat", B1_CARDS[1])):
        a = ease_out((t - at) / 0.35)
        S.tool_card(img, bx, label, icon, t, alpha=a * fo, slide=(1 - a) * 18, lit=lit)
    if joined:   # a pulse runs back and forth along the joined cable
        u = ((t - B1_JOIN) * 0.9) % 1.0
        S.edge_pulse(img, TOOL_A, TOOL_B, u if int((t - B1_JOIN) * 0.9) % 2 == 0 else 1 - u)
    S.phrase(img, PHRASES["b1"][0], t, at=PHRASES["b1"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def s_b2(t, dur, tg):
    img = S.void(bob(tg))
    idea = ease_out((t - 0.3) / 0.3) * (1 - ease_out((t - B2_IDEA_OUT + 0.3) / 0.3))
    S.pill(img, *IDEA, alpha=idea)
    pulses = {n: 1 - clamp((t - at) / 0.5) for n, at in zip(ORDER, B2_NODES) if t >= at}
    hot = {}
    if t >= B2_FLOW:
        for i, e in enumerate(EDGES):
            hot[e] = 0.6 * (1 - clamp(abs((t - B2_FLOW - 0.25 * i) - 0.3) / 0.4))
    draw_map(img, t, node_at=B2_NODES, edge_at=B2_EDGES, pulses=pulses, hot=hot)
    if t >= B2_FLOW:
        for i, (a, b) in enumerate(EDGES):
            S.edge_pulse(img, box(a), box(b), (t - B2_FLOW - 0.25 * i) / 0.6)
    ox, oy = path(t, [(0.0, 540, 200), (0.5, 540, 452), (B2_IDEA_OUT, 540, 452), (B2_IDEA_OUT + 0.5, 540, 745), (dur, 540, 745)])
    S.orb(img, ox, oy, t, alpha=ease_out(t / 0.4))
    S.phrase(img, PHRASES["b2"][0], t, at=PHRASES["b2"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def s_b3(t, dur, tg):
    img = S.void(bob(tg))
    pulses = {n: 1 - clamp((t - at) / 0.45) for n, at in zip(ORDER, B3_READ) if t >= at}
    states = {}
    if B3_BUILD <= t < B3_CHECK:
        states["Payments"] = ("building", ease_out((t - B3_BUILD) / 0.3))
    elif B3_CHECK <= t < B3_DONE:
        states["Payments"] = ("checking", 1.0)
    elif t >= B3_DONE:
        states["Payments"] = ("done", 1.0)
        pulses["Payments"] = max(pulses.get("Payments", 0), 1 - clamp((t - B3_DONE) / 0.6))
    draw_map(img, t, states=states, pulses=pulses)
    px, py = center("Payments")
    keys = [(0.0, -40, 240)] + [(at, *center(n)) for n, at in zip(ORDER, B3_READ)] + [(B3_BUILD, *perch("Payments")), (B3_CHECK - 0.4, *perch("Payments")),
                                                                                    (B3_CHECK, px - 70, py + 105), (dur, px - 70, py + 105)]
    ox, oy = path(t, keys)
    wig = 7 * math.sin(t * 26) if B3_BUILD + 0.25 < t < B3_CHECK - 0.5 else 0
    S.orb(img, ox + wig, oy, t)
    if t >= B3_CHECK - 0.5:   # the second light arrives, looks the piece over, and leaves
        cx, cy = path(t, [(B3_CHECK - 0.5, 1040, 300), (B3_CHECK, px + 40, py - 20), (B3_CHECK + 0.5, px - 50, py - 30), (B3_DONE - 0.2, px + 30, py + 10),
                          (B3_DONE, px, py - 6), (B3_LEAVE, px, py - 6), (B3_LEAVE + 0.6, 1040, 300)])
        S.orb(img, cx, cy, t, alpha=1 - clamp((t - B3_LEAVE - 0.3) / 0.3), kind="check")
    S.phrase(img, PHRASES["b3"][0], t, at=PHRASES["b3"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def s_b4(t, dur, tg):
    img = S.void(bob(tg))
    states = {"Payments": ("done", 1.0)}
    changed = t >= B4_CHANGE
    pulses = {"Bookings": max(0.0, 1 - (t - B4_CHANGE) / 0.9)} if changed else {}
    jiggle = {"Bookings": 9 * math.sin((t - B4_CHANGE) * 40) * max(0.0, 1 - (t - B4_CHANGE) / 0.5)} if changed else {}
    flag = ease_out((t - B4_FLAG) / 0.35)
    flags = {"Payments": flag, "Reminders": flag}
    out_edges = [("Bookings", "Payments"), ("Bookings", "Reminders")]
    hot = {e: 0.8 * (1 - clamp(abs(t - B4_RIPPLE - 0.3) / 0.5)) for e in out_edges}
    draw_map(img, t, states=states, pulses=pulses, flags=flags, hot=hot, jiggle=jiggle)
    for a, b in out_edges:
        S.edge_pulse(img, box(a), box(b), (t - B4_RIPPLE) / 0.6, color=S.WARN)
    bx, by = center("Bookings")
    ox, oy = path(t, [(0.0, P["Payments"][0] + S.NODE_W / 2 - 70, P["Payments"][1] + S.NODE_H / 2 + 105), (B4_CHANGE - 0.1, *perch("Bookings")), (B4_CHANGE + 0.6, *perch("Bookings")),
                      (B4_CHANGE + 1.1, bx, by + 120), (dur, bx, by + 120)])
    S.orb(img, ox, oy, t)
    S.phrase(img, PHRASES["b4"][0], t, at=PHRASES["b4"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def s_b5(t, dur, tg):
    img = S.void(bob(tg))
    flag = 1 - ease_out(t / 0.5)
    states = {"Payments": ("done", 1.0)}
    pulses = {}
    for n, at in B5_CHIPS.items():
        if t >= at:
            states[n] = ("building" if n == "Bookings" else "done", ease_out((t - at) / 0.3))
            pulses[n] = 1 - clamp((t - at) / 0.5)
    if t >= 1.6:
        pulses["Bookings"] = max(pulses.get("Bookings", 0), 0.3 + 0.2 * math.sin((t - 1.6) * 4))
    draw_map(img, t, states=states, pulses=pulses, flags={"Payments": flag, "Reminders": flag})
    bx, by = center("Bookings")
    ox, oy = path(t, [(0.0, bx, by + 120), (0.9, *perch("Bookings")), (dur, *perch("Bookings"))])
    S.orb(img, ox, oy, t)
    S.phrase(img, PHRASES["b5"][0], t, at=PHRASES["b5"][1], until=1e9)
    S.draw_dm(img, bob(tg), "hat-tip" if t >= B5_TIP else "pointing")
    return img


SCENES = [("title", 2.0, s_title), ("b1", 4.5, s_b1), ("b2", 6.5, s_b2), ("b3", 8.0, s_b3), ("b4", 5.5, s_b4), ("b5", 4.5, s_b5), ("end", 3.0, None)]
CAPTIONS = [
    (2.2, 3.9, "You connect it to your"), (3.95, 6.2, "AI coding tool, once."),
    (6.7, 8.6, "Tell your agent what you're building,"), (8.65, 10.5, "and it lays it out as a map:"), (10.55, 12.8, "every piece, and how they connect."),
    (13.2, 14.2, "Before it builds,"), (14.25, 15.9, "your agent reads the map."),
    (16.1, 17.6, "When a piece is finished,"), (17.65, 19.2, "a second check confirms it"), (19.25, 20.8, "before it counts as done."),
    (21.2, 23.0, "And when one piece changes,"), (23.05, 26.2, "Dandy flags everything it touches."),
    (26.7, 28.3, "So the map stays current,"), (28.35, 30.6, "and you never update it by hand."),
]
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
        return [S.text_el(f"node {n}", n, box(n), **({"enter_at": at[i]} if at else {})) for i, n in enumerate(ORDER)]

    def chip(n, word, gold=False, **kw):   # a status word inside its node
        return dict(name=f"chip {n}", type="text", role="body", text=word, lines=[word], gold=gold, **kw)

    out = [dict(id="title", type="title", duration=durs["title"], laid_out=[
        S.text_el("title", " ".join(TITLE), (min(b[0] for b in tb), tb[0][1], max(b[2] for b in tb), tb[-1][3]), role="headline", lines=TITLE, exit_at=1.3),
        dict(name="dandy_man", type="sprite", exit_at=1.35,
             bbox=(S.TITLE_DM_X0 + tspr.width * 0.2, S.TITLE_DM_Y0, S.TITLE_DM_X0 + tspr.width * 0.8, S.TITLE_DM_Y0 + S.TITLE_DM_H))])]
    out.append(dict(id="b1", type="stage", duration=durs["b1"], laid_out=[
        S.text_el("tool card", "Your AI coding tool", TOOL_A, lines=["Your AI", "coding tool"]), S.text_el("dandy card", "Dandy", TOOL_B), ph("b1"), dm] + caps("b1")))
    out.append(dict(id="b2", type="stage", duration=durs["b2"], laid_out=[S.text_el("idea", IDEA[2], S.pill_box(*IDEA), exit_at=B2_IDEA_OUT)]
                    + nodes(B2_NODES) + [ph("b2"), dm] + caps("b2")))
    out.append(dict(id="b3", type="stage", duration=durs["b3"], laid_out=nodes() + [chip("Payments", "building", gold=True, enter_at=B3_BUILD, exit_at=B3_CHECK),
                                                                                    ph("b3"), dm] + caps("b3")))
    out.append(dict(id="b4", type="stage", duration=durs["b4"], laid_out=nodes() + [ph("b4"), dm] + caps("b4")))
    chips5 = [chip("Payments", "done")] + [chip(n, "building" if n == "Bookings" else "done", gold=n == "Bookings", enter_at=at) for n, at in B5_CHIPS.items()]
    out.append(dict(id="b5", type="stage", duration=durs["b5"], laid_out=nodes() + chips5 + [ph("b5"), dm] + caps("b5")))
    out.append(S.end_card_scene(durs["end"]))
    return out


def events(starts, durs):
    b1, b2, b3, b4, b5 = (starts[k] for k in ("b1", "b2", "b3", "b4", "b5"))
    ev = [(STILL, "whoosh", dict(gain=0.2), 0.0), (starts["title"] + 1.3, "whoosh", dict(gain=0.3), 0.3),
          (b1 + B1_CARDS[0], "pop", dict(gain=0.3, f=440), -0.5), (b1 + B1_CARDS[1], "pop", dict(gain=0.3, f=554), 0.5),
          (b1 + B1_CABLE, "zip", dict(gain=0.16), 0.0), (b1 + B1_JOIN, "chime", dict(gain=0.32, f0=988), 0.0), (b1 + B1_JOIN, "tick", dict(gain=0.35), 0.0),
          (b2 - 0.2, "whoosh", dict(gain=0.3), 0.0), (b2 + 0.3, "pop", dict(gain=0.25, f=520), 0.0)]
    for i, at in enumerate(B2_NODES):
        ev.append((b2 + at, "pop", dict(gain=0.3, f=523 * 2 ** (i * 2 / 12)), (P[ORDER[i]][0] - 405) / 500))
    for at in B2_EDGES:
        ev.append((b2 + at, "zip", dict(gain=0.13), 0.0))
    ev.append((b2 + B2_FLOW, "chime", dict(gain=0.2, f0=1319), 0.0))
    for i, at in enumerate(B3_READ):
        ev.append((b3 + at, "tick", dict(gain=0.25), (P[ORDER[i]][0] - 405) / 500))
    for k in range(6):
        ev.append((b3 + B3_BUILD + 0.3 + 0.16 * k, "tick", dict(gain=0.16), 0.5))
    ev += [(b3 + B3_CHECK - 0.5, "whoosh", dict(gain=0.2, dur=0.45), 0.6), (b3 + B3_CHECK, "pop", dict(gain=0.25, f=880), 0.5),
           (b3 + B3_DONE, "chime", dict(gain=0.32, f0=1047), 0.4),
           (b4 + B4_CHANGE, "pop", dict(gain=0.35, f=300), 0.0), (b4 + B4_RIPPLE, "zip", dict(gain=0.2), 0.0),
           (b4 + B4_FLAG, "pop", dict(gain=0.3, f=360), 0.5), (b4 + B4_FLAG + 0.05, "pop", dict(gain=0.3, f=340), -0.5),
           (b5, "whoosh", dict(gain=0.25), 0.0)]
    for i, at in enumerate(B5_CHIPS.values()):
        ev.append((b5 + at, "pop", dict(gain=0.25, f=660 + 110 * i), -0.4 + 0.3 * i))
    ev += [(b5 + B5_TIP + 0.1, "chime", dict(gain=0.3, f0=880), 0.4), (starts["end"] + 0.3, "chime", dict(gain=0.32, f0=660), 0.0)]
    return ev


SPEC = dict(video_dir=HERE, slug="11-how-dandy-works", look_tag="stage", scenes=SCENES, captions=CAPTIONS, qa_scenes=qa_scenes,
            events=events, still_s=STILL, voiceover=os.path.join(HERE, "voiceover", "stage.json"))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if S.render_video(SPEC, a.preview, a.stills, a.final) else 1)

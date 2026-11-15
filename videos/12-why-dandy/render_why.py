"""Video 12, Why use Dandy? Third of the pinned series, in the Void Stage look (render/stage.py).

Usage:  python3 videos/12-why-dandy/render_why.py [--preview] [--stills] [--final]

Frame one is the thumbnail: a still title card that holds for half a second (also saved as out/12-thumbnail.png).
Four reasons, one beat each: the pile of re-explaining messages gives way to the map; the project sleeps for weeks
and the agent picks it straight back up; a change flags the pieces it touches before anything breaks; three projects
sit side by side, each showing where it stands. Then all three run to finished while Dandy Man tips his hat.

The example app and its layout are the same as videos 10 and 11.
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
TITLE = ["Why use", "Dandy?"]
P = {"Sign up": (86, 290), "Calendar": (405, 290), "Bookings": (405, 480), "Payments": (724, 480), "Reminders": (86, 480)}
ORDER = ["Sign up", "Calendar", "Bookings", "Payments", "Reminders"]
EDGES = [("Sign up", "Calendar"), ("Calendar", "Bookings"), ("Bookings", "Payments"), ("Bookings", "Reminders")]
PHRASES = {"b1": ("No more re-explaining", 0.9), "b2": ("Leave. Come back.", 1.0), "b3": ("See it before it breaks", 1.0),
           "b4": ("Every project, at a glance", 1.0), "b5": ("Finish what you start", 0.6)}

# b1: the pile of repeated explanations, then the map
BUBBLES = [((86, 290, 596, 430), "Like I said...", 0.3), ((236, 460, 746, 600), None, 0.9), ((386, 630, 896, 770), None, 1.5)]
B1_CLEAR, B1_MAP = 2.6, 3.0
# b2: weeks pass
GRID = (750, 300)            # top-left of the calendar grid, in the empty top-right slot
WEEKS = (862, 355, "weeks later")
WEEKS_SIZE = 32
B2_SLEEP, B2_DAYS, B2_WEEKS, B2_WAKE, B2_BACK = 0.6, (0.8, 2.2), 2.2, 2.9, 3.7
# b3: a change flags what it touches
B3_CHANGE, B3_RIPPLE, B3_FLAG = 0.8, 1.5, 2.1
# b4 / b5: every project at a glance, then finished
CARDS = [((86, 300, 356, 760), "Booking app", ["done", "done", "building", "next", "next"], 0.6, 0.4),
         ((405, 300, 675, 760), "Portfolio", ["done", "done", "done", "done", "next"], 0.8, 0.8),
         ((724, 300, 994, 760), "Budget tool", ["done", "next", "next", "next", "next"], 0.2, 1.2)]
B5_FINISH, B5_TIP = (0.5, 0.9, 1.3), 2.4


def center(name):
    x, y = P[name]
    return x + S.NODE_W / 2, y + S.NODE_H / 2


def box(name):
    return S.node_box(*P[name])


def perch(name):
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


def draw_map(img, t, node_at=None, alpha=1.0, states=None, pulses=None, flags=None, hot=None, jiggle=None):
    states, pulses, flags, hot, jiggle = states or {}, pulses or {}, flags or {}, hot or {}, jiggle or {}
    node_at = node_at or [-9] * 5
    S.map_glow(img, alpha=alpha * ease_out((t - node_at[0]) / 0.8))
    for (a, b) in EDGES:
        at = max(node_at[ORDER.index(a)], node_at[ORDER.index(b)]) + 0.1
        S.edge(img, box(a), box(b), p=ease_out((t - at) / 0.3), alpha=alpha, hot=hot.get((a, b), 0))
    for name, at in zip(ORDER, node_at):
        a = ease_out((t - at) / 0.25)
        st = states.get(name)
        x, y = P[name]
        S.node(img, x + jiggle.get(name, 0), y, name, alpha=a * alpha, slide=(1 - a) * 14, state=st[0] if st else None,
               state_alpha=st[1] if st else 1.0, pulse=pulses.get(name, 0), flag=flags.get(name, 0))


def s_title(t, dur, tg):
    img = S.void(bob(tg))
    S.title_card(img, TITLE, tg, out=(t - 1.3) / 0.6)
    S.draw_dm(img, bob(tg), "idle", **S.dm_place((t - 1.35) / 0.65))
    return img


def s_b1(t, dur, tg):
    img = S.void(bob(tg))
    clear = ease_out((t - B1_CLEAR) / 0.35)
    for i, (bx, text, at) in enumerate(BUBBLES):
        a = ease_out((t - at) / 0.3)
        S.chat_bubble(img, bx, text, alpha=a * (1 - clear), slide=(1 - a) * 18 - clear * 30)
    node_at = [B1_MAP + 0.08 * i for i in range(5)]
    draw_map(img, t, node_at=node_at, pulses={"Bookings": 0.3 + 0.2 * math.sin(t * 4)} if t > B1_MAP + 1.2 else None)
    if t >= B1_MAP + 0.4:
        ox, oy = path(t, [(B1_MAP + 0.4, -40, 240), (B1_MAP + 1.1, *perch("Bookings")), (dur, *perch("Bookings"))])
        S.orb(img, ox, oy, t)
    S.phrase(img, PHRASES["b1"][0], t, at=PHRASES["b1"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def calendar(img, t):
    """Three weeks of days ticking by, then the 'weeks later' tag takes their place."""
    from PIL import ImageDraw
    a = ease_out((t - B2_DAYS[0] + 0.2) / 0.2) * (1 - ease_out((t - B2_WEEKS + 0.1) / 0.25))
    if a > 0:
        d = ImageDraw.Draw(img, "RGBA")
        n = int(21 * clamp((t - B2_DAYS[0]) / (B2_DAYS[1] - B2_DAYS[0])) + 0.999)
        for k in range(21):
            x, y = GRID[0] + (k % 7) * 32, GRID[1] + (k // 7) * 32
            on = k < n
            d.rounded_rectangle((x, y, x + 24, y + 24), radius=6, fill=(S.PURPLE_HI if on else S.CARD) + (int((255 if on else 200) * a),),
                                outline=S.SOFT + (int(120 * a),), width=1)
    S.pill(img, *WEEKS, alpha=ease_out((t - B2_WEEKS) / 0.3), size=WEEKS_SIZE)


def s_b2(t, dur, tg):
    img = S.void(bob(tg))
    asleep = smooth((t - B2_SLEEP) / 0.5) * (1 - smooth((t - B2_WAKE) / 0.5))
    states = {"Payments": ("next", 1.0)}
    pulses = {"Payments": 1 - clamp((t - B2_BACK) / 0.7)} if t >= B2_BACK else {}
    if t >= B2_BACK + 0.7:
        pulses["Payments"] = 0.3 + 0.2 * math.sin((t - B2_BACK) * 4)
    draw_map(img, t, alpha=1 - 0.62 * asleep, states=states, pulses=pulses)
    calendar(img, t)
    if t < B2_SLEEP + 0.4:
        S.orb(img, *perch("Bookings"), t, alpha=1 - clamp((t - B2_SLEEP) / 0.4))
    if t >= B2_WAKE + 0.2:
        ox, oy = path(t, [(B2_WAKE + 0.2, -40, 240), (B2_BACK, *perch("Payments")), (dur, *perch("Payments"))])
        S.orb(img, ox, oy, t, alpha=ease_out((t - B2_WAKE - 0.2) / 0.3))
    S.phrase(img, PHRASES["b2"][0], t, at=PHRASES["b2"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def s_b3(t, dur, tg):
    img = S.void(bob(tg))
    changed = t >= B3_CHANGE
    pulses = {"Bookings": max(0.0, 1 - (t - B3_CHANGE) / 0.9)} if changed else {}
    jiggle = {"Bookings": 9 * math.sin((t - B3_CHANGE) * 40) * max(0.0, 1 - (t - B3_CHANGE) / 0.5)} if changed else {}
    flag = ease_out((t - B3_FLAG) / 0.35) * (1 - ease_out((t - dur + 0.4) / 0.4))
    out_edges = [("Bookings", "Payments"), ("Bookings", "Reminders")]
    hot = {e: 0.8 * (1 - clamp(abs(t - B3_RIPPLE - 0.3) / 0.5)) for e in out_edges}
    draw_map(img, t, pulses=pulses, flags={"Payments": flag, "Reminders": flag}, hot=hot, jiggle=jiggle)
    for a, b in out_edges:
        S.edge_pulse(img, box(a), box(b), (t - B3_RIPPLE) / 0.6, color=S.WARN)
    bx, by = center("Bookings")
    ox, oy = path(t, [(0.0, *perch("Payments")), (B3_CHANGE - 0.1, *perch("Bookings")), (B3_CHANGE + 0.6, *perch("Bookings")),
                      (B3_CHANGE + 1.1, bx, by + 120), (dur, bx, by + 120)])
    S.orb(img, ox, oy, t)
    S.phrase(img, PHRASES["b3"][0], t, at=PHRASES["b3"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def s_b4(t, dur, tg):
    img = S.void(bob(tg))
    S.map_glow(img, alpha=ease_out(t / 1.0))
    for bx, title, states, prog, at in CARDS:
        a = ease_out((t - at) / 0.35)
        S.project_card(img, bx, title, states, prog * ease_out((t - at - 0.2) / 0.8), alpha=a, slide=(1 - a) * 20, pulse=1 - clamp((t - at) / 0.6) if t >= at else 0)
    k = int(max(0, t - 2.2) / 0.9) % 3
    ox, oy = path(t, [(1.6, -40, 240), (2.2, CARDS[0][0][0] + 30, 300)]) if t < 2.2 else (CARDS[k][0][0] + 30, 300)
    if t >= 1.6:
        S.orb(img, ox, oy, t)
    S.phrase(img, PHRASES["b4"][0], t, at=PHRASES["b4"][1], until=dur)
    S.draw_dm(img, bob(tg), "pointing")
    return img


def s_b5(t, dur, tg):
    img = S.void(bob(tg))
    S.map_glow(img)
    for (bx, title, states, prog, _), at in zip(CARDS, B5_FINISH):
        q = ease_out((t - at) / 0.9)
        n_done = sum(1 for s_ in states if s_ == "done")
        upto = n_done + int((5 - n_done) * q + 0.001)
        st = ["done" if i < upto else ("next" if s_ == "building" else s_) for i, s_ in enumerate(states)]
        S.project_card(img, bx, title, st, lerp(prog, 1.0, q), pulse=(1 - clamp((t - at - 0.9) / 0.7)) if t >= at + 0.9 else 0)
    S.phrase(img, PHRASES["b5"][0], t, at=PHRASES["b5"][1], until=1e9)
    S.draw_dm(img, bob(tg), "hat-tip" if t >= B5_TIP else "pointing")
    return img


SCENES = [("title", 2.0, s_title), ("b1", 5.5, s_b1), ("b2", 5.5, s_b2), ("b3", 5.5, s_b3), ("b4", 5.5, s_b4), ("b5", 4.5, s_b5), ("end", 3.0, None)]
CAPTIONS = [
    (2.2, 3.9, "Because you stop re-explaining"), (3.95, 5.4, "your project every time"), (5.45, 7.2, "you open a new chat."),
    (7.7, 9.6, "Because you can leave a project"), (9.65, 10.6, "for weeks,"), (10.65, 12.7, "and pick it up in a minute."),
    (13.2, 15.0, "Because when one piece changes,"), (15.05, 16.6, "you see what it touches"), (16.65, 18.2, "before it breaks."),
    (18.7, 20.9, "And because you can finally see"), (20.95, 23.6, "where every project stands."),
    (24.2, 26.1, "Dandy keeps your projects moving,"), (26.15, 28.2, "so you finish what you start."),
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
        return [S.text_el(f"node {n}", n, box(n), **({"enter_at": at} if at else {})) for n in ORDER]

    out = [dict(id="title", type="title", duration=durs["title"], laid_out=[
        S.text_el("title", " ".join(TITLE), (min(b[0] for b in tb), tb[0][1], max(b[2] for b in tb), tb[-1][3]), role="headline", lines=TITLE, exit_at=1.3),
        dict(name="dandy_man", type="sprite", exit_at=1.35,
             bbox=(S.TITLE_DM_X0 + tspr.width * 0.2, S.TITLE_DM_Y0, S.TITLE_DM_X0 + tspr.width * 0.8, S.TITLE_DM_Y0 + S.TITLE_DM_H))])]
    # the bubbles overlap each other on purpose (a pile), so only the one with words is declared
    out.append(dict(id="b1", type="stage", duration=durs["b1"], laid_out=[S.text_el("bubble", BUBBLES[0][1], BUBBLES[0][0], exit_at=B1_CLEAR + 0.35)]
                    + nodes(B1_MAP) + [ph("b1"), dm] + caps("b1")))
    out.append(dict(id="b2", type="stage", duration=durs["b2"], laid_out=nodes() + [
        S.text_el("weeks", WEEKS[2], S.pill_box(*WEEKS, size=WEEKS_SIZE), enter_at=B2_WEEKS),
        dict(name="chip Payments", type="text", role="body", text="next", lines=["next"]), ph("b2"), dm] + caps("b2")))
    out.append(dict(id="b3", type="stage", duration=durs["b3"], laid_out=nodes() + [ph("b3"), dm] + caps("b3")))
    cards = [S.text_el(f"project {tl}", tl, bx, enter_at=at) for bx, tl, _, _, at in CARDS]
    out.append(dict(id="b4", type="stage", duration=durs["b4"], laid_out=cards + [ph("b4"), dm] + caps("b4")))
    out.append(dict(id="b5", type="stage", duration=durs["b5"], laid_out=[S.text_el(f"project {tl}", tl, bx) for bx, tl, _, _, _ in CARDS] + [ph("b5"), dm] + caps("b5")))
    out.append(S.end_card_scene(durs["end"]))
    for sc in out:
        if sc["id"] == "b4":
            sc["laid_out"][0]["gold"] = True     # the one building dot, on the Booking app card
    return out


def events(starts, durs):
    b1, b2, b3, b4, b5 = (starts[k] for k in ("b1", "b2", "b3", "b4", "b5"))
    ev = [(STILL, "whoosh", dict(gain=0.2), 0.0), (starts["title"] + 1.3, "whoosh", dict(gain=0.3), 0.3)]
    for i, (_, _, at) in enumerate(BUBBLES):
        ev.append((b1 + at, "pop", dict(gain=0.3, f=330 - 30 * i), -0.4 + 0.4 * i))
    ev += [(b1 + B1_CLEAR, "whoosh", dict(gain=0.35), 0.0), (b1 + B1_MAP + 0.1, "chime", dict(gain=0.25, f0=988), 0.0),
           (b1 + B1_MAP + 1.1, "tick", dict(gain=0.3), 0.0), (b2 + B2_SLEEP, "whoosh", dict(gain=0.2, dur=0.8), 0.0)]
    for k in range(21):
        ev.append((b2 + B2_DAYS[0] + k * (B2_DAYS[1] - B2_DAYS[0]) / 21, "tick", dict(gain=0.14), 0.5))
    ev += [(b2 + B2_WEEKS, "pop", dict(gain=0.3, f=520), 0.5), (b2 + B2_WAKE, "whoosh", dict(gain=0.25), 0.0), (b2 + B2_BACK, "chime", dict(gain=0.3, f0=1175), 0.4),
           (b3 + B3_CHANGE, "pop", dict(gain=0.35, f=300), 0.0), (b3 + B3_RIPPLE, "zip", dict(gain=0.2), 0.0),
           (b3 + B3_FLAG, "pop", dict(gain=0.3, f=360), 0.5), (b3 + B3_FLAG + 0.05, "pop", dict(gain=0.3, f=340), -0.5), (b4 - 0.1, "whoosh", dict(gain=0.3), 0.0)]
    for i, c in enumerate(CARDS):
        ev.append((b4 + c[4], "pop", dict(gain=0.3, f=440 * 2 ** (i * 3 / 12)), -0.6 + 0.6 * i))
    for i, at in enumerate(B5_FINISH):
        ev.append((b5 + at + 0.9, "chime", dict(gain=0.28, f0=880 * 2 ** (i * 2 / 12)), -0.6 + 0.6 * i))
    ev += [(b5 + B5_TIP + 0.1, "chime", dict(gain=0.3, f0=880), 0.4), (starts["end"] + 0.3, "chime", dict(gain=0.32, f0=660), 0.0)]
    return ev


SPEC = dict(video_dir=HERE, slug="12-why-dandy", look_tag="stage", scenes=SCENES, captions=CAPTIONS, qa_scenes=qa_scenes,
            events=events, still_s=STILL, voiceover=os.path.join(HERE, "voiceover", "stage.json"))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    sys.exit(0 if S.render_video(SPEC, a.preview, a.stills, a.final) else 1)

"""Automated QA checks on a laid-out scene list.

Each check returns a list of (scene_id, message). Any message fails the render and the
Dandy QA verdict. Checks run on the settled layout (final positions), not on animation
frames, so a walking Dandy Man is judged where he stops.
"""
import re


def _gap(a, b):
    """Smallest axis gap between two boxes (x0, y0, x1, y1); negative when they overlap."""
    dx = max(a[0] - b[2], b[0] - a[2])
    dy = max(a[1] - b[3], b[1] - a[3])
    return max(dx, dy)


def check_layout(scenes, canvas, contract):
    out = []
    min_gap = contract["layout"]["min_gap_px"]
    W, H = canvas["w"], canvas["h"]
    margin = int(min(W, H) * contract["layout"]["outer_margin_pct_of_short_edge"])
    top = contract["layout"]["vertical_safe_top_px"] if H > W else margin
    bottom = H - (contract["layout"]["vertical_safe_bottom_px"] if H > W else margin)
    safe = (margin, top, W - margin, bottom)
    for sc in scenes:
        for e in sc["laid_out"]:
            if e.get("background"):
                b = e["bbox"]
                if b[0] < 0 or b[1] < 0 or b[2] > W or b[3] > H:
                    out.append((sc["id"], f"{e['name']} (background) leaves the canvas: bbox={tuple(int(v) for v in b)}"))
        boxes = [(e["name"], e["bbox"]) for e in sc["laid_out"] if e.get("bbox") and not e.get("background")]
        spans = {e["name"]: (e.get("enter_at", 0), e.get("exit_at") if e.get("exit_at") is not None else sc["duration"])
                 for e in sc["laid_out"]}
        for name, b in boxes:
            if b[0] < safe[0] or b[1] < safe[1] or b[2] > safe[2] or b[3] > safe[3]:
                out.append((sc["id"], f"{name} leaves the safe zone {safe}: bbox={tuple(int(v) for v in b)}"))
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                (na, a), (nb, b) = boxes[i], boxes[j]
                sa, sb = spans[na], spans[nb]
                if sa[1] <= sb[0] or sb[1] <= sa[0]:
                    continue  # never on screen together
                g = _gap(a, b)
                if g < min_gap:
                    verb = "overlaps" if g < 0 else f"is only {int(g)}px from"
                    out.append((sc["id"], f"{na} {verb} {nb} (min gap {min_gap}px)"))
    return out


def check_copy(scenes, contract):
    out = []
    rules = contract["copy_rules"]
    t = contract["type"]
    for sc in scenes:
        words = 0
        for e in sc["laid_out"]:
            if e["type"] != "text":
                continue
            text = e["text"]
            for ch in rules["banned_characters"]:
                if ch in text:
                    out.append((sc["id"], f"{e['name']}: banned character {ch!r} (long dash)"))
            low = text.lower()
            for ph in rules["banned_phrases"]:
                if re.search(r"\b" + re.escape(ph) + r"\b", low):
                    out.append((sc["id"], f"{e['name']}: banned phrase '{ph}'"))
            n = len(e["lines"])
            limit = t["max_headline_lines"] if e["role"] == "headline" else t["max_body_lines"]
            if n > limit:
                out.append((sc["id"], f"{e['name']}: {n} lines, limit {limit} for {e['role']}"))
            words += len(text.split())
        if words > t["max_words_on_screen"]:
            out.append((sc["id"], f"{words} words on screen, limit {t['max_words_on_screen']}"))
    return out


def check_gold(scenes, contract):
    out = []
    limit = contract["palette_rules"]["max_gold_elements_per_frame"]
    for sc in scenes:
        n = sum(1 for e in sc["laid_out"] if e.get("gold"))
        if n > limit:
            out.append((sc["id"], f"{n} gold elements, limit {limit}"))
    return out


def check_end_card(scenes):
    if not scenes or scenes[-1]["type"] != "end_card":
        return [("video", "last scene must be the shared end card")]
    return []


def run_all(scenes, canvas, contract):
    problems = []
    problems += check_layout(scenes, canvas, contract)
    problems += check_copy(scenes, contract)
    problems += check_gold(scenes, contract)
    problems += check_end_card(scenes)
    return problems

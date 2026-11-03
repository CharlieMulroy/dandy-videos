"""Render a Dandy video from a scene spec.

Usage:  python3 render/render.py videos/01-why-dandy [--canvas vertical|horizontal|both] [--preview] [--stills t1,t2]

Reads  <video>/scenes.json, style/contract.json and the SVG assets, lays every scene out on
the grid, runs the QA checks, renders frames, assembles MP4s with ffmpeg and writes a
contact sheet (one frame per scene) to <video>/out/. Fails loudly if any check fails.

Scene spec (positions are fractions of the canvas so one spec renders both canvases; any of
x, y, width, height may be overridden per canvas with a suffix: x_horizontal, height_vertical):
{
  "takeaway": "one sentence",
  "scenes": [
    {"id": "s1", "duration": 4, "enter": "fade|wipe|cut", "exit": "fade|cut",
     "elements": [
       {"name": "h", "type": "text", "role": "headline|body|caption", "text": "...",
        "x": 0.08, "y": 0.30, "align": "left|center", "width": 0.84, "enter_at": 0.0,
        "exit_at": null, "gold": false, "chalk": false, "strike_at": null, "rot_at": null,
        "move": {"at": 2.0, "ms": 800, "dx": 0.1, "dy": 0}},
       {"name": "dm", "type": "sprite", "asset": "cast/dandy-man/idle.svg",
        "x": 0.25, "y": 0.80, "height": 0.45, "anchor": "feet|center|topleft",
        "enter": "walk|rise|fade|cut", "enter_at": 0.5, "walk_frames": ["a.svg", "b.svg"],
        "sequence": [{"asset": "cast/dandy-man/hat-tip.svg", "at": 2.0}], "flip": false,
        "background": true  (excluded from the gap check; must still be inside the canvas)},
       {"name": "g", "type": "graph", "x": 0.5, "y": 0.55, "width": 0.7,
        "nodes": ["Ingest", "Clean", "Report"], "edges": [[0,1],[1,2]], "edge_labels": ["rows", "rows"],
        "enter_at": 0.3, "chalk": false, "rot_at": null, "break_at": null, "broken_edge": 1,
        "spread": {"at": 1.0, "ms": 800, "px": 120}, "merge_at": 3.0,
        "ripple_at": 4.0, "gold_node": 0}
     ]},
    {"id": "end", "type": "end_card", "duration": 3}
  ]
}
"""
import argparse
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

import cairosvg
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import checks  # noqa: E402

FONT_DIR = "/usr/share/fonts/opentype/inter"
FONTS = {"headline": "Inter-Bold.otf", "body": "Inter-Regular.otf", "caption": "Inter-Medium.otf"}

with open(os.path.join(ROOT, "style", "contract.json")) as f:
    CONTRACT = json.load(f)
PAL = CONTRACT["palette"]
FPS = CONTRACT["motion"]["fps"]
M = CONTRACT["motion"]
TR = M["transition_ms"] / 1000
RISE_S, RISE_PX = M["text_entry"]["ms"] / 1000, M["text_entry"]["rise_px"]


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def snap(v, unit=None):
    unit = unit or CONTRACT["layout"]["spacing_unit_px"]
    return int(round(v / unit) * unit)


_sprite_cache = {}


def load_sprite(rel, height, flip=False):
    key = (rel, height, flip)
    if key not in _sprite_cache:
        path = os.path.join(ROOT, rel)
        if rel.lower().endswith(".png"):
            im = Image.open(path).convert("RGBA")
            im = im.resize((int(im.width * height / im.height), height), Image.LANCZOS)
        else:
            png = cairosvg.svg2png(url=path, output_height=height)
            im = Image.open(io.BytesIO(png)).convert("RGBA")
        if flip:
            im = ImageOps.mirror(im)
        _sprite_cache[key] = im
    return _sprite_cache[key]


def font(role, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, FONTS[role]), size)


def wrap(text, fnt, max_w, draw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


_bg_cache = {}


def background(W, H, floor_y=None):
    """Dark purple base with a soft radial light behind the action and an optional stage floor."""
    key = (W, H, floor_y)
    if key in _bg_cache:
        return _bg_cache[key].copy()
    base = rgb(PAL["background"])
    lift = rgb(PAL["background_lift"])
    small = Image.new("RGB", (W // 8, H // 8), base)
    d = ImageDraw.Draw(small)
    cx, cy, r = small.width * 0.5, small.height * 0.42, small.width * 0.75
    for i in range(40, 0, -1):
        f = i / 40
        col = tuple(int(base[k] + (lift[k] - base[k]) * 0.75 * (1 - f)) for k in range(3))
        d.ellipse((cx - r * f, cy - r * f * 1.15, cx + r * f, cy + r * f * 1.15), fill=col)
    small = small.filter(ImageFilter.GaussianBlur(radius=12))
    bg = small.resize((W, H), Image.BICUBIC)
    if floor_y is not None:
        fy = int(floor_y * H)
        d = ImageDraw.Draw(bg)
        dark = tuple(int(c * 0.82) for c in base)
        d.rectangle((0, fy, W, H), fill=dark)
        d.line([(0, fy), (W, fy)], fill=lift, width=3)
    _bg_cache[key] = bg
    return bg.copy()


def draw_shadow(frame, x0, y0, w, h):
    """Soft ellipse under a character's feet."""
    sw, sh = int(w * 0.75), max(10, int(h * 0.035))
    layer = Image.new("RGBA", (sw + 40, sh + 40), (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse((20, 20, 20 + sw, 20 + sh), fill=(0, 0, 0, 110))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=8))
    frame.alpha_composite(layer, (int(x0 + w / 2 - sw / 2 - 20), int(y0 + h - sh / 2 - 20)))


# ---------- layout ----------
def layout_scene(scene, canvas_name):
    cv = CONTRACT["canvases"][canvas_name]
    W, H = cv["w"], cv["h"]
    margin = int(min(W, H) * CONTRACT["layout"]["outer_margin_pct_of_short_edge"])
    sizes = CONTRACT["type"][canvas_name]
    measure = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    laid = []
    stype = scene.get("type", "normal")

    def pick(e, key, default=None):
        return e.get(f"{key}_{canvas_name}", e.get(key, default))
    base = dict(id=scene["id"], type=stype, duration=scene["duration"], enter=scene.get("enter", "fade"),
                exit=scene.get("exit", "fade"), W=W, H=H, floor=pick(scene, "floor"), push=scene.get("push", 0.04))

    def pick(e, key, default=None):
        return e.get(f"{key}_{canvas_name}", e.get(key, default))

    if stype == "end_card":
        dm_h = int(H * (0.32 if H > W else 0.6))
        spr = load_sprite(CONTRACT["cast"]["dandy_man_idle"], dm_h)
        x = margin
        y = H * 0.5 - spr.height / 2
        laid.append(dict(name="dandy_man", type="sprite", img=spr, x=snap(x), y=snap(y),
                         bbox=(x, y, x + spr.width, y + spr.height), enter="fade", enter_at=0.0,
                         sequence=[], walk_frames=[]))
        cx = (x + spr.width + (W - margin)) / 2
        fh = font("headline", int(sizes["headline"] * 1.5))
        tw = measure.textlength("Dandy", font=fh)
        hat_h = int(H * (0.09 if H > W else 0.16))
        hat = load_sprite("motifs/logo-hat-light.png", hat_h)
        ty = H * 0.5 - sizes["headline"] * 0.9
        hy = ty - hat.height - CONTRACT["layout"]["spacing_unit_px"] * 2
        laid.append(dict(name="logo_hat", type="sprite", img=hat, x=snap(cx - hat.width / 2), y=snap(hy),
                         bbox=(cx - hat.width / 2, hy, cx + hat.width / 2, hy + hat.height), enter="fade", enter_at=0.0,
                         sequence=[], walk_frames=[]))
        laid.append(dict(name="wordmark", type="text", role="headline", text="Dandy", lines=["Dandy"],
                         font=fh, color=PAL["text"], x=snap(cx - tw / 2), y=snap(ty), align="left",
                         bbox=(cx - tw / 2, ty, cx + tw / 2, ty + fh.size * 1.1), enter_at=0.0, gold=False))
        yy = ty + fh.size * 1.1 + CONTRACT["layout"]["spacing_unit_px"] * 3
        for i, line in enumerate(CONTRACT["copy_rules"]["end_card_lines"]):
            role = "body" if i == 0 else "caption"
            fb = font(role, sizes[role])
            lw = measure.textlength(line, font=fb)
            gold = i == 1
            laid.append(dict(name=f"end_line_{i}", type="text", role=role, text=line, lines=[line], font=fb,
                             color=PAL["accent_gold"] if gold else PAL["soft"], x=snap(cx - lw / 2), y=snap(yy),
                             align="left", bbox=(cx - lw / 2, yy, cx + lw / 2, yy + fb.size * 1.1),
                             enter_at=0.3 + 0.2 * i, gold=gold))
            yy += fb.size * 1.1 + CONTRACT["layout"]["spacing_unit_px"] * 3
        return dict(base, laid_out=laid)

    for e in scene["elements"]:
        t = e["type"]
        x = pick(e, "x") * W
        y = pick(e, "y") * H
        common = dict(name=e["name"], enter_at=e.get("enter_at", 0), exit_at=e.get("exit_at"),
                      gold=bool(e.get("gold")), rot_at=e.get("rot_at"), background=bool(e.get("background")),
                      move=e.get("move"))
        if t == "text":
            role = e.get("role", "body")
            fnt = font(role, sizes[role])
            max_w = pick(e, "width", 1 - 2 * margin / W) * W
            lines = wrap(e["text"], fnt, max_w, measure)
            lh = fnt.size * 1.2
            widths = [measure.textlength(l, font=fnt) for l in lines]
            bw, bh = max(widths), lh * len(lines)
            align = e.get("align", "left")
            x0 = x - bw / 2 if align == "center" else x
            x0, y0 = snap(x0), snap(y)
            color = PAL["accent_gold"] if e.get("gold") else (PAL["soft"] if e.get("chalk") else PAL["text"])
            if e.get("color") in PAL:
                color = PAL[e["color"]]
            lt = bool(e.get("lower_third"))
            bx0 = x0 - (CONTRACT["layout"]["spacing_unit_px"] + 8) if lt else x0
            laid.append(dict(common, type="text", role=role, text=e["text"], lines=lines, font=fnt, color=color,
                             x=x0, y=y0, align=align, bbox=(bx0, y0, x0 + bw, y0 + bh), strike_at=e.get("strike_at"),
                             chalk=bool(e.get("chalk")), lower_third=lt))
        elif t == "sprite":
            h = int(pick(e, "height", 0.4) * H)
            flip = bool(e.get("flip"))
            spr = load_sprite(e["asset"], h, flip)
            anchor = e.get("anchor", "feet")
            if anchor == "feet":
                x0, y0 = x - spr.width / 2, y - spr.height
            elif anchor == "center":
                x0, y0 = x - spr.width / 2, y - spr.height / 2
            else:
                x0, y0 = x, y
            x0, y0 = snap(x0), snap(y0)
            frames = {}
            for a in e.get("walk_frames", []):
                frames[a] = load_sprite(a, h, flip)
            seq = [dict(asset=s["asset"], at=s["at"], img=load_sprite(s["asset"], h, flip)) for s in e.get("sequence", [])]
            laid.append(dict(common, type="sprite", img=spr, x=x0, y=y0, bbox=(x0, y0, x0 + spr.width, y0 + spr.height),
                             enter=e.get("enter", "fade"), walk_frames=[frames[a] for a in e.get("walk_frames", [])],
                             sequence=seq, idle=bool(e.get("idle", anchor == "feet" and not e.get("background"))),
                             shadow=bool(e.get("shadow", anchor == "feet" and not e.get("background")))))
        elif t == "graph":
            gw = pick(e, "width", 0.7) * W
            n = len(e["nodes"])
            fnt = font("caption", sizes["caption"])
            node_h = sizes["caption"] * 2.2
            gap = CONTRACT["layout"]["spacing_unit_px"] * (4 if e.get("edge_labels") else 3)
            node_w = (gw - gap * (n - 1)) / n
            x0 = snap(x - gw / 2)
            y0 = snap(y - node_h / 2)
            nodes = []
            for i, label in enumerate(e["nodes"]):
                nx = x0 + i * (node_w + gap)
                nodes.append(dict(label=label, box=(nx, y0, nx + node_w, y0 + node_h)))
            spread = e.get("spread")
            pad = spread["px"] if spread else 0
            panel = bool(e.get("panel"))
            ppad = CONTRACT["layout"]["spacing_unit_px"] * 2 if panel else 0
            laid.append(dict(common, type="graph", enter=e.get("enter", "fade"), nodes=nodes, edges=e.get("edges", []), font=fnt, chalk=bool(e.get("chalk")),
                             bbox=(x0 - pad - ppad, y0 - (sizes["caption"] * 1.4 if e.get("edge_labels") else 0) - ppad, x0 + gw + pad + ppad, y0 + node_h + ppad),
                             panel=panel,
                             broken_edge=e.get("broken_edge"), break_at=e.get("break_at"), gold_node=e.get("gold_node"),
                             spread=spread, merge_at=e.get("merge_at"), ripple_at=e.get("ripple_at"),
                             edge_labels=e.get("edge_labels"), label_font=font("caption", int(sizes["caption"] * 0.7))))
        else:
            raise ValueError(f"unknown element type {t}")
    return dict(base, laid_out=laid)


# ---------- drawing ----------
def with_alpha(layer, alpha):
    if alpha < 1:
        layer.putalpha(layer.split()[3].point(lambda v: int(v * alpha)))
    return layer


def draw_text(frame, el, alpha, dx, dy, t_local):
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    lh = el["font"].size * 1.2
    col = rgb(el["color"])
    chalk = el.get("chalk")
    write_s = 0.55  # seconds to write one chalk line
    first_lx = None
    for i, line in enumerate(el["lines"]):
        lw = d.textlength(line, font=el["font"])
        lx = el["x"] if el["align"] == "left" else el["bbox"][0] + (el["bbox"][2] - el["bbox"][0] - lw) / 2
        if first_lx is None:
            first_lx = lx
        if chalk:
            p = max(0.0, min(1.0, (t_local - i * write_s) / write_s))
            if p <= 0:
                continue
            ly = el["y"] + i * lh
            tl = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            ImageDraw.Draw(tl).text((lx + dx, ly + dy), line, font=el["font"], fill=col + (235,))
            mask = Image.new("L", frame.size, 0)
            ImageDraw.Draw(mask).rectangle((lx + dx - 4, ly + dy - 10, lx + dx + lw * p + 6, ly + dy + lh), fill=255)
            tl.putalpha(Image.composite(tl.split()[3], Image.new("L", frame.size, 0), mask))
            layer.alpha_composite(tl)
        else:
            p = ease_out((t_local - 0.15 * i) / RISE_S)
            if p <= 0:
                continue
            ly = el["y"] + i * lh + (1 - p) * RISE_PX
            d.text((lx + dx, ly + dy), line, font=el["font"], fill=col + (int(255 * p),))
        if el.get("strike_at") is not None and t_local + el["enter_at"] >= el["strike_at"]:
            sp = ease_out((t_local + el["enter_at"] - el["strike_at"]) / 0.3)
            yy = el["y"] + i * lh + el["font"].size * 0.58 + dy
            d.line([(lx + dx, yy), (lx + dx + lw * sp, yy)], fill=rgb(PAL["warning"]) + (255,), width=max(4, el["font"].size // 10))
    if el.get("lower_third") and first_lx is not None:
        p = ease_out(t_local / RISE_S)
        bar_h = (lh * len(el["lines"]) - el["font"].size * 0.2) * p
        bx = first_lx + dx - CONTRACT["layout"]["spacing_unit_px"] - 2
        d.rounded_rectangle((bx, el["y"] + dy, bx + 6, el["y"] + dy + bar_h), radius=3, fill=rgb(PAL["highlight"]) + (255,))
    frame.alpha_composite(with_alpha(layer, alpha))


def paste_sprite(frame, img, x, y, alpha):
    if alpha < 1:
        img = img.copy()
        img.putalpha(img.split()[3].point(lambda p: int(p * alpha)))
    frame.alpha_composite(img, (int(x), int(y)))


def draw_sprite(frame, el, t_local, alpha, dx, dy):
    img = el["img"]
    for s in el["sequence"]:
        if t_local + el["enter_at"] >= s["at"]:
            img = s["img"]
    if el["enter"] == "walk":
        p = ease_out(t_local / 1.1)
        dx += -(1 - p) * (el["x"] + img.width + 40)
        if p < 1 and el["walk_frames"]:
            img = el["walk_frames"][int(t_local / 0.16) % len(el["walk_frames"])]
        elif p < 1:
            dy -= abs(math.sin(t_local * 9)) * 10
        a = 1.0
    elif el["enter"] == "rise":
        p = ease_out(t_local / RISE_S)
        dy += (1 - p) * RISE_PX
        a = p
    elif el["enter"] == "cut":
        a = 1.0
    else:
        a = ease_out(t_local / TR)
    if el.get("idle") and not (el["enter"] == "walk" and t_local < 1.1):
        dy += math.sin(t_local * 2 * math.pi / 3.2) * 3
    if el.get("shadow"):
        draw_shadow(frame, el["x"] + dx, el["y"], img.width, img.height) if a * alpha >= 0.99 else None
    paste_sprite(frame, img, el["x"] + dx, el["y"] + dy, a * alpha)


def rounded(d, box, fill, outline=None, width=0, r=16):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def draw_graph(frame, el, t_local, alpha, dx, dy):
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    t_abs = t_local + el["enter_at"]
    edge_s = M["edge_draw_ms"] / 1000
    lift, hi, soft, txt, gold, warn = (rgb(PAL[k]) for k in ("background_lift", "highlight", "soft", "text", "accent_gold", "warning"))
    line_col = soft if el["chalk"] else hi
    fill = (0, 0, 0, 0) if el["chalk"] else lift + (255,)
    n = len(el["nodes"])
    # per-node x offsets: spread apart, then merge back
    offs = [0.0] * n
    if el["spread"] and t_abs >= el["spread"]["at"]:
        p = ease_out((t_abs - el["spread"]["at"]) / (el["spread"]["ms"] / 1000))
        if el["merge_at"] is not None and t_abs >= el["merge_at"]:
            p *= 1 - ease_out((t_abs - el["merge_at"]) / 0.8)
        for i in range(n):
            offs[i] = (i - (n - 1) / 2) * 2 * el["spread"]["px"] * p / max(1, n - 1)
    boxes = []
    for i, nd in enumerate(el["nodes"]):
        b = nd["box"]
        boxes.append((b[0] + offs[i] + dx, b[1] + dy, b[2] + offs[i] + dx, b[3] + dy))
    if el.get("panel"):
        pp = CONTRACT["layout"]["spacing_unit_px"] * 2
        allb = (min(b[0] for b in boxes) - pp, min(b[1] for b in boxes) - pp - (el["label_font"].size * 1.6 + 12 if el.get("edge_labels") else 0),
                max(b[2] for b in boxes) + pp, max(b[3] for b in boxes) + pp)
        glow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle((allb[0] - 6, allb[1] - 6, allb[2] + 6, allb[3] + 6), radius=28, fill=hi + (70,))
        layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(radius=18)))
        rounded(d, allb, fill=lift + (255,), outline=hi + (255,), width=3, r=24)
    # ripple: nodes light up in turn after ripple_at; first node stays gold
    lit = set()
    if el["ripple_at"] is not None and t_abs >= el["ripple_at"]:
        k = int((t_abs - el["ripple_at"]) / 0.45)
        lit = {min(k, n - 1)}
    for i, nd in enumerate(el["nodes"]):
        box = boxes[i]
        # pop-in: scale 0.7 -> 1.06 -> 1.0 over 380 ms, staggered per node (skipped on cut entry)
        pop = 1.0
        if el.get("enter") != "cut":
            q = (t_local - 0.12 * i) / 0.38
            if q <= 0:
                continue
            if q < 1:
                pop = 0.7 + 0.36 * ease_out(q) - 0.06 * ease_out(max(0, (q - 0.6) / 0.4))
        if pop != 1.0:
            cxb, cyb = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            hw, hh = (box[2] - box[0]) / 2 * pop, (box[3] - box[1]) / 2 * pop
            box = (cxb - hw, cyb - hh, cxb + hw, cyb + hh)
        is_gold = (el.get("gold_node") == i and (el["ripple_at"] is None or t_abs >= el["ripple_at"])) or i in lit
        col = gold if is_gold else line_col
        rounded(d, box, fill=fill, outline=col + (255,), width=4)
        lw = d.textlength(nd["label"], font=el["font"])
        d.text(((box[0] + box[2]) / 2 - lw / 2, box[1] + (box[3] - box[1]) / 2 - el["font"].size / 2),
               nd["label"], font=el["font"], fill=txt + (255,))
    for k, (a, b) in enumerate(el["edges"]):
        start = k * edge_s
        if el.get("enter") != "cut":
            start = max(start, 0.12 * max(a, b) + 0.3)  # wait for the target node to pop in
        if el["ripple_at"] is not None and t_abs >= el["ripple_at"]:
            start = el["ripple_at"] - el["enter_at"] + k * 0.45
            p = ease_out((t_local - start) / 0.4)
        else:
            p = ease_out((t_local - start) / edge_s)
        if p <= 0:
            continue
        ba, bb = boxes[a], boxes[b]
        x1, y1 = ba[2], (ba[1] + ba[3]) / 2
        x2, y2 = bb[0], (bb[1] + bb[3]) / 2
        xe, ye = x1 + (x2 - x1) * p, y1 + (y2 - y1) * p
        broken = el.get("broken_edge") == k and (el["break_at"] is None or t_abs >= el["break_at"])
        col = warn if broken else line_col
        w = 6
        if broken:
            bp = 1.0 if el["break_at"] is None else ease_out((t_abs - el["break_at"]) / 0.4)
            xm = (x1 + x2) / 2
            g = 14 * bp
            d.line([(x1, y1), (xm - g, y1 + 6 * bp)], fill=col + (255,), width=w)
            d.line([(xm + g, y1 - 6 * bp), (xe, ye)], fill=col + (255,), width=w)
        else:
            d.line([(x1, y1), (xe, ye)], fill=col + (255,), width=w)
            if p >= 1:
                d.polygon([(x2, y2), (x2 - 18, y2 - 10), (x2 - 18, y2 + 10)], fill=col + (255,))
        if el.get("edge_labels") and p >= 1 and k < len(el["edge_labels"]):
            lab = el["edge_labels"][k]
            lf = el["label_font"]
            lw = d.textlength(lab, font=lf)
            cx = (x1 + x2) / 2
            top = ba[1]
            pill = (cx - lw / 2 - 10, top - lf.size * 1.6 - 12, cx + lw / 2 + 10, top - 12)
            rounded(d, pill, fill=lift + (255,), outline=line_col + (255,), width=2, r=lf.size)
            d.text((cx - lw / 2, pill[1] + 6), lab, font=lf, fill=txt + (255,))
    frame.alpha_composite(with_alpha(layer, alpha))


def context_rot(frame, bbox, p, bg):
    x0, y0, x1, y1 = (int(v) for v in bbox)
    pad = 40
    box = (max(0, x0 - pad), max(0, y0 - pad), min(frame.width, x1 + pad), min(frame.height, y1 + pad))
    region = frame.crop(box)
    region = ImageEnhance.Color(region).enhance(1 - 0.9 * p)
    region = region.filter(ImageFilter.GaussianBlur(radius=12 * p))
    a = region.split()[3].point(lambda v: int(v * (1 - 0.6 * p)))
    region.putalpha(a)
    base = bg.crop(box).convert("RGBA")
    base.alpha_composite(region)
    frame.paste(base, box)


def element_alpha_and_offset(el, t):
    """Visibility alpha (exit fade) and move offset at absolute scene time t."""
    alpha = 1.0
    if el.get("exit_at") is not None and t >= el["exit_at"]:
        alpha = 1 - ease_out((t - el["exit_at"]) / TR)
    dx = dy = 0.0
    mv = el.get("move")
    if mv and t >= mv["at"]:
        p = ease_out((t - mv["at"]) / (mv.get("ms", 800) / 1000))
        dx = mv.get("dx", 0) * p
        dy = mv.get("dy", 0) * p
    return alpha, dx, dy


def render_frame(scene, t):
    W, H = scene["W"], scene["H"]
    bg = background(W, H, scene.get("floor"))
    frame = bg.convert("RGBA")
    for el in scene["laid_out"]:
        t_local = t - el.get("enter_at", 0)
        if t_local < 0:
            continue
        alpha, dx, dy = element_alpha_and_offset(el, t)
        if alpha <= 0:
            continue
        dx *= W
        dy *= H
        if el["type"] == "text":
            draw_text(frame, el, alpha, dx, dy, t_local)
        elif el["type"] == "sprite":
            draw_sprite(frame, el, t_local, alpha, dx, dy)
        elif el["type"] == "graph":
            p = 1.0 if el.get("enter") == "cut" else ease_out(t_local / TR)
            draw_graph(frame, el, t_local, p * alpha, dx, dy)
        if el.get("rot_at") is not None and t >= el["rot_at"]:
            rp = ease_out((t - el["rot_at"]) / (M["context_rot_ms"] / 1000))
            context_rot(frame, el["bbox"], rp, bg)
    return frame


def scene_alpha(scene, t):
    d = scene["duration"]
    a = 1.0
    if scene["enter"] == "fade" and t < TR:
        a = ease_out(t / TR)
    elif scene["enter"] == "wipe" and t < 0.2:
        a = 0.0
    if scene["exit"] == "fade" and t > d - TR:
        a = min(a, ease_out((d - t) / TR))
    return a


# ---------- pipeline ----------
def load_scenes(video_dir, canvas_name):
    with open(os.path.join(video_dir, "scenes.json")) as f:
        spec = json.load(f)
    return spec, [layout_scene(s, canvas_name) for s in spec["scenes"]]


def qa(video_dir, canvas_name, spec, scenes):
    cv = CONTRACT["canvases"][canvas_name]
    problems = checks.run_all(scenes, cv, CONTRACT)
    out_dir = os.path.join(video_dir, "out")
    os.makedirs(out_dir, exist_ok=True)
    report = dict(canvas=canvas_name, takeaway=spec.get("takeaway"), problems=[list(p) for p in problems],
                  scenes=[dict(id=s["id"], duration=s["duration"], elements=[e["name"] for e in s["laid_out"]]) for s in scenes])
    with open(os.path.join(out_dir, f"qa-{canvas_name}.json"), "w") as f:
        json.dump(report, f, indent=2)
    if problems:
        print(f"QA FAILED ({canvas_name}):")
        for sid, msg in problems:
            print(f"  [{sid}] {msg}")
        return False
    return True


def draw_captions(frame, captions, t_global, canvas_name):
    cue = next((c for c in captions["cues"] if c["start"] <= t_global < c["end"]), None)
    if cue is None:
        return
    W, H = frame.size
    sizes = CONTRACT["type"][canvas_name]
    fnt = font("headline", int(sizes["body"] * 0.95))
    d = ImageDraw.Draw(frame)
    tw = d.textlength(cue["text"], font=fnt)
    y = captions.get(f"y_{canvas_name}", captions.get("y", 0.8)) * H
    x = W / 2 - tw / 2
    pad = 18
    d.rounded_rectangle((x - pad, y - pad * 0.6, x + tw + pad, y + fnt.size * 1.15 + pad * 0.4), radius=14,
                        fill=rgb(PAL["background"]) + (200,))
    d.text((x, y), cue["text"], font=fnt, fill=rgb(PAL["text"]) + (255,))


def composite(scene, t, captions=None, t_global=0.0, canvas_name="vertical"):
    frame = render_frame(scene, t)
    push = scene.get("push", 0)
    if push:
        sc = 1 + push * (t / scene["duration"])
        W, H = frame.size
        nw, nh = int(W * sc), int(H * sc)
        big = frame.resize((nw, nh), Image.BILINEAR)
        frame = big.crop(((nw - W) // 2, (nh - H) // 2, (nw - W) // 2 + W, (nh - H) // 2 + H))
    a = scene_alpha(scene, t)
    if a < 1:
        bg = Image.new("RGBA", frame.size, rgb(PAL["background"]) + (255,))
        frame = Image.blend(bg, frame, a)
    if captions:
        draw_captions(frame, captions, t_global, canvas_name)
    return frame.convert("RGB")


def stills(video_dir, canvas_name, times):
    """Write out/stills/<scene>-<t>.png for inspection; times = list of seconds within each scene."""
    spec, scenes = load_scenes(video_dir, canvas_name)
    out = os.path.join(video_dir, "out", "stills")
    os.makedirs(out, exist_ok=True)
    for sc in scenes:
        for t in times:
            if t <= sc["duration"]:
                composite(sc, t).save(os.path.join(out, f"{sc['id']}-{t:04.1f}.png"))
    print("stills in", out)


def render_video(video_dir, canvas_name, preview=False):
    spec, scenes = load_scenes(video_dir, canvas_name)
    if not qa(video_dir, canvas_name, spec, scenes):
        return False
    out_dir = os.path.join(video_dir, "out")
    tmp = tempfile.mkdtemp(prefix="dandy-frames-")
    contact = []
    n = 0
    step = 1.0 / FPS
    captions = None
    cap_path = os.path.join(video_dir, "captions.json")
    if os.path.exists(cap_path) and not preview:
        with open(cap_path) as f:
            captions = json.load(f)
    offset = 0.0
    for sc in scenes:
        frames_in_scene = int(sc["duration"] * FPS)
        for i in range(frames_in_scene):
            if preview and i % 3:
                continue
            t = i * step
            frame = composite(sc, t, captions, offset + t, canvas_name)
            frame.save(os.path.join(tmp, f"f{n:06d}.png"), compress_level=1)
            n += 1
        contact.append(composite(sc, sc["duration"] - 0.4, captions, offset + sc["duration"] - 0.4, canvas_name))
        offset += sc["duration"]
    fps = FPS // 3 if preview else FPS
    mp4 = os.path.join(out_dir, f"{os.path.basename(os.path.normpath(video_dir))}-{canvas_name}.mp4")
    audio = spec.get("audio")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "f%06d.png")]
    if audio and not preview:
        total = sum(sc["duration"] for sc in scenes)
        cmd += ["-ss", str(audio.get("offset_s", 0)), "-i", os.path.join(ROOT, audio["file"]),
                "-af", "highpass=f=80,afftdn=nf=-28,loudnorm=I=-16:TP=-1.5:LRA=11,apad",
                "-t", str(total), "-c:a", "aac", "-b:a", "160k"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", mp4]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    th = 480
    thumbs = [im.resize((int(im.width * th / im.height), th)) for im in contact]
    cols = min(len(thumbs), 4)
    rows = math.ceil(len(thumbs) / cols)
    tw = thumbs[0].width
    sheet = Image.new("RGB", (cols * (tw + 24) + 24, rows * (th + 24) + 24), rgb(PAL["background_lift"]))
    for i, im in enumerate(thumbs):
        sheet.paste(im, (24 + (i % cols) * (tw + 24), 24 + (i // cols) * (th + 24)))
    sheet.save(os.path.join(out_dir, f"contact-{canvas_name}.png"))
    print(f"rendered {mp4} ({n} frames) and contact-{canvas_name}.png; QA passed")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_dir")
    ap.add_argument("--canvas", default="both")
    ap.add_argument("--preview", action="store_true", help="10 fps, faster")
    ap.add_argument("--stills", default=None, help="comma-separated seconds; write stills instead of a video")
    a = ap.parse_args()
    names = ["vertical", "horizontal"] if a.canvas == "both" else [a.canvas]
    if a.stills:
        times = [float(x) for x in a.stills.split(",")]
        for c in names:
            spec, scenes = load_scenes(a.video_dir, c)
            qa(a.video_dir, c, spec, scenes)
            stills(a.video_dir, c, times)
        return
    ok = all(render_video(a.video_dir, c, a.preview) for c in names)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

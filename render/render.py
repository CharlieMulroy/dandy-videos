"""Render a Dandy video from a scene spec.

Usage:  python3 render/render.py videos/01-why-dandy [--canvas vertical|horizontal|both] [--preview]

Reads  <video>/scenes.json, style/contract.json and the SVG assets, lays every scene out on
the grid, runs the QA checks, renders frames, assembles MP4s with ffmpeg and writes a
contact sheet (one frame per scene) to <video>/out/. Fails loudly if any check fails.

Scene spec (positions are fractions of the canvas so one spec renders both canvases):
{
  "takeaway": "one sentence",
  "scenes": [
    {"id": "s1", "duration": 4, "transition": "fade",
     "elements": [
       {"name": "h", "type": "text", "role": "headline|body|caption", "text": "...",
        "x": 0.08, "y": 0.30, "align": "left|center", "width": 0.84, "enter_at": 0.0,
        "gold": false, "rot_at": null},
       {"name": "dm", "type": "sprite", "asset": "cast/dandy-man/candidates/b.svg",
        "x": 0.25, "y": 0.80, "height": 0.45, "height_horizontal": 0.7, "anchor": "feet", "enter": "walk|rise|fade",
        "enter_at": 0.5},
       {"name": "g", "type": "graph", "x": 0.5, "y": 0.55, "width": 0.7,
        "nodes": ["Ingest", "Clean", "Report"], "edges": [[0,1],[1,2]], "enter_at": 0.3,
        "rot_at": null, "broken_edge": null}
     ]},
    {"id": "end", "type": "end_card", "duration": 3}
  ]
}
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

import cairosvg
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

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


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def snap(v, unit=None):
    unit = unit or CONTRACT["layout"]["spacing_unit_px"]
    return int(round(v / unit) * unit)


# ---------- assets ----------
_sprite_cache = {}


def load_sprite(rel, height):
    key = (rel, height)
    if key not in _sprite_cache:
        path = os.path.join(ROOT, rel)
        png = cairosvg.svg2png(url=path, output_height=height)
        import io
        _sprite_cache[key] = Image.open(io.BytesIO(png)).convert("RGBA")
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


# ---------- layout ----------
def layout_scene(scene, canvas_name):
    cv = CONTRACT["canvases"][canvas_name]
    W, H = cv["w"], cv["h"]
    margin = int(min(W, H) * CONTRACT["layout"]["outer_margin_pct_of_short_edge"])
    sizes = CONTRACT["type"][canvas_name]
    measure = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    laid = []
    stype = scene.get("type", "normal")

    if stype == "end_card":
        # Fixed composition: Dandy Man left, wordmark + lines center/right.
        dm_h = int(H * (0.36 if H > W else 0.6))
        spr = load_sprite(CONTRACT["cast"]["dandy_man_idle"], dm_h)
        x = margin
        y = H * 0.5 - spr.height / 2
        laid.append(dict(name="dandy_man", type="sprite", img=spr, x=snap(x), y=snap(y),
                         bbox=(x, y, x + spr.width, y + spr.height), enter="fade", enter_at=0.0))
        cx = (x + spr.width + (W - margin)) / 2
        fh = font("headline", int(sizes["headline"] * 1.4))
        tw = measure.textlength("Dandy", font=fh)
        ty = H * 0.5 - sizes["headline"] * 1.2
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
        return dict(id=scene["id"], type=stype, duration=scene["duration"],
                    transition=scene.get("transition", "fade"), laid_out=laid, W=W, H=H)

    for e in scene["elements"]:
        t = e["type"]
        x = e["x"] * W
        y = e["y"] * H
        if t == "text":
            role = e.get("role", "body")
            fnt = font(role, sizes[role])
            max_w = e.get("width", 1 - 2 * margin / W) * W
            lines = wrap(e["text"], fnt, max_w, measure)
            lh = fnt.size * 1.2
            widths = [measure.textlength(l, font=fnt) for l in lines]
            bw, bh = max(widths), lh * len(lines)
            align = e.get("align", "left")
            x0 = x - bw / 2 if align == "center" else x
            x0, y0 = snap(x0), snap(y)
            laid.append(dict(name=e["name"], type="text", role=role, text=e["text"], lines=lines, font=fnt,
                             color=PAL["accent_gold"] if e.get("gold") else PAL["text"], x=x0, y=y0,
                             align=align, bbox=(x0, y0, x0 + bw, y0 + bh), enter_at=e.get("enter_at", 0),
                             gold=bool(e.get("gold")), rot_at=e.get("rot_at")))
        elif t == "sprite":
            h = int(e.get(f"height_{canvas_name}", e.get("height", 0.4)) * H)
            spr = load_sprite(e["asset"], h)
            anchor = e.get("anchor", "feet")
            x0 = x - spr.width / 2
            y0 = y - spr.height if anchor == "feet" else y - spr.height / 2
            x0, y0 = snap(x0), snap(y0)
            laid.append(dict(name=e["name"], type="sprite", img=spr, x=x0, y=y0,
                             bbox=(x0, y0, x0 + spr.width, y0 + spr.height), enter=e.get("enter", "fade"),
                             enter_at=e.get("enter_at", 0), gold=bool(e.get("gold")), rot_at=e.get("rot_at")))
        elif t == "graph":
            gw = e.get("width", 0.7) * W
            n = len(e["nodes"])
            fnt = font("caption", sizes["caption"])
            node_h = sizes["caption"] * 2.2
            gap = CONTRACT["layout"]["spacing_unit_px"] * 3
            node_w = (gw - gap * (n - 1)) / n
            x0 = snap(x - gw / 2)
            y0 = snap(y - node_h / 2)
            nodes = []
            for i, label in enumerate(e["nodes"]):
                nx = x0 + i * (node_w + gap)
                nodes.append(dict(label=label, box=(nx, y0, nx + node_w, y0 + node_h)))
            laid.append(dict(name=e["name"], type="graph", nodes=nodes, edges=e.get("edges", []), font=fnt,
                             bbox=(x0, y0, x0 + gw, y0 + node_h), enter_at=e.get("enter_at", 0),
                             gold=bool(e.get("gold")), rot_at=e.get("rot_at"), broken_edge=e.get("broken_edge"),
                             gold_node=e.get("gold_node")))
        else:
            raise ValueError(f"unknown element type {t}")
    return dict(id=scene["id"], type=stype, duration=scene["duration"],
                transition=scene.get("transition", "fade"), laid_out=laid, W=W, H=H)


# ---------- drawing ----------
def draw_text(frame, el, alpha, dy):
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    lh = el["font"].size * 1.2
    rgb = hex_rgb(el["color"])
    for i, line in enumerate(el["lines"]):
        lw = d.textlength(line, font=el["font"])
        lx = el["x"] if el["align"] == "left" else el["bbox"][0] + (el["bbox"][2] - el["bbox"][0] - lw) / 2
        d.text((lx, el["y"] + i * lh + dy), line, font=el["font"], fill=rgb + (int(255 * alpha),))
    frame.alpha_composite(layer)


def draw_sprite(frame, el, alpha, dx, dy):
    img = el["img"]
    if alpha < 1:
        a = img.split()[3].point(lambda p: int(p * alpha))
        img = img.copy()
        img.putalpha(a)
    frame.alpha_composite(img, (int(el["x"] + dx), int(el["y"] + dy)))


def rounded(d, box, fill, outline=None, width=0, r=16):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def draw_graph(frame, el, t_local, alpha):
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    edge_ms = CONTRACT["motion"]["edge_draw_ms"] / 1000
    lift, hi, txt, gold, warn = (hex_rgb(PAL[k]) for k in ("background_lift", "highlight", "text", "accent_gold", "warning"))
    for i, nd in enumerate(el["nodes"]):
        box = nd["box"]
        col = gold if el.get("gold_node") == i else hi
        rounded(d, box, fill=lift + (255,), outline=col + (255,), width=4)
        lw = d.textlength(nd["label"], font=el["font"])
        d.text(((box[0] + box[2]) / 2 - lw / 2, box[1] + (box[3] - box[1]) / 2 - el["font"].size / 2),
               nd["label"], font=el["font"], fill=txt + (255,))
    for k, (a, b) in enumerate(el["edges"]):
        start = k * edge_ms
        p = ease_out((t_local - start) / edge_ms)
        if p <= 0:
            continue
        ba, bb = el["nodes"][a]["box"], el["nodes"][b]["box"]
        x1, y1 = ba[2], (ba[1] + ba[3]) / 2
        x2, y2 = bb[0], (bb[1] + bb[3]) / 2
        xe, ye = x1 + (x2 - x1) * p, y1 + (y2 - y1) * p
        broken = el.get("broken_edge") == k
        col = warn if broken else hi
        if broken:
            xm = (x1 + x2) / 2
            d.line([(x1, y1), (xm - 14, ye)], fill=col + (255,), width=6)
            d.line([(xm + 14, ye), (xe, ye)], fill=col + (255,), width=6)
        else:
            d.line([(x1, y1), (xe, ye)], fill=col + (255,), width=6)
            if p >= 1:
                d.polygon([(x2, y2), (x2 - 18, y2 - 10), (x2 - 18, y2 + 10)], fill=col + (255,))
    if alpha < 1:
        layer.putalpha(layer.split()[3].point(lambda v: int(v * alpha)))
    frame.alpha_composite(layer)


def context_rot(frame, el_bbox, p):
    """Desaturate and blur a region: the only blur in the system."""
    x0, y0, x1, y1 = (int(v) for v in el_bbox)
    pad = 40
    box = (max(0, x0 - pad), max(0, y0 - pad), min(frame.width, x1 + pad), min(frame.height, y1 + pad))
    region = frame.crop(box)
    region = ImageEnhance.Color(region).enhance(1 - 0.9 * p)
    region = region.filter(ImageFilter.GaussianBlur(radius=12 * p))
    a = region.split()[3].point(lambda v: int(v * (1 - 0.6 * p)))
    region.putalpha(a)
    base = Image.new("RGBA", region.size, hex_rgb(PAL["background"]) + (255,))
    base.alpha_composite(region)
    frame.paste(base, box)


def render_frame(scene, t):
    W, H = scene["W"], scene["H"]
    frame = Image.new("RGBA", (W, H), hex_rgb(PAL["background"]) + (255,))
    m = CONTRACT["motion"]
    rise_ms, rise_px = m["text_entry"]["ms"] / 1000, m["text_entry"]["rise_px"]
    for el in scene["laid_out"]:
        t_local = t - el.get("enter_at", 0)
        if t_local < 0:
            continue
        if el["type"] == "text":
            # one line at a time: stagger by 150 ms per line
            for i in range(len(el["lines"])):
                p = ease_out((t_local - 0.15 * i) / rise_ms)
                if p <= 0:
                    continue
                sub = dict(el, lines=[el["lines"][i]], y=el["y"] + i * el["font"].size * 1.2)
                draw_text(frame, sub, p, (1 - p) * rise_px)
        elif el["type"] == "sprite":
            if el.get("enter") == "walk":
                p = ease_out(t_local / 0.9)
                dx = -(1 - p) * (el["x"] + el["img"].width)
                bob = abs(math.sin(t_local * 9)) * 10 * (1 - p)
                draw_sprite(frame, el, 1.0, dx, -bob)
            elif el.get("enter") == "rise":
                p = ease_out(t_local / rise_ms)
                draw_sprite(frame, el, p, 0, (1 - p) * rise_px)
            else:
                p = ease_out(t_local / (m["transition_ms"] / 1000))
                draw_sprite(frame, el, p, 0, 0)
        elif el["type"] == "graph":
            p = ease_out(t_local / (m["transition_ms"] / 1000))
            draw_graph(frame, el, t_local, p)
        if el.get("rot_at") is not None and t >= el["rot_at"]:
            rp = ease_out((t - el["rot_at"]) / (m["context_rot_ms"] / 1000))
            context_rot(frame, el["bbox"], rp)
    return frame


def transition_alpha(t, duration):
    tr = CONTRACT["motion"]["transition_ms"] / 1000
    if t < tr:
        return ease_out(t / tr)
    if t > duration - tr:
        return ease_out((duration - t) / tr)
    return 1.0


# ---------- pipeline ----------
def render_video(video_dir, canvas_name, preview=False):
    with open(os.path.join(video_dir, "scenes.json")) as f:
        spec = json.load(f)
    scenes = [layout_scene(s, canvas_name) for s in spec["scenes"]]
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

    tmp = tempfile.mkdtemp(prefix="dandy-frames-")
    contact = []
    n = 0
    step = 1.0 / FPS
    for sc in scenes:
        frames_in_scene = int(sc["duration"] * FPS)
        for i in range(frames_in_scene):
            t = i * step
            frame = render_frame(sc, t)
            a = transition_alpha(t, sc["duration"])
            if a < 1:
                bg = Image.new("RGBA", frame.size, hex_rgb(PAL["background"]) + (255,))
                frame = Image.blend(bg, frame, a)
            if preview and i % 3:
                continue
            frame.convert("RGB").save(os.path.join(tmp, f"f{n:06d}.png"), compress_level=1)
            n += 1
            if i == frames_in_scene - int(0.3 * FPS):
                contact.append(frame.convert("RGB"))
    fps = FPS // 3 if preview else FPS
    mp4 = os.path.join(out_dir, f"{os.path.basename(os.path.normpath(video_dir))}-{canvas_name}.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "f%06d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", mp4], check=True)
    shutil.rmtree(tmp)

    # contact sheet: one frame per scene, thumbnails in a row (vertical) or column pairs
    th = 480
    thumbs = [im.resize((int(im.width * th / im.height), th)) for im in contact]
    cols = min(len(thumbs), 6)
    rows = math.ceil(len(thumbs) / cols)
    tw = thumbs[0].width
    sheet = Image.new("RGB", (cols * (tw + 24) + 24, rows * (th + 24) + 24), hex_rgb(PAL["background_lift"]))
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
    a = ap.parse_args()
    names = ["vertical", "horizontal"] if a.canvas == "both" else [a.canvas]
    ok = all(render_video(a.video_dir, c, a.preview) for c in names)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

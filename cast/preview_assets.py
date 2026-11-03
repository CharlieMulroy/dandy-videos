"""Render every SVG under cast/ and motifs/ to cast/previews/<name>.png on the brand background,
plus one labelled contact sheet at cast/previews/all.png.

Run:  python3 cast/preview_assets.py
"""
import glob
import io
import json
import os

import cairosvg
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(HERE, "previews")
os.makedirs(OUT, exist_ok=True)

with open(os.path.join(ROOT, "style", "contract.json")) as f:
    P = json.load(f)["palette"]
BG, TEXT = P["background"], P["text"]
FONT = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"


def main():
    paths = sorted(glob.glob(os.path.join(HERE, "**", "*.svg"), recursive=True)) + sorted(
        glob.glob(os.path.join(ROOT, "motifs", "*.svg"))
    )
    paths = [p for p in paths if "/candidates/" not in p]
    thumbs = []
    th = 360
    for p in paths:
        png = cairosvg.svg2png(url=p, output_height=th * 2)
        im = Image.open(io.BytesIO(png)).convert("RGBA")
        bg = Image.new("RGBA", im.size, BG)
        bg.alpha_composite(im)
        rel = os.path.relpath(p, ROOT)
        name = rel.replace("/", "__").replace(".svg", "")
        bg.convert("RGB").save(os.path.join(OUT, f"{name}.png"))
        scale = th / im.height
        thumbs.append((rel, bg.resize((max(1, int(im.width * scale)), th))))

    pad, label_h = 30, 34
    try:
        font = ImageFont.truetype(FONT, 20)
    except OSError:
        font = ImageFont.load_default()
    cols = 4
    cell_w = max(t.width for _, t in thumbs) + pad
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w + pad, rows * (th + label_h + pad) + pad), BG)
    d = ImageDraw.Draw(sheet)
    for i, (rel, t) in enumerate(thumbs):
        x = pad + (i % cols) * cell_w
        y = pad + (i // cols) * (th + label_h + pad)
        sheet.paste(t, (x, y))
        d.text((x, y + th + 6), rel, fill=TEXT, font=font)
    sheet.save(os.path.join(OUT, "all.png"))
    print("wrote", len(thumbs), "previews and", os.path.join(OUT, "all.png"))


if __name__ == "__main__":
    main()

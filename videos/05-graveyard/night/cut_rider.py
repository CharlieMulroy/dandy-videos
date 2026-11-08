"""Cut the painted rider (assets/rider-source.png) into puppet parts for rider.py.

Usage:  python3 videos/05-graveyard/night/cut_rider.py [--check]

v2 source (Nov 7): Charlie's second generation, delivered with a transparent background, so the matte is the
source's own alpha. (v1, rider-source-v1.png, was dark on dark and needed GrabCut plus hand-traced fixes; see git
history.) Parts: four legs (each rotates about a pivot hidden under the body), the lantern (swings from the hand)
and the body (everything else; the cloak, tail and mane ripple at draw time). Writes assets/rider/{body,fl_far,
fl_near,hl_near,hl_far,lantern}.png and assets/rider/rig.json (pivots, ground line, body length, glass centre).
All coordinates are source pixels (1448 x 1086).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "assets", "rider-source.png")
OUT = os.path.join(HERE, "assets", "rider")

# legs: the whole leg (with overlap up into the body), the cut (only the part inside it is removed from the body
# layer) and the pivot it rotates about
LEGS = {
    "fl_far": dict(poly=[(330, 650), (250, 662), (185, 678), (150, 720), (110, 790), (70, 840), (25, 900), (65, 912), (102, 880), (108, 842), (132, 802),
                         (172, 742), (212, 712), (272, 702), (330, 706)],
                   cut=lambda x, y: x < 300, pivot=(322, 676)),
    "fl_near": dict(poly=[(395, 676), (320, 686), (268, 708), (252, 746), (282, 792), (308, 838), (352, 874), (448, 874), (442, 822), (400, 808), (346, 798),
                          (322, 768), (302, 746), (332, 732), (395, 726)],
                    cut=lambda x, y: (x < 385) & (y > 690), pivot=(398, 700)),
    "hl_near": dict(poly=[(756, 722), (832, 728), (908, 790), (934, 842), (906, 868), (842, 888), (762, 932), (738, 976), (724, 1024), (646, 1024), (656, 964),
                          (698, 932), (758, 894), (838, 858), (878, 840), (848, 806), (798, 782), (756, 762)],
                    cut=lambda x, y: y > 752, pivot=(800, 738)),
    "hl_far": dict(poly=[(988, 638), (1062, 648), (1112, 688), (1176, 722), (1202, 758), (1252, 818), (1302, 858), (1348, 872), (1398, 898), (1404, 952),
                         (1318, 952), (1288, 902), (1238, 862), (1178, 802), (1138, 776), (1078, 762), (1018, 746), (982, 722)],
                   cut=lambda x, y: (x > 1048) & (y > 665), pivot=(1022, 692)),
}
LANTERN = dict(poly=[(312, 102), (332, 102), (336, 138), (354, 150), (366, 166), (366, 254), (358, 272), (284, 272), (276, 254), (276, 166), (290, 150), (308, 138)],
               pivot=(322, 106))
GROUND_Y = 1015         # where the lowest hoof sits; the shadow goes here
BODY_LEN = 790          # chest to buttock, px
GLASS = (322, 212)      # lantern glass centre
BELLY_Y = 778           # nothing of the body hangs below this


def poly_mask(shape, poly):
    im = Image.new("L", (shape[1], shape[0]), 0)
    ImageDraw.Draw(im).polygon([tuple(p) for p in poly], fill=255)
    return np.asarray(im) > 127


def soft(mask, r):
    return np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255


def build():
    src = Image.open(SRC).convert("RGBA")
    arr = np.asarray(src)
    rgb, alpha = arr[..., :3], arr[..., 3].astype(np.float32) / 255
    shape = alpha.shape
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    os.makedirs(OUT, exist_ok=True)
    rig = dict(size=[shape[1], shape[0]], ground_y=GROUND_Y, body_len=BODY_LEN, glass=list(GLASS), parts={})

    def save(name, al):
        Image.fromarray(np.dstack([rgb, (np.clip(al, 0, 1) * 255).astype(np.uint8)]), "RGBA").save(os.path.join(OUT, f"{name}.png"))

    cut_all = np.zeros(shape, np.float32)
    for name, leg in LEGS.items():
        pm = ndi.binary_dilation(poly_mask(shape, leg["poly"]), iterations=20)
        save(name, alpha * soft(pm, 1.0))
        cut_all = np.maximum(cut_all, (pm & leg["cut"](xx, yy)).astype(np.float32))
        rig["parts"][name] = dict(pivot=list(leg["pivot"]))
    lsoft = soft(poly_mask(shape, LANTERN["poly"]), 1.0)
    save("lantern", alpha * lsoft)
    rig["parts"]["lantern"] = dict(pivot=list(LANTERN["pivot"]))
    feather = soft(cut_all > 0.5, 7)
    body = alpha * (1 - np.clip(feather * 1.15, 0, 1)) * (1 - lsoft)
    body[yy > BELLY_Y] = 0
    save("body", body)
    with open(os.path.join(OUT, "rig.json"), "w") as f:
        json.dump(rig, f, indent=2)


def check():
    rig = json.load(open(os.path.join(OUT, "rig.json")))
    W, H = rig["size"]
    sheet = Image.new("RGB", (W, H), (110, 120, 135))
    for name in ("fl_far", "hl_far", "hl_near", "fl_near", "lantern", "body"):
        p = Image.open(os.path.join(OUT, f"{name}.png"))
        sheet.paste(p, (0, 0), p)
    d = ImageDraw.Draw(sheet)
    colors = dict(fl_far=(255, 80, 80), fl_near=(255, 200, 60), hl_near=(80, 255, 120), hl_far=(80, 180, 255), lantern=(220, 120, 255))
    for name, p in rig["parts"].items():
        x, y = p["pivot"]
        d.ellipse((x - 8, y - 8, x + 8, y + 8), outline=colors[name], width=3)
        poly = [tuple(v) for v in (LEGS[name]["poly"] if name in LEGS else LANTERN["poly"])]
        d.line(poly + [poly[0]], fill=colors[name], width=2)
    gx, gy = rig["glass"]
    d.ellipse((gx - 6, gy - 6, gx + 6, gy + 6), outline=(255, 255, 255), width=2)
    d.line((0, rig["ground_y"], W, rig["ground_y"]), fill=(255, 255, 255), width=1)
    sheet.resize((W * 3 // 4, H * 3 // 4)).save("/tmp/rig_check.png")
    b = Image.new("RGB", (W, H), (110, 120, 135))
    body = Image.open(os.path.join(OUT, "body.png"))
    b.paste(body, (0, 0), body)
    b.resize((W * 3 // 4, H * 3 // 4)).save("/tmp/rig_body.png")


if __name__ == "__main__":
    if "--check" not in sys.argv:
        build()
    check()
    print("parts in", OUT)

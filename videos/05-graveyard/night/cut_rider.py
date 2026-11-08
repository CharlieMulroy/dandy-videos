"""Cut the painted rider (assets/rider-source.png) into puppet parts for rider.py.

Usage:  python3 videos/05-graveyard/night/cut_rider.py [--check]

The source is a dark figure on a dark background, so colour keying alone loses the belly, the cloak's inner fold
and the far legs. The matte is: GrabCut on a contrast-boosted copy, plus hand-traced polygons for the regions it
misses, minus the lantern's halo (we draw our own light). Parts: four legs (each rotates about a pivot inside the
body), the lantern (swings from the hand) and the body (everything else; the cloak, tail and mane ripple at
draw time). Writes assets/rider/{body,fl_far,fl_near,hl_near,hl_far,lantern}.png at source resolution and
assets/rider/rig.json with pivots, the ground line, the body length and the lantern glass centre.
All coordinates below are source pixels (1448 x 1086).
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "assets", "rider-source.png")
OUT = os.path.join(HERE, "assets", "rider")

# regions GrabCut drops because they are nearly background-dark
FG_POLYS = [
    # belly and the tops of the legs under it
    [(300, 640), (420, 650), (470, 640), (560, 610), (640, 620), (720, 640), (800, 650), (860, 660), (900, 700), (900, 735), (840, 745), (790, 745),
     (760, 760), (740, 760), (700, 752), (620, 755), (540, 748), (470, 735), (420, 720), (380, 700), (330, 690), (300, 680)],
    # the cloak's shadowed inner fold behind the rider's back
    [(640, 280), (700, 300), (780, 330), (860, 355), (880, 380), (850, 395), (780, 395), (700, 400), (640, 410), (610, 400), (610, 330)],
    # rider's face and collar
    [(545, 105), (600, 105), (620, 160), (600, 215), (560, 215), (548, 170)],
]
# the lantern's glow on the background, everything left of the rider and above the mane except arm, hand and lantern
HALO = [(130, 30), (520, 30), (520, 90), (545, 100), (545, 300), (470, 300), (400, 290), (330, 282), (260, 283), (200, 288), (130, 288)]
KEEP_IN_HALO = [
    [(322, 88), (400, 92), (450, 118), (500, 132), (548, 140), (560, 215), (530, 215), (495, 200), (445, 185), (400, 168), (360, 145), (330, 132)],  # hand and arm
    [(500, 50), (690, 60), (690, 110), (500, 115)],                                     # tricorn
    [(130, 268), (190, 268), (190, 330), (130, 330)],                                   # the horse's ears
]
# legs: polygon of the whole leg (with overlap up into the body), the cut line (only the part below/outside it is
# removed from the body layer) and the pivot it rotates about
LEGS = {
    "fl_far": dict(poly=[(345, 635), (300, 640), (240, 653), (188, 662), (158, 684), (124, 758), (88, 783), (52, 838), (25, 900), (115, 900), (112, 842),
                         (136, 800), (176, 742), (206, 712), (262, 703), (300, 702), (345, 702)],
                   cut=lambda x, y: x < 305, pivot=(325, 672)),
    "fl_near": dict(poly=[(455, 640), (400, 645), (330, 668), (288, 688), (255, 703), (246, 732), (268, 764), (298, 802), (318, 838), (362, 864), (445, 864),
                          (436, 824), (402, 798), (346, 788), (322, 758), (304, 738), (334, 722), (400, 708), (455, 706)],
                    cut=lambda x, y: (x < 400) & (y > 660), pivot=(415, 675)),
    "hl_near": dict(poly=[(740, 698), (800, 696), (882, 732), (932, 788), (948, 830), (928, 852), (872, 860), (802, 882), (748, 916), (722, 966), (702, 1004),
                          (650, 1004), (656, 940), (698, 904), (758, 874), (828, 840), (876, 822), (848, 790), (800, 762), (756, 742)],
                    cut=lambda x, y: y > 742, pivot=(800, 722)),
    "hl_far": dict(poly=[(980, 636), (1060, 646), (1100, 668), (1168, 688), (1192, 718), (1232, 778), (1292, 838), (1342, 858), (1394, 888), (1398, 938),
                         (1318, 938), (1288, 892), (1238, 852), (1178, 792), (1138, 762), (1078, 748), (1018, 732), (978, 712)],
                   cut=lambda x, y: (x > 1045) & (y > 655), pivot=(1015, 680)),
}
LANTERN = dict(poly=[(331, 96), (352, 96), (354, 128), (364, 132), (374, 152), (374, 236), (366, 258), (312, 258), (300, 236), (300, 152), (312, 132), (328, 128)], pivot=(341, 100))
GROUND_Y = 990          # where the lowest hoof sits; the shadow goes here
BODY_LEN = 820          # chest to buttock, px
GLASS = (334, 196)      # lantern glass centre


def poly_mask(shape, poly):
    im = Image.new("L", (shape[1], shape[0]), 0)
    ImageDraw.Draw(im).polygon(poly, fill=255)
    return np.asarray(im) > 127


def build():
    rgb = np.asarray(Image.open(SRC).convert("RGB"))
    a = rgb.astype(np.float32)
    lum = a.mean(2)
    shape = lum.shape
    boost = np.clip((a - 8) * 6, 0, 255).astype(np.uint8)
    seed = cv2.GaussianBlur(lum, (0, 0), 3) > 14.5
    lab, n = ndi.label(seed)
    sizes = ndi.sum(seed, lab, range(1, n + 1))
    seed = np.isin(lab, 1 + np.where(sizes > 1500)[0])
    dist = ndi.distance_transform_edt(~seed)
    gc = np.full(shape, cv2.GC_PR_BGD, np.uint8)
    gc[dist > 45] = cv2.GC_BGD
    gc[ndi.binary_erosion(seed, iterations=3)] = cv2.GC_PR_FGD
    gc[ndi.binary_erosion(seed, iterations=12)] = cv2.GC_FGD
    halo = poly_mask(shape, HALO)
    keep = np.zeros(shape, bool)
    for p in KEEP_IN_HALO:
        keep |= poly_mask(shape, p)
    gc[halo & ~keep] = cv2.GC_BGD
    for p in FG_POLYS:
        gc[poly_mask(shape, p)] = cv2.GC_FGD
    gc[:8] = gc[-8:] = cv2.GC_BGD
    gc[:, :8] = gc[:, -8:] = cv2.GC_BGD
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(cv2.cvtColor(boost, cv2.COLOR_RGB2BGR), gc, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    m = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)
    m &= ~(halo & ~keep)
    m = ndi.binary_fill_holes(ndi.binary_closing(m, iterations=2))
    lab, n = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, n + 1))
    m = np.isin(lab, 1 + np.where(sizes > 1500)[0])
    alpha = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.4))).astype(np.float32) / 255

    os.makedirs(OUT, exist_ok=True)
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    cut_all = np.zeros(shape, np.float32)
    rig = dict(size=[shape[1], shape[0]], ground_y=GROUND_Y, body_len=BODY_LEN, glass=list(GLASS), parts={})

    def save(name, al):
        out = np.dstack([rgb, (np.clip(al, 0, 1) * 255).astype(np.uint8)])
        Image.fromarray(out, "RGBA").save(os.path.join(OUT, f"{name}.png"))

    for name, leg in LEGS.items():
        pm = ndi.binary_dilation(poly_mask(shape, leg["poly"]), iterations=22)
        soft = np.asarray(Image.fromarray((pm * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))).astype(np.float32) / 255
        save(name, alpha * soft)
        cut = pm & leg["cut"](xx, yy)
        cut_all = np.maximum(cut_all, cut.astype(np.float32))
        rig["parts"][name] = dict(pivot=list(leg["pivot"]))
    lm = poly_mask(shape, LANTERN["poly"])
    lsoft = np.asarray(Image.fromarray((lm * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))).astype(np.float32) / 255
    save("lantern", lsoft)
    rig["parts"]["lantern"] = dict(pivot=list(LANTERN["pivot"]))
    # body: everything minus the legs below their cut lines (feathered so the joint blends over the leg beneath)
    # and minus the lantern (sharp: it hangs in empty air)
    feather = np.asarray(Image.fromarray((cut_all * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7))).astype(np.float32) / 255
    body = alpha * (1 - np.clip(feather * 1.15, 0, 1)) * (1 - lsoft)
    body[yy > 775] = 0  # nothing of the body hangs below the belly; stray leg strokes there would not move
    save("body", body)
    with open(os.path.join(OUT, "rig.json"), "w") as f:
        json.dump(rig, f, indent=2)
    return alpha


def check():
    """A contact sheet: the matte over a mid-grey, and each part outlined with its pivot."""
    rig = json.load(open(os.path.join(OUT, "rig.json")))
    W, H = rig["size"]
    sheet = Image.new("RGB", (W, H), (110, 120, 135))
    body = Image.open(os.path.join(OUT, "body.png"))
    for name in ("fl_far", "hl_far", "hl_near", "fl_near", "lantern"):
        sheet.paste(Image.open(os.path.join(OUT, f"{name}.png")), (0, 0), Image.open(os.path.join(OUT, f"{name}.png")))
    sheet.paste(body, (0, 0), body)
    d = ImageDraw.Draw(sheet)
    colors = dict(fl_far=(255, 80, 80), fl_near=(255, 200, 60), hl_near=(80, 255, 120), hl_far=(80, 180, 255), lantern=(220, 120, 255))
    for name, p in rig["parts"].items():
        x, y = p["pivot"]
        d.ellipse((x - 8, y - 8, x + 8, y + 8), outline=colors[name], width=3)
        poly = [tuple(v) for v in (LEGS[name]["poly"] if name in LEGS else LANTERN["poly"])]
        d.line(poly + [poly[0]], fill=colors[name], width=2)
    d.line((0, rig["ground_y"], W, rig["ground_y"]), fill=(255, 255, 255), width=1)
    sheet.resize((W // 2 + 362, H // 2 + 272)).save("/tmp/rig_check.png")
    # the body alone, to see the joint feathering
    b = Image.new("RGB", (W, H), (110, 120, 135))
    b.paste(body, (0, 0), body)
    b.resize((W // 2 + 362, H // 2 + 272)).save("/tmp/rig_body.png")


if __name__ == "__main__":
    if "--check" not in sys.argv:
        build()
    check()
    print("parts in", OUT)

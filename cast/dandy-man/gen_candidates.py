"""Generate Dandy Man candidate SVGs from the character sheet.

Run:  python3 cast/dandy-man/gen_candidates.py
Writes cast/dandy-man/candidates/{a,b,c}.svg and PNG previews on the purple background.
viewBox is 0 0 400 800; feet sit on y=780 so the figure anchors to the grid at the feet.
"""
import json
import math
import os

import cairosvg
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "candidates")
os.makedirs(OUT, exist_ok=True)

with open(os.path.join(ROOT, "style", "contract.json")) as f:
    P = json.load(f)["palette"]

PRIMARY, SOFT, TEXT, GOLD, BG, LIFT = (
    P["primary"], P["soft"], P["text"], P["accent_gold"], P["background"], P["background_lift"]
)
SHADE = "#3E1480"  # darker than primary for trousers/shoes; 60% of the figure stays purple


def hat(tilt_deg, tall=True):
    # Classic top hat, sized to the head: crown 68 wide at the base, 78 tall; brim 112 wide.
    # Sits lower on the head (brim line y=206) so it covers the top of the skull.
    base = 206
    top = base - 78 if tall else base - 56
    crown = f"M166 {base} L163 {top + 5} Q163 {top} 168 {top} L232 {top} Q237 {top} 237 {top + 5} L234 {base} Z"
    brim = f"M144 {base + 1} Q145 {base - 6} 151 {base - 5} L249 {base - 5} Q255 {base - 6} 256 {base + 1} Q200 {base + 11} 144 {base + 1} Z"
    return f"""
  <g transform="rotate({tilt_deg} 200 {base})">
    <path d="{crown}" fill="{PRIMARY}"/>
    <rect x="165" y="{base - 18}" width="70" height="12" fill="{GOLD}"/>
    <path d="{brim}" fill="{PRIMARY}"/>
  </g>"""


def head(brow="flat"):
    brow_path = (
        "M176 219 Q186 213 194 219" if brow == "flat" else "M174 214 Q186 204 196 216"
    )
    return f"""
  <circle cx="200" cy="236" r="40" fill="{TEXT}"/>
  <circle cx="186" cy="232" r="3.5" fill="{BG}"/>
  <circle cx="214" cy="232" r="3.5" fill="{BG}"/>
  <path d="{brow_path}" stroke="{BG}" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M206 219 Q214 213 224 219" stroke="{BG}" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M200 254 C194 246 184 247 181 250 C179 253 185 257 200 258 C215 257 221 253 219 250 C216 247 206 246 200 254 Z" fill="{BG}"/>
  <line x1="194" y1="263" x2="206" y2="263" stroke="{BG}" stroke-width="2.5" stroke-linecap="round"/>
  <rect x="191" y="270" width="18" height="32" fill="{TEXT}"/>"""


def body(arms="cane", slim=1.0):
    sw = int(60 * slim)  # half shoulder width
    ww = int(44 * slim)  # half waist width
    coat = (
        f"M{200 - sw} 300 Q{200 - sw - 6} 300 {200 - sw - 4} 312 "
        f"L{200 - ww} 440 L{200 - ww + 6} 560 L{200 - 6} 560 L200 452 "
        f"L{200 + 6} 560 L{200 + ww - 6} 560 L{200 + ww} 440 "
        f"L{200 + sw + 4} 312 Q{200 + sw + 6} 300 {200 + sw} 300 Z"
    )
    waistcoat = f"M{200 - 26} 300 L200 326 L{200 + 26} 300 L{200 + 22} 420 L{200 - 22} 420 Z"
    lapels = (
        f"M{200 - 26} 300 L{200 - 14} 360 L200 326 Z M{200 + 26} 300 L{200 + 14} 360 L200 326 Z"
    )
    collar = ""
    cravat = (f"M199 316 L184 307 L184 325 Z M201 316 L216 307 L216 325 Z "
              f"M196 311 L204 311 L204 321 L196 321 Z")
    buttons = "".join(
        f'<circle cx="200" cy="{y}" r="3" fill="{TEXT}"/>' for y in (350, 374, 398)
    )
    legs = (
        f'<rect x="{200 - ww + 6}" y="430" width="{ww - 12}" height="262" fill="{PRIMARY}"/>'
        f'<rect x="{200 + 6}" y="430" width="{ww - 12}" height="262" fill="{PRIMARY}"/>'
        f'<rect x="{200 - ww + 2}" y="686" width="{ww - 2}" height="14" rx="6" fill="{LIFT}"/>'
        f'<rect x="{200 + 2}" y="686" width="{ww - 2}" height="14" rx="6" fill="{LIFT}"/>'
    )
    if arms == "cane":
        arms_svg = f"""
  <path d="M{200 - sw} 310 L{200 - sw - 16} 430" stroke="{PRIMARY}" stroke-width="24" stroke-linecap="round" fill="none"/>
  <circle cx="{200 - sw - 18}" cy="444" r="12" fill="{TEXT}"/>
  <path d="M{200 + sw} 310 L{200 + sw + 18} 420" stroke="{PRIMARY}" stroke-width="24" stroke-linecap="round" fill="none"/>
  <circle cx="{200 + sw + 22}" cy="434" r="12" fill="{TEXT}"/>
  <path d="M{200 + sw + 22} 424 L{200 + sw + 30} 690" stroke="{SOFT}" stroke-width="7" stroke-linecap="round" fill="none"/>
  <circle cx="{200 + sw + 22}" cy="434" r="12" fill="{TEXT}"/>
  <circle cx="{200 + sw + 22}" cy="416" r="11" fill="{GOLD}"/>
  <rect x="{200 + sw + 26}" y="682" width="9" height="14" rx="3" fill="{SOFT}"/>"""
    elif arms == "behind":
        arms_svg = f"""
  <path d="M{200 - sw} 310 Q{200 - sw - 30} 380 {200 - 10} 420" stroke="{PRIMARY}" stroke-width="22" stroke-linecap="round" fill="none"/>
  <path d="M{200 + sw} 310 Q{200 + sw + 30} 380 {200 + 10} 420" stroke="{PRIMARY}" stroke-width="22" stroke-linecap="round" fill="none"/>"""
    else:  # holding a glowing node out to the right
        arms_svg = f"""
  <path d="M{200 - sw} 310 L{200 - sw - 16} 430" stroke="{PRIMARY}" stroke-width="24" stroke-linecap="round" fill="none"/>
  <circle cx="{200 - sw - 18}" cy="444" r="12" fill="{TEXT}"/>
  <path d="M{200 + sw} 310 L{200 + sw + 70} 372" stroke="{PRIMARY}" stroke-width="24" stroke-linecap="round" fill="none"/>
  <circle cx="{200 + sw + 76}" cy="378" r="12" fill="{TEXT}"/>
  <circle cx="{200 + sw + 96}" cy="352" r="26" fill="{GOLD}" opacity="0.25"/>
  <circle cx="{200 + sw + 96}" cy="352" r="14" fill="{GOLD}"/>"""
    return f"""
  {legs}
  <path d="{coat}" fill="{PRIMARY}"/>
  <path d="{waistcoat}" fill="{SOFT}"/>
  <path d="{lapels}" fill="{PRIMARY}"/>
  {buttons}
  <path d="{collar}" fill="{TEXT}"/>
  <path d="{cravat}" fill="{TEXT}" stroke="{BG}" stroke-width="2.5" stroke-linejoin="round"/>
  {arms_svg}"""


def figure(hat_tilt, arms, slim, brow, tall):
    # Body first, then head and hat so the hat sits on top.
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 700" width="400" height="700">
  {body(arms=arms, slim=slim)}
  {head(brow=brow)}
  {hat(hat_tilt, tall=tall)}
</svg>
"""


CANDIDATES = {
    "a": dict(hat_tilt=0, arms="cane", slim=1.0, brow="flat", tall=True,
              label="A  Classic: straight hat, cane"),
    "b": dict(hat_tilt=-12, arms="behind", slim=0.92, brow="raised", tall=True,
              label="B  Logo tilt, hands behind back, slimmer"),
    "c": dict(hat_tilt=-8, arms="node", slim=1.0, brow="flat", tall=False,
              label="C  Shorter hat, holding the glowing node"),
}


def main():
    previews = []
    for key, spec in CANDIDATES.items():
        label = spec.pop("label")
        svg = figure(**spec)
        path = os.path.join(OUT, f"{key}.svg")
        with open(path, "w") as f:
            f.write(svg)
        png = os.path.join(OUT, f"{key}.png")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=png, output_width=400, output_height=700)
        previews.append((label, png))

    # Contact sheet on the brand background.
    W, H = 400, 700
    pad = 60
    sheet = Image.new("RGB", (len(previews) * (W + pad) + pad, H + pad * 2 + 40), BG)
    for i, (label, png) in enumerate(previews):
        im = Image.open(png).convert("RGBA")
        sheet.paste(im, (pad + i * (W + pad), pad), im)
    sheet.save(os.path.join(OUT, "contact-sheet.png"))
    with open(os.path.join(OUT, "labels.txt"), "w") as f:
        f.write("\n".join(l for l, _ in previews) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()

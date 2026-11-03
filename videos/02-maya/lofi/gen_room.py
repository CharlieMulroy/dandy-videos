"""Video 02's own look: a cozy room at night, drawn as layered SVGs in 1080x1920 room coordinates.

Run:  python3 videos/02-maya/lofi/gen_room.py
Writes videos/02-maya/lofi/layers/*.svg:
  back.svg          wall, window frame and sky, board frame, floor, rug, plant, cat
  maya-<pose>.svg   typing | slumped | up (sitting up, hand off the keyboard)
  front.svg         desk, monitor bezel, lamp, mug, keyboard (in front of Maya's legs)
Everything that moves or carries text (rain, steam, screen, sticky notes, sky phase) is drawn by render_lofi.py.
Colours stay in the contract palette plus two warm tones for wood and skin.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "layers")
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(ROOT, "style", "contract.json")) as f:
    P = json.load(f)["palette"]
BG, LIFT, PRIMARY, HI, SOFT, TEXT, GOLD, WARN = (P[k] for k in ("background", "background_lift", "primary", "highlight", "soft", "text", "accent_gold", "warning"))
WOOD, WOOD_DARK, SKIN, HAIR, JEANS = "#4A3566", "#33234A", "#F1C9A5", "#2B1A3F", "#3D2A72"
W, H = 1080, 1920
FLOOR = 1420

# shared geometry (render_lofi.py imports these)
WINDOW = (640, 300, 1000, 760)      # x0, y0, x1, y1
BOARD = (80, 330, 580, 780)
SCREEN = (560, 900, 900, 1120)      # monitor screen (inside the bezel)
DESK_Y = 1180
MUG = (955, 1104)                   # mug top centre (steam rises from here)


def svg(body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">\n' + "\n".join(body) + "\n</svg>\n"


def holed(fill):
    """The wall as four rectangles around the window hole (cairosvg has no mask support)."""
    x0, y0, x1, y1 = WINDOW
    return [f'<rect x="0" y="0" width="{W}" height="{y0}" fill="{fill}"/>',
            f'<rect x="0" y="{y1}" width="{W}" height="{FLOOR - y1}" fill="{fill}"/>',
            f'<rect x="0" y="{y0}" width="{x0}" height="{y1 - y0}" fill="{fill}"/>',
            f'<rect x="{x1}" y="{y0}" width="{W - x1}" height="{y1 - y0}" fill="{fill}"/>']


def back():
    x0, y0, x1, y1 = WINDOW
    bx0, by0, bx1, by1 = BOARD
    b = [
        '<defs>',
        f'  <linearGradient id="wall" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{FLOOR}"><stop offset="0" stop-color="{BG}"/><stop offset="1" stop-color="{LIFT}"/></linearGradient>',
        f'  <radialGradient id="lamp" gradientUnits="userSpaceOnUse" cx="{W * 0.88}" cy="{FLOOR * 0.5}" r="{W * 0.55}"><stop offset="0" stop-color="{GOLD}" stop-opacity="0.22"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>',
        f'  <radialGradient id="screenlight" gradientUnits="userSpaceOnUse" cx="{W * 0.67}" cy="{FLOOR * 0.53}" r="{W * 0.3}"><stop offset="0" stop-color="{HI}" stop-opacity="0.18"/><stop offset="1" stop-color="{HI}" stop-opacity="0"/></radialGradient>',
        '</defs>',
        *holed("url(#wall)"),
        # skirting + floor
        f'<rect x="0" y="{FLOOR}" width="{W}" height="{H - FLOOR}" fill="#120A20"/>',
        f'<rect x="0" y="{FLOOR - 18}" width="{W}" height="18" fill="{LIFT}"/>',
        # floorboards
        *[f'<line x1="0" y1="{FLOOR + 70 + i * 90}" x2="{W}" y2="{FLOOR + 70 + i * 90}" stroke="{BG}" stroke-width="3"/>' for i in range(6)],
        # rug
        f'<ellipse cx="420" cy="1690" rx="330" ry="110" fill="{LIFT}"/>',
        f'<ellipse cx="420" cy="1690" rx="300" ry="92" fill="none" stroke="{PRIMARY}" stroke-width="10" opacity="0.7"/>',
        f'<ellipse cx="420" cy="1690" rx="200" ry="58" fill="none" stroke="{PRIMARY}" stroke-width="8" opacity="0.5"/>',
        # window: frame, sky placeholder (render draws the sky phase under this), bars, sill
        f'<rect x="{x0 - 9}" y="{y0 - 9}" width="{x1 - x0 + 18}" height="{y1 - y0 + 18}" rx="6" fill="none" stroke="{WOOD}" stroke-width="18"/>',
        f'<line x1="{(x0 + x1) / 2}" y1="{y0}" x2="{(x0 + x1) / 2}" y2="{y1}" stroke="{WOOD}" stroke-width="10"/>',
        f'<line x1="{x0}" y1="{(y0 + y1) / 2}" x2="{x1}" y2="{(y0 + y1) / 2}" stroke="{WOOD}" stroke-width="10"/>',
        f'<rect x="{x0 - 30}" y="{y1 + 18}" width="{x1 - x0 + 60}" height="22" rx="6" fill="{WOOD}"/>',
        # curtain on the left of the window
        f'<path d="M{x0 - 70} {y0 - 40} L{x0 + 30} {y0 - 40} Q{x0 + 10} {(y0 + y1) / 2} {x0 + 40} {y1 + 10} L{x0 - 70} {y1 + 10} Z" fill="{PRIMARY}" opacity="0.85"/>',
        f'<rect x="{x0 - 90}" y="{y0 - 54}" width="{x1 - x0 + 160}" height="14" rx="7" fill="{WOOD}"/>',
        # bulletin board: cork, frame
        f'<rect x="{bx0 - 16}" y="{by0 - 16}" width="{bx1 - bx0 + 32}" height="{by1 - by0 + 32}" rx="12" fill="{WOOD}"/>',
        f'<rect x="{bx0}" y="{by0}" width="{bx1 - bx0}" height="{by1 - by0}" rx="6" fill="#5A4463"/>',
        f'<rect x="{bx0}" y="{by0}" width="{bx1 - bx0}" height="{by1 - by0}" rx="6" fill="url(#wall)" opacity="0.35"/>',
        # fairy lights along the top of the wall
        f'<path d="M0 150 Q270 230 540 150 T1080 150" stroke="{LIFT}" stroke-width="4" fill="none"/>',
        *[f'<circle cx="{60 + i * 108}" cy="{150 + (60 if i % 2 else 10) + (i % 3) * 8}" r="9" fill="{GOLD}" opacity="{0.55 + 0.15 * (i % 3)}"/>' for i in range(10)],
        # shelf above the board with books and a small plant
        f'<rect x="{bx0 - 10}" y="240" width="300" height="16" rx="5" fill="{WOOD}"/>',
        f'<rect x="{bx0 + 10}" y="176" width="26" height="64" rx="3" fill="{PRIMARY}"/>',
        f'<rect x="{bx0 + 40}" y="190" width="22" height="50" rx="3" fill="{SOFT}"/>',
        f'<rect x="{bx0 + 66}" y="168" width="30" height="72" rx="3" fill="{HI}"/>',
        f'<rect x="{bx0 + 100}" y="196" width="20" height="44" rx="3" fill="{GOLD}" opacity="0.8"/>',
        f'<rect x="{bx0 + 200}" y="206" width="44" height="34" rx="6" fill="{WOOD_DARK}"/>',
        f'<path d="M{bx0 + 222} 206 Q{bx0 + 190} 160 {bx0 + 200} 140 Q{bx0 + 222} 170 {bx0 + 222} 206 M{bx0 + 222} 206 Q{bx0 + 250} 156 {bx0 + 262} 150 Q{bx0 + 240} 180 {bx0 + 222} 206" fill="#3F8E6A"/>',
        # tall plant on the floor, right
        f'<g transform="translate(-900 0)"><rect x="958" y="1330" width="84" height="100" rx="14" fill="{WOOD_DARK}"/>',
        f'<path d="M1000 1330 Q930 1250 950 1150 Q1000 1210 1000 1330 M1000 1330 Q1060 1240 1070 1140 Q1010 1200 1000 1330 M1000 1330 Q980 1230 1010 1100 Q1030 1200 1000 1330 M1000 1330 Q900 1290 880 1210 Q960 1250 1000 1330 M1000 1330 Q1100 1300 1120 1220 Q1040 1250 1000 1330" fill="#3F8E6A"/></g>',
        # cat asleep on the rug
        f'<ellipse cx="300" cy="1640" rx="96" ry="40" fill="{SOFT}"/>',
        f'<circle cx="380" cy="1612" r="34" fill="{SOFT}"/>',
        f'<path d="M356 1588 L352 1556 L376 1580 Z M404 1588 L408 1556 L384 1580 Z" fill="{SOFT}"/>',
        f'<path d="M206 1646 Q160 1620 186 1588" stroke="{SOFT}" stroke-width="16" stroke-linecap="round" fill="none"/>',
        f'<path d="M366 1616 Q372 1622 378 1616 M386 1616 Q392 1622 398 1616" stroke="{BG}" stroke-width="3" fill="none" stroke-linecap="round"/>',
        # light pools (lamp warm, screen cool) on the wall
        *holed("url(#lamp)"),
        *holed("url(#screenlight)"),
    ]
    return svg(b)


def maya(pose="typing"):
    """Side view, facing right, seated at x~300. Hoodie in logo purple, bun, headphones."""
    hip = (300, 1250)
    b = ['<defs>',
         f'  <linearGradient id="hood" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{HI}"/><stop offset="1" stop-color="{PRIMARY}"/></linearGradient>',
         '</defs>']
    # chair (behind her)
    b += [
        f'<rect x="180" y="1040" width="34" height="240" rx="14" fill="{WOOD_DARK}"/>',          # back
        f'<rect x="190" y="1255" width="190" height="30" rx="12" fill="{WOOD_DARK}"/>',         # seat
        f'<rect x="272" y="1285" width="26" height="110" fill="{WOOD_DARK}"/>',                 # post
        f'<path d="M200 1400 L370 1400 M285 1395 L285 1370" stroke="{WOOD_DARK}" stroke-width="18" stroke-linecap="round"/>',
    ]
    if pose == "slumped":
        torso = f'<path d="M{hip[0] - 10} 1270 Q{hip[0] + 40} 1120 {hip[0] + 150} 1148 L{hip[0] + 170} 1200 Q{hip[0] + 60} 1200 {hip[0] + 30} 1280 Z" fill="url(#hood)"/>'
        head_c = (hip[0] + 175, 1150)
        arm = f'<path d="M{hip[0] + 90} 1180 L{hip[0] + 220} 1176" stroke="url(#hood)" stroke-width="44" stroke-linecap="round" fill="none"/>'
        hand = f'<circle cx="{hip[0] + 232}" cy="1176" r="20" fill="{SKIN}"/>'
    else:
        lean = 0 if pose == "up" else 24
        torso = f'<path d="M{hip[0] - 20} 1270 L{hip[0] - 8} 1000 Q{hip[0] + 40 + lean} 960 {hip[0] + 110 + lean} 1010 L{hip[0] + 60 + lean} 1270 Z" fill="url(#hood)"/>'
        head_c = (hip[0] + 60 + lean, 930)
        if pose == "up":
            arm = f'<path d="M{hip[0] + 40} 1060 Q{hip[0] + 120} 1100 {hip[0] + 150} 1040" stroke="url(#hood)" stroke-width="44" stroke-linecap="round" fill="none"/>'
            hand = f'<circle cx="{hip[0] + 156}" cy="1030" r="20" fill="{SKIN}"/>'
        else:
            arm = f'<path d="M{hip[0] + 50} 1070 Q{hip[0] + 120} 1120 {hip[0] + 190} 1166" stroke="url(#hood)" stroke-width="44" stroke-linecap="round" fill="none"/>'
            hand = f'<circle cx="{hip[0] + 200}" cy="1170" r="20" fill="{SKIN}"/>'
    hx, hy = head_c
    b += [
        # legs: thigh forward, shin down (jeans)
        f'<path d="M{hip[0]} 1262 L{hip[0] + 150} 1262 L{hip[0] + 150} 1400" stroke="{JEANS}" stroke-width="52" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
        f'<ellipse cx="{hip[0] + 168}" cy="1408" rx="40" ry="16" fill="{TEXT}"/>',               # shoe
        torso,
        arm,
        hand,
        # neck + head
        f'<circle cx="{hx}" cy="{hy}" r="54" fill="{SKIN}"/>',
        # hair: cap over the back of the head, bun behind
        f'<path d="M{hx - 56} {hy + 12} Q{hx - 64} {hy - 64} {hx} {hy - 60} Q{hx + 50} {hy - 58} {hx + 52} {hy - 14} Q{hx + 22} {hy - 36} {hx - 18} {hy - 22} Q{hx - 40} {hy - 8} {hx - 56} {hy + 12} Z" fill="{HAIR}"/>',
        f'<circle cx="{hx - 64}" cy="{hy - 28}" r="24" fill="{HAIR}"/>',
        # headphones: band and cup
        f'<path d="M{hx - 44} {hy - 10} Q{hx - 10} {hy - 78} {hx + 36} {hy - 44}" stroke="{TEXT}" stroke-width="9" fill="none" stroke-linecap="round"/>',
        f'<rect x="{hx - 60}" y="{hy - 20}" width="26" height="40" rx="10" fill="{TEXT}"/>',
        # eye and brow (facing right)
        f'<circle cx="{hx + 30}" cy="{hy - 4}" r="5" fill="{HAIR}"/>',
        f'<path d="M{hx + 18} {hy - 20} Q{hx + 32} {hy - 26} {hx + 42} {hy - 18}" stroke="{HAIR}" stroke-width="4" fill="none" stroke-linecap="round"/>',
    ]
    if pose == "slumped":
        b.append(f'<path d="M{hx + 24} {hy + 22} Q{hx + 34} {hy + 18} {hx + 42} {hy + 24}" stroke="{HAIR}" stroke-width="4" fill="none" stroke-linecap="round"/>')  # small frown
    return svg(b)


def front():
    sx0, sy0, sx1, sy1 = SCREEN
    b = [
        # desk top and legs
        f'<rect x="360" y="{DESK_Y}" width="690" height="34" rx="10" fill="{WOOD}"/>',
        f'<rect x="380" y="{DESK_Y + 34}" width="26" height="{FLOOR - DESK_Y - 34}" fill="{WOOD_DARK}"/>',
        f'<rect x="1004" y="{DESK_Y + 34}" width="26" height="{FLOOR - DESK_Y - 34}" fill="{WOOD_DARK}"/>',
        f'<rect x="380" y="{DESK_Y + 120}" width="650" height="14" fill="{WOOD_DARK}"/>',
        # monitor: stand, bezel; the screen itself is drawn by the renderer
        f'<rect x="{(sx0 + sx1) / 2 - 16}" y="{sy1 + 20}" width="32" height="40" fill="{WOOD_DARK}"/>',
        f'<rect x="{(sx0 + sx1) / 2 - 90}" y="{DESK_Y - 16}" width="180" height="16" rx="6" fill="{WOOD_DARK}"/>',
        f'<rect x="{sx0 - 18}" y="{sy0 - 18}" width="{sx1 - sx0 + 36}" height="{sy1 - sy0 + 36}" rx="14" fill="#120A20"/>',
        # keyboard
        f'<rect x="430" y="{DESK_Y - 14}" width="210" height="14" rx="5" fill="{LIFT}"/>',
        # lamp: base, arm, shade, bulb glow
        f'<ellipse cx="1030" cy="{DESK_Y + 2}" rx="36" ry="10" fill="{WOOD_DARK}"/>',
        f'<path d="M1030 {DESK_Y} L1030 980 L975 890" stroke="{WOOD_DARK}" stroke-width="12" stroke-linecap="round" fill="none"/>',
        f'<path d="M930 870 L1010 870 L1040 920 L905 920 Z" fill="{PRIMARY}"/>',
        f'<ellipse cx="972" cy="922" rx="60" ry="12" fill="{GOLD}" opacity="0.9"/>',
        # mug
        f'<rect x="{MUG[0] - 32}" y="{MUG[1]}" width="64" height="72" rx="10" fill="{SOFT}"/>',
        f'<path d="M{MUG[0] + 32} {MUG[1] + 18} Q{MUG[0] + 70} {MUG[1] + 36} {MUG[0] + 32} {MUG[1] + 56}" stroke="{SOFT}" stroke-width="10" fill="none"/>',
        f'<ellipse cx="{MUG[0]}" cy="{MUG[1]}" rx="32" ry="8" fill="{TEXT}" opacity="0.5"/>',
        # a sticky note stuck to the monitor bezel
        f'<rect x="{sx1 - 40}" y="{sy0 - 10}" width="56" height="56" rx="3" fill="{GOLD}" transform="rotate(8 {sx1 - 12} {sy0 + 18})" opacity="0.9"/>',
    ]
    return svg(b)


FILES = {"back.svg": back(), "front.svg": front(), "maya-typing.svg": maya("typing"),
         "maya-slumped.svg": maya("slumped"), "maya-up.svg": maya("up")}

if __name__ == "__main__":
    for name, content in FILES.items():
        with open(os.path.join(OUT, name), "w") as f:
            f.write(content)
        print("wrote", os.path.relpath(os.path.join(OUT, name), ROOT))

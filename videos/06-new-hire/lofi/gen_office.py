"""Video 06's look: the Maya lofi style (video 02) moved to an office on a quiet morning.

Run:  python3 videos/06-new-hire/lofi/gen_office.py
Writes videos/06-new-hire/lofi/layers/*.svg in 1080x1920 room coordinates:
  back.svg          wall, window and blinds, whiteboard frame, clock face, shelf, plant, floor
  hire-<pose>.svg   typing | confused | binder (seated, facing right) | board (standing, facing left)
  front.svg         desk, three monitor bezels, keyboard, mug
Everything that moves or carries text (sky, light beams, dust, clock hands, whiteboard marks, monitor
contents, sticky notes, the Dandy panel) is drawn per frame by render_office.py.
The room is cool blue-grey and warm wood; brand purple is kept for the Dandy panel and the end card.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(HERE, "layers")
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(ROOT, "style", "contract.json")) as f:
    P = json.load(f)["palette"]
TEXT = P["text"]

# office palette (story colours; brand purple stays out of the room)
WALL_TOP, WALL_BOT = "#222B40", "#2E3954"
FLOOR_C, SKIRT = "#161B29", "#3A4562"
WOOD, WOOD_DARK = "#7A5A44", "#4E3A2E"
METAL, METAL_DARK = "#5B6680", "#3A4357"
BEZEL = "#0E1220"
BLIND = "#B9C3D6"
BOARD_FRAME = "#9AA6BD"
BOARD_FACE = "#E9EDF3"
LEAF = "#3F8E6A"
SKIN, HAIR = "#E9BE98", "#2A2230"
SHIRT, SHIRT_DARK = "#8FB0DA", "#6E8FBC"
TIE = "#22304F"
TROUSERS, SHOE = "#3A4256", "#2A1E18"
GLASSES = "#1F1A24"
LANYARD = "#E9EDF3"

W, H = 1080, 1920
FLOOR = 1420

# shared geometry (render_office.py imports these)
WINDOW = (640, 280, 1010, 700)
BOARD = (80, 330, 580, 760)                 # whiteboard face
CLOCK = (520, 190, 46)                      # cx, cy, r
DESK_Y = 1180
SCREEN = (650, 880, 930, 1100)              # main monitor screen (chat, Dandy panel)
SCREEN_L = (480, 930, 620, 1090)            # left monitor screen
SCREEN_R = (955, 930, 1060, 1090)           # right monitor screen
MUG = (895, 1110)
HEAD = {"typing": (384, 930), "confused": (360, 920), "binder": (360, 930), "board": (700, 820)}


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
    cx, cy, cr = CLOCK
    b = [
        '<defs>',
        f'  <linearGradient id="wall" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{FLOOR}"><stop offset="0" stop-color="{WALL_TOP}"/><stop offset="1" stop-color="{WALL_BOT}"/></linearGradient>',
        f'  <radialGradient id="sun" gradientUnits="userSpaceOnUse" cx="{(x0 + x1) / 2}" cy="{(y0 + y1) / 2}" r="{W * 0.6}"><stop offset="0" stop-color="#F3D9B1" stop-opacity="0.16"/><stop offset="1" stop-color="#F3D9B1" stop-opacity="0"/></radialGradient>',
        '</defs>',
        *holed("url(#wall)"),
        # floor, skirting, carpet tiles
        f'<rect x="0" y="{FLOOR}" width="{W}" height="{H - FLOOR}" fill="{FLOOR_C}"/>',
        f'<rect x="0" y="{FLOOR - 18}" width="{W}" height="18" fill="{SKIRT}"/>',
        *[f'<line x1="0" y1="{FLOOR + 80 + i * 100}" x2="{W}" y2="{FLOOR + 80 + i * 100}" stroke="{WALL_TOP}" stroke-width="3"/>' for i in range(5)],
        *[f'<line x1="{i * 180}" y1="{FLOOR}" x2="{i * 180 - 120}" y2="{H}" stroke="{WALL_TOP}" stroke-width="3"/>' for i in range(1, 8)],
        # window frame; blinds are horizontal slats with gaps (the sky shows through the gaps)
        *[f'<rect x="{x0}" y="{y}" width="{x1 - x0}" height="22" fill="{BLIND}" opacity="0.92"/>' for y in range(y0 + 8, y1 - 10, 34)],
        f'<line x1="{x0 + 70}" y1="{y0}" x2="{x0 + 70}" y2="{y1}" stroke="{METAL_DARK}" stroke-width="3"/>',
        f'<line x1="{x1 - 70}" y1="{y0}" x2="{x1 - 70}" y2="{y1}" stroke="{METAL_DARK}" stroke-width="3"/>',
        f'<rect x="{x0 - 12}" y="{y0 - 12}" width="{x1 - x0 + 24}" height="{y1 - y0 + 24}" rx="6" fill="none" stroke="{METAL}" stroke-width="20"/>',
        f'<rect x="{x0 - 24}" y="{y0 - 30}" width="{x1 - x0 + 48}" height="26" rx="6" fill="{METAL}"/>',
        f'<rect x="{x0 - 30}" y="{y1 + 12}" width="{x1 - x0 + 60}" height="20" rx="6" fill="{METAL}"/>',
        # whiteboard: frame, face, tray
        f'<rect x="{bx0 - 14}" y="{by0 - 14}" width="{bx1 - bx0 + 28}" height="{by1 - by0 + 28}" rx="10" fill="{BOARD_FRAME}"/>',
        f'<rect x="{bx0}" y="{by0}" width="{bx1 - bx0}" height="{by1 - by0}" rx="4" fill="{BOARD_FACE}"/>',
        f'<rect x="{bx0 + 40}" y="{by1 + 14}" width="{bx1 - bx0 - 80}" height="16" rx="5" fill="{BOARD_FRAME}"/>',
        f'<rect x="{bx0 + 90}" y="{by1 + 6}" width="54" height="10" rx="4" fill="#2F6FD6"/>',
        f'<rect x="{bx0 + 160}" y="{by1 + 6}" width="54" height="10" rx="4" fill="#D64545"/>',
        # wall clock (hands drawn per frame)
        f'<circle cx="{cx}" cy="{cy}" r="{cr + 8}" fill="{METAL}"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{cr}" fill="{BOARD_FACE}"/>',
        *[f'<line x1="{cx}" y1="{cy - cr + 6}" x2="{cx}" y2="{cy - cr + 14}" stroke="{METAL_DARK}" stroke-width="4" transform="rotate({k * 30} {cx} {cy})"/>' for k in range(12)],
        # shelf above the window side with binders
        f'<rect x="140" y="250" width="260" height="14" rx="5" fill="{WOOD}"/>',
        *[f'<rect x="{150 + i * 30}" y="{180 + (i % 2) * 8}" width="24" height="{70 - (i % 2) * 8}" rx="3" fill="{c}"/>' for i, c in enumerate(("#4C6FA8", "#7D8AA6", "#4C6FA8", "#A3784F", "#7D8AA6"))],
        f'<rect x="320" y="210" width="50" height="40" rx="6" fill="{WOOD_DARK}"/>',
        f'<path d="M345 210 Q320 170 330 150 Q345 180 345 210 M345 210 Q370 166 382 160 Q362 188 345 210" fill="{LEAF}"/>',
        # tall plant, floor left
        f'<rect x="46" y="1320" width="84" height="100" rx="14" fill="{WOOD_DARK}"/>',
        f'<path d="M88 1320 Q18 1240 38 1140 Q88 1200 88 1320 M88 1320 Q148 1230 158 1130 Q98 1190 88 1320 M88 1320 Q68 1220 98 1090 Q118 1190 88 1320 M88 1320 Q-12 1280 -32 1200 Q48 1240 88 1320" fill="{LEAF}"/>',
        # warm glow around the window on the wall
        *holed("url(#sun)"),
    ]
    return svg(b)


def cape_behind(sx, sy, length, flare=0):
    """Cape hanging from the shoulders at (sx, sy), draped down the back."""
    return [f'<path d="M{sx - 30} {sy - 10} Q{sx - 95 - flare} {sy + length * 0.45} {sx - 80 - flare} {sy + length} L{sx + 20} {sy + length - 20} Q{sx + 10} {sy + length * 0.5} {sx + 30} {sy - 6} Z" fill="{CAPE}"/>',
            f'<path d="M{sx - 30} {sy - 10} Q{sx - 95 - flare} {sy + length * 0.45} {sx - 80 - flare} {sy + length} L{sx - 46 - flare / 2} {sy + length - 6} Q{sx - 60} {sy + length * 0.5} {sx - 14} {sy - 4} Z" fill="{CAPE_DARK}" opacity="0.7"/>']


def head(hx, hy, facing=1, brow_up=False, down=False):
    f = facing
    b = [f'<circle cx="{hx}" cy="{hy}" r="54" fill="{SKIN}"/>',
         # ear
         f'<ellipse cx="{hx - 14 * f}" cy="{hy + 6}" rx="10" ry="14" fill="{SKIN}" stroke="#D9A882" stroke-width="2"/>',
         # short hair with a quiff at the front
         f'<path d="M{hx - 56 * f} {hy + 6} Q{hx - 62 * f} {hy - 60} {hx} {hy - 62} Q{hx + 50 * f} {hy - 76} {hx + 62 * f} {hy - 40} Q{hx + 34 * f} {hy - 44} {hx + 20 * f} {hy - 30} Q{hx - 20 * f} {hy - 34} {hx - 30 * f} {hy - 10} Q{hx - 44 * f} {hy - 2} {hx - 56 * f} {hy + 6} Z" fill="{HAIR}"/>',
         # eye, brow, small smile
         f'<circle cx="{hx + 30 * f}" cy="{hy + (5 if down else -2)}" r="5" fill="{HAIR}"/>',
         # glasses: one round lens seen side-on, a bridge stub at the nose and the arm back to the ear
         f'<circle cx="{hx + 32 * f}" cy="{hy - 2}" r="15" fill="#DDE6F2" fill-opacity="0.25" stroke="{GLASSES}" stroke-width="4"/>',
         f'<line x1="{hx + 47 * f}" y1="{hy - 4}" x2="{hx + 54 * f}" y2="{hy - 6}" stroke="{GLASSES}" stroke-width="4" stroke-linecap="round"/>',
         f'<line x1="{hx + 17 * f}" y1="{hy - 4}" x2="{hx - 10 * f}" y2="{hy}" stroke="{GLASSES}" stroke-width="4" stroke-linecap="round"/>']
    by = -26 if brow_up else -18
    b.append(f'<path d="M{hx + 18 * f} {hy + by} Q{hx + 32 * f} {hy + by - 6} {hx + 44 * f} {hy + by + 2}" stroke="{HAIR}" stroke-width="4" fill="none" stroke-linecap="round"/>')
    if brow_up:
        b.append(f'<ellipse cx="{hx + 34 * f}" cy="{hy + 26}" rx="6" ry="7" fill="#9C5D4A"/>')  # small "o" mouth
    else:
        b.append(f'<path d="M{hx + 24 * f} {hy + 22} Q{hx + 34 * f} {hy + 30} {hx + 44 * f} {hy + 22}" stroke="#9C5D4A" stroke-width="4" fill="none" stroke-linecap="round"/>')
    return b


def torso_seated(hip, lean):
    """Shirt, tie, lanyard for a seated figure facing right."""
    x, y = hip
    return [f'<path d="M{x - 20} 1270 L{x - 8} 1000 Q{x + 40 + lean} 958 {x + 112 + lean} 1008 L{x + 62 + lean} 1270 Z" fill="{SHIRT}"/>',
            f'<path d="M{x - 20} 1270 L{x - 8} 1000 Q{x + 6 + lean / 2} 984 {x + 20 + lean / 2} 990 L{x + 8} 1270 Z" fill="{SHIRT_DARK}" opacity="0.6"/>',
            # collar and tie down the front edge
            f'<path d="M{x + 74 + lean} 986 L{x + 98 + lean} 1000 L{x + 84 + lean} 1012 Z" fill="{LANYARD}"/>',
            f'<path d="M{x + 92 + lean} 1004 L{x + 102 + lean} 1012 L{x + 82 + lean} 1150 L{x + 70 + lean} 1136 Z" fill="{TIE}"/>',
            # lanyard and badge
            f'<path d="M{x + 40 + lean} 990 L{x + 66 + lean} 1080" stroke="{LANYARD}" stroke-width="5" fill="none"/>',
            f'<rect x="{x + 54 + lean}" y="1078" width="30" height="40" rx="4" fill="{LANYARD}"/>',
            f'<rect x="{x + 60 + lean}" y="1086" width="18" height="6" rx="2" fill="{METAL}"/>']


def legs_seated(hip):
    x, y = hip
    return [f'<path d="M{x} 1262 L{x + 150} 1262 L{x + 150} 1400" stroke="{TROUSERS}" stroke-width="54" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
            f'<ellipse cx="{x + 170}" cy="{1408}" rx="42" ry="16" fill="{SHOE}"/>']


def chair():
    return [f'<rect x="180" y="1030" width="34" height="250" rx="14" fill="{METAL_DARK}"/>',
            f'<rect x="190" y="1255" width="190" height="30" rx="12" fill="{METAL_DARK}"/>',
            f'<rect x="272" y="1285" width="26" height="110" fill="{METAL_DARK}"/>',
            f'<path d="M200 1400 L370 1400 M285 1395 L285 1370" stroke="{METAL_DARK}" stroke-width="18" stroke-linecap="round"/>']


def hire(pose="typing"):
    hip = (300, 1250)
    x = hip[0]
    b = []
    if pose == "board":
        # standing beside the whiteboard, facing left, marker raised to the board's right edge
        hx, hy = HEAD["board"]
        sx, sy = hx + 6, 900
        b += [f'<path d="M{sx - 40} 1180 L{sx - 46} {FLOOR - 10} M{sx + 30} 1180 L{sx + 36} {FLOOR - 10}" stroke="{TROUSERS}" stroke-width="54" stroke-linecap="round"/>',
              f'<ellipse cx="{sx - 66}" cy="{FLOOR - 4}" rx="40" ry="14" fill="{SHOE}"/>',
              f'<ellipse cx="{sx + 16}" cy="{FLOOR - 4}" rx="40" ry="14" fill="{SHOE}"/>',
              f'<path d="M{sx - 70} 1200 L{sx - 64} 900 Q{sx} 862 {sx + 64} 900 L{sx + 70} 1200 Z" fill="{SHIRT}"/>',
              f'<path d="M{sx + 20} 900 Q{sx + 64} 902 {sx + 64} 900 L{sx + 70} 1200 L{sx + 30} 1200 Z" fill="{SHIRT_DARK}" opacity="0.5"/>',
              f'<path d="M{sx - 8} 904 L{sx + 8} 904 L{sx + 12} 1060 L{sx} 1080 L{sx - 12} 1060 Z" fill="{TIE}"/>',
              f'<rect x="{sx + 18}" y="990" width="30" height="40" rx="4" fill="{LANYARD}"/>',
              # far arm relaxed, near arm raised to the board with a marker
              f'<path d="M{sx + 50} 920 Q{sx + 70} 1020 {sx + 56} 1110" stroke="{SHIRT_DARK}" stroke-width="40" stroke-linecap="round" fill="none"/>',
              f'<circle cx="{sx + 56}" cy="{1120}" r="19" fill="{SKIN}"/>',
              f'<path d="M{sx - 50} 924 Q{sx - 110} 860 {sx - 150} 760" stroke="{SHIRT}" stroke-width="42" stroke-linecap="round" fill="none"/>',
              f'<circle cx="{sx - 154}" cy="{750}" r="20" fill="{SKIN}"/>',
              f'<rect x="{sx - 172}" y="{714}" width="12" height="40" rx="4" fill="#2F6FD6" transform="rotate(-30 {sx - 166} {734})"/>']
        b += head(hx, hy, facing=-1)
        return svg(b)
    b += chair()
    b += legs_seated(hip)
    lean = 24 if pose == "typing" else (6 if pose == "confused" else 10)
    b += torso_seated(hip, lean)
    hx, hy = HEAD[pose]
    if pose == "typing":
        b += [f'<path d="M{x + 50} 1070 Q{x + 120} 1120 {x + 200} 1162" stroke="{SHIRT}" stroke-width="42" stroke-linecap="round" fill="none"/>',
              f'<circle cx="{x + 210}" cy="1166" r="20" fill="{SKIN}"/>']
    elif pose == "confused":
        # puzzled: near elbow on the desk edge, forearm up, hand at the chin
        b += [f'<path d="M{x + 60} 1060 Q{x + 100} 1150 {x + 140} 1170" stroke="{SHIRT}" stroke-width="42" stroke-linecap="round" fill="none"/>',
              f'<path d="M{x + 140} 1170 Q{x + 128} 1080 {x + 106} {hy + 50}" stroke="{SHIRT}" stroke-width="38" stroke-linecap="round" fill="none"/>',
              f'<circle cx="{x + 100}" cy="{hy + 46}" r="20" fill="{SKIN}"/>']
    elif pose == "binder":
        # the arm reaching up to the binder; the binder itself is binder.svg, drawn above the desk
        b += [f'<path d="M{x + 40} 1060 Q{x + 100} 1120 {x + 136} 1112" stroke="{SHIRT}" stroke-width="42" stroke-linecap="round" fill="none"/>']
    b += head(hx, hy, facing=1, brow_up=(pose == "confused"), down=(pose == "binder"))
    return svg(b)


BINDER = (452, 1050)   # centre of the book he holds at chest height


def binder():
    """A book held open toward his face, seen from the side: we see its back cover tipped toward him, a sliver of
    page edge along the top, and his hand around the near bottom corner. Nothing on it moves."""
    x, y = BINDER
    tl, tr, br, bl = (x - 48, y - 62), (x + 14, y - 74), (x + 40, y + 58), (x - 22, y + 70)
    b = [f'<path d="M{tl[0]} {tl[1]} L{tr[0]} {tr[1]} L{tr[0] + 6} {tr[1] + 10} L{tl[0] + 6} {tl[1] + 10} Z" fill="{BOARD_FACE}"/>',
         f'<path d="M{tl[0] + 6} {tl[1] + 10} L{tr[0] + 6} {tr[1] + 10} L{br[0]} {br[1]} L{bl[0]} {bl[1]} Z" fill="#3E5C92"/>',
         f'<path d="M{tl[0] + 6} {tl[1] + 10} L{bl[0]} {bl[1]} L{bl[0] + 10} {bl[1] - 2} L{tl[0] + 15} {tl[1] + 9} Z" fill="#2F4A78"/>',
         f'<path d="M{tl[0] + 22} {tl[1] + 34} L{tr[0] - 6} {tr[1] + 26}" stroke="#7D97C4" stroke-width="4" stroke-linecap="round"/>',
         f'<circle cx="{bl[0] + 14}" cy="{bl[1] - 8}" r="19" fill="{SKIN}"/>',
         f'<circle cx="{br[0] - 2}" cy="{br[1] - 30}" r="17" fill="{SKIN}"/>']
    return svg(b)


def monitor(scr, stand=True):
    x0, y0, x1, y1 = scr
    b = [f'<rect x="{x0 - 14}" y="{y0 - 14}" width="{x1 - x0 + 28}" height="{y1 - y0 + 28}" rx="12" fill="{BEZEL}"/>']
    if stand:
        cx = (x0 + x1) / 2
        b += [f'<rect x="{cx - 12}" y="{y1 + 14}" width="24" height="{DESK_Y - y1 - 30}" fill="{METAL_DARK}"/>',
              f'<rect x="{cx - 60}" y="{DESK_Y - 16}" width="120" height="16" rx="6" fill="{METAL_DARK}"/>']
    return b


def front():
    b = [
        f'<rect x="380" y="{DESK_Y}" width="700" height="34" rx="10" fill="{WOOD}"/>',
        f'<rect x="400" y="{DESK_Y + 34}" width="26" height="{FLOOR - DESK_Y - 34}" fill="{WOOD_DARK}"/>',
        f'<rect x="1030" y="{DESK_Y + 34}" width="26" height="{FLOOR - DESK_Y - 34}" fill="{WOOD_DARK}"/>',
        f'<rect x="400" y="{DESK_Y + 120}" width="650" height="14" fill="{WOOD_DARK}"/>',
        *monitor(SCREEN_L), *monitor(SCREEN_R), *monitor(SCREEN),
        f'<rect x="470" y="{DESK_Y - 14}" width="210" height="14" rx="5" fill="{METAL}"/>',
        f'<rect x="{MUG[0] - 30}" y="{MUG[1]}" width="60" height="70" rx="10" fill="{BOARD_FACE}"/>',
        f'<path d="M{MUG[0] + 30} {MUG[1] + 18} Q{MUG[0] + 64} {MUG[1] + 36} {MUG[0] + 30} {MUG[1] + 54}" stroke="{BOARD_FACE}" stroke-width="10" fill="none"/>',
        f'<ellipse cx="{MUG[0]}" cy="{MUG[1]}" rx="30" ry="8" fill="#6B4A36"/>',
    ]
    return svg(b)


FILES = {"back.svg": back(), "front.svg": front(), **{f"hire-{p}.svg": hire(p) for p in ("typing", "confused", "binder", "board")}, "binder.svg": binder()}

if __name__ == "__main__":
    for name, content in FILES.items():
        with open(os.path.join(OUT, name), "w") as f:
            f.write(content)
        print("wrote", os.path.relpath(os.path.join(OUT, name), ROOT))

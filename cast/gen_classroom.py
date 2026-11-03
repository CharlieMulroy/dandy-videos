"""The classroom: a full-canvas backdrop for informational videos (vertical 1080x1920).

Run:  python3 cast/gen_classroom.py   ->  motifs/classroom.svg
Used as a `background: true` sprite at (0, 0), height 1.0. The blackboard's writable area is
x 60..1020, y 250..1120 in canvas px (inside the safe zone); Dandy Man stands at the left of it.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
with open(os.path.join(ROOT, "style", "contract.json")) as f:
    P = json.load(f)["palette"]
BG, LIFT, PRIMARY, HI, SOFT, TEXT, GOLD = (P[k] for k in ("background", "background_lift", "primary", "highlight", "soft", "text", "accent_gold"))
WOOD, WOOD_DARK, BOARD = "#4A3566", "#33234A", "#241838"
W, H, FLOOR = 1080, 1920, 1500
BX0, BY0, BX1, BY1 = 60, 250, 1020, 1120


def classroom():
    b = [
        '<defs>',
        f'  <linearGradient id="wall" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{FLOOR}"><stop offset="0" stop-color="{BG}"/><stop offset="1" stop-color="{LIFT}"/></linearGradient>',
        f'  <radialGradient id="winlight" gradientUnits="userSpaceOnUse" cx="{W * 0.5}" cy="{H * 0.36}" r="{W * 0.9}"><stop offset="0" stop-color="{SOFT}" stop-opacity="0.10"/><stop offset="1" stop-color="{SOFT}" stop-opacity="0"/></radialGradient>',
        '</defs>',
        f'<rect x="0" y="0" width="{W}" height="{FLOOR}" fill="url(#wall)"/>',
        f'<rect x="0" y="0" width="{W}" height="{FLOOR}" fill="url(#winlight)"/>',
        # wainscot panel on the lower wall
        f'<rect x="0" y="1200" width="{W}" height="{FLOOR - 1200}" fill="{LIFT}"/>',
        f'<rect x="0" y="1200" width="{W}" height="12" fill="{WOOD}"/>',
        *[f'<rect x="{24 + i * 132}" y="1232" width="100" height="{FLOOR - 1264}" rx="6" fill="none" stroke="{WOOD}" stroke-width="4" opacity="0.6"/>' for i in range(8)],
        # floor: boards with a slight perspective of lines
        f'<rect x="0" y="{FLOOR}" width="{W}" height="{H - FLOOR}" fill="#140B24"/>',
        f'<rect x="0" y="{FLOOR - 14}" width="{W}" height="14" fill="{WOOD}"/>',
        *[f'<line x1="0" y1="{FLOOR + 60 + i * 80}" x2="{W}" y2="{FLOOR + 60 + i * 80}" stroke="{BG}" stroke-width="3"/>' for i in range(6)],
        *[f'<line x1="{120 + i * 240}" y1="{FLOOR}" x2="{60 + i * 300 - 60}" y2="{H}" stroke="{BG}" stroke-width="3"/>' for i in range(5)],
        # the blackboard: frame, slate, chalk tray with chalk and eraser
        f'<rect x="{BX0 - 22}" y="{BY0 - 22}" width="{BX1 - BX0 + 44}" height="{BY1 - BY0 + 44}" rx="14" fill="{WOOD}"/>',
        f'<rect x="{BX0 - 10}" y="{BY0 - 10}" width="{BX1 - BX0 + 20}" height="{BY1 - BY0 + 20}" rx="8" fill="{WOOD_DARK}"/>',
        f'<rect x="{BX0}" y="{BY0}" width="{BX1 - BX0}" height="{BY1 - BY0}" rx="4" fill="{BOARD}"/>',
        # faint old chalk ghosting
        f'<ellipse cx="{BX0 + 700}" cy="{BY0 + 500}" rx="180" ry="90" fill="{SOFT}" opacity="0.04"/>',
        f'<ellipse cx="{BX0 + 260}" cy="{BY0 + 760}" rx="140" ry="60" fill="{SOFT}" opacity="0.03"/>',
        f'<rect x="{BX0 + 40}" y="{BY1 + 22}" width="{BX1 - BX0 - 80}" height="22" rx="6" fill="{WOOD}"/>',
        f'<rect x="{BX0 + 110}" y="{BY1 + 12}" width="54" height="10" rx="5" fill="{TEXT}"/>',
        f'<rect x="{BX0 + 180}" y="{BY1 + 12}" width="54" height="10" rx="5" fill="{SOFT}"/>',
        f'<rect x="{BX1 - 190}" y="{BY1 + 4}" width="96" height="18" rx="4" fill="{PRIMARY}"/>',
        # letter cards above the board
        *[f'<rect x="{BX0 + 6 + i * 96}" y="150" width="70" height="56" rx="4" fill="{TEXT}" opacity="0.9"/>' for i in range(10)],
        *[f'<text x="{BX0 + 41 + i * 96}" y="190" font-family="Inter, sans-serif" font-weight="700" font-size="34" text-anchor="middle" fill="{PRIMARY}">{c}</text>' for i, c in enumerate("ABCDEFGHIJ")],
        # clock, top right corner above the cards
        f'<circle cx="980" cy="84" r="52" fill="{SOFT}"/>',
        f'<circle cx="980" cy="84" r="44" fill="{TEXT}"/>',
        f'<line x1="980" y1="84" x2="980" y2="56" stroke="{BG}" stroke-width="5" stroke-linecap="round"/>',
        f'<line x1="980" y1="84" x2="1004" y2="92" stroke="{BG}" stroke-width="4" stroke-linecap="round"/>',
        f'<circle cx="980" cy="84" r="4" fill="{BG}"/>',
        # teacher's desk, bottom right: top, front panel, apple, globe, books
        f'<rect x="700" y="1270" width="360" height="26" rx="8" fill="{WOOD}"/>',
        f'<rect x="716" y="1296" width="328" height="190" rx="6" fill="{WOOD_DARK}"/>',
        f'<rect x="740" y="1320" width="280" height="60" rx="6" fill="none" stroke="{WOOD}" stroke-width="4" opacity="0.7"/>',
        f'<rect x="740" y="1400" width="280" height="60" rx="6" fill="none" stroke="{WOOD}" stroke-width="4" opacity="0.7"/>',
        f'<circle cx="760" cy="1250" r="22" fill="{GOLD}"/>',
        f'<path d="M760 1228 Q764 1214 776 1210" stroke="{WOOD_DARK}" stroke-width="4" fill="none" stroke-linecap="round"/>',
        f'<rect x="820" y="1240" width="110" height="30" rx="4" fill="{PRIMARY}"/>',
        f'<rect x="828" y="1216" width="96" height="24" rx="4" fill="{SOFT}"/>',
        f'<ellipse cx="990" cy="1268" rx="34" ry="8" fill="{WOOD_DARK}"/>',
        f'<line x1="990" y1="1268" x2="990" y2="1230" stroke="{WOOD_DARK}" stroke-width="6"/>',
        f'<circle cx="990" cy="1192" r="42" fill="{HI}"/>',
        f'<path d="M962 1170 Q990 1160 1016 1178 M956 1198 Q990 1186 1024 1200 M968 1222 Q992 1210 1014 1220" stroke="{PRIMARY}" stroke-width="6" fill="none" stroke-linecap="round"/>',
        f'<path d="M960 1160 A44 44 0 0 1 1022 1226" stroke="{WOOD_DARK}" stroke-width="5" fill="none"/>',
        # plant in the bottom-left corner
        f'<rect x="40" y="1400" width="90" height="96" rx="12" fill="{WOOD_DARK}"/>',
        f'<path d="M85 1400 Q20 1330 40 1240 Q86 1300 85 1400 M85 1400 Q140 1320 160 1230 Q110 1290 85 1400 M85 1400 Q70 1320 96 1200 Q118 1300 85 1400" fill="#3F8E6A"/>',
        # wastebasket beside the desk
        f'<path d="M620 1420 L636 1496 L686 1496 L702 1420 Z" fill="{LIFT}" stroke="{WOOD}" stroke-width="4"/>',
    ]
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">\n' + "\n".join("  " + x for x in b) + "\n</svg>\n"


if __name__ == "__main__":
    out = os.path.join(ROOT, "motifs", "classroom.svg")
    with open(out, "w") as f:
        f.write(classroom())
    print("wrote", os.path.relpath(out, ROOT))

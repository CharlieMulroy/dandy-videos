"""Generate the supporting figures and props (not Dandy Man) as SVGs.

Run:  python3 cast/gen_figures.py
Writes cast/figures/*.svg and motifs/*.svg. Colors come from style/contract.json.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
FIG = os.path.join(HERE, "figures")
MOTIFS = os.path.join(ROOT, "motifs")
os.makedirs(FIG, exist_ok=True)
os.makedirs(MOTIFS, exist_ok=True)

with open(os.path.join(ROOT, "style", "contract.json")) as f:
    P = json.load(f)["palette"]
PRIMARY, HI, SOFT, TEXT, GOLD, BG, LIFT = (
    P["primary"], P["highlight"], P["soft"], P["text"], P["accent_gold"], P["background"], P["background_lift"]
)


def svg(viewbox, body):
    w, h = viewbox.split()[2:]
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" width="{w}" height="{h}">\n{body}\n</svg>\n'


# ---------- Employee (stick figure, soft purple, cape) ----------
def employee(cape="flutter", bubble=False, bubble_graph=False):
    """viewBox 0 0 300 600, feet at y=600. Figure centred at x=130 so a bubble fits to the right."""
    cx = 130
    stroke = f'stroke="{SOFT}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    if cape == "flutter":
        cape_path = f"M{cx - 14} 196 Q{cx - 90} 300 {cx - 70} 420 Q{cx - 30} 380 {cx + 2} 400 L{cx - 6} 220 Z"
    else:  # drooping straight down behind the body
        cape_path = f"M{cx - 16} 196 L{cx - 34} 440 Q{cx - 10} 448 {cx + 4} 430 L{cx - 2} 220 Z"
    parts = [
        # (cape removed Nov 2 at Charlie's request; cape_path kept for the super employee video)
        # body
        f'<line x1="{cx}" y1="190" x2="{cx}" y2="400" {stroke}/>',
        # legs
        f'<path d="M{cx} 400 L{cx - 40} 594" {stroke}/>',
        f'<path d="M{cx} 400 L{cx + 40} 594" {stroke}/>',
        # arms
        f'<path d="M{cx} 240 L{cx - 56} 340" {stroke}/>',
        f'<path d="M{cx} 240 L{cx + 56} 340" {stroke}/>',
        # head
        f'<circle cx="{cx}" cy="150" r="34" fill="{SOFT}"/>',
        f'<circle cx="{cx - 11}" cy="146" r="4" fill="{BG}"/>',
        f'<circle cx="{cx + 11}" cy="146" r="4" fill="{BG}"/>',
    ]
    if cape == "flutter":
        parts.append(f'<path d="M{cx - 10} 164 Q{cx} 172 {cx + 10} 164" stroke="{BG}" stroke-width="3" fill="none" stroke-linecap="round"/>')
    else:
        parts.append(f'<line x1="{cx - 9}" y1="167" x2="{cx + 9}" y2="167" stroke="{BG}" stroke-width="3" stroke-linecap="round"/>')
    if bubble:
        ob = f'stroke="{TEXT}" stroke-width="5" fill="none"'
        parts += [
            f'<circle cx="{cx + 44}" cy="122" r="6" {ob}/>',
            f'<circle cx="{cx + 62}" cy="104" r="9" {ob}/>',
            f'<ellipse cx="{cx + 106}" cy="58" rx="60" ry="34" {ob}/>',
        ]
        if bubble_graph:
            # three tiny nodes and two edges inside the bubble: what the agent is holding in mind
            gx = cx + 106 - 40
            for i in range(3):
                parts.append(f'<rect x="{gx + i * 30}" y="50" width="20" height="16" rx="4" fill="none" stroke="{HI}" stroke-width="3"/>')
            for i in range(2):
                parts.append(f'<line x1="{gx + 20 + i * 30}" y1="58" x2="{gx + 30 + i * 30}" y2="58" stroke="{HI}" stroke-width="3"/>')
    return svg("0 0 300 600", "\n".join("  " + p for p in parts))


# ---------- Builder at a desk, side view ----------
def builder():
    """viewBox 0 0 700 500, floor at y=500. Builder faces right toward the monitor."""
    stroke = f'stroke="{TEXT}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    bx = 230  # builder's hip x
    parts = [
        # desk: top + two legs
        f'<rect x="300" y="300" width="360" height="22" rx="6" fill="{LIFT}"/>',
        f'<rect x="320" y="322" width="18" height="178" fill="{LIFT}"/>',
        f'<rect x="622" y="322" width="18" height="178" fill="{LIFT}"/>',
        # monitor: stand, bezel, screen glow
        f'<rect x="470" y="262" width="16" height="40" fill="{LIFT}"/>',
        f'<rect x="440" y="290" width="76" height="12" rx="4" fill="{LIFT}"/>',
        f'<rect x="380" y="120" width="196" height="146" rx="10" fill="{LIFT}"/>',
        f'<rect x="394" y="134" width="168" height="118" rx="6" fill="{HI}" opacity="0.55"/>',
        # small graph on screen: three nodes and two edges
        f'<rect x="412" y="180" width="38" height="22" rx="5" fill="{TEXT}" opacity="0.85"/>',
        f'<rect x="459" y="180" width="38" height="22" rx="5" fill="{TEXT}" opacity="0.85"/>',
        f'<rect x="506" y="180" width="38" height="22" rx="5" fill="{TEXT}" opacity="0.85"/>',
        f'<line x1="450" y1="191" x2="459" y2="191" stroke="{TEXT}" stroke-width="3"/>',
        f'<line x1="497" y1="191" x2="506" y2="191" stroke="{TEXT}" stroke-width="3"/>',
        # chair seat + back + post
        f'<rect x="{bx - 70}" y="330" width="120" height="16" rx="6" fill="{LIFT}"/>',
        f'<rect x="{bx - 80}" y="210" width="16" height="130" rx="6" fill="{LIFT}"/>',
        f'<rect x="{bx - 18}" y="346" width="16" height="154" fill="{LIFT}"/>',
        # builder: seated, torso leaning slightly forward
        f'<path d="M{bx - 20} 330 L{bx} 200" {stroke}/>',                 # torso
        f'<path d="M{bx - 20} 330 L{bx + 60} 330 L{bx + 60} 494" {stroke}/>',  # thigh + shin
        f'<path d="M{bx - 6} 240 L{bx + 90} 290" {stroke}/>',             # arm to keyboard
        f'<circle cx="{bx + 8}" cy="160" r="34" fill="{TEXT}"/>',
        f'<circle cx="{bx + 22}" cy="156" r="4" fill="{BG}"/>',
        # keyboard
        f'<rect x="{bx + 80}" y="286" width="110" height="12" rx="4" fill="{SOFT}"/>',
    ]
    return svg("0 0 700 500", "\n".join("  " + p for p in parts))


# ---------- Blackboard ----------
def blackboard():
    parts = [
        f'<rect x="0" y="0" width="1200" height="720" rx="10" fill="{SOFT}"/>',
        f'<rect x="14" y="14" width="1172" height="692" rx="6" fill="{LIFT}"/>',
        # chalk tray
        f'<rect x="80" y="718" width="1040" height="22" rx="6" fill="{SOFT}"/>',
        f'<rect x="100" y="740" width="1000" height="20" rx="4" fill="{PRIMARY}" opacity="0.6"/>',
        # a piece of chalk and an eraser on the tray
        f'<rect x="150" y="706" width="56" height="10" rx="5" fill="{TEXT}"/>',
        f'<rect x="980" y="700" width="90" height="18" rx="4" fill="{PRIMARY}"/>',
    ]
    return svg("0 0 1200 760", "\n".join("  " + p for p in parts))


# ---------- Clocks ----------
def clock(hour, minute, night):
    cx, cy, r = 86, 100, 62
    ha = math.radians((hour % 12 + minute / 60) * 30 - 90)
    ma = math.radians(minute * 6 - 90)
    hx, hy = cx + math.cos(ha) * r * 0.5, cy + math.sin(ha) * r * 0.5
    mx, my = cx + math.cos(ma) * r * 0.74, cy + math.sin(ma) * r * 0.74
    ticks = "".join(
        f'<line x1="{cx + math.cos(a) * (r - 10):.1f}" y1="{cy + math.sin(a) * (r - 10):.1f}" '
        f'x2="{cx + math.cos(a) * (r - 4):.1f}" y2="{cy + math.sin(a) * (r - 4):.1f}" stroke="{BG}" stroke-width="3"/>'
        for a in (math.radians(k * 90 - 90) for k in range(4))
    )
    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="{r + 6}" fill="{SOFT}"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{TEXT}"/>',
        ticks,
        f'<line x1="{cx}" y1="{cy}" x2="{hx:.1f}" y2="{hy:.1f}" stroke="{BG}" stroke-width="6" stroke-linecap="round"/>',
        f'<line x1="{cx}" y1="{cy}" x2="{mx:.1f}" y2="{my:.1f}" stroke="{BG}" stroke-width="4" stroke-linecap="round"/>',
        f'<circle cx="{cx}" cy="{cy}" r="5" fill="{BG}"/>',
    ]
    if night:
        parts.append(f'<path d="M166 40 A22 22 0 1 0 186 70 A16 16 0 1 1 166 40 Z" fill="{GOLD}"/>')
    else:
        parts.append(f'<circle cx="172" cy="52" r="14" fill="{GOLD}"/>')
        parts += [
            f'<line x1="{172 + math.cos(a) * 20:.1f}" y1="{52 + math.sin(a) * 20:.1f}" '
            f'x2="{172 + math.cos(a) * 26:.1f}" y2="{52 + math.sin(a) * 26:.1f}" stroke="{GOLD}" stroke-width="3" stroke-linecap="round"/>'
            for a in (math.radians(k * 45) for k in range(8))
        ]
    return svg("0 0 200 200", "\n".join("  " + p for p in parts))


FILES = {
    os.path.join(FIG, "employee.svg"): employee("flutter"),
    os.path.join(FIG, "employee-blank.svg"): employee("droop", bubble=True),
    os.path.join(FIG, "employee-thinking.svg"): employee("flutter", bubble=True, bubble_graph=True),
    os.path.join(FIG, "builder.svg"): builder(),
    os.path.join(MOTIFS, "blackboard.svg"): blackboard(),
    os.path.join(MOTIFS, "clock-night.svg"): clock(11, 48, night=True),
    os.path.join(MOTIFS, "clock-morning.svg"): clock(9, 2, night=False),
}

if __name__ == "__main__":
    for path, content in FILES.items():
        with open(path, "w") as f:
            f.write(content)
        print("wrote", os.path.relpath(path, ROOT))

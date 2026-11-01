#!/usr/bin/env python3
"""Generate docs/img/greek_squat_logo.svg: the Stoa in one-point perspective, a small black cube with a glowing mu
floating in the sky past the far end, two phones in the foreground joined by one USB-C, particles rising into the cube.

    python3 docs/img/greek_squat_logo_gen.py   # writes greek_squat_logo.svg next to this file
"""
import math, os, random

W, H = 1200, 675
VX, VY = 600, 300                 # vanishing point
L, R, T, B = -600, 600, -300, 375  # near cross-section relative to the vanishing point
FAR = 0.22                         # scale of the far end
random.seed(7)


def P(x, y, s):
    return (VX + x * s, VY + y * s)


def poly(pts, **a):
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"
    return f'<path d="{d}" {" ".join(f"{k.replace("_", "-")}=\"{v}\"" for k, v in a.items())}/>'


def line(p, q, **a):
    return f'<path d="M{p[0]:.1f} {p[1]:.1f} L{q[0]:.1f} {q[1]:.1f}" {" ".join(f"{k.replace("_", "-")}=\"{v}\"" for k, v in a.items())}/>'


def s_of(z):  # depth z (1 = near plane) -> screen scale
    return 1 / z


ZFAR = 1 / FAR
o = []
o.append(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">GREEK SQUAT · phone-net-ICKS</title>
<desc id="d">A stone colonnade in one-point perspective, after the Stoa at the UCLA Film and Television Archive. At the far end a
small black cube with the Greek letter mu floats in the sky above the horizon. In the foreground an iPhone and an Android phone
join at one USB-C plug, and points of light rise from it up the corridor into the cube.</desc>
<defs>
 <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d1a30"/><stop offset=".62" stop-color="#2b5a86"/><stop offset=".86" stop-color="#9bdfff"/><stop offset="1" stop-color="#f3e7c4"/></linearGradient>
 <linearGradient id="wall" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8f8676"/><stop offset="1" stop-color="#4a463d"/></linearGradient>
 <linearGradient id="floor" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#7d7466"/><stop offset="1" stop-color="#3b372f"/></linearGradient>
 <linearGradient id="ceil" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5a3518"/><stop offset="1" stop-color="#2a1a0d"/></linearGradient>
 <linearGradient id="top" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a0d14" stop-opacity=".92"/><stop offset="1" stop-color="#0a0d14" stop-opacity="0"/></linearGradient>
 <linearGradient id="bottom" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#0a0d14" stop-opacity=".9"/><stop offset="1" stop-color="#0a0d14" stop-opacity="0"/></linearGradient>
 <radialGradient id="halo" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#6ee7ff" stop-opacity=".55"/><stop offset="1" stop-color="#6ee7ff" stop-opacity="0"/></radialGradient>
 <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
 <linearGradient id="stem" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#e8414b"/><stop offset=".5" stop-color="#9bdfff"/><stop offset="1" stop-color="#3ddc97"/></linearGradient>
 <filter id="cloud" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="6"/></filter>
 <linearGradient id="alu" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e9ecf0"/><stop offset="1" stop-color="#b7bcc4"/></linearGradient>
 <linearGradient id="alu2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a9aeb6"/><stop offset="1" stop-color="#7c818a"/></linearGradient>
 <filter id="soft"><feGaussianBlur stdDeviation="1.2"/></filter>
 <g id="chip"><rect x="-26" y="-26" width="52" height="52" rx="5" fill="#121722" stroke="currentColor" stroke-width="3"/>
  <rect x="-15" y="-15" width="30" height="30" rx="3" fill="none" stroke="currentColor" stroke-width="2" opacity=".7"/>
  <path d="M-16 -26v-9M-5 -26v-9M5 -26v-9M16 -26v-9M-16 26v9M-5 26v9M5 26v9M16 26v9M-26 -16h-9M-26 -5h-9M-26 5h-9M-26 16h-9M26 -16h9M26 -5h9M26 5h9M26 16h9" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></g>
</defs>
<rect width="{W}" height="{H}" fill="#0a0d14"/>''')

# sky behind everything (seen through the colonnade and the far end)
o.append(f'<rect x="{VX + L * FAR:.0f}" y="0" width="{W}" height="{H}" fill="url(#sky)"/>')
fx0, fy0 = P(L, T, FAR); fx1, fy1 = P(R, B, FAR)
hy = VY + 0.62 * B * FAR   # horizon inside the far opening
# distant hills through the far end and between columns
hills = [(fx0 - 400, hy + 6)] + [(x, hy - 6 - 10 * math.sin(x / 37) - 6 * math.sin(x / 13)) for x in range(int(fx0) - 400, W + 20, 12)] + [(W + 20, hy + 6)]
o.append(poly(hills + [(W + 20, H), (fx0 - 400, H)], fill="#2c3a4a", opacity=".9"))

# clouds: soft banks across the sky (the cloud the black box sits in front of)
CL = []
for (x, y, rx, ry, op) in [(600, 270, 118, 26, .9), (548, 286, 80, 20, .85), (660, 290, 86, 19, .85), (590, 252, 62, 20, .9), (640, 258, 48, 18, .85),
                           (510, 268, 56, 14, .6), (700, 270, 58, 14, .6), (604, 300, 120, 12, .55), (900, 170, 160, 26, .25), (1080, 110, 150, 24, .22),
                           (820, 240, 110, 18, .25), (1010, 250, 140, 20, .22)]:
    CL.append(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="#e7eef8" opacity="{op}"/>')
o.append('<g filter="url(#cloud)">' + "".join(CL) + '</g>')

# floor
o.append(poly([P(L, B, 1), P(R, B, 1), P(R, B, FAR), P(L, B, FAR)], fill="url(#floor)"))
z = 1.0
while z < ZFAR:  # slab joints across the floor
    s = s_of(z); o.append(line(P(L, B, s), P(R - 60, B, s), stroke="#2c2924", stroke_width=f"{max(.5, 2 * s):.2f}", opacity=".7")); z += 0.35
for xw in (-300, 0, 300):
    o.append(line(P(xw, B, 1), P(xw, B, FAR), stroke="#2c2924", stroke_width="1.2", opacity=".6"))

# ceiling with slats
o.append(poly([P(L, T, 1), P(R, T, 1), P(R, T, FAR), P(L, T, FAR)], fill="url(#ceil)"))
z = 1.0
while z < ZFAR:
    s = s_of(z); o.append(line(P(L, T, s), P(R, T, s), stroke="#b0703a", stroke_width=f"{max(.5, 4 * s):.2f}", opacity=f"{.35 + .4 * s:.2f}")); z += 0.09

# left wall: stone courses + door recesses
o.append(poly([P(L, T, 1), P(L, T, FAR), P(L, B, FAR), P(L, B, 1)], fill="url(#wall)"))
for yw in range(int(T) + 90, int(B), 90):
    o.append(line(P(L, yw, 1), P(L, yw, FAR), stroke="#2f2b25", stroke_width="1", opacity=".55"))
zd = 1.25
while zd + 0.3 < ZFAR:
    a, b = s_of(zd), s_of(zd + 0.3)
    o.append(poly([P(L, B, a), P(L, -40, a), P(L, -40, b), P(L, B, b)], fill="#1d1712", stroke="#b9ae96", stroke_width=f"{max(.6, 3 * a):.2f}"))
    zd += 0.62

# far end wall with its opening (the light)
ow0, ow1, oh0 = -260, 260, T
o.append(poly([P(L, T, FAR), P(R, T, FAR), P(R, oh0, FAR), P(L, oh0, FAR)], fill="#6d665a"))
o.append(poly([P(L, oh0, FAR), P(ow0, oh0, FAR), P(ow0, B, FAR), P(L, B, FAR)], fill="#6d665a"))
o.append(poly([P(ow1, oh0, FAR), P(R, oh0, FAR), P(R, B, FAR), P(ow1, B, FAR)], fill="#5d574d"))

# right side: architrave strip over the colonnade, low rail, columns far to near
o.append(poly([P(R, T, 1), P(R, T, FAR), P(R, T + 40, FAR), P(R, T + 40, 1)], fill="#a39a86"))
o.append(poly([P(R, B - 95, 1), P(R, B - 95, FAR), P(R, B, FAR), P(R, B, 1)], fill="#6d665a", opacity=".85"))
cols = []
zc = 1.12
while zc < ZFAR - 0.05:
    cols.append(zc); zc += 0.40
for zc in reversed(cols):
    s = s_of(zc)
    cx0, cx1 = 528, 588
    x0, _ = P(cx0, 0, s); x1, _ = P(cx1, 0, s)
    _, ytop = P(0, T + 40, s); _, ycap = P(0, T + 62, s); _, ybot = P(0, B, s)
    # sunlight on the floor between this column and the next one in
    s2 = s_of(zc - 0.2) if zc - 0.2 > 1 else 1
    o.append(poly([P(330, B, s), P(560, B, s), P(560, B, s2), P(330, B, s2)], fill="#f3e7c4", opacity=f"{.25 + .3 * s:.2f}"))
    o.append(poly([P(cx0 - 14, T + 40, s), P(cx1 + 14, T + 40, s), P(cx1 + 14, T + 50, s), P(cx0 - 14, T + 50, s)], fill="#d9cfba"))
    o.append(poly([P(cx0 - 10, T + 50, s), P(cx1 + 10, T + 50, s), P(cx1, T + 62, s), P(cx0, T + 62, s)], fill="#c7bba1"))
    o.append(f'<rect x="{x0:.1f}" y="{ycap:.1f}" width="{x1 - x0:.1f}" height="{ybot - ycap:.1f}" fill="#cdc2a9"/>')
    o.append(f'<rect x="{x1 - (x1 - x0) * .35:.1f}" y="{ycap:.1f}" width="{(x1 - x0) * .35:.1f}" height="{ybot - ycap:.1f}" fill="#8f8572" opacity=".7"/>')
    for f in (.2, .4, .6, .8):
        xf = x0 + (x1 - x0) * f
        o.append(line((xf, ycap), (xf, ybot), stroke="#7d7462", stroke_width=f"{max(.4, 1.3 * s):.2f}", opacity=".8"))

# soft dark bands so the wordmark and the foreground read
o.append(f'<rect width="{W}" height="150" fill="url(#top)"/>')
o.append(f'<rect y="{H - 190}" width="{W}" height="190" fill="url(#bottom)"/>')

# the cube: a small black box tilted in the sky, in front of the clouds, mu on its face
cxc, cyc, e = VX, VY - 44, 20
dx, dy = 13, 11                         # depth of the box (we are below it: side + underside show)
fr = [(-e, -e), (e, -e), (e, e), (-e, e)]
bk = [(x + dx, y + dy) for x, y in fr]
pt = lambda q: f"{cxc + q[0]:.1f} {cyc + q[1]:.1f}"
cg = [f'<g transform="rotate(-11 {cxc} {cyc})">']
cg.append(f'<path d="M{pt(fr[1])} L{pt(bk[1])} L{pt(bk[2])} L{pt(fr[2])} Z" fill="#11161f" stroke="#6ee7ff" stroke-width="1.3" stroke-linejoin="round"/>')
cg.append(f'<path d="M{pt(fr[3])} L{pt(fr[2])} L{pt(bk[2])} L{pt(bk[3])} Z" fill="#1a2130" stroke="#6ee7ff" stroke-width="1.3" stroke-linejoin="round"/>')
cg.append(f'<path d="M{pt(fr[0])} L{pt(fr[1])} L{pt(fr[2])} L{pt(fr[3])} Z" fill="#04060a" stroke="#6ee7ff" stroke-width="2" stroke-linejoin="round"/>')
cg.append(f'<path d="M{pt((-e + 3, -e + 3))} L{pt((e - 3, -e + 3))}" stroke="#9bdfff" stroke-width="1" opacity=".5"/>')
cg.append(f'<text x="{cxc}" y="{cyc + e * .5:.1f}" font-family="Georgia, \'Times New Roman\', serif" font-size="{e * 1.6:.0f}" font-style="italic" fill="#6ee7ff" text-anchor="middle" filter="url(#glow)">μ</text>')
cg.append('</g>')
o.append(f'<circle cx="{cxc}" cy="{cyc}" r="52" fill="url(#halo)" opacity=".8"/>')
o.extend(cg)

# particles: from the USB-C up the corridor into the cube
ux, uy = VX, H - 96   # top of the Mac mini: the light starts here
paths = []
for k in range(7):
    sway = (k - 3) * 55
    c1 = (ux + sway * 1.4, uy - 140)
    c2 = (VX - sway * .5 + random.uniform(-30, 30), cyc + 170)
    paths.append(((ux, uy - 10), c1, c2, (cxc + random.uniform(-12, 12), cyc + e * .9)))


def bez(p, t):
    a, b, c, d = p
    m = 1 - t
    return (m**3 * a[0] + 3 * m * m * t * b[0] + 3 * m * t * t * c[0] + t**3 * d[0],
            m**3 * a[1] + 3 * m * m * t * b[1] + 3 * m * t * t * c[1] + t**3 * d[1])


cols_p = ["#6ee7ff", "#9bdfff", "#f0b429", "#8a6fd1", "#f3e7c4"]
o.append('<g filter="url(#glow)">')
for i, p in enumerate(paths):
    d = f"M{p[0][0]:.1f} {p[0][1]:.1f} C{p[1][0]:.1f} {p[1][1]:.1f} {p[2][0]:.1f} {p[2][1]:.1f} {p[3][0]:.1f} {p[3][1]:.1f}"
    o.append(f'<path id="fp{i}" d="{d}" fill="none" stroke="#6ee7ff" stroke-width=".6" opacity=".18"/>')
    for j in range(14):
        t = (j + random.random() * .6) / 14
        x, y = bez(p, t)
        x += random.uniform(-10, 10) * (1 - t); y += random.uniform(-8, 8) * (1 - t)
        r = 0.9 + 3.6 * (1 - t) * random.uniform(.5, 1)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{random.choice(cols_p)}" opacity="{.45 + .5 * (1 - t):.2f}"/>')
    for j in range(3):  # moving points (animated in browsers)
        o.append(f'<circle r="2.6" fill="{cols_p[(i + j) % len(cols_p)]}" opacity="0"><animateMotion dur="{4 + i * .3:.1f}s" begin="{j * 1.4 + i * .2:.1f}s" repeatCount="indefinite"><mpath href="#fp{i}"/></animateMotion>'
                 f'<animate attributeName="opacity" values="0;1;.8;0" dur="{4 + i * .3:.1f}s" begin="{j * 1.4 + i * .2:.1f}s" repeatCount="indefinite"/></circle>')
o.append('</g>')

# two hands hold two phones up in landscape; a Y-split USB-C joins them; the light rises off the plug
LINE = "#9bdfff"; HANDF = "#1b2232"


def hand(cx, cy, side):
    """Line-art hand under a landscape phone at (cx, cy); side = -1 left hand, +1 right hand. Forearm runs off the bottom."""
    g = []
    wx = cx - side * 20
    g.append(f'<path d="M{wx - 52} {H + 10} C {wx - 50} {H - 40}, {wx - 46} {cy + 120}, {wx - 40} {cy + 82} L {wx + 40} {cy + 82} C {wx + 46} {cy + 120}, {wx + 52} {H - 40}, {wx + 56} {H + 10} Z" fill="{HANDF}" stroke="{LINE}" stroke-width="2.4"/>')
    g.append(f'<path d="M{wx - 78} {cy + 60} C {wx - 82} {cy + 20}, {wx + 82} {cy + 20}, {wx + 78} {cy + 60} C {wx + 70} {cy + 96}, {wx - 70} {cy + 96}, {wx - 78} {cy + 60} Z" fill="{HANDF}" stroke="{LINE}" stroke-width="2.4"/>')
    return "".join(g)


def fingers(cx, cy, side):
    """Finger tips curling over the bottom edge, thumb on the front corner (drawn over the phone)."""
    g = []
    wx = cx - side * 20
    for i, dx in enumerate((-48, -18, 12, 42)):
        g.append(f'<rect x="{wx + dx - 12}" y="{cy + 54}" width="24" height="30" rx="12" fill="{HANDF}" stroke="{LINE}" stroke-width="2"/>')
    tx = cx - side * 112
    g.append(f'<g transform="rotate({side * -38} {tx} {cy + 40})"><rect x="{tx - 15}" y="{cy + 2}" width="30" height="66" rx="15" fill="{HANDF}" stroke="{LINE}" stroke-width="2.2"/>'
             f'<path d="M{tx - 9} {cy + 12} q 9 -7 18 0" fill="none" stroke="{LINE}" stroke-width="1.6" opacity=".7"/></g>')
    return "".join(g)


def phone_land(cx, cy, rot, frame, emoji):
    return (f'<g transform="translate({cx} {cy}) rotate({rot})">'
            f'<rect x="-150" y="-78" width="300" height="156" rx="26" fill="{frame}" stroke="{frame}" stroke-width="3"/>'
            f'<rect x="-140" y="-68" width="280" height="136" rx="18" fill="#0a0d14"/>'
            f'<rect x="-140" y="-68" width="280" height="136" rx="18" fill="url(#halo)" opacity=".35"/>'
            f'<text x="0" y="22" font-size="74" text-anchor="middle" font-family="\'Apple Color Emoji\',\'Segoe UI Emoji\',\'Noto Color Emoji\',sans-serif">{emoji}</text>'
            f'</g>')


lx, ly, lrot = 250, 520, -9
rx_, ry_, rrot = 950, 520, 9
# M4 Mac mini on the floor, back panel toward us (plain silver, no logo)
MW, MH, MD = 200, 34, 46                     # rear-face width, rear-face height, top depth on screen
mx, my = VX, H - 70                          # centre of the rear face
mtop = my - MH / 2                           # top edge of the rear face
usb1 = (mx - 58, my + 2); usb2 = (mx - 2, my + 2)    # two of the three USB-C ports: red left, green right
# cable: each phone's USB-C port is on the inner short edge in landscape
lport = (lx + 150 * math.cos(math.radians(lrot)) + 6, ly + 150 * math.sin(math.radians(lrot)))
rport = (rx_ - 150 * math.cos(math.radians(rrot)) - 6, ry_ - 150 * math.sin(math.radians(rrot)))
o.append(hand(lx, ly, -1)); o.append(hand(rx_, ry_, 1))
o.append(phone_land(lx, ly, lrot, "#d7263d", "🍎"))
o.append(phone_land(rx_, ry_, rrot, "#2fbf71", "🤖"))
o.append(fingers(lx, ly, -1)); o.append(fingers(rx_, ry_, 1))
# the Mac mini: soft shadow, top face in perspective, rear face with its ports
o.append(f'<ellipse cx="{mx}" cy="{my + MH / 2 + 6}" rx="{MW * .62:.0f}" ry="10" fill="#000" opacity=".45" filter="url(#soft)"/>')
o.append(f'<circle cx="{ux}" cy="{uy}" r="70" fill="url(#halo)"/>')
o.append(f'<path d="M{mx - MW / 2 + 6} {mtop} L{mx + MW / 2 - 6} {mtop} Q{mx + MW / 2} {mtop} {mx + MW / 2 - 14} {mtop - 6} L{mx + MW / 2 - 34} {mtop - MD + 6} Q{mx + MW / 2 - 40} {mtop - MD} {mx + MW / 2 - 48} {mtop - MD} L{mx - MW / 2 + 48} {mtop - MD} Q{mx - MW / 2 + 40} {mtop - MD} {mx - MW / 2 + 34} {mtop - MD + 6} L{mx - MW / 2 + 14} {mtop - 6} Q{mx - MW / 2} {mtop} {mx - MW / 2 + 6} {mtop} Z" fill="url(#alu)" stroke="#e7eef8" stroke-width="1"/>')
o.append(f'<rect x="{mx - MW / 2}" y="{mtop}" width="{MW}" height="{MH}" rx="9" fill="url(#alu2)" stroke="#e7eef8" stroke-width="1"/>')
o.append(f'<ellipse cx="{ux}" cy="{mtop - MD / 2}" rx="34" ry="8" fill="none" stroke="#6ee7ff" stroke-width="1.6" opacity=".7"/>')
# rear ports, left to right: 2 USB-C (used), 1 USB-C, HDMI, Ethernet, power
port = lambda x, w, h, r: f'<rect x="{x - w / 2:.1f}" y="{my - h / 2 + 2:.1f}" width="{w}" height="{h}" rx="{r}" fill="#1a1d22" stroke="#5c6470" stroke-width=".8"/>'
for x in (usb1[0], mx - 30, usb2[0]):
    o.append(port(x, 16, 6, 3))
o.append(f'<path d="M{mx + 18} {my - 2} h22 l-3 7 h-16 z" fill="#1a1d22" stroke="#5c6470" stroke-width=".8"/>')
o.append(port(mx + 58, 15, 11, 1.5))
o.append(f'<circle cx="{mx + 84}" cy="{my + 2}" r="5" fill="#1a1d22" stroke="#5c6470" stroke-width=".8"/>')
# cables come toward us, then turn into the rear ports (drawn in front of the box)
o.append(f'<path d="M{lport[0]:.0f} {lport[1]:.0f} C {lport[0] + 60:.0f} {lport[1] + 70:.0f}, {usb1[0] - 70} {usb1[1] + 70}, {usb1[0]} {usb1[1] + 12}" fill="none" stroke="#e8414b" stroke-width="7" stroke-linecap="round"/>')
o.append(f'<path d="M{rport[0]:.0f} {rport[1]:.0f} C {rport[0] - 60:.0f} {rport[1] + 80:.0f}, {usb2[0] + 70} {usb2[1] + 72}, {usb2[0]} {usb2[1] + 12}" fill="none" stroke="#3ddc97" stroke-width="7" stroke-linecap="round"/>')
# plugs seated in the two used ports
for (x, y), c in ((usb1, "#e8414b"), (usb2, "#3ddc97")):
    o.append(f'<rect x="{x - 9}" y="{y - 1}" width="18" height="13" rx="4" fill="#222831" stroke="{c}" stroke-width="2"/>')

# wordmark
o.append('''<g font-family="ui-monospace,'SF Mono',Menlo,monospace" text-anchor="middle">
 <text x="600" y="66" font-size="54" font-weight="800" fill="#e7eef8" letter-spacing="6">GREEK <tspan fill="#f0b429">SQUAT</tspan></text>
 <text x="600" y="98" font-size="17" fill="#6ee7ff">phone<tspan fill="#f0b429">+</tspan>net<tspan fill="#f0b429">+</tspan>I.C.K.S.</text>
</g>
</svg>''')

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "greek_squat_logo.svg")
open(out, "w", encoding="utf-8").write("\n".join(o))
print("wrote", out)

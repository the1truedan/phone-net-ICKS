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
 <linearGradient id="cubeFront" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3a414d"/><stop offset=".45" stop-color="#151a22"/><stop offset="1" stop-color="#030406"/></linearGradient>
 <linearGradient id="cubeSide" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1b2028"/><stop offset="1" stop-color="#020304"/></linearGradient>
 <linearGradient id="cubeUnder" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#262c36"/><stop offset="1" stop-color="#0a0c10"/></linearGradient>
 <linearGradient id="gold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe7a3"/><stop offset=".55" stop-color="#f0b429"/><stop offset="1" stop-color="#a8741a"/></linearGradient>
 <radialGradient id="warmhalo" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff4d6" stop-opacity=".55"/><stop offset="1" stop-color="#fff4d6" stop-opacity="0"/></radialGradient>
 <linearGradient id="handfill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2b3445"/><stop offset="1" stop-color="#121722"/></linearGradient>
 <linearGradient id="bezelsheen" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff" stop-opacity=".28"/><stop offset=".5" stop-color="#ffffff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".25"/></linearGradient>
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
for (x, y, rx, ry, op) in [(600, 290, 118, 24, .9), (552, 304, 76, 18, .85), (656, 306, 80, 18, .85), (592, 274, 58, 18, .9), (636, 280, 46, 16, .85),
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

# the cube: a small black box tilted in the sky, in front of the clouds, a gold mu inscribed on its face
cxc, cyc, e = VX, VY - 22, 12
dx, dy = 9, 8                           # depth of the box (we are below it: side + underside show)
fr = [(-e, -e), (e, -e), (e, e), (-e, e)]
bk = [(x + dx, y + dy) for x, y in fr]
pt = lambda q: f"{cxc + q[0]:.1f} {cyc + q[1]:.1f}"
EDGE = "#d9dee6"
cg = [f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -3;0 0" dur="6s" repeatCount="indefinite"/><g transform="rotate(-11 {cxc} {cyc})"><g><animateTransform attributeName="transform" type="rotate" values="-8 {cxc} {cyc};8 {cxc} {cyc};-8 {cxc} {cyc}" dur="9s" repeatCount="indefinite"/>']
cg.append(f'<path d="M{pt(fr[1])} L{pt(bk[1])} L{pt(bk[2])} L{pt(fr[2])} Z" fill="url(#cubeSide)" stroke="{EDGE}" stroke-width=".7" stroke-opacity=".55" stroke-linejoin="round"/>')
cg.append(f'<path d="M{pt(fr[3])} L{pt(fr[2])} L{pt(bk[2])} L{pt(bk[3])} Z" fill="url(#cubeUnder)" stroke="{EDGE}" stroke-width=".7" stroke-opacity=".45" stroke-linejoin="round"/>')
cg.append(f'<path d="M{pt(fr[0])} L{pt(fr[1])} L{pt(fr[2])} L{pt(fr[3])} Z" fill="url(#cubeFront)" stroke="{EDGE}" stroke-width=".9" stroke-opacity=".8" stroke-linejoin="round"/>')
cg.append(f'<path d="M{pt((-e + 1.5, -e + 1.2))} L{pt((e - 1.5, -e + 1.2))}" stroke="#ffffff" stroke-width=".8" opacity=".55"/>')
cg.append(f'<text x="{cxc}" y="{cyc + e * .5:.1f}" font-family="Georgia, \'Times New Roman\', serif" font-size="{e * 1.55:.0f}" font-style="italic" fill="url(#gold)" text-anchor="middle">μ</text>')
cg.append('</g></g></g>')
ox0, oy0 = P(ow0, T, FAR); ox1, oy1 = P(ow1, B, FAR)   # the far opening: the cube lives only in this sky
o.append(f'<clipPath id="opening"><rect x="{ox0:.1f}" y="{oy0 + 3:.1f}" width="{ox1 - ox0:.1f}" height="{oy1 - oy0 - 3:.1f}"/></clipPath>')
o.append('<g clip-path="url(#opening)">')
o.append(f'<circle cx="{cxc}" cy="{cyc}" r="30" fill="url(#warmhalo)"/>')
o.extend(cg)
o.append('</g>')

# particles: from the USB-C up the corridor into the cube
ux, uy = VX, H - 112  # top of the Mac mini: the light starts here
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
        o.append(f'<circle r="2.6" fill="{cols_p[(i + j) % len(cols_p)]}" opacity="0"><animateMotion dur="{4 + i * .3:.1f}s" begin="{1.2 + j * 1.4 + i * .2:.1f}s" repeatCount="indefinite"><mpath href="#fp{i}"/></animateMotion>'
                 f'<animate attributeName="opacity" values="0;1;.8;0" dur="{4 + i * .3:.1f}s" begin="{1.2 + j * 1.4 + i * .2:.1f}s" repeatCount="indefinite"/></circle>')
o.append('</g>')

# two hands hold two phones up in landscape; each phone's cable runs to the front ports of a small desktop
SKIN = "url(#handfill)"; HLINE = "#9bdfff"


def hand_back(side):
    """Palm and forearm, in the phone's own coordinates (drawn before the phone). side -1 = left hand."""
    m = side
    return (f'<path d="M{-62 * m} 330 C {-66 * m} 240, {-74 * m} 160, {-70 * m} 112 C {-68 * m} 88, {-54 * m} 74, {-30 * m} 72 '
            f'L {40 * m} 72 C {60 * m} 74, {70 * m} 90, {68 * m} 114 C {66 * m} 160, {60 * m} 240, {56 * m} 330 Z" '
            f'fill="{SKIN}" stroke="{HLINE}" stroke-opacity=".45" stroke-width="1.4"/>')


def hand_front(side):
    """Thumb resting on the lower screen edge, and the index finger tip curling round the bottom (drawn over the phone)."""
    m = side
    thumb = (f'<path d="M{-62 * m} 100 C {-70 * m} 78, {-60 * m} 52, {-38 * m} 44 C {-26 * m} 40, {-14 * m} 44, {-15 * m} 55 '
             f'C {-16 * m} 64, {-28 * m} 70, {-36 * m} 76 C {-42 * m} 82, {-46 * m} 92, {-48 * m} 104 Z" '
             f'fill="{SKIN}" stroke="{HLINE}" stroke-opacity=".55" stroke-width="1.3"/>')
    nail = f'<path d="M{-33 * m} 47 C {-26 * m} 44, {-19 * m} 46, {-19 * m} 53 C {-23 * m} 55, {-29 * m} 54, {-33 * m} 51 Z" fill="#9bdfff" opacity=".18"/>'
    tips = "".join(f'<path d="M{x * m - 9 * m} 78 C {x * m - 9 * m} 70, {x * m + 9 * m} 70, {x * m + 9 * m} 78 L {x * m + 8 * m} 86 L {x * m - 8 * m} 86 Z" '
                   f'fill="{SKIN}" stroke="{HLINE}" stroke-opacity=".35" stroke-width="1"/>' for x in (6, 26, 46))
    return thumb + nail + tips


def phone_land(cx, cy, rot, frame, emoji, side):
    return (f'<g transform="translate({cx} {cy}) rotate({rot})">' + hand_back(side) +
            f'<rect x="-150" y="-78" width="300" height="156" rx="26" fill="{frame}"/>'
            f'<rect x="-150" y="-78" width="300" height="156" rx="26" fill="url(#bezelsheen)"/>'
            f'<rect x="-140" y="-68" width="280" height="136" rx="18" fill="#0a0d14"/>'
            f'<rect x="-140" y="-68" width="280" height="136" rx="18" fill="url(#halo)" opacity=".3"/>'
            f'<text x="0" y="22" font-size="70" text-anchor="middle" font-family="\'Apple Color Emoji\',\'Segoe UI Emoji\',\'Noto Color Emoji\',sans-serif">{emoji}</text>'
            + hand_front(side) + '</g>')


lx, ly, lrot = 250, 500, -9
rx_, ry_, rrot = 950, 500, 9


def edge_port(cx, cy, rot, sign):  # centre of the phone's inner short edge
    r = math.radians(rot)
    return (cx + sign * 150 * math.cos(r), cy + sign * 150 * math.sin(r))


lport = edge_port(lx, ly, lrot, 1); rport = edge_port(rx_, ry_, rrot, -1)

# the desktop (M4 Mac mini proportions: wide, low, rounded), seen from the front, a little above
MW, MH, MD = 220, 40, 54
mx, my = VX, H - 64                      # centre of the front face
ftop = my - MH / 2
port1 = (mx - 74, my - 2); port2 = (mx - 52, my - 2)   # the two front USB-C ports
jack = (mx - 32, my - 2); led = (mx + 88, my - 2)

CRED, CGRN = "#c9404a", "#34b37a"
cab_l = f"M{lport[0] + 10:.1f} {lport[1]:.1f} C {lport[0] + 90:.1f} {lport[1] + 20:.1f}, {port1[0] - 150:.1f} {my + 70:.1f}, {port1[0]:.1f} {port1[1] + 9:.1f}"
cab_r = f"M{rport[0] - 10:.1f} {rport[1]:.1f} C {rport[0] - 90:.1f} {rport[1] + 30:.1f}, {port2[0] + 220:.1f} {my + 90:.1f}, {port2[0]:.1f} {port2[1] + 9:.1f}"

o.append(phone_land(lx, ly, lrot, "#d7263d", "🍎", -1))
o.append(phone_land(rx_, ry_, rrot, "#2fbf71", "🤖", 1))

# soft floor shadow, then the box
o.append(f'<ellipse cx="{mx}" cy="{my + MH / 2 + 4}" rx="{MW * .6:.0f}" ry="9" fill="#000" opacity=".5" filter="url(#soft)"/>')
o.append(f'<circle cx="{ux}" cy="{uy + 10}" r="80" fill="url(#halo)" opacity=".75"/>')
tl, tr_ = mx - MW / 2 + 22, mx + MW / 2 - 22
o.append(f'<path d="M{mx - MW / 2 + 12} {ftop} L{mx + MW / 2 - 12} {ftop} C{mx + MW / 2} {ftop}, {mx + MW / 2 - 8} {ftop - 10}, {tr_ - 4} {ftop - MD + 10} '
         f'C{tr_ - 10} {ftop - MD}, {tr_ - 18} {ftop - MD}, {tr_ - 26} {ftop - MD} L{tl + 26} {ftop - MD} C{tl + 18} {ftop - MD}, {tl + 10} {ftop - MD}, {tl + 4} {ftop - MD + 10} '
         f'C{mx - MW / 2 + 8} {ftop - 10}, {mx - MW / 2} {ftop}, {mx - MW / 2 + 12} {ftop} Z" fill="url(#alu)"/>')
o.append(f'<rect x="{mx - MW / 2}" y="{ftop}" width="{MW}" height="{MH}" rx="12" fill="url(#alu2)"/>')
o.append(f'<path d="M{mx - MW / 2 + 12} {ftop + .6} H{mx + MW / 2 - 12}" stroke="#ffffff" stroke-width="1.2" opacity=".7"/>')
o.append(f'<rect x="{mx - MW / 2 + 16}" y="{my + MH / 2 - 3}" width="{MW - 32}" height="5" rx="2.5" fill="#15181d"/>')   # dark foot ring
# a faint embossed mark on the top (a mu, not a brand)
o.append(f'<text x="{mx}" y="{(ftop - MD / 2) + 6:.1f}" font-family="Georgia,serif" font-style="italic" font-size="26" fill="#a9aeb6" opacity=".55" text-anchor="middle" transform="translate(0 {(ftop - MD / 2) * .62:.1f}) scale(1 .38)">μ</text>')
# front ports, headphone jack, status light
for (x, y) in (port1, port2):
    o.append(f'<rect x="{x - 7}" y="{y - 2.5}" width="14" height="5" rx="2.5" fill="#1b1e23" stroke="#6b717b" stroke-width=".6"/>')
o.append(f'<circle cx="{jack[0]}" cy="{jack[1]}" r="2.6" fill="#1b1e23" stroke="#6b717b" stroke-width=".6"/>')
o.append(f'<circle cx="{led[0]}" cy="{led[1]}" r="1.8" fill="#e9fff4"/><circle cx="{led[0]}" cy="{led[1]}" r="5" fill="#bfffe0" opacity=".35" filter="url(#soft)"/>')

# cables: a dark core line under a slim coloured jacket, moulded plugs at both ends
for d, c, pid in ((cab_l, CRED, "cabL"), (cab_r, CGRN, "cabR")):
    o.append(f'<path d="{d}" fill="none" stroke="#05070b" stroke-width="6.5" stroke-linecap="round" opacity=".8"/>')
    o.append(f'<path id="{pid}" d="{d}" fill="none" stroke="{c}" stroke-width="4" stroke-linecap="round"/>')
    o.append(f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="1" stroke-linecap="round" opacity=".25" transform="translate(0 -1)"/>')
for (x, y), c in ((port1, CRED), (port2, CGRN)):
    o.append(f'<rect x="{x - 8}" y="{y - 5}" width="16" height="13" rx="3.5" fill="#2a2f37" stroke="{c}" stroke-width="1.4"/>')
for (x, y, rot, c) in ((lport[0] + 6, lport[1], lrot, CRED), (rport[0] - 6, rport[1], rrot, CGRN)):
    o.append(f'<g transform="translate({x:.1f} {y:.1f}) rotate({rot})"><rect x="-8" y="-6" width="16" height="12" rx="3.5" fill="#2a2f37" stroke="{c}" stroke-width="1.4"/></g>')

# stage 1 animation: pulses run along each cable from the phone into the desktop
o.append('<g filter="url(#glow)">')
for pid, c in (("cabL", "#ffd2d6"), ("cabR", "#d2ffe9")):
    for j in range(4):
        o.append(f'<circle r="2.6" fill="{c}" opacity="0"><animateMotion dur="2.4s" begin="{j * .6:.1f}s" repeatCount="indefinite"><mpath href="#{pid}"/></animateMotion>'
                 f'<animate attributeName="opacity" values="0;1;1;0" dur="2.4s" begin="{j * .6:.1f}s" repeatCount="indefinite"/></circle>')
o.append('</g>')

# wordmark
o.append('''<g font-family="ui-monospace,'SF Mono',Menlo,monospace" text-anchor="middle">
 <text x="600" y="66" font-size="54" font-weight="800" fill="#e7eef8" letter-spacing="6">GREEK <tspan fill="#f0b429">SQUAT</tspan></text>
 <text x="600" y="98" font-size="17" fill="#6ee7ff">phone<tspan fill="#f0b429">+</tspan>net<tspan fill="#f0b429">+</tspan>I.C.K.S.</text>
</g>
</svg>''')

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "greek_squat_logo.svg")
open(out, "w", encoding="utf-8").write("\n".join(o))
print("wrote", out)

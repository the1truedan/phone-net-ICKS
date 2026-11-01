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
ow0, ow1, oh0 = -260, 260, -285
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

# the cube: small, black, face-on, in the sky above the horizon, with mu on its front
cxc, cyc, e = VX, VY - 22, 30          # front face centre and half-size
f0 = (cxc - e, cyc - e); f1 = (cxc + e, cyc + e)
k = .80                                 # back face scaled toward the vanishing point (we are below it: see its underside)
bk = lambda x, y: (VX + (x - VX) * k, VY + (y - VY) * k + 0)
o.append(f'<circle cx="{cxc}" cy="{cyc}" r="88" fill="url(#halo)"/>')
# underside and sides that recede toward the vanishing point
o.append(poly([(f0[0], f1[1]), (f1[0], f1[1]), bk(f1[0], f1[1]), bk(f0[0], f1[1])], fill="#0b0f17", stroke="#6ee7ff", stroke_width="1.2"))
o.append(poly([(f0[0], f0[1]), (f0[0], f1[1]), bk(f0[0], f1[1]), bk(f0[0], f0[1])], fill="#070a10", stroke="#6ee7ff", stroke_width="1.2"))
o.append(poly([(f1[0], f0[1]), (f1[0], f1[1]), bk(f1[0], f1[1]), bk(f1[0], f0[1])], fill="#070a10", stroke="#6ee7ff", stroke_width="1.2"))
o.append(f'<rect x="{f0[0]}" y="{f0[1]}" width="{2 * e}" height="{2 * e}" fill="#05070b" stroke="#6ee7ff" stroke-width="2"/>')
o.append(f'<text x="{cxc}" y="{cyc + e * .52:.1f}" font-family="Georgia, \'Times New Roman\', serif" font-size="{e * 1.7:.0f}" font-style="italic" fill="#6ee7ff" text-anchor="middle" filter="url(#glow)">μ</text>')

# particles: from the USB-C up the corridor into the cube
ux, uy = VX, H - 34
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

# phones in the foreground (bottom left iOS, bottom right Android) and one USB-C
def phone(cx, cy, rot, color, label, notch):
    g = [f'<g transform="translate({cx} {cy}) rotate({rot})">',
         f'<rect x="-70" y="-125" width="140" height="250" rx="{28 if notch else 18}" fill="#0f141e" stroke="{color}" stroke-width="4"/>']
    g.append('<rect x="-20" y="-114" width="40" height="11" rx="5.5" fill="#05070b"/>' if notch else '<circle cx="0" cy="-110" r="5" fill="#05070b"/>')
    g.append(f'<g color="{color}" transform="translate(0 -18)"><use href="#chip"/></g>')
    g.append(f'<text x="0" y="-14" fill="{color}" font-family="ui-monospace,Menlo,monospace" font-size="{13 if len(label) < 5 else 9}" font-weight="700" text-anchor="middle">{label}</text></g>')
    return "".join(g)


o.append(f'<path d="M232 600 C 360 660, 470 650, {ux - 36} {uy}" fill="none" stroke="#e7eef8" stroke-width="7" stroke-linecap="round"/>')
o.append(f'<path d="M968 600 C 840 660, 730 650, {ux + 36} {uy}" fill="none" stroke="#3ddc97" stroke-width="7" stroke-linecap="round"/>')
o.append(phone(150, 560, -12, "#e7eef8", "iOS", True))
o.append(phone(1050, 560, 12, "#3ddc97", "ANDROID", False))
o.append(f'<circle cx="{ux}" cy="{uy}" r="48" fill="url(#halo)"/>')
o.append(f'<rect x="{ux - 38}" y="{uy - 17}" width="76" height="34" rx="17" fill="#181e2c" stroke="#6ee7ff" stroke-width="3"/>')
o.append(f'<rect x="{ux - 20}" y="{uy - 5.5}" width="40" height="11" rx="5.5" fill="#6ee7ff"/>')

# wordmark
o.append('''<g font-family="ui-monospace,'SF Mono',Menlo,monospace" text-anchor="middle">
 <text x="600" y="66" font-size="54" font-weight="800" fill="#e7eef8" letter-spacing="6">GREEK <tspan fill="#f0b429">SQUAT</tspan></text>
 <text x="600" y="98" font-size="17" fill="#6ee7ff">phone<tspan fill="#f0b429">+</tspan>net<tspan fill="#f0b429">+</tspan>I.C.K.S.</text>
</g>
</svg>''')

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "greek_squat_logo.svg")
open(out, "w", encoding="utf-8").write("\n".join(o))
print("wrote", out)

#!/usr/bin/env python3
"""Write the two hero animations as standalone SVG files (SMIL, no JavaScript), so they play inside
the GitHub README as plain images and on the GitHub Pages site.

    python3 scripts/site/make_hero_svgs.py      # writes site/data-finger-point.svg and site/turbo.svg
"""
import math, os, random

SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "site")
random.seed(7)


def f(x):
    return f"{x:.1f}"


def data_finger_point():
    W, H, CUBE = 1200, 620, (600, 380)
    src = [(150, 170, "#2a97c4"), (600, 120, "#8a6fd1"), (1050, 175, "#c4841a")]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="D.A.T.A. F.I.N.G.E.R. P.O.I.N.T.: a Mac mini, an Android phone and a car dash camera send dots over Wi-Fi, with no cables, into a black cube marked with the micro sign. A laser from the cube pops a passing cloud.">',
         '<defs><radialGradient id="fl" cx="50%" cy="80%" r="70%"><stop offset="0" stop-color="#121826"/><stop offset="1" stop-color="#07090e"/></radialGradient>'
         '<filter id="bl"><feGaussianBlur stdDeviation="6"/></filter><linearGradient id="tp" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1b2232"/><stop offset="1" stop-color="#121826"/></linearGradient></defs>',
         f'<rect width="{W}" height="{H}" fill="url(#fl)"/>',
         '<style>.l{fill:#7d889c;font:13px ui-monospace,Menlo,monospace}</style>',
         # devices
         '<g transform="translate(150,170)" opacity=".8"><rect x="-55" y="-14" width="110" height="28" rx="9" fill="#c9ced8"/><rect x="-55" y="10" width="110" height="5" rx="2" fill="#9aa1ae"/><circle cx="40" cy="0" r="2.5" fill="#4cc27e"/><text class="l" y="44" text-anchor="middle">Mac mini</text></g>',
         '<g transform="translate(600,120)" opacity=".8"><rect x="-17" y="-34" width="34" height="68" rx="6" fill="#1f2636" stroke="#5c6880"/><rect x="-13" y="-28" width="26" height="54" rx="3" fill="#2a97c4" opacity=".55"/><text class="l" y="54" text-anchor="middle">Android</text></g>',
         '<g transform="translate(1050,175)" opacity=".8"><rect x="-34" y="-18" width="68" height="34" rx="6" fill="#1f2636" stroke="#5c6880"/><circle cy="-1" r="11" fill="#0b0e14" stroke="#8b97ad" stroke-width="2"/><circle cy="-1" r="4" fill="#c4841a"/><rect x="-8" y="-30" width="16" height="12" rx="2" fill="#5c6880"/><text class="l" y="40" text-anchor="middle">car dash cam</text></g>']
    # wifi arcs
    for i, (x, y, c) in enumerate(src):
        for k, r in enumerate((16, 28, 40)):
            o.append(f'<path d="M{x - r},{y - 36} A{r},{r} 0 0 1 {x + r},{y - 36}" fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round" opacity="0">'
                     f'<animate attributeName="opacity" values="0;.9;0" dur="1.8s" begin="{k * .3 + i * .2:.1f}s" repeatCount="indefinite"/></path>')
    # cloud, laser, bubbles on a 12 s loop: drift 0-8.5 s, laser 8.5-8.8 s, pop
    o.append('<g opacity="1"><animateTransform attributeName="transform" type="translate" values="1260,70;760,70;760,70" keyTimes="0;.71;1" dur="12s" repeatCount="indefinite"/>'
             '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.735;.736;1" dur="12s" repeatCount="indefinite"/>'
             '<path d="M0,20 a18,18 0 0 1 22,-22 a26,26 0 0 1 48,4 a18,18 0 0 1 10,34 h-74 a16,16 0 0 1 -6,-16z" fill="#c9d4e6" opacity=".85"/></g>')
    o.append('<line x1="600" y1="353" x2="800" y2="100" stroke="#ff4d6d" stroke-width="3" opacity="0">'
             '<animate attributeName="opacity" values="0;0;.95;.95;0;0" keyTimes="0;.71;.715;.74;.8;1" dur="12s" repeatCount="indefinite"/></line>')
    for k in range(14):
        dx, dy, r = (random.random() - .5) * 140, (random.random() - .3) * 90, 3 + random.random() * 5
        o.append(f'<circle cx="800" cy="92" r="{f(r)}" fill="none" stroke="#c9d4e6" stroke-width="1.5" opacity="0">'
                 f'<animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;.736;.737;.85;1" dur="12s" repeatCount="indefinite"/>'
                 f'<animateTransform attributeName="transform" type="translate" values="0,0;0,0;{f(dx)},{f(dy)};{f(dx)},{f(dy)}" keyTimes="0;.736;.85;1" dur="12s" repeatCount="indefinite"/></circle>')
    # dot swarm: precomputed spiral paths into the cube
    for i in range(120):
        x0, y0, c = src[i % 3]
        turn = (1 if random.random() < .5 else -1) * (1.4 + random.random())
        jit = (random.random() - .5) * 26
        pts = []
        for s in range(25):
            t = s / 24
            e = t * t * (3 - 2 * t)
            bx, by = x0 + (CUBE[0] - x0) * e, y0 + (CUBE[1] - y0) * e
            a, rad = t * math.pi * 2 * turn, (1 - t) * 70 + jit * (1 - t)
            pts.append(f"{f(bx + math.cos(a) * rad)},{f(by + math.sin(a) * rad * .55)}")
        dur = 5 + random.random() * 5
        beg = -random.random() * dur
        o.append(f'<circle r="{f(2.6 + random.random() * 1.6)}" fill="{c}"><animateMotion dur="{dur:.2f}s" begin="{beg:.2f}s" repeatCount="indefinite" path="M{" L".join(pts)}"/>'
                 f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.08;.9;1" dur="{dur:.2f}s" begin="{beg:.2f}s" repeatCount="indefinite"/></circle>')
    # cube on top
    o.append('<g transform="translate(600,415)"><polygon points="-150,-62 0,-128 150,-62 0,4" fill="none" stroke="#6ee7ff" stroke-width="12" opacity=".25" filter="url(#bl)"><animate attributeName="opacity" values=".15;.4;.15" dur="3.2s" repeatCount="indefinite"/></polygon>'
             '<polygon points="-150,-62 0,-128 150,-62 0,4" fill="url(#tp)" stroke="#2b3346" stroke-width="2"/>'
             '<polygon points="-150,-62 0,4 0,160 -150,94" fill="#0b0e14" stroke="#2b3346" stroke-width="2"/>'
             '<polygon points="150,-62 0,4 0,160 150,94" fill="#10141c" stroke="#2b3346" stroke-width="2"/>'
             '<text x="-75" y="72" text-anchor="middle" font-size="96" font-family="Georgia,serif" fill="#6ee7ff" opacity=".9">µ</text>'
             '<circle cx="0" cy="-62" r="5" fill="#ff4d6d" opacity=".8"/></g>')
    o.append('<text class="l" x="600" y="606" text-anchor="middle">D.A.T.A. F.I.N.G.E.R. P.O.I.N.T. · no cables · Wi-Fi only · counts and hashes in, nothing personal out</text></svg>')
    return "\n".join(o)


def turbo():
    # 22 s loop: Wi-Fi 0-7 s, cable (T.U.R.B.O.) 7-17 s, back to Wi-Fi 17-22 s
    D = 22
    kt = lambda *s: ";".join(f"{x / D:.4f}" for x in s)
    air = "M190,150 C380,40 560,40 690,170"
    cable = "M150,282 C160,470 610,470 700,300"
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 500" role="img" aria-label="T.U.R.B.O. handoff: a phone sends files to a micro-sign cube over Wi-Fi at about 18 megabytes a second. A USB-C cable plugs in and the pull moves to the cable at about 40 megabytes a second. The cable is unplugged and the pull goes back to Wi-Fi.">',
         '<defs><filter id="g"><feGaussianBlur stdDeviation="5"/></filter></defs><rect width="1000" height="500" fill="#07090e"/>',
         '<style>.l{fill:#7d889c;font:13px ui-monospace,Menlo,monospace}.b{font:700 30px ui-monospace,Menlo,monospace}</style>',
         # phone
         '<g transform="translate(150,190)"><rect x="-42" y="-86" width="84" height="172" rx="14" fill="#151a24" stroke="#5c6880" stroke-width="2"/><rect x="-34" y="-74" width="68" height="140" rx="6" fill="#0b0e14"/>'
         '<text y="-40" text-anchor="middle" class="l" style="font-size:11px">please</text><text y="-26" text-anchor="middle" class="l" style="font-size:11px">don\'t touch</text>'
         '<rect x="-26" y="-6" width="52" height="8" rx="4" fill="#1f2636"/>'
         f'<rect x="-26" y="-6" width="0" height="8" rx="4" fill="#6ee7ff"><animate attributeName="width" values="0;8;46;52" keyTimes="{kt(0, 7, 17, 22)}" dur="{D}s" repeatCount="indefinite"/></rect>'
         '<rect x="-10" y="86" width="20" height="6" rx="2" fill="#5c6880"/><text y="122" text-anchor="middle" class="l">phone</text></g>',
         # wifi arcs dim while on cable
         f'<g fill="none" stroke="#2a97c4" stroke-linecap="round" stroke-width="3"><animate attributeName="opacity" values="1;1;.25;.25;1;1" keyTimes="{kt(0, 6.99, 7, 16.99, 17, 22)}" dur="{D}s" repeatCount="indefinite"/>'
         '<path d="M128,80 A30,30 0 0 1 172,80" opacity=".9"/><path d="M118,70 A44,44 0 0 1 182,70" opacity=".6"/><path d="M108,60 A58,58 0 0 1 192,60" opacity=".35"/></g>',
         # cube
         '<g transform="translate(790,215)"><polygon points="-110,-48 0,-98 110,-48 0,2" fill="none" stroke="#6ee7ff" stroke-width="10" opacity=".25" filter="url(#g)"/>'
         '<polygon points="-110,-48 0,-98 110,-48 0,2" fill="#1b2232" stroke="#2b3346" stroke-width="2"/><polygon points="-110,-48 0,2 0,120 -110,70" fill="#0b0e14" stroke="#2b3346" stroke-width="2"/>'
         '<polygon points="110,-48 0,2 0,120 110,70" fill="#10141c" stroke="#2b3346" stroke-width="2"/><text x="-55" y="58" text-anchor="middle" font-size="74" font-family="Georgia,serif" fill="#6ee7ff">µ</text>'
         '<text y="150" text-anchor="middle" class="l">desk computer · checksums + custody</text></g>',
         # cable
         f'<path d="{cable}" fill="none" stroke="#ffb020" stroke-width="7" stroke-linecap="round" opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="{kt(0, 6.99, 7, 16.99, 17, 22)}" dur="{D}s" repeatCount="indefinite"/></path>']
    # Wi-Fi dots (visible 0-7 and 17-22), cable dots (visible 7-17)
    vis_wifi = f'values="1;1;0;0;1;1" keyTimes="{kt(0, 6.99, 7, 16.99, 17, 22)}"'
    vis_usb = f'values="0;0;1;1;0;0" keyTimes="{kt(0, 6.99, 7, 16.99, 17, 22)}"'
    for i in range(14):
        o.append(f'<circle r="4" fill="#2a97c4"><animateMotion dur="2.4s" begin="{-i * 2.4 / 14:.2f}s" repeatCount="indefinite" path="{air}"/>'
                 f'<animate attributeName="opacity" {vis_wifi} dur="{D}s" repeatCount="indefinite"/></circle>')
    for i in range(36):
        o.append(f'<circle r="4" fill="#ffb020"><animateMotion dur="1.1s" begin="{-i * 1.1 / 36:.2f}s" repeatCount="indefinite" path="{cable}"/>'
                 f'<animate attributeName="opacity" {vis_usb} dur="{D}s" repeatCount="indefinite"/></circle>')
    # readouts: swap text blocks by phase
    def block(vis, mode, col, now, avg, log):
        return (f'<g opacity="0"><animate attributeName="opacity" {vis} dur="{D}s" repeatCount="indefinite"/>'
                f'<text x="330" y="232" class="b" fill="{col}">{mode}</text><text x="330" y="270" class="b" fill="#e8edf6">{now}</text>'
                f'<text x="330" y="298" class="l" style="font-size:15px">{avg}</text><text x="500" y="488" text-anchor="middle" class="l" style="fill:#b9c3d6">{log}</text></g>')
    o.append(block(f'values="1;1;0;0" keyTimes="{kt(0, 6.99, 7, 22)}"', "📡 Wi-Fi", "#2a97c4", "17.8 MB/s now", "17.6 MB/s average", "new files 31/476 (📡 Wi-Fi · 17.8 MB/s now)"))
    o.append(block(vis_usb, "⚡ T.U.R.B.O. · USB-C", "#ffb020", "40.8 MB/s now", "36.9 MB/s average", "handoff: USB-C cable found · new files 33/476 (⚡ T.U.R.B.O. · USB-C · 40.8 MB/s now · 36.9 MB/s avg)"))
    o.append(block(f'values="0;0;1;1" keyTimes="{kt(0, 16.99, 17, 22)}"', "📡 Wi-Fi", "#2a97c4", "17.4 MB/s now", "30.2 MB/s average", "handoff: cable gone, back to Wi-Fi · new files 440/476"))
    o.append('</svg>')
    return "\n".join(o)


if __name__ == "__main__":
    for name, fn in (("data-finger-point.svg", data_finger_point), ("turbo.svg", turbo)):
        p = os.path.join(SITE, name)
        open(p, "w").write(fn())
        print(p, os.path.getsize(p), "bytes")

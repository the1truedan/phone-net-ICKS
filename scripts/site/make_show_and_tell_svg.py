#!/usr/bin/env python3
"""v0.9.4.1.1 S.H.O.W. A.N.D. T.E.L.L. hero animation (SMIL, no scripts), same look as turbo.svg / data-finger-point.svg.
Story, one 24 s loop:
  0-9 s   sealed (locked) records drop into the µ cube; pages come out with a green check; counter 0/25 -> 25/25,
          clock 0 -> 24 min, PDF/UA pass bar fills.
  9-20 s  six source streams (care records, clinic export, own notes, hours, pay stubs, agency letters) flow into a
          29-cell month grid; cells light month by month; a few cells flash amber (a gap between need and hours).
  20-24 s caption holds, then resets.
Aggregate numbers only; no names, dates of care or case details.
    python3 scripts/site/make_show_and_tell_svg.py > site/show-and-tell.svg
"""
DUR = 24
BG, PANEL, LINE, DIM, ACC, BLUE, AMB, GRN = "#07090e", "#151a24", "#2b3346", "#7d889c", "#6ee7ff", "#2a97c4", "#ffb020", "#4ade80"


def kt(*pairs):
    """values/keyTimes from (time_s, value) pairs."""
    return ";".join(str(v) for _, v in pairs), ";".join(f"{t / DUR:.4f}" for t, _ in pairs)


def anim(attr, *pairs, extra=""):
    v, k = kt(*pairs)
    return f'<animate attributeName="{attr}" values="{v}" keyTimes="{k}" dur="{DUR}s" repeatCount="indefinite"{extra}/>'


out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 500" role="img" aria-label="S.H.O.W. A.N.D. T.E.L.L.: '
       'sealed records drop into a micro-sign cube and come out as accessible, checked pages: 25 of 25 in 24 minutes. Then six '
       'local sources flow into a 29-month grid; months light up and a few flash amber where care needs and paid hours do not match.">',
       f'<defs><filter id="g"><feGaussianBlur stdDeviation="5"/></filter></defs><rect width="1000" height="500" fill="{BG}"/>',
       f'<style>.l{{fill:{DIM};font:13px ui-monospace,Menlo,monospace}}.b{{font:700 26px ui-monospace,Menlo,monospace}}'
       f'.s{{fill:{DIM};font:11px ui-monospace,Menlo,monospace}}</style>',
       f'<text x="40" y="44" class="b" fill="{ACC}">S.H.O.W. A.N.D. T.E.L.L.</text>',
       f'<text x="40" y="66" class="l">v0.9.4.1.1 · sealed records to accessible pages, then every month cross-checked · local only</text>']

# --- act 1: sealed records -> µ cube -> checked pages -------------------------------------------------------------
for i in range(5):  # envelopes falling into the cube, staggered
    y0, d = 90, i * 1.5
    out.append(f'<g opacity="0"><rect x="-26" y="-17" width="52" height="34" rx="3" fill="{PANEL}" stroke="#5c6880" stroke-width="2"/>'
               f'<path d="M-26,-17 L0,4 L26,-17" fill="none" stroke="#5c6880" stroke-width="2"/>'
               f'<rect x="-6" y="-2" width="12" height="10" rx="2" fill="{AMB}"/><path d="M-4,-2 v-4 a4,4 0 0 1 8,0 v4" fill="none" stroke="{AMB}" stroke-width="2"/>'
               f'<animateTransform attributeName="transform" type="translate" values="150,{y0};150,{y0};150,210;150,210" '
               f'keyTimes="0;{d / DUR:.4f};{(d + 1.2) / DUR:.4f};1" dur="{DUR}s" repeatCount="indefinite"/>'
               + anim("opacity", (0, 0), (d, 0), (d + .05, 1), (d + 1.1, 1), (d + 1.25, 0), (DUR, 0)) + '</g>')

out.append(f'<g transform="translate(150,280)"><polygon points="-70,-30 0,-62 70,-30 0,2" fill="none" stroke="{ACC}" stroke-width="10" opacity=".25" filter="url(#g)">'
           + anim("opacity", (0, .15), (4.5, .45), (9, .15), (DUR, .15)) + '</polygon>'
           f'<polygon points="-70,-30 0,-62 70,-30 0,2" fill="#1b2232" stroke="{LINE}" stroke-width="2"/>'
           f'<polygon points="-70,-30 0,2 0,78 -70,46" fill="#0b0e14" stroke="{LINE}" stroke-width="2"/>'
           f'<polygon points="70,-30 0,2 0,78 70,46" fill="#10141c" stroke="{LINE}" stroke-width="2"/>'
           f'<text x="-35" y="38" text-anchor="middle" font-size="46" font-family="Georgia,serif" fill="{ACC}">µ</text>'
           f'<text y="104" text-anchor="middle" class="l">P.A.P.E. · on this desk</text></g>')

for i in range(6):  # pages coming out with a check, then fading
    d = 1.2 + i * 1.3
    out.append(f'<g opacity="0"><rect x="-15" y="-20" width="30" height="40" rx="2" fill="#e7eef8"/>'
               f'<path d="M-9,-10 h18 M-9,-3 h18 M-9,4 h12" stroke="#9aa6ba" stroke-width="2"/>'
               f'<circle cx="11" cy="15" r="7" fill="{GRN}"/><path d="M7,15 l3,3 l5,-6" fill="none" stroke="#06210f" stroke-width="2"/>'
               f'<animateTransform attributeName="transform" type="translate" values="230,300;230,300;330,300;330,300" '
               f'keyTimes="0;{d / DUR:.4f};{(d + 1) / DUR:.4f};1" dur="{DUR}s" repeatCount="indefinite"/>'
               + anim("opacity", (0, 0), (d, 0), (d + .1, 1), (d + 1.6, 1), (d + 2.0, 0), (DUR, 0)) + '</g>')

# counters: records, minutes, PDF/UA bar
for n in range(0, 26, 5):
    t0 = n / 25 * 8.5
    t1 = min(t0 + 8.5 / 5, 8.5) if n < 25 else 20.5
    out.append(f'<text x="290" y="160" class="b" fill="#e7eef8" opacity="0">{n}/25'
               + anim("opacity", (0, 0), (t0, 0), (t0 + .01, 1), (t1, 1), (t1 + .01, 0), (DUR, 0)) + '</text>')
for m in (0, 6, 12, 18, 24):
    t0 = m / 24 * 8.5
    t1 = t0 + 8.5 / 4 if m < 24 else 20.5
    out.append(f'<text x="290" y="196" class="l" opacity="0">{m:02d} min · 787 pages'
               + anim("opacity", (0, 0), (t0, 0), (t0 + .01, 1), (t1, 1), (t1 + .01, 0), (DUR, 0)) + '</text>')
out.append(f'<text x="290" y="128" class="s">records accessible</text>'
           f'<rect x="290" y="210" width="150" height="8" rx="4" fill="#1f2636"/>'
           f'<rect x="290" y="210" width="0" height="8" rx="4" fill="{GRN}">' + anim("width", (0, 0), (8.5, 150), (20.5, 150), (20.6, 0), (DUR, 0)) + '</rect>'
           f'<text x="290" y="236" class="s">PDF/UA-1: 0 of 25 before · 25 of 25 after</text>')

# --- act 2: six sources -> 29-month grid ----------------------------------------------------------------------------
src = [("care records", ACC), ("clinic export", "#9bdfff"), ("own notes", "#f0b429"), ("hours", "#c4b5fd"),
       ("pay stubs", GRN), ("agency letters", "#fca5a5")]
for i, (name, col) in enumerate(src):
    y = 290 + i * 26
    out.append(f'<text x="470" y="{y + 4}" class="s" text-anchor="end" opacity="0">{name}'
               + anim("opacity", (0, 0), (9, 0), (9.4, 1), (20.5, 1), (21, 0), (DUR, 0)) + '</text>')
    for j in range(3):
        out.append(f'<circle r="3.5" fill="{col}" opacity="0"><animateMotion dur="2s" begin="{-j * .66:.2f}s" repeatCount="indefinite" '
                   f'path="M480,{y} C560,{y} 600,{360} 640,{360}"/>'
                   + anim("opacity", (0, 0), (9.2, 0), (9.5, 1), (19.5, 1), (20, 0), (DUR, 0)) + '</circle>')

amber = {5, 6, 13, 18, 19, 20}   # illustrative only: a few months where need and paid hours differ
for k in range(29):
    cx, cy = 660 + (k % 10) * 30, 300 + (k // 10) * 30
    t = 10 + k * (9 / 29)
    fill = AMB if k in amber else ACC
    out.append(f'<rect x="{cx}" y="{cy}" width="24" height="24" rx="4" fill="#1b2232" stroke="{LINE}"/>'
               f'<rect x="{cx}" y="{cy}" width="24" height="24" rx="4" fill="{fill}" opacity="0">'
               + anim("opacity", (0, 0), (t, 0), (t + .3, .85 if k in amber else .55), (20.5, .85 if k in amber else .55), (21, 0), (DUR, 0)) + '</rect>')
out.append(f'<text x="660" y="282" class="s">29 months · 6 sources · one local GPU</text>'
           f'<text x="660" y="410" class="s" opacity="0">amber = need and paid hours do not match'
           + anim("opacity", (0, 0), (15, 0), (15.5, 1), (20.5, 1), (21, 0), (DUR, 0)) + '</text>')

out.append(f'<text x="40" y="470" class="l">25 sealed records · 787 pages · 24 min to accessible · 29 months cross-checked in 23 min · nothing left the house</text>')
out.append('</svg>')
print("\n".join(out))

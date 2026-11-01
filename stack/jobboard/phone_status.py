#!/usr/bin/env python3
"""Full-screen status page for the phone being pulled (phone-net-ICKS look). Standard library only.

Shows counts only (no names, no message text), so it is safe on a screen anyone can see.

    python3 stack/jobboard/phone_status.py --root /path/to/recon_dir [--port 8799]
    adb reverse tcp:8799 tcp:8799          # the phone reaches the Mac over the USB cable
    adb shell am start -a android.intent.action.VIEW -d http://localhost:8799 com.android.chrome
    adb shell svc power stayon usb         # screen stays on while plugged in (undo: svc power stayon false)

Reads from --root: PULL_LOG.txt ("content://X rows=N", "phase... done", "sdcard + system done"),
android_*/mms_parts (saved attachment count), voicemail_vvm/SHA256SUMS_share.txt, ios_backup/ (size).
"""
import argparse, glob, json, os, re, subprocess, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

A = argparse.ArgumentParser()
A.add_argument("--root", required=True)
A.add_argument("--port", type=int, default=8799)
A.add_argument("--bind", default="127.0.0.1")
A.add_argument("--title", default="Recon in progress")
A.add_argument("--next", default="📲 When you're ready: connect the iPad, unlock it, tap <b>Trust</b>.", help="finish-screen next step (HTML)")
A.add_argument("--redact", action="store_true", help="screenshot mode: generic title, counts rounded")
ARGS = A.parse_args()
SAMPLES = []  # (time, attachments saved) for the ETA


def du(path):
    try:
        return int(subprocess.run(["du", "-sk", path], capture_output=True, text=True).stdout.split()[0]) * 1024
    except Exception:
        return 0


def status():
    R = ARGS.root
    log = open(os.path.join(R, "PULL_LOG.txt"), encoding="utf-8", errors="replace").read() if os.path.exists(os.path.join(R, "PULL_LOG.txt")) else ""
    rows = {k: int(v) for k, v in re.findall(r"content://(\S+) rows=(\d+)", log)}
    steps = []
    def add(icon, name, done, total=None, note=""):
        steps.append({"icon": icon, "name": name, "done": done, "total": total, "note": note})
    for key, icon, name in [("sms", "💬", "Texts"), ("mms", "🖼️", "Picture messages"), ("call_log/calls", "📞", "Calls"),
                            ("com.android.contacts/raw_contacts", "👥", "Contacts"), ("com.android.calendar/events", "📅", "Calendar")]:
        if key in rows:
            add(icon, name, rows[key], rows[key])
    parts_total = rows.get("mms/part")
    parts_dir = (glob.glob(os.path.join(R, "android_*", "mms_parts")) or [None])[0]
    if parts_total and parts_dir:
        n = len(os.listdir(parts_dir))
        now = time.time()
        SAMPLES.append((now, n)); del SAMPLES[:-60]
        eta = ""
        old = [s for s in SAMPLES if now - s[0] > 20]
        if old and n > old[0][1] and n < parts_total:
            rate = (n - old[0][1]) / (now - old[0][0])
            m = int((parts_total - n) / rate / 60)
            eta = f"about {m // 60} h {m % 60} min left" if m >= 60 else f"about {m} min left"
        add("📎", "Message attachments", n, parts_total, eta)
    md = re.findall(r"mms part binaries=(\d+) \(resume done\)", log)
    if md:
        for st in steps:
            if st["name"] == "Message attachments":
                st["done"] = st["total"] = int(md[-1]); st["note"] = "all saved"
    nf = re.findall(r"new files (\d+)/(\d+)", log)
    if nf:
        k, tot = map(int, nf[-1])
        add("🗂️", "New files", tot if "phase1 done" in log else k, tot, re.search(r"SAFE TO UNPLUG: (\d+) new files", log) and f"{re.search(r'SAFE TO UNPLUG: (\d+) new files', log).group(1)} saved, rest already on the drive" or "")
    m = re.search(r"sdcard \+ system done \(([^,]+), (\d+) files\)", log)
    if m:
        add("📁", "Phone storage", int(m.group(2)), int(m.group(2)), m.group(1))
    vm = os.path.join(R, "voicemail_vvm", "SHA256SUMS_share.txt")
    if os.path.exists(vm):
        u = len({l.split()[0] for l in open(vm) if l.strip()})
        add("🎙️", "Voicemails", u, u)
    ios = os.path.join(R, "ios_backup")
    if "phase2 done" in log:
        add("📲", "iPad backup", 1, 1, f"{du(ios) / 1e9:.1f} GB")
    elif re.search(r"\d iOS device [0-9a-fA-F-]{8,}", log):
        add("📲", "iPad backup", 0, None, f"{du(ios) / 1e9:.1f} GB so far")
    elif "phase2 waiting" in log:
        add("📲", "iPad backup", 0, None, "waiting for the iPad")
    phone_steps = [st for st in steps if st["name"] != "iPad backup"]
    complete = bool(phone_steps) and all(st["total"] and st["done"] >= st["total"] for st in phone_steps)
    summary = {st["name"]: st["done"] for st in phone_steps}
    if m:
        summary["Storage"] = m.group(1)
    total = sum(s["total"] or 0 for s in steps) or 1
    done = sum(min(s["done"], s["total"] or 0) for s in steps)
    last = log.strip().splitlines()[-1][:19] if log.strip() else ""
    if ARGS.redact:
        rnd = lambda n: n if n is None or n < 20 else (round(n, -1) if n < 1000 else round(n, -2))
        for st in steps:
            st["done"], st["total"] = rnd(st["done"]), rnd(st["total"])
            st["note"] = re.sub(r"\d+(\.\d+)?\s?(M|GB)", "", st["note"]).strip(" ·")
    if ARGS.redact:
        summary = {k: (rnd(v) if isinstance(v, int) else "") for k, v in summary.items()}
    return {"next": ARGS.next, "complete": complete, "summary": summary,
            "title": "Saving a loved one's phone" if ARGS.redact else ARGS.title, "steps": steps, "pct": 100.0 if complete else round(100 * done / total, 1), "updated": time.strftime("%-I:%M:%S %p"), "last_log": last}


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0a0d14"><title>phone+net+I.C.K.S. · status</title>
<style>
:root{--bg:#0a0d14;--panel:#121722;--panel2:#181e2c;--line:#273044;--fg:#e7eef8;--dim:#8b97ad;--dimmer:#5c6880;--accent:#6ee7ff;--soft:#9bdfff;--mu:#f0b429;--violet:#8a6fd1;
--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--fg);font-family:ui-sans-serif,-apple-system,"Segoe UI",system-ui,sans-serif}
body{display:flex;flex-direction:column;align-items:center;padding:max(18px,env(safe-area-inset-top)) 16px 24px;overflow-x:hidden;
background:radial-gradient(1200px 700px at 50% -10%,#10223a 0%,transparent 60%),var(--bg)}
.logo{display:block;flex:none;width:min(62vw,320px);height:auto;aspect-ratio:240/200;margin-top:2vh}
.word{font-family:var(--mono);font-size:clamp(20px,6vw,34px);letter-spacing:.04em;margin:8px 0 2px;text-align:center}
.word b{color:var(--accent)} .word i{color:var(--mu);font-style:normal}
.sub{color:var(--dim);font-size:clamp(14px,3.8vw,18px);text-align:center}
.big{font-family:var(--mono);font-size:clamp(46px,16vw,96px);font-weight:700;margin:2vh 0 0;color:var(--accent);text-shadow:0 0 24px #6ee7ff55}
.bar{width:min(92vw,560px);height:10px;border-radius:6px;background:var(--panel2);border:1px solid var(--line);overflow:hidden;margin:6px 0 2vh}
.bar>div{height:100%;background:linear-gradient(90deg,var(--accent),var(--violet));width:0;transition:width 1s}
.steps{width:min(94vw,560px);display:grid;gap:10px}
.step{display:flex;align-items:center;gap:14px;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 14px}
.ring{width:54px;height:54px;flex:none}.ring circle{fill:none;stroke-width:6}.ring .bg{stroke:var(--grid,#1f2636)}
.ring .fg{stroke:var(--accent);stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%;transition:stroke-dashoffset 1s}
.ring.done .fg{stroke:#3ddc97}.ring.spin .fg{stroke:var(--mu);animation:spin 1.6s linear infinite;transform-origin:50% 50%}
@keyframes spin{to{transform:rotate(270deg)}}
.ring text{fill:var(--fg);font:600 13px var(--mono);text-anchor:middle;dominant-baseline:central}
.name{font-size:clamp(17px,4.6vw,22px);font-weight:600}.meta{color:var(--dim);font-family:var(--mono);font-size:clamp(13px,3.4vw,15px)}
.done{display:none;width:min(94vw,560px);text-align:center;margin:0 0 2vh}
.done h2{font-family:var(--mono);font-size:clamp(30px,9vw,52px);letter-spacing:.06em;color:#3ddc97;margin:.2em 0;text-shadow:0 0 22px #3ddc9755}
.done p{font-size:clamp(17px,4.6vw,21px);line-height:1.5;margin:.4em 0;color:var(--fg)}
.stats{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:14px 0}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 8px}
.stat b{display:block;font-family:var(--mono);font-size:clamp(20px,6vw,28px);color:var(--accent)}
.stat span{color:var(--dim);font-size:clamp(13px,3.6vw,15px)}
.next{background:#3ddc9718;border:1px solid #3ddc97;border-radius:14px;padding:12px;font-size:clamp(17px,4.6vw,20px);margin-top:8px}
body.finished .bar,body.finished #pct{display:none}body.finished .done{display:block}
.foot{color:var(--dimmer);font-family:var(--mono);font-size:12px;margin-top:2vh;text-align:center}
.tap{color:var(--dimmer);font-size:12px;margin-top:6px}
.brand{color:var(--dimmer);font-family:var(--mono);font-size:12px;margin-top:10px;text-align:center;line-height:1.6}.brand i{color:var(--dim)}.brand b{color:var(--mu);font-weight:400}
/* logo animation */
.pulse{animation:pulse 2.4s ease-out infinite;transform-origin:center}
.pulse.d2{animation-delay:.8s}.pulse.d3{animation-delay:1.6s}
@keyframes pulse{0%{opacity:.9;transform:scale(.6)}100%{opacity:0;transform:scale(1.5)}}
.node{animation:blink 2.4s ease-in-out infinite}.node.n2{animation-delay:.6s}.node.n3{animation-delay:1.2s}.node.n4{animation-delay:1.8s}
@keyframes blink{0%,100%{fill:#5c6880}50%{fill:#6ee7ff}}
.flow{stroke-dasharray:4 6;animation:flow 1.2s linear infinite}@keyframes flow{to{stroke-dashoffset:-20}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
</style></head><body>
<svg class="logo" width="240" height="200" viewBox="0 0 240 200" aria-label="phone-net-ICKS">
 <g transform="translate(120 100)">
  <circle class="pulse" r="70" fill="none" stroke="#6ee7ff" stroke-width="1.5"/>
  <circle class="pulse d2" r="70" fill="none" stroke="#8a6fd1" stroke-width="1.5"/>
  <circle class="pulse d3" r="70" fill="none" stroke="#f0b429" stroke-width="1.2"/>
 </g>
 <g stroke="#273044" stroke-width="2" fill="none">
  <path class="flow" stroke="#6ee7ff" d="M120 100 L40 40"/><path class="flow" stroke="#6ee7ff" d="M120 100 L200 40"/>
  <path class="flow" stroke="#8a6fd1" d="M120 100 L40 160"/><path class="flow" stroke="#f0b429" d="M120 100 L200 160"/>
 </g>
 <circle class="node" cx="40" cy="40" r="9"/><circle class="node n2" cx="200" cy="40" r="9"/>
 <circle class="node n3" cx="40" cy="160" r="9"/><circle class="node n4" cx="200" cy="160" r="9"/>
 <rect x="96" y="56" width="48" height="88" rx="10" fill="#121722" stroke="#6ee7ff" stroke-width="3"/>
 <rect x="103" y="66" width="34" height="62" rx="3" fill="#0a0d14"/>
 <path d="M108 112 l8 -14 l7 9 l6 -8 l5 13 z" fill="#6ee7ff" opacity=".8"/>
 <circle cx="120" cy="136" r="3" fill="#6ee7ff"/>
</svg>
<div class="word">phone<i>+</i>net<i>+</i><b>I.C.K.S.</b></div>
<div class="sub" id="title">Recon in progress</div>
<div class="big" id="pct">–</div>
<div class="bar"><div id="bar"></div></div>
<div class="done" id="done"><h2>WORK COMPLETED</h2>
<p>Everything on this phone is safe now: the words, the voices, the pictures.<br>Nothing left the house. Take a breath. You did this.</p>
<div class="stats" id="stats"></div>
<div class="next">✅ <b>Safe to unplug this phone.</b><br><span id="next"></span></div></div>
<div class="steps" id="steps"></div>
<div class="foot">please leave plugged in · <span id="upd"></span></div>
<div class="tap" id="tap">tap for full screen</div>
<div class="brand"><i>prepare for the care when we cannot be there</i><br><b>μ</b> M.A.N.A.G.E.R. LLC © 2026 · MIT License</div>
<script>
const C=2*Math.PI*24;
function ring(s){const pct=s.total?Math.min(1,s.done/s.total):0;const cls=s.total&&s.done>=s.total?'done':(s.total?'':'spin');
 const off=s.total?C*(1-pct):C*0.7;const label=s.total?(s.done>=s.total?'✓':Math.floor(pct*100)+'%'):'…';
 return `<svg class="ring ${cls}" viewBox="0 0 60 60"><circle class="bg" cx="30" cy="30" r="24"/><circle class="fg" cx="30" cy="30" r="24" stroke-dasharray="${C}" stroke-dashoffset="${off}"/><text x="30" y="30">${label}</text></svg>`}
function fmt(n){return n.toLocaleString()}
async function tick(){try{const r=await fetch('status.json',{cache:'no-store'});const j=await r.json();
 document.getElementById('title').textContent=j.complete?j.title.replace('saving','saved'):j.title;document.getElementById('pct').textContent=j.pct+'%';
 document.getElementById('bar').style.width=j.pct+'%';document.getElementById('upd').textContent='updated '+j.updated;
 document.body.classList.toggle('finished',!!j.complete);document.getElementById('next').innerHTML=j.next||'';
 if(j.complete){const ic={"Texts":"💬","Picture messages":"🖼️","Calls":"📞","Contacts":"👥","Calendar":"📅","Message attachments":"📎","Phone storage":"📁","Voicemails":"🎙️","Storage":"💾"};
  const lab={"Message attachments":"attachments","Picture messages":"picture msgs","Phone storage":"files","Storage":"storage"};
  document.getElementById('stats').innerHTML=Object.entries(j.summary).filter(([k,v])=>v!=='').map(([k,v])=>`<div class="stat"><b>${typeof v==='number'?fmt(v):v}</b><span>${ic[k]||''} ${(lab[k]||k).toLowerCase()}</span></div>`).join('');}
 document.getElementById('steps').innerHTML=j.steps.map(s=>`<div class="step">${ring(s)}<div><div class="name">${s.icon} ${s.name}</div><div class="meta">${s.total?fmt(s.done)+' / '+fmt(s.total):''}${s.note?(s.total?' · ':'')+s.note:''}</div></div></div>`).join('');
}catch(e){document.getElementById('upd').textContent='waiting for the Mac…'}}
tick();setInterval(tick,3000);
let wl=null;async function wake(){try{wl=await navigator.wakeLock.request('screen')}catch(e){}}
wake();document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')wake()});
document.body.addEventListener('click',()=>{document.documentElement.requestFullscreen?.().catch(()=>{});document.getElementById('tap').style.display='none';wake()});
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/status.json"):
            body, ct = json.dumps(status()).encode(), "application/json"
        else:
            body, ct = PAGE.encode(), "text/html; charset=utf-8"
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"phone status on http://{ARGS.bind}:{ARGS.port}", flush=True)
    ThreadingHTTPServer((ARGS.bind, ARGS.port), H).serve_forever()

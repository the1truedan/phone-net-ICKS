#!/usr/bin/env python3
"""Full-screen status page for the phone being pulled (phone-net-ICKS look). Standard library only.

Shows counts only (no message text). While files copy it also shows the current file name (camera-style names
such as 20261118_152753.mp4) and the retry lines; --redact hides those names for a screen anyone can see.
2026-11-19: big percent-by-bytes, MB/s, ETA clock, terminal panel with spinner, red STALLED after 90 s with no
new bytes, μ brand box.

    python3 stack/jobboard/phone_status.py --root /path/to/recon_dir [--port 8799]
    adb reverse tcp:8799 tcp:8799          # the phone reaches the Mac over the USB cable
    adb shell am start -a android.intent.action.VIEW -d http://localhost:8799   (the app picks the default browser, else Brave, else Chrome)
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


_HIST = {"t": 0, "v": None}


def history():
    """All pulls for this phone: every sibling folder with the same _delta_ prefix (cached 10 min)."""
    if time.time() - _HIST["t"] < 600:
        return _HIST["v"]
    v = None
    m = re.match(r"(.*_delta_)\d{4}-\d{2}-\d{2}\w*$", os.path.abspath(ARGS.root))
    if m:
        dirs = sorted(d for d in glob.glob(m.group(1) + "*") if os.path.exists(os.path.join(d, "custody_log.txt")))
        files = texts = calls = 0
        for d in dirs:
            try:
                files += sum(1 for _ in open(os.path.join(d, "SHA256SUMS.txt"), errors="replace"))
            except OSError:
                pass
            lg = os.path.join(d, "PULL_LOG.txt")
            t = open(lg, errors="replace").read() if os.path.exists(lg) else ""
            texts += sum(int(x) for x in re.findall(r"content://sms rows=(\d+)", t)[-1:])
            calls += sum(int(x) for x in re.findall(r"content://call_log/calls rows=(\d+)", t)[-1:])
        if dirs:
            first = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(dirs[0]))
            v = {"pulls": len(dirs), "files": files, "texts": texts, "calls": calls, "since": first.group(0) if first else ""}
    _HIST.update(t=time.time(), v=v)
    return v


STALL_S = 90        # no new bytes for this long while files are copying = STALLED (red)
BYTES = []          # (time, bytes saved) seen by this server, for the smoothed speed
GROW = {"t": 0.0, "b": -1}


def _ts(s):
    try:
        return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M:%S"))
    except ValueError:
        return None


def _left(sec):
    m = int(sec // 60)
    return f"{int(sec)} s" if sec < 120 else (f"{m // 60} h {m % 60:02d} min" if m >= 60 else f"{m} min")


def transfer(R, log, wanted, pl, nf, now=None):
    """Bytes view of the file copy: percent by size, smoothed MB/s, ETA, the file being copied, STALLED, retries.

    Bytes saved = finished files + the partial file on disk (stat), so it works with any pull script; the
    `bytes D/T` lines play_delta_pull.sh writes every 30 s give the speed when this page has only just opened."""
    now = now or time.time()
    run = log[log.rfind("phase1 start"):] if "phase1 start" in log else log
    tot_b = sum(sz for sz, _ in wanted)
    done_b, last_act, cur = 0, 0.0, None
    for sz, lp in wanted:
        try:
            st = os.stat(lp)
        except OSError:
            continue
        done_b += min(st.st_size, sz)
        last_act = max(last_act, st.st_mtime)
        if st.st_size < sz and (cur is None or st.st_mtime > cur[3]):
            cur = (os.path.basename(lp), st.st_size, sz, st.st_mtime)
    try:
        last_act = max(last_act, os.path.getmtime(pl))
    except OSError:
        pass
    # smoothed speed over the last ~15 s of samples; a retry deletes the partial file, so a drop starts over
    if BYTES and done_b < BYTES[-1][1]:
        BYTES.clear()
    BYTES.append((now, done_b))
    while BYTES and now - BYTES[0][0] > 60:
        BYTES.pop(0)
    if GROW["b"] >= 0 and done_b > GROW["b"]:   # growth seen by this server (the first sample is only a baseline)
        GROW["t"] = now
    GROW["b"] = done_b
    last_act = max(last_act, GROW["t"])
    speed = None
    ref = next((s for s in BYTES if now - s[0] <= 18), None)
    if ref and now - ref[0] >= 5:
        speed = max(0.0, (done_b - ref[1]) / (now - ref[0]))
    else:   # page just opened: use the pull script's own bytes lines
        bl = [(_ts(t), int(d)) for t, d in re.findall(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) bytes (\d+)/\d+", run)]
        bl = [b for b in bl if b[0]]
        if len(bl) >= 2 and now - bl[-1][0] < 120:
            old = next((b for b in reversed(bl[:-1]) if bl[-1][0] - b[0] >= 10), None)
            if old and bl[-1][1] >= old[1]:
                speed = (bl[-1][1] - old[1]) / (bl[-1][0] - old[0])
    finished = "phase1 done" in run
    active = bool(nf) and not finished and tot_b > 0 and done_b < tot_b
    idle = now - last_act if last_act else 0
    stalled = active and idle >= STALL_S
    moving = active and not stalled and idle < 20
    if stalled:
        speed = 0.0
    eta_s = (tot_b - done_b) / speed if active and speed and speed > 1024 else None
    ev = [l for l in run.splitlines() if re.search(r" (retry \d|FAILED|STALLED|NOT COMPLETE)", l)]
    k, n = (int(nf[-1][0]), int(nf[-1][1])) if nf else (0, len(wanted))
    out = {"pct_b": round(100 * done_b / tot_b, 1) if tot_b else 0.0, "done_b": done_b, "tot_b": tot_b,
           "speed": speed, "eta_s": eta_s, "left": _left(eta_s) if eta_s is not None else "",
           "eta_clock": time.strftime("%-I:%M %p", time.localtime(now + eta_s)) if eta_s is not None else "",
           "k": k, "n": n, "active": active, "moving": moving, "stalled": stalled, "idle_s": int(idle),
           "waiting_phone": stalled and bool(ev) and " retry " in run.strip().splitlines()[-1],
           "cur": {"name": cur[0], "done": cur[1], "size": cur[2], "pct": round(100 * cur[1] / cur[2], 1)} if cur and active else None,
           "retries": sum(1 for l in ev if " retry " in l), "stalls": sum(1 for l in ev if " STALLED " in l),
           "failed": sum(1 for l in ev if " FAILED " in l), "events": [l[11:] for l in ev[-6:]]}
    if ARGS.redact:   # file names stay off a screen anyone can see
        if out["cur"]:
            out["cur"]["name"] = "a file"
        out["events"] = [re.sub(r"(retry \d for |STALLED |FAILED )(.+?)(?= \(| at \d|$)", r"\1a file", e) for e in out["events"]]
    return out


def status():
    R = ARGS.root
    wanted = []
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
    pl, pr = os.path.join(R, "_pull_list.txt"), os.path.join(R, "_prior.txt")
    if os.path.exists(pl):
        prior = set(open(pr).read().split("\n")) if os.path.exists(pr) else set()
        kinds = {"rec": ("🎙️", "New recordings", r"\.(m4a|mp3|wav|amr|aac|ogg|opus)$|/\.pending-"),
                 "vid": ("🎬", "New videos", r"\.(mp4|mov|3gp)$"), "pic": ("🖼️", "New pictures", r"\.(jpe?g|png|heic)$")}
        want = {k: 0 for k in kinds}; have = {k: 0 for k in kinds}
        wanted = []   # (phone size, local path) of every file this pull copies, for the byte counts
        for line in open(pl, errors="replace"):
            parts = line.rstrip("\n").split("|", 2)
            if len(parts) < 3 or f"{parts[1]}|{os.path.basename(parts[2])}" in prior:
                continue
            lp = os.path.join(R, parts[2].replace("/storage/", "", 1))
            sz = int(parts[1]) if parts[1].isdigit() else 0
            wanted.append((sz, lp))
            for k, (_, _, rx) in kinds.items():
                if re.search(rx, parts[2], re.I):
                    want[k] += 1
                    try:
                        if os.path.getsize(lp) >= sz:   # a partial file is not saved yet
                            have[k] += 1
                    except OSError:
                        pass
                    break
        for k, (ic, name, _) in kinds.items():
            if want[k]:
                add(ic, name, have[k], want[k])
    nf = re.findall(r"new files (\d+)/(\d+)(?: \(([^)]*)\))?", log)
    xfer = transfer(R, log, wanted, pl, nf) if os.path.exists(pl) else None
    if nf:
        k, tot = int(nf[-1][0]), int(nf[-1][1])
        speed = nf[-1][2]   # e.g. "⚡ T.U.R.B.O. · USB-C · 38.2 MB/s now · 35.0 MB/s avg" (Wi-Fi pulls)
        if speed and "phase1 done" not in log:
            add("🗂️", "New files", k, tot, speed)
        else:
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
    # Texts, calls and contacts are saved in one quick step and count as finished at once. Until the file list exists,
    # show a waiting "New files" step so the page does not open at 100% (or show SECURED) before any file is copied.
    files_seen = bool(nf) or os.path.exists(pl) or bool(m)
    if not files_seen and "phase1 done" not in log:
        add("🗂️", "New files", 0, None, "listing the phone…")
    phone_steps = [st for st in steps if st["name"] != "iPad backup"]
    complete = "phase1 done" in log or (files_seen and bool(phone_steps) and all(st["total"] and st["done"] >= st["total"] for st in phone_steps))
    summary = {st["name"]: st["done"] for st in phone_steps if st["total"] is not None}
    if m:
        summary["Storage"] = m.group(1)
    # Weigh by step, not by count (thousands of text rows must not swamp 19 files). Quick database steps weigh 1, file
    # copies weigh 3; a step with no total yet counts as 0.
    quick = {"Texts", "Picture messages", "Calls", "Contacts", "Calendar", "Voicemails"}
    w = lambda s: 1 if s["name"] in quick else 3
    total = sum(w(s) for s in steps) or 1
    done = sum(w(s) * min(s["done"] / s["total"], 1) for s in steps if s["total"])
    last = log.strip().splitlines()[-1][:19] if log.strip() else ""
    if ARGS.redact:
        rnd = lambda n: n if n is None or n < 20 else (round(n, -1) if n < 1000 else round(n, -2))
        for st in steps:
            st["done"], st["total"] = rnd(st["done"]), rnd(st["total"])
            st["note"] = re.sub(r"\d+(\.\d+)?\s?(M|GB)", "", st["note"]).strip(" ·")
    if ARGS.redact:
        summary = {k: (rnd(v) if isinstance(v, int) else "") for k, v in summary.items()}
    h = None if ARGS.redact else history()
    pct = min(99.0, round(100 * done / total, 1))
    if xfer and xfer["tot_b"] and not complete:
        pct = min(99.9, xfer["pct_b"])   # while files copy, the big number is the share of bytes saved
    return {"history": h, "last_done": last, "next": ARGS.next, "complete": complete, "summary": summary, "xfer": xfer,
            "title": "Saving a loved one's phone" if ARGS.redact else ARGS.title, "steps": steps, "pct": 100.0 if complete else pct, "updated": time.strftime("%-I:%M:%S %p"), "last_log": last}


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
.fine{color:var(--dim);font-family:var(--mono);font-size:clamp(12px,3.2vw,14px);line-height:1.6;margin-top:12px}
.next{background:#3ddc9718;border:1px solid #3ddc97;border-radius:14px;padding:12px;font-size:clamp(17px,4.6vw,20px);margin-top:8px}
body.finished .bar,body.finished #pct,body.finished .steps,body.finished .foot{display:none}body.finished .done{display:block}
.done h2.secured{font-size:clamp(40px,13vw,84px);line-height:1.05;margin:.3em 0}
.unplug{font-family:var(--mono);font-weight:800;font-size:clamp(44px,14vw,92px);line-height:1.05;letter-spacing:.04em;color:#0a0d14;background:#3ddc97;border-radius:18px;padding:.25em .2em;margin:.2em 0 .4em}
/* slow pulse, about once a second: well under the 3-per-second flash limit */
.secured,.unplug{animation:beacon 1.1s ease-in-out infinite alternate}@keyframes beacon{from{opacity:1}to{opacity:.25}}
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
body>*{flex-shrink:0}  /* the page is taller than the screen: nothing may squash (bar and panel have overflow:hidden) */
/* μ cube, centred in the logo, same look as the site SVGs (turbo.svg, greek_squat_logo.svg): dark isometric cube,
   cyan glow edge, serif μ on the left face. Sways slowly; brighter and quicker while bytes are moving. */
.cube{transform-box:fill-box;transform-origin:50% 60%;animation:sway 9s ease-in-out infinite}
.cube .glow{animation:glowp 3.2s ease-in-out infinite}
.cube .mu{animation:mug 3.2s ease-in-out infinite}
body.moving .cube{animation-duration:3s}body.moving .cube .glow{animation-duration:1s}body.moving .cube .mu{animation-duration:1s}
body.stalled .cube .glow{stroke:#ff5d5d;animation:none;opacity:.55}body.stalled .cube{animation:none}
@keyframes sway{0%,100%{transform:rotate(-6deg) translateY(0)}50%{transform:rotate(6deg) translateY(-4px)}}
@keyframes glowp{0%,100%{opacity:.15}50%{opacity:.6}}
@keyframes mug{0%,100%{filter:drop-shadow(0 0 2px #6ee7ff66)}50%{filter:drop-shadow(0 0 9px #6ee7ffcc)}}
/* finished: the μ cube stays above DATA POINTS SECURED, alone, turning like a turntable (Dan 2026-11-19: brand front and centre) */
body.finished .logo>g:not(.cube),body.finished .logo>circle,body.finished .logo>defs~g:not(.cube){display:none}
body.finished .logo{width:min(82vw,360px);margin:-3vh 0 -7vh;animation:turn 6s linear infinite;transform-style:preserve-3d}
body.finished .cube{animation:none}body.finished .cube .glow{animation-duration:1.4s}
@keyframes turn{from{transform:perspective(600px) rotateY(0)}to{transform:perspective(600px) rotateY(360deg)}}
/* terminal-style live transfer panel (uv / Claude Code CLI look) */
.kpis{flex:none;width:min(94vw,560px);display:none;grid-template-columns:1fr 1fr;gap:10px;margin:0 0 10px}
.kpis.on{display:grid}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:8px 12px;font-family:var(--mono)}
.kpi b{display:block;font-size:clamp(30px,10vw,54px);line-height:1.1;color:var(--fg);white-space:nowrap}
.kpi b small{font-size:.45em;color:var(--dim);font-weight:400}
.kpi span{color:var(--dim);font-size:clamp(12px,3.4vw,15px)}.kpi em{font-style:normal;color:var(--soft)}
.term{flex:none;width:min(94vw,560px);display:none;background:#05070b;border:1px solid var(--line);border-radius:12px;margin:0 0 2vh;
font-family:var(--mono);font-size:clamp(13px,3.6vw,16px);overflow:hidden}
.term.on{display:block}
.tbar{display:flex;align-items:center;gap:6px;padding:7px 10px;background:var(--panel2);border-bottom:1px solid var(--line);color:var(--dimmer);font-size:12px}
.tbar i{width:10px;height:10px;border-radius:50%;background:#ff5f57}.tbar i+i{background:#febc2e}.tbar i+i+i{background:#28c840}.tbar span{margin-left:6px}
.tbody{padding:10px 12px 12px;line-height:1.55}
.tl{white-space:pre;overflow:hidden;text-overflow:ellipsis}
.sp{color:var(--accent);display:inline-block;width:1.4em}.tb{color:var(--accent)}.tb u{text-decoration:none;color:#273044}
.dim{color:var(--dim)}.ok{color:#3ddc97}.warn{color:var(--mu)}.bad{color:#ff5d5d}
.tlog{margin-top:6px;border-top:1px dashed var(--line);padding-top:6px;font-size:.85em}.tlog:empty{display:none}
.stall{flex:none;display:none;font-family:var(--mono);font-weight:800;color:#fff;background:#d92b2b;border-radius:12px;padding:10px 12px;
width:min(94vw,560px);text-align:center;font-size:clamp(20px,6vw,30px);margin:0 0 10px;animation:beacon 1.1s ease-in-out infinite alternate}
.stall small{display:block;font-weight:400;font-size:.55em;opacity:.9}
body.stalled .stall{display:block}body.stalled #pct{color:#ff5d5d;text-shadow:0 0 24px #ff5d5d55}body.stalled .term{border-color:#d92b2b}
body.stalled .bar>div{background:#d92b2b}body.stalled .sp{color:#ff5d5d}
body.finished .kpis,body.finished .term,body.finished .stall{display:none!important}
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
 <defs><filter id="cg" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="4"/></filter>
  <linearGradient id="gold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe29a"/><stop offset="1" stop-color="#f0b429"/></linearGradient></defs>
 <g class="cube" aria-label="μ M.A.N.A.G.E.R."><g transform="translate(120 102)">
  <polygon class="glow" points="-40,-16 0,-34 40,-16 0,2" fill="none" stroke="#6ee7ff" stroke-width="8" filter="url(#cg)"/>
  <polygon points="-40,-16 0,-34 40,-16 0,2" fill="#1b2232" stroke="#2b3346" stroke-width="1.6"/>
  <polygon points="-40,-16 0,2 0,46 -40,28" fill="#0b0e14" stroke="#2b3346" stroke-width="1.6"/>
  <polygon points="40,-16 0,2 0,46 40,28" fill="#10141c" stroke="#2b3346" stroke-width="1.6"/>
  <path d="M-38,-15.2 L0,1.2 L38,-15.2" fill="none" stroke="#9bdfff" stroke-width=".8" opacity=".5"/>
  <text class="mu" x="-20" y="26" text-anchor="middle" font-size="34" font-style="italic" font-family="Georgia,'Times New Roman',serif" fill="url(#gold)">μ</text>
  <text x="20" y="26" text-anchor="middle" font-size="34" font-style="italic" font-family="Georgia,'Times New Roman',serif" fill="#6ee7ff" opacity=".22">μ</text>
 </g></g>
</svg>
<div class="word">phone<i>+</i>net<i>+</i><b>I.C.K.S.</b></div>
<div class="sub" id="title">Recon in progress</div>
<div class="big" id="pct">–</div>
<div class="bar"><div id="bar"></div></div>
<div class="stall" id="stall"></div>
<div class="kpis" id="kpis"><div class="kpi"><b id="kspd">–</b><span>speed now</span></div>
<div class="kpi"><b id="keta">–</b><span>left · done <em id="kclock">–</em></span></div></div>
<div class="term" id="term"><div class="tbar"><i></i><i></i><i></i><span>adb pull · phone → Mac</span></div>
<div class="tbody"><div class="tl" id="t1"></div><div class="tl" id="t2"></div><div class="tl dim" id="t3"></div><div class="tlog" id="tlog"></div></div></div>
<div class="done" id="done"><h2 class="secured">DATA POINTS<br>SECURED</h2>
<div class="unplug">SAFE TO<br>DISCONNECT</div>
<p>Everything on this phone is safe now: the words, the voices, the pictures.<br>Nothing left the house. Take a breath. You did this.</p>
<div class="stats" id="stats"></div>
<div class="next"><span id="next"></span></div>
<div class="fine" id="fine"></div></div>
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
// live transfer panel: braille spinner while bytes move, eighth-block bar, bytes eased forward between 3 s polls
const SP='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏',RM=matchMedia('(prefers-reduced-motion: reduce)').matches;let X=null,XT=0,fi=0;
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function hb(n){const u=['B','KB','MB','GB','TB'];let i=0;while(n>=1000&&i<4){n/=1000;i++}return (i?n.toFixed(n<10?2:1):Math.round(n))+' '+u[i]}
function mmss(s){s=Math.max(0,s|0);return s>=60?Math.floor(s/60)+' min '+(s%60)+' s':s+' s'}
function tbar(f,w){f=Math.max(0,Math.min(1,f));const e=f*w,full=Math.floor(e),k=Math.floor((e-full)*8),part=k>0?'▏▎▍▌▋▊▉'[k-1]:'';
 return '█'.repeat(full)+part+'<u>'+'░'.repeat(Math.max(0,w-full-(part?1:0)))+'</u>'}
function barW(){const t=document.getElementById('term'),fs=parseFloat(getComputedStyle(t).fontSize)||15;return Math.max(10,Math.floor((t.clientWidth-24)/(fs*0.6))-10)}
function put(id,h){const e=document.getElementById(id);if(e._h!==h){e._h=h;e.innerHTML=h}}
function frame(){const x=X;if(!x||!x.tot_b||document.body.classList.contains('finished'))return;
 const dt=(Date.now()-XT)/1000;let b=x.done_b;if(x.moving&&x.speed)b=Math.min(x.tot_b,x.done_b+x.speed*Math.min(dt,4));
 if(x.moving&&!RM)fi=(fi+1)%SP.length;
 const sp=x.stalled?'✗':(x.moving?SP[fi]:(x.active?'·':'✓')),w=barW(),f=b/x.tot_b;
 put('t1',`<span class="sp">${sp}</span><span class="tb">${tbar(f,w)}</span> ${(100*f).toFixed(1)}%`);
 const word=x.stalled?(x.waiting_phone?'<span class="bad">Waiting for phone</span>':'<span class="bad">Stalled</span>'):(x.active?(x.moving?'<span class="ok">Pulling…</span>':'<span class="warn">Working…</span>'):'<span class="ok">Copied</span>');
 put('t2',`${word} <span class="dim">${hb(b)} / ${hb(x.tot_b)} · file ${Math.min(x.k+(x.active?1:0),x.n)}/${x.n}</span>`);
 const c=x.cur;let cd=c?c.done:0;if(c&&x.moving&&x.speed)cd=Math.min(c.size,c.done+x.speed*Math.min(dt,4));
 put('t3',c?`↳ ${esc(c.name)} <span class="tb">${tbar(cd/c.size,Math.min(12,Math.floor(w/3)))}</span> ${(100*cd/c.size).toFixed(0)}% · ${hb(cd)}/${hb(c.size)}`:(x.active?'↳ next file…':''))}
setInterval(frame,90);
async function tick(){try{const r=await fetch('status.json',{cache:'no-store'});const j=await r.json();
 document.getElementById('title').textContent=j.complete?j.title.replace('saving','saved'):j.title;document.getElementById('pct').textContent=j.pct+'%';
 document.getElementById('bar').style.width=j.pct+'%';document.getElementById('upd').textContent='updated '+j.updated;
 document.body.classList.toggle('finished',!!j.complete);document.getElementById('next').innerHTML=j.next||'';
 if(j.complete){const ic={"Texts":"💬","Picture messages":"🖼️","Calls":"📞","Contacts":"👥","Calendar":"📅","Message attachments":"📎","Phone storage":"📁","Voicemails":"🎙️","Storage":"💾"};
  const lab={"Message attachments":"attachments","Picture messages":"picture msgs","Phone storage":"files","Storage":"storage"};
  const h=j.history,sm=j.summary;
  document.getElementById('fine').innerHTML=`This pull${j.last_done?' · finished '+j.last_done:''}: ${fmt(sm['New files']??0)} new files · ${fmt(sm['Texts']??0)} texts · ${fmt(sm['Calls']??0)} calls`+
   (h?`<br>All pulls of this phone since ${h.since}: ${fmt(h.pulls)} pulls · ${fmt(h.files)} files saved · ${fmt(h.texts)} texts · ${fmt(h.calls)} calls`:'');
  document.getElementById('stats').innerHTML=Object.entries(j.summary).filter(([k,v])=>v!=='').map(([k,v])=>`<div class="stat"><b>${typeof v==='number'?fmt(v):v}</b><span>${ic[k]||''} ${(lab[k]||k).toLowerCase()}</span></div>`).join('');}
 X=j.xfer;XT=Date.now();const on=!!(X&&X.tot_b&&!j.complete);
 document.body.classList.toggle('stalled',!!(on&&X.stalled));document.body.classList.toggle('moving',!!(on&&X.moving&&!X.stalled));
 for(const id of ['kpis','term'])document.getElementById(id).classList.toggle('on',on);
 if(on){document.getElementById('kspd').innerHTML=X.stalled?'0.0<small> MB/s</small>':(X.speed!=null?(X.speed/1e6).toFixed(1)+'<small> MB/s</small>':'–');
  document.getElementById('keta').textContent=X.stalled?'—':(X.left||'–');document.getElementById('kclock').textContent=X.eta_clock?'at '+X.eta_clock:'–';
  document.getElementById('stall').innerHTML='⚠ STALLED<small>no new bytes for '+mmss(X.idle_s)+' · '+(X.waiting_phone?'waiting for the phone to come back — check the cable':'the pull restarts this file by itself after 3 min')+'</small>';
  const cnt=[X.retries&&`<span class="warn">↻ ${X.retries} retr${X.retries>1?'ies':'y'}</span>`,X.stalls&&`<span class="bad">⚠ ${X.stalls} stall${X.stalls>1?'s':''} restarted</span>`,X.failed&&`<span class="bad">✗ ${X.failed} FAILED</span>`].filter(Boolean).join(' · ');
  document.getElementById('tlog').innerHTML=(cnt?cnt+'<br>':'')+X.events.map(e=>`<div class="tl ${/FAILED|STALLED|NOT COMPLETE/.test(e)?'bad':'warn'}">${esc(e)}</div>`).join('');
  frame();}
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

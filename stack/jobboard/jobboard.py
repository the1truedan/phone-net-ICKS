#!/usr/bin/env python3
"""phone-net I.C.K.S. job board: a local page that shows the GPU transcription queues and can pause, resume, start or stop them.

Stdlib only. Binds to 127.0.0.1. Every control call needs the per-run token that is printed at start and embedded in the page,
so another website cannot trigger it. Paths and hosts come from config/jobboard.toml (git-ignored); per-queue purpose notes and
any local report pages come from files that config points at, so nothing case-specific lives in this code.

    python3 stack/jobboard/jobboard.py [--config config/jobboard.toml] [--port 8797] [--dry-run]
"""
import argparse, glob, html, json, os, re, secrets, shlex, shutil, statistics, subprocess, sys, time, tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOKEN = secrets.token_urlsafe(18)
SAFE_LOG = re.compile(r"^(\d\d:\d\d:\d\d \w+: (ok|FAIL|SKIP_LONG \d+min)|\w{3} \w{3} +\d+ [\d:]+ \w+ \d{4} (STAGE \w+|\w+_DONE|EXTRACT_FAIL \w+))")
START_LINE = re.compile(r"^(\d\d:\d\d:\d\d) (\w+): ")


def load_toml(path):
    with open(path, "rb") as fh:
        return tomllib.load(fh)


class Redactor:
    """Blocks out (█) names and identifiers in everything the board serves, for screenshots and demos.
    Terms come from a local, git-ignored file (one per line; lines starting with 'cs:' are matched case-sensitively),
    plus built-in patterns for phone numbers, emails, street addresses, SSNs and long digit runs."""
    PATTERNS = [r"\b\d{3}[-.)\s]{1,2}\d{3}[-.\s]\d{4}\b", r"[\w.+-]+@[\w-]+\.[\w.]+", r"\b\d{3}-\d{2}-\d{4}\b",
                r"\b\d{3,6}\s+\d{0,3}\w*\s+(Ave|Avenue|St|Street|Rd|Road|Lot|Dr|Drive|Blvd)\b[\w .,#]*", r"\b\d{6,}\b",
                r"(?<![\w/])/(Volumes|Users|home|mnt|MCP_WIP)/[^\s<>\"']*"]   # absolute local paths

    def __init__(self, path):
        self.rx = []
        for ln in (open(path, errors="ignore").read().splitlines() if path and os.path.exists(path) else []):
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            cs = ln.startswith("cs:")
            term = ln[3:].strip() if cs else ln
            # letters/digits only as boundaries, so names inside file names (A_B_C.md) are caught too
            self.rx.append(re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", 0 if cs else re.I))
        self.rx += [re.compile(p, re.I) for p in self.PATTERNS]

    def __call__(self, text):
        # only touch text between tags so markup, styles and scripts keep working
        def fix(seg):
            for r in self.rx:
                seg = r.sub(lambda m: "█" * len(m.group(0)), seg)
            return seg
        return re.sub(r"(>)([^<]+)(<)|^([^<]+)$", lambda m: (m.group(1) + fix(m.group(2)) + m.group(3)) if m.group(1) else fix(m.group(4)), text, flags=re.M)

    def json(self, obj):
        if isinstance(obj, str):
            out = obj
            for r in self.rx:
                out = r.sub(lambda m: "█" * len(m.group(0)), out)
            return out
        if isinstance(obj, list):
            return [self.json(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self.json(v) for k, v in obj.items()}
        return obj


def sh(cmd, timeout=15):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (subprocess.TimeoutExpired, OSError):
        return ""


def ffprobe_s(path):
    out = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], timeout=20).strip()
    try:
        return float(out)
    except ValueError:
        return None


class Board:
    def __init__(self, cfg):
        self.c = cfg
        self.c.setdefault("dry_run", False)
        self.c.setdefault("remote_cache_s", 15)
        self._remote = (0, {})
        self._speed = (0, None)
        self._dur = {}
        self.registry = {}
        self.redact = Redactor(self.c.get("redact_file")) if self.c.get("redact") else None
        if self.c.get("registry_file") and os.path.exists(self.c["registry_file"]):
            self.registry = load_toml(self.c["registry_file"]).get("queue", {})

    # ---------- queues ----------
    def qname(self, path):
        return re.sub(self.c.get("queue_name_regex", r"^$"), "", os.path.splitext(os.path.basename(path))[0])

    def queue_files(self):
        return {self.qname(q): q for q in glob.glob(self.c["queue_glob"])}

    def label_map(self):
        m = {}
        for name, q in self.queue_files().items():
            for ln in open(q, errors="ignore"):
                p = ln.rstrip("\n").split("\t")
                if len(p) >= 2:
                    m[p[0]] = (name, p[-1])
        return m

    def results(self):
        res = {}
        for p in glob.glob(os.path.join(self.c["results_dir"], "*.json")):
            b = os.path.basename(p)
            m = re.fullmatch(self.c["result_pattern"].replace(".", r"\.").replace("{label}", r"(\w+)"), b)
            if m:
                res[m.group(1)] = os.path.getmtime(p)
        return res

    def queues(self, res):
        out = []
        for name, q in sorted(self.queue_files().items()):
            labels = [ln.split("\t", 1)[0] for ln in open(q, errors="ignore") if ln.strip()]
            st_ = os.stat(q)
            created = getattr(st_, "st_birthtime", st_.st_mtime)
            done_t = [res[lb] for lb in labels if lb in res]
            reg = self.registry.get(name, {})
            out.append({"queue": name, "total": len(labels), "done": len(done_t),
                        "created": time.strftime("%m-%d %H:%M", time.localtime(created)),
                        "last_done": time.strftime("%m-%d %H:%M", time.localtime(max(done_t))) if done_t else "",
                        "purpose": reg.get("purpose", ""), "gain": reg.get("gain", ""), "source": reg.get("source", ""),
                        "outputs": reg.get("outputs", ""),
                        "flag": reg.get(self.c.get("flag_field", "flag"), ""), "flag_party": reg.get(self.c.get("flag_party_field", "flag_party"), "")})
        return out

    # ---------- processes and hosts ----------
    def runners(self):
        rx = re.compile(self.c["runner_match"])
        qdir = os.path.dirname(self.c["queue_glob"])
        rows = []
        for ln in sh(["ps", "-axo", "pid=,etime=,command="]).splitlines():
            parts = ln.strip().split(None, 2)
            if len(parts) == 3 and rx.search(parts[2]) and "jobboard" not in parts[2]:
                pid, et, cmd = parts
                # macOS hides other processes' environment, so read the queue file the runner holds open
                held = [x[1:] for x in sh(["lsof", "-Fn", "-p", pid]).splitlines() if x.startswith("n" + qdir) and x.endswith(".tsv")]
                rows.append({"pid": int(pid), "elapsed": et, "script": os.path.basename(cmd.split()[-1]),
                             "queue": self.qname(held[0]) if held else ""})
        return rows

    def local_host(self):
        la = os.getloadavg()
        return {"load1": round(la[0], 2), "cpus": os.cpu_count()}

    def remote(self):
        t, cached = self._remote
        if time.time() - t < self.c["remote_cache_s"]:
            return cached
        flag = shlex.quote(self.c["pause_flag"])
        inprog = self.c.get("remote_inprogress_glob", "")
        cmd = ("nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader,nounits; "
               f"test -e {flag} && echo PAUSED || echo RUNNING; "
               f"pgrep -fc {shlex.quote(self.c.get('remote_worker_match', 'fine_comb_visit.py'))} || true; "
               "nproc; cat /proc/loadavg; free -m | awk '/^Mem:/{print $2, $7}'; "
               "top -bn1 | awk -F',' '/Cpu\\(s\\)/{for(i=1;i<=NF;i++) if($i ~ /id/){gsub(/[^0-9.]/,\"\",$i); print 100-$i}}'; "
               f"echo ---; for f in {inprog}; do [ -e \"$f\" ] && stat -c '%Y %n' \"$f\" && ffprobe -v error -show_entries format=duration -of csv=p=0 \"$f\"; done 2>/dev/null; "
               f"echo +++; ps -eo args | grep {shlex.quote('[p]ython.*' + self.c.get('remote_worker_match', 'fine_comb_visit.py'))} | grep -oE -- '--label [A-Za-z0-9_]+' | cut -d' ' -f2 | sort -u")
        out = sh(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=6", self.c["remote_host"], cmd], timeout=25).splitlines()
        r = {"reachable": bool(out)}
        try:
            used, total, util, temp = [x.strip() for x in out[0].split(",")]
            r.update(gpu_used_mib=int(used), gpu_total_mib=int(total), gpu_util=int(util), gpu_temp=int(temp))
            r["paused"] = out[1].strip() == "PAUSED"
            r["workers"] = int(out[2]) if out[2].strip().isdigit() else 0
            r["cpus"] = int(out[3]); r["load1"] = float(out[4].split()[0])
            mt, ma = out[5].split(); r["mem_total_mib"], r["mem_avail_mib"] = int(mt), int(ma)
            r["cpu_pct"] = round(float(out[6]), 1) if out[6].strip() else None
            sep = out.index("---")
            sep2 = out.index("+++") if "+++" in out else len(out)
            r["running_labels"] = [x.strip() for x in out[sep2 + 1:] if x.strip()]
            r["workers"] = len(r["running_labels"])   # distinct items being processed, not raw process count
            cur, rest = [], out[sep + 1:sep2]
            for i in range(0, len(rest) - 1, 2):
                ts, path = rest[i].split(" ", 1)
                lab = re.sub(r"\.orig48k\.wav$|\.lev\.wav$", "", os.path.basename(path))
                if not any(c["label"] == lab for c in cur):
                    cur.append({"label": lab, "started": int(ts), "audio_s": float(rest[i + 1]) if rest[i + 1].strip() else None})
            r["current"] = cur
        except (IndexError, ValueError):
            pass
        self._remote = (time.time(), r)
        return r

    def speed(self, res, lm):
        """Median processing seconds per audio second over recent finished items (start = log line time, end = result file)."""
        t, v = self._speed
        if time.time() - t < 300:
            return v
        starts = {}
        for p in self.c.get("log_files", []):
            try:
                for ln in open(p, errors="ignore"):
                    m = START_LINE.match(ln)
                    if m:
                        starts[m.group(2)] = m.group(1)
            except OSError:
                pass
        ratios = []
        for lab, fin in sorted(res.items(), key=lambda x: -x[1])[:40]:
            if lab not in starts or lab not in lm:
                continue
            end = time.localtime(fin)
            h, mi, s = map(int, starts[lab].split(":"))
            st_ = time.mktime((end.tm_year, end.tm_mon, end.tm_mday, h, mi, s, 0, 0, -1))
            if st_ > fin:
                st_ -= 86400
            src = lm[lab][1]
            if src not in self._dur:
                self._dur[src] = ffprobe_s(src) if os.path.exists(src) else None
            d = self._dur[src]
            if d and 60 < d and 0 < fin - st_ < 6 * 3600:
                ratios.append((fin - st_) / d)
        v = statistics.median(ratios) if len(ratios) >= 3 else None
        self._speed = (time.time(), v)
        return v

    def logs(self, n=10):
        res = {}
        for p in self.c.get("log_files", []):
            try:
                lines = open(p, errors="ignore").read().splitlines()
            except OSError:
                continue
            res[os.path.basename(p)] = [ln for ln in lines if SAFE_LOG.match(ln)][-n:]
        return res

    def status(self):
        res = self.results()
        lm = self.label_map()
        runners = self.runners()
        chain_up = any(re.search(self.c.get("chain_match", r"^$"), r["script"]) for r in runners)
        chained = set(self.c.get("chained_queues", [])) if chain_up else set()
        qs = self.queues(res)
        for q in qs:
            q["in_chain"] = q["queue"] in chained
        rem = self.remote()
        sp = self.speed(res, lm)
        now = time.time()
        cur, clear = [], []
        running = set(rem.get("running_labels", []))
        for c in rem.get("current", []):
            c["stale"] = now - c["started"] > self.c.get("stale_after_s", 8 * 3600)
            if c["label"] not in running and (c["label"] in res or c["stale"]):
                clear.append(c["label"])   # finished or abandoned; nothing is using these staging copies
                if c["label"] in res:
                    continue
            cur.append(c)
        self.cleared_note = getattr(self, "cleared_note", "")
        if clear and self.c.get("auto_clear_stale") and rem.get("running_labels") is not None:
            self.cleared_note = self.clear_staging(clear)
            cur = [c for c in cur if c["label"] not in clear]
        rem = dict(rem, current=cur)
        for c in cur:
            c["queue"] = lm.get(c["label"], ("?",))[0]
            c["elapsed_s"] = int(now - c["started"])
            if sp and c.get("audio_s"):
                est = c["audio_s"] * sp
                c["est_total_s"] = int(est)
                c["pct"] = min(99, int(100 * c["elapsed_s"] / est)) if est else None
        recent = [{"label": lb, "queue": lm.get(lb, ("?",))[0], "finished": time.strftime("%m-%d %H:%M", time.localtime(t))}
                  for lb, t in sorted(res.items(), key=lambda x: -x[1])[: self.c.get("recent_n", 15)]]
        return {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "dry_run": self.c["dry_run"], "remote": rem, "cleared": self.cleared_note,
                "local": self.local_host(), "speed": round(sp, 3) if sp else None, "queues": qs, "runners": runners,
                "recent": recent, "logs": self.logs(),
                "reports": [r.get("name", "") for r in self.c.get("reports", [])], "flag_label": self.c.get("flag_label", "flagged")}

    # ---------- controls ----------
    def _run(self, argv, detach=False):
        if self.c["dry_run"]:
            return {"dry_run": True, "would_run": " ".join(shlex.quote(a) for a in argv)}
        if detach:
            subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return {"started": True}
        return {"output": sh(argv)}

    def pause(self):
        self._remote = (0, {})
        return self._run(["ssh", "-o", "BatchMode=yes", self.c["remote_host"], f"touch {shlex.quote(self.c['pause_flag'])}"])

    def resume(self):
        self._remote = (0, {})
        return self._run(["ssh", "-o", "BatchMode=yes", self.c["remote_host"], f"rm -f {shlex.quote(self.c['pause_flag'])}"])

    def start(self, queue):
        qs = self.queue_files()
        if queue not in qs:
            return {"error": "unknown queue"}
        if any(r["queue"] == queue for r in self.runners()):
            return {"error": "a runner for this queue is already active"}
        if next(q for q in self.status()["queues"] if q["queue"] == queue)["in_chain"]:
            return {"error": "this queue is waiting in a running chain script; starting it now would run it twice"}
        log = os.path.join(self.c["log_dir"], f"jobboard_{queue}_{time.strftime('%Y%m%d_%H%M%S')}.log")
        cmd = f"Q={shlex.quote(qs[queue])} {shlex.quote(self.c['runner_script'])} >> {shlex.quote(log)} 2>&1"
        return self._run(["/bin/bash", "-c", cmd], detach=True)

    def clear_staging(self, labels):
        """Remove the GPU-host staging copies (<label>.orig48k.wav / .lev.wav) of finished or abandoned items. Originals are never touched."""
        labels = [lb for lb in labels if re.fullmatch(r"[A-Za-z0-9_]+", lb)]
        stage = os.path.dirname(self.c.get("remote_inprogress_glob", ""))
        if not labels or not stage:
            return ""
        files = " ".join(shlex.quote(f"{stage}/{lb}{ext}") for lb in labels for ext in (".orig48k.wav", ".lev.wav"))
        out = self._run(["ssh", "-o", "BatchMode=yes", self.c["remote_host"], f"rm -f {files}"])
        self._remote = (0, {})
        verb = "would clear" if self.c["dry_run"] else "cleared"
        return f"{time.strftime('%H:%M')} {verb} staging for: {', '.join(labels)}"

    def stop(self, pid):
        if pid not in {r["pid"] for r in self.runners()}:
            return {"error": "not a job-board runner pid"}
        return self._run(["kill", str(pid)])

    def report(self, i):
        reps = self.c.get("reports", [])
        if not 0 <= i < len(reps) or not os.path.exists(reps[i]["path"]):
            return None, None
        p = reps[i]["path"]
        body = open(p, errors="ignore").read()
        if p.endswith((".html", ".htm")):
            return body, "text/html; charset=utf-8"
        name = html.escape(reps[i]["name"])
        if p.endswith(".md") and shutil.which("pandoc"):
            # pandoc's default is to drop raw HTML from the Markdown; links become local hrefs
            inner = sh(["pandoc", "-f", "gfm", "-t", "html5", "--no-highlight", p], timeout=30)
        else:
            inner = f"<pre style='white-space:pre-wrap'>{html.escape(body)}</pre>"
        return (f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                f"<title>{name}</title><style>{REPORT_CSS}</style></head><body><div class=muted>{name} · {html.escape(os.path.basename(p))} · "
                f"modified {time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(p)))}</div>{inner}</body></html>"), "text/html; charset=utf-8"


REPORT_CSS = """:root{--bg:#fcfcfb;--fg:#1f1f1d;--muted:#6b6b66;--line:#e4e4df;--card:#fff;--acc:#2a78d6;--code:#f1f1ed}
@media (prefers-color-scheme:dark){:root{--bg:#1a1a19;--fg:#ececea;--muted:#a3a39d;--line:#33332f;--card:#22221f;--acc:#3987e5;--code:#2b2b28}}
body{background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,sans-serif;max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:23px;margin:.6em 0 .3em}h2{font-size:18px;margin-top:1.6em;border-bottom:1px solid var(--line);padding-bottom:4px}h3{font-size:15.5px;margin-top:1.3em}
table{width:100%;border-collapse:collapse;margin:8px 0 14px;display:block;overflow-x:auto}td,th{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top;font-variant-numeric:tabular-nums}
th{background:var(--card);font-weight:600}code{background:var(--code);padding:1px 5px;border-radius:4px;font-size:.92em}
pre{background:var(--code);padding:10px;border-radius:6px;overflow-x:auto}blockquote{border-left:3px solid var(--acc);margin:8px 0;padding:2px 12px;color:var(--muted)}
a{color:var(--acc)}img{max-width:100%}.muted{color:var(--muted);font-size:12.5px}li{margin:2px 0}"""


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Job Board</title><style>
:root{--bg:#fcfcfb;--fg:#1f1f1d;--muted:#6b6b66;--line:#e4e4df;--bar:#2a78d6;--warn:#c98500;--bad:#e34948;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#1a1a19;--fg:#ececea;--muted:#a3a39d;--line:#33332f;--bar:#3987e5;--card:#22221f}}
body{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif;margin:0;padding:16px;max-width:1200px}
h1{font-size:20px;margin:0 0 4px}.muted{color:var(--muted)}section{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:12px 0}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:5px 6px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums;vertical-align:top}
.bar{height:8px;background:var(--line);border-radius:4px;overflow:hidden;min-width:110px}.bar>i{display:block;height:100%;background:var(--bar)}
button{font:inherit;padding:4px 10px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--fg);cursor:pointer}
button:hover{border-color:var(--bar)}.pill{display:inline-block;padding:1px 8px;border-radius:10px;border:1px solid var(--line);white-space:nowrap}
.paused{color:var(--warn)}.bad{color:var(--bad)}pre{white-space:pre-wrap;margin:4px 0 10px;font-size:12px}.stats{display:flex;gap:18px;flex-wrap:wrap}
.stats div{min-width:150px}tr.flag td:first-child{box-shadow:inset 3px 0 0 var(--warn)}.flagpill{border-color:var(--warn);color:var(--warn)}.big{font-size:18px}details summary{cursor:pointer}.small{font-size:12px}a{color:var(--bar)}
</style></head><body>
<h1>Job Board <span class="muted" id="t"></span></h1><div class="muted" id="rep"></div>
<section id="gpu"></section><section><b>On the GPU now</b><table id="cur"></table></section>
<section><b>Queues</b> <span class="muted small">(click a row for purpose and expected gain)</span><table id="q"></table></section>
<section><b>Recently finished</b><table id="fin"></table></section>
<section><b>Runners</b><table id="r"></table></section><section><b>Recent log lines</b><div id="l"></div></section>
<script>
const TOKEN="__TOKEN__";
async function post(p,b){const r=await fetch(p,{method:"POST",headers:{"X-Token":TOKEN,"Content-Type":"application/json"},body:JSON.stringify(b||{})});alert(JSON.stringify(await r.json()));load();}
function esc(s){return String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}
function mins(s){if(s==null)return"?";const m=Math.round(s/60);return m>=60?`${Math.floor(m/60)}h ${m%60}m`:`${m}m`}
function bar(p){return `<div class="bar"><i style="width:${p||0}%"></i></div>`}
async function load(){const s=await (await fetch("/api/status")).json();
document.getElementById("t").textContent=s.time+(s.dry_run?"  (DRY RUN: buttons only show what they would do)":"");
document.getElementById("rep").innerHTML=s.reports.length?"Reports: "+s.reports.map((n,i)=>`<a href="/report/${i}" target="_blank">${esc(n)}</a>`).join(" · "):"";
const g=s.remote,L=s.local;
document.getElementById("gpu").innerHTML=g.reachable?`<div class="stats">
<div><div class="muted small">GPU memory</div><div class="big">${g.gpu_used_mib} / ${g.gpu_total_mib} MiB</div>${bar(100*g.gpu_used_mib/g.gpu_total_mib)}</div>
<div><div class="muted small">GPU busy · temp</div><div class="big">${g.gpu_util}% · ${g.gpu_temp}°C</div>${bar(g.gpu_util)}</div>
<div><div class="muted small">GPU host CPU</div><div class="big">${g.cpu_pct??"?"}% · load ${g.load1} / ${g.cpus}</div>${bar(g.cpu_pct)}</div>
<div><div class="muted small">GPU host memory</div><div class="big">${((g.mem_total_mib-g.mem_avail_mib)/1024).toFixed(1)} / ${(g.mem_total_mib/1024).toFixed(0)} GiB</div>${bar(100*(g.mem_total_mib-g.mem_avail_mib)/g.mem_total_mib)}</div>
<div><div class="muted small">This computer</div><div class="big">load ${L.load1} / ${L.cpus}</div></div>
<div><div class="muted small">State</div><div class="big"><span class="pill ${g.paused?"paused":""}">${g.paused?"PAUSED":"running"}</span> ${g.workers} item${g.workers==1?"":"s"} processing</div>
<button onclick="post('/api/pause')">Pause</button> <button onclick="post('/api/resume')">Resume</button></div></div>
${s.cleared?`<div class="small">${esc(s.cleared)}</div>`:""}<div class="muted small">Speed: ${s.speed?`${(1/s.speed).toFixed(1)}× real time (median of recent items)`:"not enough history yet"}</div>`:`<b class="bad">GPU host not reachable over ssh</b>`;
const cur=(g.current||[]);document.getElementById("cur").innerHTML=cur.length?"<tr><th>Item</th><th>Queue</th><th>Audio</th><th>Running</th><th>Est. progress</th></tr>"+cur.map(c=>`<tr><td>${esc(c.label)}</td><td>${esc(c.queue)}</td><td>${mins(c.audio_s)}</td><td>${mins(c.elapsed_s)}</td><td>${c.stale?'<span class="pill paused">stale leftover (not running)</span>':c.pct!=null?bar(c.pct)+`<span class="small muted">${c.pct}% of ~${mins(c.est_total_s)}</span>`:'<span class="muted small">estimating…</span>'}</td></tr>`).join(""):"<tr><td class=muted>nothing staged on the GPU right now</td></tr>";
document.getElementById("q").innerHTML="<tr><th>Queue</th><th>Done</th><th></th><th>Created</th><th>Last finished</th><th></th></tr>"+s.queues.map(q=>{const p=q.total?Math.round(100*q.done/q.total):0;const run=s.runners.some(r=>r.queue==q.queue);
const act=run?'<span class="pill">running</span>':q.in_chain?'<span class="pill muted">waiting in chain</span>':(q.done<q.total?`<button onclick="event.stopPropagation();if(confirm('Start ${esc(q.queue)}?'))post('/api/start',{queue:'${esc(q.queue)}'})">Start</button>`:'');
return `<tr class="${q.flag?"flag":""}" onclick="const d=this.nextElementSibling;d.hidden=!d.hidden" style="cursor:pointer"><td><b>${esc(q.queue)}</b> ${q.flag?`<span class="pill flagpill small">⚖ ${esc(s.flag_label)}${q.flag_party?" · "+esc(q.flag_party):""}</span>`:""}</td><td>${q.done} / ${q.total}</td><td>${bar(p)}</td><td class="muted">${q.created}</td><td class="muted">${q.last_done}</td><td>${act}</td></tr>
<tr hidden><td></td><td colspan="5" class="small">${q.purpose?`<b>Purpose:</b> ${esc(q.purpose)}<br>`:""}${q.source?`<b>Source:</b> ${esc(q.source)}<br>`:""}${q.gain?`<b>Expected gain:</b> ${esc(q.gain)}<br>`:""}${q.outputs?`<b>Outputs:</b> ${esc(q.outputs)}<br>`:""}${q.flag?`<b class="paused">⚖ ${esc(s.flag_label)}${q.flag_party?" ("+esc(q.flag_party)+")":""}:</b> ${esc(q.flag)}`:""}${!(q.purpose||q.gain)?'<span class="muted">no notes for this queue</span>':""}</td></tr>`}).join("");
document.getElementById("fin").innerHTML="<tr><th>Item</th><th>Queue</th><th>Finished</th></tr>"+s.recent.map(f=>`<tr><td>${esc(f.label)}</td><td>${esc(f.queue)}</td><td>${f.finished}</td></tr>`).join("");
document.getElementById("r").innerHTML="<tr><th>PID</th><th>Script</th><th>Queue</th><th>Running for</th><th></th></tr>"+(s.runners.map(r=>`<tr><td>${r.pid}</td><td>${esc(r.script)}</td><td>${esc(r.queue||"(chain)")}</td><td>${esc(r.elapsed)}</td><td><button onclick="if(confirm('Stop runner ${r.pid}? The item already on the GPU finishes; no new items start.'))post('/api/stop',{pid:${r.pid}})">Stop</button></td></tr>`).join("")||"<tr><td class=muted>none</td></tr>");
document.getElementById("l").innerHTML=Object.entries(s.logs).map(([f,L])=>`<div class="muted">${esc(f)}</div><pre>${esc(L.join("\\n"))||"(nothing yet)"}</pre>`).join("");}
load();setInterval(load,15000);
</script></body></html>"""


def make_handler(board):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            if board.redact:
                body = board.redact(body) if isinstance(body, str) else board.redact.json(body)
            b = body.encode() if isinstance(body, str) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.headers.get("Host", "").split(":")[0] not in ("127.0.0.1", "localhost"):
                return self._send(403, {"error": "forbidden"})
            if self.path == "/":
                return self._send(200, PAGE.replace("__TOKEN__", TOKEN), "text/html; charset=utf-8")
            if self.path == "/api/status":
                return self._send(200, board.status())
            m = re.fullmatch(r"/report/(\d+)", self.path)
            if m:
                body, ctype = board.report(int(m.group(1)))
                return self._send(200, body, ctype) if body else self._send(404, {"error": "no such report"})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.headers.get("X-Token") != TOKEN or self.headers.get("Host", "").split(":")[0] not in ("127.0.0.1", "localhost"):
                return self._send(403, {"error": "forbidden"})
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                body = {}
            routes = {"/api/pause": lambda: board.pause(), "/api/resume": lambda: board.resume(),
                      "/api/start": lambda: board.start(str(body.get("queue", ""))),
                      "/api/stop": lambda: board.stop(int(body.get("pid", 0)))}
            if self.path not in routes:
                return self._send(404, {"error": "not found"})
            self._send(200, routes[self.path]())
    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "jobboard.toml"))
    ap.add_argument("--port", type=int, default=8797)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--redact", action="store_true", help="block out names/identifiers listed in redact_file (for screenshots)")
    a = ap.parse_args()
    cfg = load_toml(a.config)
    if a.dry_run:
        cfg["dry_run"] = True
    if a.redact:
        cfg["redact"] = True
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(Board(cfg)))
    print(f"job board: http://127.0.0.1:{a.port}/  (token {TOKEN}){'  DRY RUN' if cfg.get('dry_run') else ''}{'  REDACTED' if cfg.get('redact') else ''}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""phone-net I.C.K.S. job board: a local page that shows the GPU transcription queues and can pause, resume, start or stop them.

Stdlib only. Binds to 127.0.0.1. Every control call needs the per-run token that is printed at start and embedded in the page,
so another website cannot trigger it. Paths and hosts come from config/jobboard.toml (git-ignored); per-queue purpose notes and
any local report pages come from files that config points at, so nothing case-specific lives in this code.

    python3 stack/jobboard/jobboard.py [--config config/jobboard.toml] [--port 8797] [--dry-run]
"""
import argparse
import threading, glob, html, json, os, re, secrets, shlex, shutil, statistics, subprocess, sys, time, tomllib
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
        # 2026-10-02: leave <script> blocks alone (a blocked word such as a host name must not break the page's code); the data the
        # script renders arrives through /api/status, which is redacted separately, and host badges are blocked in the page itself
        parts = re.split(r"(<script\b.*?</script>)", text, flags=re.S | re.I)
        return "".join(x if x.lower().startswith("<script") else
                       re.sub(r"(>)([^<]+)(<)|^([^<]+)$", lambda m: (m.group(1) + fix(m.group(2)) + m.group(3)) if m.group(1) else fix(m.group(4)), x, flags=re.M)
                       for x in parts)

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
        self.priority = None
        if os.path.exists(os.path.join(self.c["log_dir"], ".jobboard_priority.json")):
            self.release_priority("left over from a previous board run")
        if self.c.get("registry_file") and os.path.exists(self.c["registry_file"]):
            self.registry = load_toml(self.c["registry_file"]).get("queue", {})

    # ---------- queues ----------
    def qname(self, path):
        return re.sub(self.c.get("queue_name_regex", r"^$"), "", os.path.splitext(os.path.basename(path))[0])

    def queue_files(self):
        return {self.qname(q): q for q in glob.glob(self.c["queue_glob"])}

    def long_skipped(self):
        """Labels the runner's length guard sent to the excerpt route (first column of long_skip_file)."""
        p = self.c.get("long_skip_file", "")
        try:
            return {ln.split("\t", 1)[0] for ln in open(p, errors="ignore") if ln.strip()}
        except OSError:
            return set()

    def rev_dir(self):
        return self.c.get("reverse_dir") or os.path.join(os.path.dirname(self.c["queue_glob"]), "from_end")

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
        pats = [self.c["result_pattern"]] + self.c.get("extra_result_patterns", [])   # e.g. CHUNKS_{label}.json for chunked recordings
        for p in glob.glob(os.path.join(self.c["results_dir"], "*.json")):
            b = os.path.basename(p)
            for pat in pats:
                m = re.fullmatch(pat.replace(".", r"\.").replace("{label}", r"(\w+)"), b)
                if m:
                    res[m.group(1)] = max(res.get(m.group(1), 0), os.path.getmtime(p))
                    break
        return res

    def chunk_coverage(self, res):
        """2026-10-02: a long recording routed to chunk queues is covered when every 15-min piece is processed or confirmed silent.
        Pieces come from CSV tier lists (chunk_tier_glob: label,hash,...) and silent pieces from silent_lists (first column = piece)."""
        cov = {}
        if not self.c.get("chunk_tier_glob"):
            return cov
        silent = set()
        for f in self.c.get("silent_lists", []):
            try:
                silent |= {ln.split("\t", 1)[0] for ln in open(f, errors="ignore")}
            except OSError:
                pass
        for f in glob.glob(self.c["chunk_tier_glob"]):
            for ln in open(f, errors="ignore"):
                parts = ln.split(",")
                if len(parts) < 2 or parts[0] == "label":
                    continue
                t, d = cov.get(parts[1], (0, 0))
                cov[parts[1]] = (t + 1, d + (parts[0] in res or parts[0] in silent))
        return cov

    def queues(self, res):
        out = []
        cov = self.chunk_coverage(res)
        def covered(lb):   # all pieces of a routed long recording processed or silent
            h = lb.split("_", 1)[-1]; t, d = cov.get(h, (0, 0))
            return t > 0 and d >= t
        for name, q in sorted(self.queue_files().items()):
            labels = [ln.split("\t", 1)[0] for ln in open(q, errors="ignore") if ln.strip()]
            st_ = os.stat(q)
            created = getattr(st_, "st_birthtime", st_.st_mtime)
            done_t = [res[lb] for lb in labels if lb in res]
            via_chunks = [lb for lb in labels if lb not in res and covered(lb)]
            pending_pieces = sum(cov.get(lb.split("_", 1)[-1], (0, 0))[0] - cov.get(lb.split("_", 1)[-1], (0, 0))[1]
                                 for lb in labels if lb not in res and not covered(lb))
            reg = self.registry.get(name, {})
            longs = self.long_skipped()
            out.append({"queue": name, "total": len(labels), "done": len(done_t) + len(via_chunks),
                        "too_long": sum(1 for lb in labels if lb not in res and lb in longs and not covered(lb)),
                        "via_chunks": len(via_chunks), "pending_pieces": pending_pieces,
                        "created": time.strftime("%m-%d %H:%M", time.localtime(created)),
                        "last_done": time.strftime("%m-%d %H:%M", time.localtime(max(done_t))) if done_t else "",
                        "last_done_ts": max(done_t) if done_t else 0,
                        "first_done": time.strftime("%m-%d %H:%M", time.localtime(min(done_t))) if done_t else "",
                        "span_s": int(max(done_t) - min(done_t)) if len(done_t) > 1 else 0,
                        "purpose": reg.get("purpose", ""), "gain": reg.get("gain", ""), "source": reg.get("source", ""),
                        "outputs": reg.get("outputs", ""),
                        "flag": reg.get(self.c.get("flag_field", "flag"), ""), "flag_party": reg.get(self.c.get("flag_party_field", "flag_party"), "")})
        return out

    # ---------- processes and hosts ----------
    def runners(self):
        rx = re.compile(self.c["runner_match"])
        qdir = os.path.dirname(self.c["queue_glob"])
        rows = []
        procs = []
        for ln in sh(["ps", "-axo", "pid=,ppid=,stat=,etime=,command="]).splitlines():
            parts = ln.strip().split(None, 4)
            if len(parts) == 5 and rx.search(parts[4]) and "jobboard" not in parts[4]:
                procs.append(parts)
        mine = {p[0] for p in procs}
        for pid, ppid, stat, et, cmd in procs:
            if ppid in mine:   # 2026-10-02: a bash subshell of a runner (its per-item pipeline), not a second runner
                continue
            if True:
                # macOS hides other processes' environment, so read the queue file the runner holds open
                held = [x[1:] for x in sh(["lsof", "-Fn", "-p", pid]).splitlines() if x.startswith("n" + qdir) and x.endswith(".tsv")]
                rows.append({"pid": int(pid), "elapsed": et, "script": os.path.basename(cmd.split()[-1]),
                             "queue": self.qname(held[0]) if held else "", "paused": stat.startswith("T"),
                             "from_end": bool(held) and os.path.dirname(held[0]) == self.rev_dir()})
        return rows

    def _rate(self, key, rx, tx):
        """Bytes/s since the previous sample of the same counter (None on the first sample)."""
        now = time.time(); prev = getattr(self, "_net", {}).get(key)
        self._net = dict(getattr(self, "_net", {}), **{key: (now, rx, tx)})
        if not prev or now - prev[0] < 1:
            return None, None
        dt = now - prev[0]
        return max(0, (rx - prev[1]) / dt), max(0, (tx - prev[2]) / dt)

    def local_host(self):
        """This computer: load, CPU %, and network rate on the busiest interface. It cuts pieces and runs the quick triage pass."""
        la = os.getloadavg(); n = os.cpu_count()
        cpu = sum(float(x) for x in sh(["ps", "-A", "-o", "%cpu="]).split() if x.replace(".", "", 1).isdigit()) / n
        best = (0, 0)
        for ln in sh(["netstat", "-ib"]).splitlines()[1:]:
            f = ln.split()
            if len(f) >= 10 and f[0].startswith("en") and "<Link#" in f[2]:
                try:
                    best = max(best, (int(f[6]), int(f[9])))
                except ValueError:
                    pass
        rxr, txr = self._rate("m4rv", *best)
        # Apple GPU (no sudo): the graphics driver's own statistics. Quick triage (whisper.cpp, Metal) runs here, so the GPU is the busy part.
        io = sh(["ioreg", "-r", "-d", "1", "-w", "0", "-c", "IOAccelerator"])
        gm = re.search(r'"Device Utilization %"=(\d+)', io); um = re.search(r'"In use system memory"=(\d+)', io)
        tri = [p for p in glob.glob(os.path.join(self.c["results_dir"], "TRIAGE_*.json")) if time.time() - os.path.getmtime(p) < 600]
        return {"load1": round(la[0], 2), "cpus": n, "cpu_pct": round(min(100, cpu), 1), "rx_mbs": rxr and round(rxr / 1e6, 1),
                "tx_mbs": txr and round(txr / 1e6, 1), "triage_10min": len(tri),
                "gpu_pct": int(gm.group(1)) if gm else None, "gpu_mem_gb": round(int(um.group(1)) / 2**30, 1) if um else None}

    def hosts(self):
        """Host badges: [icon, "name · role"]. Names come from host_labels in the config (defaults are generic)."""
        h = {"mac": ["🍎", "Mac · this computer"], "linux": ["🐧", "GPU host · Linux"], "unraid": ["🗄", "Server · Unraid"], "win": ["🪟", "PC · Windows"]}
        for k, v in self.c.get("host_labels", {}).items():
            if k in h: h[k][1] = v
        return h

    @staticmethod
    def _etime(et):
        d, _, rest = et.rpartition("-"); parts = [int(x) for x in rest.split(":")]
        while len(parts) < 3: parts.insert(0, 0)
        return (int(d) if d else 0) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]

    def local_jobs(self, lm, by_hash):
        """Work running on this computer, read from the process list: cutting pieces, quick triage, silence checks, uploads, batch scripts.
        Progress is real where a file or log can be measured (piece bytes, batch lines) and an estimate otherwise."""
        jobs, PIECE = [], 900 * 48000 * 2   # a 15-min 48 kHz mono 16-bit piece
        for ln in sh(["ps", "-axo", "pid=,etime=,command="]).splitlines():
            f = ln.strip().split(None, 2)
            if len(f) < 3:
                continue
            pid, el, cmd = int(f[0]), self._etime(f[1]), f[2]
            m = re.search(r"quick_triage\.py (\S+)", cmd)
            if m and "python" in cmd:
                jobs.append({"label": m.group(1), "stage": "quick triage (whisper.cpp small.en)", "elapsed_s": el, "pct": min(95, int(100 * el / 12)), "est": True}); continue
            if cmd.startswith(("ffmpeg", "/opt/homebrew/bin/ffmpeg", "nice")) and "ffmpeg" in cmd:
                out = re.search(r"(\S+/(?:auto_chunks|long_chunks_[\w-]+)/([\w]+)\.wav)\s*$", cmd)
                if out and " -ss " in cmd:
                    size = os.path.getsize(out.group(1)) if os.path.exists(out.group(1)) else 0
                    jobs.append({"label": out.group(2), "stage": "cutting 15-min piece", "elapsed_s": el, "pct": min(99, int(100 * size / PIECE)), "est": False}); continue
                if "silencedetect" in cmd:
                    w = re.search(r"-i (\S+/([\w]+)\.wav)", cmd)
                    jobs.append({"label": w.group(2) if w else "?", "stage": "silence check", "elapsed_s": el, "pct": min(95, int(100 * el / 4)), "est": True}); continue
            m = re.search(r"scp .*?/([\w]+)(?:\.orig48k)?\.wav \S*:", cmd)
            if m and cmd.startswith("scp"):
                jobs.append({"label": m.group(1), "stage": "upload to GPU host", "elapsed_s": el, "pct": None, "est": True}); continue
        for name, log, total in self.c.get("batch_jobs", []):   # [name, log file, expected lines]
            if os.path.exists(log) and time.time() - os.path.getmtime(log) < 3600:
                lines = [x for x in open(log, errors="ignore").read().splitlines() if x.strip()]
                done = any("DONE" in x for x in lines[-2:])
                if not done:
                    jobs.append({"label": name, "stage": f"batch: {len(lines)} of {total} pieces", "elapsed_s": int(time.time() - getattr(os.stat(log), "st_birthtime", os.path.getctime(log))),
                                 "pct": int(100 * len(lines) / total), "est": False})
        for j in jobs:
            j["host"] = "mac"; j["queue"] = self.queue_of(j["label"], lm, by_hash) if j["label"] not in (b[0] for b in self.c.get("batch_jobs", [])) else "batch"
        return jobs

    def storage(self):
        """Storage server link: the one 1 GbE link the GPU host and this computer share for file access. Cached like the GPU host."""
        t, v = getattr(self, "_storage", (0, {}))
        if time.time() - t < self.c["remote_cache_s"] or not self.c.get("storage_host"):
            return v
        out = sh(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", self.c["storage_host"],
                  "cat /proc/loadavg; nproc; awk 'NR>2{gsub(\":\",\" \"); print $1, $2, $10}' /proc/net/dev"], timeout=15).splitlines()
        v = {"reachable": bool(out)}
        try:
            v["load1"] = float(out[0].split()[0]); v["cpus"] = int(out[1])
            nics = [(int(b), int(c), a) for a, b, c in (x.split() for x in out[2:]) if re.match(r"(eth|bond|br)\d", a)]
            rx, tx, name = max(nics)
            v["nic"] = name; v["rx_mbs"], v["tx_mbs"] = [x and round(x / 1e6, 1) for x in self._rate("storage", rx, tx)]
        except (IndexError, ValueError):
            pass
        self._storage = (time.time(), v)
        return v

    def saturation(self, rem, loc, tw):
        """Plain-language warnings when a host is near a limit (1 GbE ~ 117 MB/s)."""
        w = []
        if rem.get("gpu_total_mib") and rem.get("gpu_used_mib", 0) > 0.9 * rem["gpu_total_mib"]:
            w.append(f"GPU memory {rem['gpu_used_mib']}/{rem['gpu_total_mib']} MiB (out-of-memory risk)")
        if rem.get("mem_total_mib") and rem.get("mem_avail_mib", 1e9) < 0.1 * rem["mem_total_mib"]:
            w.append("GPU host RAM under 10% free")
        if (rem.get("cpu_pct") or 0) > 90: w.append(f"GPU host CPU {rem['cpu_pct']}%")
        if (loc.get("cpu_pct") or 0) > 90: w.append(f"this Mac CPU {loc['cpu_pct']}%")
        for name, h in (("GPU host", rem), ("this Mac", loc), ("storage server link", tw)):
            for k in ("rx_mbs", "tx_mbs"):
                if (h.get(k) or 0) > 95: w.append(f"{name} network {h[k]} MB/s ({'in' if k == 'rx_mbs' else 'out'}) — near the 1 GbE limit")
        if tw.get("load1") and tw.get("cpus") and tw["load1"] > tw["cpus"]: w.append(f"storage server load {tw['load1']} over {tw['cpus']} threads")
        return w

    def remote(self):
        t, cached = self._remote
        if time.time() - t < self.c["remote_cache_s"]:
            return cached
        flag = shlex.quote(self.c["pause_flag"])
        inprog = self.c.get("remote_inprogress_glob", "")
        outd = self.c.get("remote_out_dir") or os.path.join(os.path.dirname(os.path.dirname(inprog)), "out")
        spool = self.c.get("remote_spool_dir") or "/nonexistent"
        cmd = ("nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader,nounits; "
               f"test -e {flag} && echo PAUSED || echo RUNNING; "
               f"pgrep -fc {shlex.quote(self.c.get('remote_worker_match', 'fine_comb_visit.py'))} || true; "
               "nproc; cat /proc/loadavg; free -m | awk '/^Mem:/{print $2, $7}'; "
               "top -bn1 | awk -F',' '/Cpu\\(s\\)/{for(i=1;i<=NF;i++) if($i ~ /id/){gsub(/[^0-9.]/,\"\",$i); print 100-$i}}'; "
               "awk 'NR>2{gsub(\":\",\" \"); if($1 !~ /^(lo|docker|veth|br-)/) {r+=$2; t+=$10}} END{print \"NET\", r, t}' /proc/net/dev; "
               f"echo ---; for f in {inprog}; do [ -e \"$f\" ] && stat -c '%Y %n' \"$f\" && ffprobe -v error -show_entries format=duration -of csv=p=0 \"$f\"; done 2>/dev/null; "
               f"echo +++; ps -eo args | grep {shlex.quote('[p]ython.*' + self.c.get('remote_worker_match', 'fine_comb_visit.py'))} | grep -oE -- '--label [A-Za-z0-9_]+' | cut -d' ' -f2 | sort -u; "
               # stage of each staged item (1 leveling, 2 loading models, 3 transcribing, 4 separating speakers, 5 naming speakers),
               # judged by the worker log and cache files written after the item was staged; then recent worker run times for the estimate
               f"echo @@@; for f in {inprog}; do case \"$f\" in *.orig48k.wav) ;; *) continue;; esac; [ -e \"$f\" ] || continue; "
               f"l=$(basename \"$f\" .orig48k.wav); o={shlex.quote(outd)}; s=1; [ \"$o/$l.log\" -nt \"$f\" ] && s=2; "
               f"[ $s = 2 ] && grep -qs 'voice activity' \"$o/$l.log\" && s=3; [ \"$o/FINECOMB_$l.asr_cache.json\" -nt \"$f\" ] && s=4; "
               f"[ \"$o/FINECOMB_$l.diar_cache.json\" -nt \"$f\" ] && s=5; echo \"$l $s\"; done; "
               f"echo %%%; ls -t {shlex.quote(outd)}/*.log 2>/dev/null | head -60 | xargs -r stat -c '%W %Y %n'; "
               # resident workers (optional): jobs waiting in the spool, jobs a worker has claimed, live workers
               f"echo ^^^; ls {shlex.quote(spool)}/queue 2>/dev/null | sed -n 's/\\.job$//p' | sed 's/^/Q /'; "
               f"ls {shlex.quote(spool)}/work 2>/dev/null | sed -n 's/\\.job\\..*$//p' | sed 's/^/W /'; "
               f"now=$(date +%s); for h in {shlex.quote(spool)}/workers/*; do [ -f \"$h\" ] && set -- $(cat \"$h\") && [ $((now - $2)) -lt 60 ] && echo \"A $(basename $h)\"; done")
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
            nl = next((x for x in out if x.startswith("NET ")), None)
            if nl:
                _, a, b = nl.split(); rxr, txr = self._rate("mrgpu", int(a), int(b))
                r["rx_mbs"], r["tx_mbs"] = rxr and round(rxr / 1e6, 1), txr and round(txr / 1e6, 1)
            sep = out.index("---")
            sep2 = out.index("+++") if "+++" in out else len(out)
            sep3 = out.index("@@@") if "@@@" in out else len(out)
            sep4 = out.index("%%%") if "%%%" in out else len(out)
            sep5 = out.index("^^^") if "^^^" in out else len(out)
            sp = [x.split(" ", 1) for x in out[sep5 + 1:] if " " in x]
            r["spool_queued"] = [b for a, b in sp if a == "Q"]
            r["spool_working"] = [b for a, b in sp if a == "W"]
            r["resident_workers"] = [b for a, b in sp if a == "A"]
            r["running_labels"] = [x.strip() for x in out[sep2 + 1:sep3] if x.strip()]
            r["stages"] = {a: int(b) for a, b in (x.split() for x in out[sep3 + 1:sep4] if len(x.split()) == 2)}
            r["recent_runs"] = [(int(a), int(b), os.path.basename(c)[:-4]) for a, b, c in (x.split(" ", 2) for x in out[sep4 + 1:sep5] if x.count(" ") >= 2) if int(a) > 0]
            r["running_labels"] = sorted(set(r["running_labels"]) | set(r["spool_working"]))   # resident workers have no --label
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

    def est_model(self, rem, lm):
        """Fit run seconds = a + b * audio seconds on recent finished items (worker log birth -> last write). Cached 2 min."""
        t, v = getattr(self, "_est", (0, None))
        if time.time() - t < 120 or not rem.get("recent_runs"):
            return v
        pts = []
        for born, last, lab in rem["recent_runs"]:
            if lab in rem.get("running_labels", []):
                continue
            if re.match(r"c15_", lab):
                a = 900.0
            else:
                src = lm.get(lab, (None, None))[1]
                if not src or not os.path.exists(src):
                    continue
                if src not in self._dur:
                    self._dur[src] = ffprobe_s(src)
                a = self._dur[src]
            d = last - born
            if a and 0 < d < 4 * 3600:
                pts.append((a, d))
        runs = [last - born for born, last, lab in rem["recent_runs"] if lab not in rem.get("running_labels", []) and 0 < last - born < 4 * 3600]
        v = (statistics.median(runs), 0.0, len(runs)) if runs else None   # fallback: average run time per item, no audio length needed
        if len(pts) >= 5:
            n = len(pts); mx = sum(p[0] for p in pts) / n; my = sum(p[1] for p in pts) / n
            sxx = sum((p[0] - mx) ** 2 for p in pts)
            b = max(0.0, sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx) if sxx else 0.0
            v = (max(10.0, my - b * mx), b, n)
        self._est = (time.time(), v)
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

    def queue_of(self, lab, lm, by_hash):
        """Queue name for a label; 15-min pieces (c15_<hash>_<min>) take their parent recording's queue."""
        if lab in lm:
            return lm[lab][0]
        m = re.fullmatch(r"c15_([0-9a-f]{12})_(\d{4})", lab)
        if m:
            return f"{by_hash.get(m.group(1), '?')} · piece {int(m.group(2))}–{int(m.group(2)) + 15} min"
        return "?"

    def status(self):
        res = self.results()
        lm = self.label_map()
        by_hash = {}
        for lab_, (qn_, _src) in lm.items():
            mm = re.search(r"([0-9a-f]{12})$", lab_)
            if mm:
                by_hash.setdefault(mm.group(1), qn_)
        runners = self.runners()
        chain_up = any(re.search(self.c.get("chain_match", r"^$"), r["script"]) for r in runners)
        chained = set(self.c.get("chained_queues", [])) if chain_up else set()
        qs = self.queues(res)
        busy = {r["queue"] for r in runners if r["queue"]}
        for q in qs:
            q["in_chain"] = q["queue"] in chained
            q["todo"] = q["total"] - q["done"] - q["too_long"] > 0
        # queues with work left first (running, then waiting in the chain, then idle); finished queues after, latest finished on top
        qs.sort(key=lambda q: (0, 0 if q["queue"] in busy else 1 if q["in_chain"] else 2, q["queue"]) if q["todo"]
                else (1, -q["last_done_ts"], q["queue"]))
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
        model = self.est_model(rem, lm)
        STG = {0: ("waiting for worker", 0, 2), 1: ("leveling audio", 0, 8), 2: ("loading models", 3, 20), 3: ("transcribing", 10, 65),
               4: ("separating speakers", 55, 92), 5: ("naming speakers", 88, 99)}
        for c in cur:
            c["queue"] = self.queue_of(c["label"], lm, by_hash)
            c["elapsed_s"] = int(now - c["started"])
            st_ = 0 if c["label"] in rem.get("spool_queued", []) else rem.get("stages", {}).get(c["label"], 1)
            c["stage"], c["stage_name"], c["lo"], c["hi"] = st_, *STG.get(st_, STG[1])
            est = None
            if model:   # fitted (fixed + per audio second), or the recent average when the fit is not ready
                est = model[0] + model[1] * (c.get("audio_s") or 0) + 5 + 0.01 * (c.get("audio_s") or 0)   # + leveling before the worker starts
            elif sp and c.get("audio_s"):
                est = c["audio_s"] * sp
            if est:
                c["est_total_s"] = int(est)
                c["pct"] = int(min(c["hi"], max(c["lo"], 100 * c["elapsed_s"] / est)))
        mac_jobs = self.local_jobs(lm, by_hash)
        recent = [{"label": lb, "queue": self.queue_of(lb, lm, by_hash), "finished": time.strftime("%m-%d %H:%M", time.localtime(t))}
                  for lb, t in sorted(res.items(), key=lambda x: -x[1])[: self.c.get("recent_n", 15)]]
        return {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "dry_run": self.c["dry_run"], "remote": rem, "cleared": self.cleared_note,
                "local": (loc := self.local_host()), "storage": (tw := self.storage()), "saturation": self.saturation(rem, loc, tw), "speed": round(sp, 3) if sp else None,
                "est_model": {"fixed_s": round(model[0]), "per_audio_min_s": round(model[1] * 60, 1), "n": model[2]} if model else None, "queues": qs, "runners": runners,
                "recent": recent, "mac_jobs": mac_jobs, "logs": self.logs(), "priority": self.priority,
                "reports": [r.get("name", "") for r in self.c.get("reports", [])], "flag_label": self.c.get("flag_label", "flagged")}

    # ---------- controls ----------
    def _run(self, argv, detach=False):
        if self.c["dry_run"]:
            return {"dry_run": True, "would_run": " ".join(shlex.quote(a) for a in argv)}
        if detach:
            subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return {"started": True}
        return {"output": sh(argv)}

    def flags(self):
        return " ".join(shlex.quote(f) for f in [self.c["pause_flag"]] + self.c.get("extra_pause_flags", []))

    def pause(self):
        self._remote = (0, {})
        return self._run(["ssh", "-o", "BatchMode=yes", self.c["remote_host"], f"touch {self.flags()}"])

    def resume(self):
        self._remote = (0, {})
        return self._run(["ssh", "-o", "BatchMode=yes", self.c["remote_host"], f"rm -f {self.flags()}"])

    def start(self, queue):
        qs = self.queue_files()
        if queue not in qs:
            return {"error": "unknown queue"}
        q = next(x for x in self.status()["queues"] if x["queue"] == queue)
        if q["total"] - q["done"] - q["too_long"] <= 0:
            return {"error": f"nothing left that can run: {q['too_long']} remaining item(s) are over the length limit and go to the excerpt route"}
        mine = [r for r in self.runners() if r["queue"] == queue]
        if any(r["from_end"] for r in mine):
            return {"error": "this queue already has a runner working from the end"}
        # A queue that is running, or waiting in a chain, gets a second runner that works through the list from the end.
        # Runners skip items whose result exists, so the two meet in the middle and at most one item is done twice.
        src = qs[queue]
        from_end = bool(mine) or q["in_chain"]
        if from_end:
            os.makedirs(self.rev_dir(), exist_ok=True)
            src = os.path.join(self.rev_dir(), os.path.basename(qs[queue]))
            lines = [ln for ln in open(qs[queue], errors="ignore") if ln.strip()]
            if not self.c["dry_run"]:
                with open(src, "w") as f:
                    f.writelines(ln if ln.endswith("\n") else ln + "\n" for ln in reversed(lines))
        tag = "_from_end" if from_end else ""
        log = os.path.join(self.c["log_dir"], f"jobboard_{queue}{tag}_{time.strftime('%Y%m%d_%H%M%S')}.log")
        cmd = f"Q={shlex.quote(src)} {shlex.quote(self.c['runner_script'])} >> {shlex.quote(log)} 2>&1"
        return dict(self._run(["/bin/bash", "-c", cmd], detach=True), from_end=from_end)

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

    # ---------- priority: run one queue now, hold the other runners until it ends ----------
    def _pstate(self):
        return os.path.join(self.c["log_dir"], ".jobboard_priority.json")

    def release_priority(self, note=""):
        st = getattr(self, "priority", None)
        if not st and os.path.exists(self._pstate()):
            try:
                st = json.load(open(self._pstate()))
            except ValueError:
                st = None
        if not st:
            return {"error": "no priority run"}
        live = {r["pid"] for r in self.runners()}
        for pid in st.get("held", []):
            if pid in live:
                self._run(["kill", "-CONT", str(pid)])
        self.priority = None
        try:
            os.remove(self._pstate())
        except OSError:
            pass
        return {"released": st.get("held", []), "note": note}

    def prioritize(self, queue):
        if getattr(self, "priority", None):
            return {"error": f"queue {self.priority['queue']} already has priority; end it first"}
        before = {r["pid"] for r in self.runners()}
        r = self.start(queue)
        if "error" in r or self.c["dry_run"]:
            return r
        pid = None
        for _ in range(20):   # find the new runner
            time.sleep(0.5)
            pid = next((x["pid"] for x in self.runners() if x["queue"] == queue and x["pid"] not in before and x["queue"]), None)
            if pid:
                break
        if not pid:
            return {"error": "started, but the new runner was not found; nothing was held"}
        held = [x["pid"] for x in self.runners() if x["pid"] != pid and x["queue"] and not x["paused"]]
        for h in held:
            self._run(["kill", "-STOP", str(h)])
        self.priority = {"queue": queue, "pid": pid, "held": held, "since": time.strftime("%H:%M")}
        json.dump(self.priority, open(self._pstate(), "w"))

        def watch():
            while True:
                time.sleep(5)
                if not getattr(self, "priority", None) or self.priority.get("pid") != pid:
                    return
                if pid not in {x["pid"] for x in self.runners()}:
                    self.release_priority(f"{queue} finished")
                    return
        threading.Thread(target=watch, daemon=True).start()
        return {"priority": queue, "runner": pid, "held": held}

    def hold(self, pid, on):
        """Pause (SIGSTOP) or resume (SIGCONT) one runner. The item already on the GPU finishes; the runner starts nothing new until resumed."""
        if pid not in {r["pid"] for r in self.runners()}:
            return {"error": "not a job-board runner pid"}
        return self._run(["kill", "-STOP" if on else "-CONT", str(pid)])

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
.stats div{min-width:150px}.ub{font-family:ui-monospace,Menlo,monospace;letter-spacing:-1px}.ubd{color:var(--bar)}.ubr{color:var(--line)}tr.flag td:first-child{box-shadow:inset 3px 0 0 var(--warn)}.flagpill{border-color:var(--warn);color:var(--warn)}.big{font-size:18px}details summary{cursor:pointer}.small{font-size:12px}a{color:var(--bar)}
</style></head><body>
<h1>Job Board <span class="muted" id="t"></span></h1><div class="muted" id="rep"></div>
<div id="pri"></div><section id="gpu"></section><section><b>Active jobs</b> <span class="muted small">(🐧 deep pass on the GPU host · 🍎 cutting, quick triage and uploads on this Mac)</span><table id="cur"></table></section>
<section><b>Queues</b> <span class="muted small">(to do first, then finished with the latest on top · click a row for purpose and expected gain)</span><table id="q"></table></section>
<section><b>Recently finished</b><table id="fin"></table></section>
<section><b>Runners</b><table id="r"></table></section><section><b>Recent log lines</b><div id="l"></div></section>
<script>
const TOKEN="__TOKEN__",REDACT=__REDACT__;
async function post(p,b){const r=await fetch(p,{method:"POST",headers:{"X-Token":TOKEN,"Content-Type":"application/json"},body:JSON.stringify(b||{})});alert(JSON.stringify(await r.json()));load();}
function esc(s){return String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}
function mins(s){if(s==null)return"?";const m=Math.round(s/60);return m>=60?`${Math.floor(m/60)}h ${m%60}m`:`${m}m`}
function bar(p){return `<div class="bar"><i style="width:${p||0}%"></i></div>`}
function ubar(p,w=30){p=Math.max(0,Math.min(100,p||0));const f=p/100*w,n=Math.floor(f),h=(f-n)>=.5&&n<w;return `<span class="ub"><span class="ubd">${"━".repeat(n)}${h?"╸":""}</span><span class="ubr">${"━".repeat(w-n-(h?1:0))}</span></span>`}
// 2026-10-02: host badges (runner + cutting + quick triage on the Mac; deep pass on the Linux GPU host; storage on the Unraid server)
const HOST=__HOSTS__;
function hb(k){const h=HOST[k];if(!h)return"";const n=h[1].split(" · ")[0];return REDACT?`<span class="pill small">${h[0]} ${"█".repeat(n.length)}</span>`:`<span class="pill small" title="${h[1]}">${h[0]} ${n}</span>`}
function secs(s){s=Math.max(0,Math.round(s));const m=Math.floor(s/60);return m?`${m}m ${String(s%60).padStart(2,"0")}s`:`${s}s`}
let CUR=[],MAC=[],T0=Date.now();
function drawCur(){const dt=(Date.now()-T0)/1000;document.getElementById("cur").innerHTML=CUR.length?"<tr><th>Item</th><th>Host</th><th>Queue</th><th>Audio</th><th>Stage</th><th>Progress</th></tr>"+CUR.map(c=>{
 if(c.stale)return `<tr><td>${esc(c.label)}</td><td>${hb('linux')}</td><td>${esc(c.queue)}</td><td>${mins(c.audio_s)}</td><td></td><td><span class="pill paused">stale leftover (not running)</span></td></tr>`;
 if(c.stage===0)return `<tr><td>${esc(c.label)}</td><td>${hb('linux')}</td><td>${esc(c.queue)}</td><td>${mins(c.audio_s)}</td><td><span class="pill small">in line</span></td><td style="white-space:nowrap">${ubar(0)} <span class="small muted">waiting for the resident worker · staged ${secs(c.elapsed_s+dt)} ago</span></td></tr>`;
 const el=c.elapsed_s+dt,raw=c.est_total_s?100*el/c.est_total_s:null,p=raw==null?(c.lo+c.hi)/2:Math.min(c.hi,Math.max(c.lo,raw));
 const left=c.est_total_s?c.est_total_s-el:null,eta=left==null?"estimating…":raw>c.hi?`finishing ${esc(c.stage_name)}…`:`~${secs(left)} left`;
 return `<tr><td>${esc(c.label)}</td><td>${hb('linux')}</td><td>${esc(c.queue)}</td><td>${mins(c.audio_s)}</td><td><span class="pill small">${c.stage}/5 ${esc(c.stage_name)}</span></td><td style="white-space:nowrap">${ubar(p)} <b>${Math.round(p)}%</b> <span class="small muted">${secs(el)}${c.est_total_s?` / ~${secs(c.est_total_s)}`:""} · ${eta}</span></td></tr>`}).join(""):"<tr><td class=muted>nothing staged on the GPU right now</td></tr>";
 document.getElementById("cur").innerHTML+=MAC.map(j=>{const el=j.elapsed_s+dt;return `<tr><td>${esc(j.label)}</td><td>${hb('mac')}</td><td>${esc(j.queue)}</td><td></td><td><span class="pill small">${esc(j.stage)}</span></td><td style="white-space:nowrap">${j.pct==null?'<span class="small muted">in progress</span>':ubar(j.pct)+` <b>${j.pct}%</b>`} <span class="small muted">${secs(el)}${j.est?" · estimated":""}</span></td></tr>`}).join("");}
async function load(){const s=await (await fetch("/api/status")).json();
document.getElementById("t").textContent=s.time+(s.dry_run?"  (DRY RUN: buttons only show what they would do)":"");
document.getElementById("pri").innerHTML=s.priority?`<section style="border-color:var(--warn)"><b class="paused">⇧ Priority: ${esc(s.priority.queue)}</b> since ${esc(s.priority.since)} · runner ${s.priority.pid} · ${s.priority.held.length} other runner(s) held until it ends <button onclick="post('/api/endpriority')">End priority</button></section>`:"";
document.getElementById("rep").innerHTML=s.reports.length?"Reports: "+s.reports.map((n,i)=>`<a href="/report/${i}" target="_blank">${esc(n)}</a>`).join(" · "):"";
const g=s.remote,L=s.local;
document.getElementById("gpu").innerHTML=g.reachable?`<div class="stats">
<div><div class="muted small">${hb('linux')} GPU memory</div><div class="big">${g.gpu_used_mib} / ${g.gpu_total_mib} MiB</div>${bar(100*g.gpu_used_mib/g.gpu_total_mib)}</div>
<div><div class="muted small">GPU busy · temp</div><div class="big">${g.gpu_util}% · ${g.gpu_temp}°C</div>${bar(g.gpu_util)}</div>
<div><div class="muted small">GPU host CPU</div><div class="big">${g.cpu_pct??"?"}% · load ${g.load1} / ${g.cpus}</div>${bar(g.cpu_pct)}</div>
<div><div class="muted small">GPU host memory</div><div class="big">${((g.mem_total_mib-g.mem_avail_mib)/1024).toFixed(1)} / ${(g.mem_total_mib/1024).toFixed(0)} GiB</div>${bar(100*(g.mem_total_mib-g.mem_avail_mib)/g.mem_total_mib)}</div>
<div><div class="muted small">GPU host network</div><div class="big">${g.rx_mbs??"…"} ↓ · ${g.tx_mbs??"…"} ↑ MB/s</div>${bar(100*Math.max(g.rx_mbs||0,g.tx_mbs||0)/117)}</div>
<div><div class="muted small">${hb('mac')} cutting + quick triage</div><div class="big">GPU ${L.gpu_pct??"?"}% · CPU ${L.cpu_pct}%</div>${bar(L.gpu_pct)}${bar(L.cpu_pct)}<div class="small muted">Apple GPU (Metal) runs quick triage · GPU memory ${L.gpu_mem_gb??"?"} GB · load ${L.load1} / ${L.cpus}</div><div class="small muted">${L.rx_mbs??"…"} ↓ · ${L.tx_mbs??"…"} ↑ MB/s · ${L.triage_10min} triaged in 10 min</div></div>
<div><div class="muted small">${hb('unraid')} ${esc(s.storage.nic||"NIC")} (shared 1 GbE)</div><div class="big">${s.storage.reachable?`${s.storage.rx_mbs??"…"} ↓ · ${s.storage.tx_mbs??"…"} ↑ MB/s`:"not reachable"}</div>${bar(100*Math.max(s.storage.rx_mbs||0,s.storage.tx_mbs||0)/117)}<div class="small muted">load ${s.storage.load1??"?"} / ${s.storage.cpus??"?"}</div></div>
<div><div class="muted small">State</div><div class="big"><span class="pill ${g.paused?"paused":""}">${g.paused?"PAUSED":"running"}</span> ${g.workers} item${g.workers==1?"":"s"} processing${(g.resident_workers||[]).length?` · ${g.resident_workers.length} resident worker${g.resident_workers.length==1?"":"s"} (models loaded)${(g.spool_queued||[]).length?` · ${g.spool_queued.length} waiting`:""}`:""}</div>
<button onclick="post('/api/pause')">Pause all</button> <button onclick="post('/api/resume')">Resume all</button></div></div>
${(s.saturation||[]).length?`<div class="bad small"><b>Saturation:</b> ${s.saturation.map(esc).join(" · ")}</div>`:`<div class="small muted">No host near a limit (GPU memory, RAM, CPU, 1 GbE links).</div>`}${s.cleared?`<div class="small">${esc(s.cleared)}</div>`:""}<div class="muted small">Speed: ${s.speed?`${(1/s.speed).toFixed(1)}× real time (median of recent items)`:"not enough history yet"}${s.est_model?(s.est_model.per_audio_min_s?` · estimate per item: ${s.est_model.fixed_s}s fixed + ${s.est_model.per_audio_min_s}s per audio minute (fit on ${s.est_model.n} recent items)`:` · estimate per item: average ${s.est_model.fixed_s}s (last ${s.est_model.n} items)`):""}</div>`:`<b class="bad">GPU host not reachable over ssh</b>`;
CUR=(g.current||[]);MAC=(s.mac_jobs||[]);T0=Date.now();drawCur();const cur=[];if(0)document.getElementById("cur").innerHTML=cur.length?"<tr><th>Item</th><th>Queue</th><th>Audio</th><th>Running</th><th>Est. progress</th></tr>"+cur.map(c=>`<tr><td>${esc(c.label)}</td><td>${esc(c.queue)}</td><td>${mins(c.audio_s)}</td><td>${mins(c.elapsed_s)}</td><td>${c.stale?'<span class="pill paused">stale leftover (not running)</span>':c.pct!=null?bar(c.pct)+`<span class="small muted">${c.pct}% of ~${mins(c.est_total_s)}</span>`:'<span class="muted small">estimating…</span>'}</td></tr>`).join(""):"<tr><td class=muted>nothing staged on the GPU right now</td></tr>";
document.getElementById("q").innerHTML="<tr><th>Queue</th><th>Done</th><th></th><th>Created</th><th>Last finished</th><th></th></tr>"+s.queues.map(q=>{const p=q.total?Math.round(100*q.done/q.total):0;const run=s.runners.some(r=>r.queue==q.queue);
const rs=s.runners.filter(r=>r.queue==q.queue),left=q.total-q.done-(q.too_long||0),qn=esc(q.queue);
const ctl=r=>`<button onclick="event.stopPropagation();post('/api/${r.paused?"release":"hold"}',{pid:${r.pid}})">${r.paused?"Resume":"Pause"}</button> <button onclick="event.stopPropagation();if(confirm('Stop ${qn} runner ${r.pid}? The item already on the GPU finishes.'))post('/api/stop',{pid:${r.pid}})">Stop</button>`;
const st=rs.map(r=>`<div style="margin:2px 0"><span class="pill ${r.paused?"paused":""}">${r.paused?"paused":"running"}${r.from_end?" · from end":""}</span> ${hb('mac')}→${hb('linux')} ${ctl(r)}</div>`).join("");
const can=left>0&&!rs.some(r=>r.from_end),fromEnd=rs.length||q.in_chain;
const btn=can?`<button onclick="event.stopPropagation();if(confirm('${fromEnd?(rs.length?`Start a second ${qn} runner from the END of the list? (the other one works from the front)`:`Start ${qn} now? It works from the end of the list; when the chain reaches ${qn} it works from the front, and they meet in the middle.`):`Start ${qn}?`}'))post('/api/start',{queue:'${qn}'})">${rs.length?"Start from end":q.in_chain?"Start now":"Start"}</button>`:"";
const rate=q.span_s>0?`${(q.done/(q.span_s/3600)).toFixed(1)}/h`:"";
const summ=q.done?`<div class="small muted">${esc(q.first_done)} → ${esc(q.last_done)}${q.span_s?` · ${mins(q.span_s)} · ${rate}`:""}</div>`:"";
const fin=!rs.length&&q.done>=q.total?'<span class="pill">✓ complete</span>'+summ
 :!rs.length&&left<=0&&q.done<q.total?`<span class="pill">✓ complete</span><div class="small muted">${q.done} done · ${q.too_long} too long → excerpt route${q.pending_pieces?` (${q.pending_pieces} pieces still queued)`:""}</div>`+summ.replace('<div class="small muted">','<div class="small muted">')
 :!rs.length&&!q.in_chain&&left>0?`<span class="pill muted">idle · ${left} left</span> `:"";
const pri=(q.in_chain||!rs.length)&&left>0&&!s.priority?` <button title="Run this queue now and hold the other runners until it ends" onclick="event.stopPropagation();if(confirm('Give ${qn} priority? It starts now; every other runner pauses after its current item and resumes when ${qn} finishes.'))post('/api/priority',{queue:'${qn}'})">⇧ Priority</button>`:"";
const act=fin+st+pri+(q.in_chain&&!rs.length?'<span class="pill muted">waiting in chain</span> ':"")+btn+(q.too_long&&left>0?`<div class="small muted">${q.too_long} too long (excerpt route)${q.pending_pieces?` · ${q.pending_pieces} pieces still queued in chunk queues`:""}</div>`:"")+(q.via_chunks?`<div class="small muted">${q.via_chunks} long recording${q.via_chunks==1?"":"s"} covered by 15-min pieces (processed or silent)</div>`:"");
const head=q.todo!==s.queues[0].todo&&q===s.queues.find(x=>!x.todo)?`<tr><td colspan="6" class="muted small" style="padding-top:12px"><b>Finished</b> · latest first</td></tr>`:q===s.queues[0]&&q.todo?`<tr><td colspan="6" class="muted small"><b>To do</b></td></tr>`:"";
return head+`<tr class="${q.flag?"flag":""}" onclick="const d=this.nextElementSibling;d.hidden=!d.hidden" style="cursor:pointer"><td><b>${esc(q.queue)}</b> ${q.flag?`<span class="pill flagpill small">⚖ ${esc(s.flag_label)}${q.flag_party?" · "+esc(q.flag_party):""}</span>`:""}</td><td>${q.done} / ${q.total}</td><td>${bar(p)}</td><td class="muted">${q.created}</td><td class="muted">${q.last_done}</td><td>${act}</td></tr>
<tr hidden><td></td><td colspan="5" class="small">${q.purpose?`<b>Purpose:</b> ${esc(q.purpose)}<br>`:""}${q.source?`<b>Source:</b> ${esc(q.source)}<br>`:""}${q.gain?`<b>Expected gain:</b> ${esc(q.gain)}<br>`:""}${q.outputs?`<b>Outputs:</b> ${esc(q.outputs)}<br>`:""}${q.flag?`<b class="paused">⚖ ${esc(s.flag_label)}${q.flag_party?" ("+esc(q.flag_party)+")":""}:</b> ${esc(q.flag)}`:""}${!(q.purpose||q.gain)?'<span class="muted">no notes for this queue</span>':""}</td></tr>`}).join("");
document.getElementById("fin").innerHTML="<tr><th>Item</th><th>Queue</th><th>Finished</th></tr>"+s.recent.map(f=>`<tr><td>${esc(f.label)}</td><td>${esc(f.queue)}</td><td>${f.finished}</td></tr>`).join("");
document.getElementById("r").innerHTML="<tr><th>PID</th><th>Host</th><th>Script</th><th>Queue</th><th>Running for</th><th></th></tr>"+(s.runners.map(r=>`<tr><td>${r.pid}</td><td>${hb('mac')} → ${hb('linux')}</td><td>${esc(r.script)}</td><td>${esc(r.queue||"(chain)")}${r.from_end?' <span class="small muted">from end</span>':""}</td><td>${esc(r.elapsed)}</td><td>${r.paused?'<span class="pill paused">paused</span> ':""}<button onclick="post('/api/${r.paused?"release":"hold"}',{pid:${r.pid}})">${r.paused?"Resume":"Pause"}</button> <button onclick="if(confirm('Stop runner ${r.pid}? The item already on the GPU finishes; no new items start.'))post('/api/stop',{pid:${r.pid}})">Stop</button></td></tr>`).join("")||"<tr><td class=muted>none</td></tr>");
document.getElementById("l").innerHTML=Object.entries(s.logs).map(([f,L])=>`<div class="muted">${esc(f)}</div><pre>${esc(L.join("\\n"))||"(nothing yet)"}</pre>`).join("");}
load();setInterval(load,15000);setInterval(drawCur,1000);
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
                return self._send(200, PAGE.replace("__TOKEN__", TOKEN).replace("__REDACT__", "true" if board.redact else "false").replace("__HOSTS__", json.dumps(board.hosts())), "text/html; charset=utf-8")
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
                      "/api/stop": lambda: board.stop(int(body.get("pid", 0))),
                      "/api/priority": lambda: board.prioritize(str(body.get("queue", ""))),
                      "/api/endpriority": lambda: board.release_priority("ended from the page"),
                      "/api/hold": lambda: board.hold(int(body.get("pid", 0)), True),
                      "/api/release": lambda: board.hold(int(body.get("pid", 0)), False)}
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

#!/usr/bin/env python3
"""Merge every job-board report, batch job and source into one "status to date" page.

Standard library only. Reads config/jobboard.toml (reports, batch_jobs, freshness_sources) and an
optional [status_merge] table:

    [status_merge]
    out = "/path/STATUS_TO_DATE_local.md"     # written here (keep it out of git)
    title = "Status to date"
    notes_file = "/path/STATUS_NOTES_local.md" # optional private markdown placed at the top
    recon_logs = [["Device pull", "/path/PULL_LOG.txt"]]   # 'key rows=N' lines become stat rows

Nothing is sent anywhere. Report headlines are copied from each report's first bullet lines, as-is.

    python3 stack/jobboard/status_merge.py [--config config/jobboard.toml] [--loop 600]
"""
import argparse, glob, os, re, time, tomllib

HOUR = 3600


def age(ts):
    if not ts:
        return "missing"
    h = (time.time() - ts) / HOUR
    return f"{h:.0f} h" if h < 48 else f"{h / 24:.0f} d"


def newest(globs):
    best = 0
    for g in globs:
        for p in glob.glob(g):
            try:
                best = max(best, os.path.getmtime(p))
            except OSError:
                pass
    return best


def headline(path, n=3):
    """First n bullet lines of a markdown report (html: <title> only)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(40000)
    except OSError:
        return []
    if path.endswith(".html"):
        m = re.search(r"<title>(.*?)</title>", text, re.S)
        return [m.group(1).strip()] if m else []
    out = []
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^([-*]|\d+\.)\s+\S", s):
            out.append(re.sub(r"^([-*]|\d+\.)\s+", "", s)[:160])
            if len(out) >= n:
                break
    return out


AUDIO = re.compile(r"\.(m4a|mp3|wav|amr|aac|ogg|opus)$|/\.pending-", re.I)


def newest_file(globs, pattern=None, limit_dirs=8):
    """Newest file (path, mtime) under the newest few folders matched by globs; optional regex filter."""
    dirs = sorted({d for g in globs for d in glob.glob(g)}, key=lambda d: os.path.getmtime(d), reverse=True)[:limit_dirs]
    best = (None, 0)
    for d in dirs:
        if os.path.isfile(d):
            cand = [(d, os.path.getmtime(d))]
        else:
            cand = []
            for root, _, files in os.walk(d):
                for f in files:
                    fp = os.path.join(root, f)
                    if pattern and not pattern.search(fp):
                        continue
                    try:
                        cand.append((fp, os.path.getmtime(fp)))
                    except OSError:
                        pass
        for c in cand:
            if c[1] > best[1]:
                best = c
    return best


def when(t):
    return time.strftime("%a %b %-d, %-I:%M %p", time.localtime(t)) if t else "—"


def build(c):
    sm = c.get("status_merge", {})
    srcs = c.get("freshness_sources", {})
    red_h = c.get("freshness_red_h", 24)
    now = time.strftime("%Y-%m-%d %H:%M")
    L = [f"# 📋 {sm.get('title', 'Status to date')}", "", f"**Built:** {now} · rebuilt by `status_merge.py` (local, no LLM)", ""]

    nf = sm.get("notes_file")
    if nf and os.path.exists(nf):
        L += [open(nf, encoding="utf-8").read().rstrip(), "", "---", ""]

    # live recon logs
    for name, log in sm.get("recon_logs", []):
        L += [f"## 📱 {name}", ""]
        if not os.path.exists(log):
            L += ["- ⏳ not started", ""]
            continue
        lines = open(log, encoding="utf-8", errors="replace").read().splitlines()
        rows = [(m.group(1), m.group(2)) for l in lines for m in [re.search(r"(\S+) rows=(\d+)", l)] if m]
        if rows:
            L += ["| Source | Rows |", "|---|---:|"] + [f"| {k} | {int(v):,} |" for k, v in rows] + [""]
        for l in lines:
            if re.search(r"binaries=|pulled |phase\d done|STOP|waiting|iOS device|WillEncrypt|partial", l):
                L.append(f"- {l}")
        L += [f"- last log line {age(os.path.getmtime(log))} ago", ""]

    # latest context: what is newest right now
    L += ["## 🆕 Latest context", ""]
    rg = sm.get("recordings_globs", [])
    if rg:
        f, t = newest_file(rg, AUDIO)
        L.append(f"- 🎙️ **Most recent recording:** {when(t)} · `{os.path.basename(f) if f else '—'}`")
    st = sm.get("sent_stamp")
    if st and os.path.exists(st):
        L.append(f"- 📧 **Most recent Gmail sent:** {when(os.path.getmtime(st))} (stamp; re-stamp after new sends)")
    pulls = sorted(glob.glob(sm.get("pull_dirs_glob", "")), key=os.path.getmtime, reverse=True)[:4] if sm.get("pull_dirs_glob") else []
    for d in pulls:
        cl = os.path.join(d, "custody_log.txt")
        line = open(cl, encoding="utf-8", errors="replace").read().strip().splitlines()[-1][:150] if os.path.exists(cl) else "running"
        L.append(f"- 📱 **Pull** `{os.path.basename(d)}`: {line}")
    L.append("")

    # sources
    L += ["## 🗃️ Sources (newest file)", "", "| Source | Newest | Files |", "|---|---|---:|"]
    src_t, src_f = {}, {}
    for k, gl in srcs.items():
        files = [p for g in gl for p in glob.glob(g)]
        src_t[k] = newest(gl)
        src_f[k] = max(files, key=lambda p: os.path.getmtime(p), default="") if files else ""
        L.append(f"| {k} | {time.strftime('%m-%d %H:%M', time.localtime(src_t[k])) if src_t[k] else '—'} ({age(src_t[k])}) | {len(files)} |")
    L.append("")

    # reports
    reps = c.get("reports", [])
    green = yellow = red = 0
    body = []
    for r in reps:
        p = r["path"]
        rt = os.path.getmtime(p) if os.path.exists(p) else 0
        names = r.get("sources", c.get("freshness_default", []))
        behind = max([src_t.get(s, 0) for s in names] or [0]) - rt
        if not rt:
            led = "⚫"
        elif not names or behind <= 0:
            led, green = "🟢", green + 1
        elif behind < red_h * HOUR:
            led, yellow = "🟡", yellow + 1
        else:
            led, red = "🔴", red + 1
        stale = [s for s in names if src_t.get(s, 0) > rt]
        body += [f"### {led} {r['name']}", f"- updated {age(rt)} ago" + (f" · newer data in: {', '.join(stale)}" if stale else " · current"),
                 f"- file: `{p}`"]
        for sname in stale:
            body.append(f"  - 🆕 {sname}: newest {when(src_t[sname])} · `{os.path.basename(src_f.get(sname, '')) or '—'}`")
        body += [f"  - {h}" for h in headline(p)]
        body.append("")
    L += [f"## 📚 Reports ({len(reps)}): 🟢 {green} · 🟡 {yellow} · 🔴 {red}", ""] + body

    # batch jobs
    L += ["## 🏃 Batch jobs", "", "| Job | Progress | Last write | State |", "|---|---:|---|---|"]
    seen = set()
    for name, log, exp in c.get("batch_jobs", []):
        if (name, log) in seen:
            continue
        seen.add((name, log))
        if os.path.exists(log):
            n = sum(1 for _ in open(log, "rb"))
            t = os.path.getmtime(log)
            pct = f"{min(100, 100 * n // exp)}%" if exp else f"{n} lines"
            st = "✅ done" if exp and n >= exp else ("🏃 running" if time.time() - t < 2 * HOUR else "💤 stopped")
        else:
            pct, t, st = "—", 0, "⚫ no log"
        L.append(f"| {name[:90]} | {pct} | {age(t)} | {st} |")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "../../config/jobboard.toml"))
    ap.add_argument("--loop", type=int, default=0, help="rebuild every N seconds")
    a = ap.parse_args()
    while True:
        c = tomllib.load(open(a.config, "rb"))
        out = c.get("status_merge", {}).get("out")
        if not out:
            raise SystemExit("set [status_merge] out = ... in the config")
        tmp = out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(build(c))
        os.replace(tmp, out)
        print(time.strftime("%F %T"), "wrote", out, flush=True)
        if not a.loop:
            break
        time.sleep(a.loop)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Save every Samsung Visual Voicemail (com.samsung.vvm) to shared storage, with a manifest.

The app keeps audio private. Its per-message Share button writes
/sdcard/VisualVoiceMail/share/VoiceMail_<share time>.amr. The file name is the share time, so this
script records sender/date/time/duration from the screen for each file it creates.

Taps only by resource id: senders (expand a row), expanded_share, the Inbox/Archive tabs, Back.
It never taps delete. Read-only for the voicemail list.

    python3 scripts/vvm_share_all.py <serial> <out_dir> [Inbox,Archive]   # then adb pull the share folder
"""
import html, os, re, subprocess, sys, time

SER, OUT = sys.argv[1], sys.argv[2]
SHARE = "/sdcard/VisualVoiceMail/share"
os.makedirs(OUT, exist_ok=True)
MAN = os.path.join(OUT, "VOICEMAIL_MANIFEST.tsv")


def sh(*a):
    return subprocess.run(["adb", "-s", SER, "shell", *a], capture_output=True, text=True).stdout


def dump():
    sh("uiautomator", "dump", "/sdcard/ui_vvm.xml")
    x = subprocess.run(["adb", "-s", SER, "exec-out", "cat", "/sdcard/ui_vvm.xml"], capture_output=True, text=True).stdout
    nodes = []
    for nd in re.findall(r"<node [^>]*>", x):
        g = lambda k: html.unescape((re.search(k + r'="([^"]*)"', nd) or [None, ""])[1])
        b = [int(v) for v in re.findall(r"\d+", g("bounds"))]
        nodes.append({"id": g("resource-id").split("/")[-1], "text": g("text"), "desc": g("content-desc"), "b": b})
    return nodes


def center(b):
    return str((b[0] + b[2]) // 2), str((b[1] + b[3]) // 2)


def rows(nodes):
    """Group sender/date/duration/time fields by vertical band."""
    out = []
    for s in [n for n in nodes if n["id"] == "senders"]:
        top = s["b"][1]
        def near(i):  # same row = field starts at or just below the sender line; take the closest
            c = [n for n in nodes if n["id"] == i and -20 <= n["b"][1] - top < 260]
            return min(c, key=lambda n: n["b"][1] - top)["text"] if c else ""
        out.append({"sender": s["text"], "date": near("date"), "time": near("timeView"),
                    "dur": near("duration"), "kind": near("contacttype").strip(" ,"), "b": s["b"]})
    return out


def share_files():
    return set(l.strip() for l in sh("ls", SHARE).splitlines() if l.strip().endswith(".amr"))


def tap(b):
    sh("input", "tap", *center(b))


done, fails = set(), {}
if os.path.exists(MAN):
    for l in open(MAN, encoding="utf-8").read().splitlines()[1:]:
        p = l.split("\t")
        done.add(tuple(p[1:6]))
else:
    open(MAN, "w", encoding="utf-8").write("tab\tsender\tdate\ttime\tduration\tkind\tfile\tsaved_at\n")

TABS = sys.argv[3].split(",") if len(sys.argv) > 3 else ["Inbox", "Archive"]
for tab in TABS:
    t = next((n for n in dump() if n["id"] == "title" and n["text"] == tab), None)
    if not t:
        print("tab not found", tab); continue
    tap(t["b"]); time.sleep(2)
    for _ in range(8):  # start at the top of the list
        sh("input", "swipe", "540", "700", "540", "1800", "300"); time.sleep(0.5)
    stale_scrolls = 0
    while stale_scrolls < 2:
        new_here = 0
        for r in rows(dump()):
            key = (r["sender"], r["date"], r["time"], r["dur"], r["kind"])
            if key in done or r["b"][1] > 1950:
                continue
            before = share_files()
            tap(r["b"]); time.sleep(1.5)
            btn = next((n for n in dump() if n["id"] == "expanded_share"), None)
            if not btn:
                fails[key] = fails.get(key, 0) + 1
                print("no share button for", r["sender"], r["date"], "try", fails[key])
                if fails[key] >= 3:
                    done.add(key)
                    with open(MAN, "a", encoding="utf-8") as fh:
                        fh.write("\t".join([tab, *key, "FAILED", time.strftime("%F %T")]) + "\n")
                continue
            tap(btn["b"]); time.sleep(2.5)
            sh("input", "keyevent", "KEYCODE_BACK"); time.sleep(1)
            if not any(n["id"] == "senders" for n in dump()):   # back closed the app list instead of the sheet
                sh("monkey", "-p", "com.samsung.vvm", "-c", "android.intent.category.LAUNCHER", "1"); time.sleep(3)
            new = sorted(share_files() - before)
            with open(MAN, "a", encoding="utf-8") as fh:
                fh.write("\t".join([tab, *key, ",".join(new) or "NONE", time.strftime("%F %T")]) + "\n")
            done.add(key); new_here += 1
            print(tab, r["date"], r["time"], r["dur"], "->", new or "NONE", flush=True)
            tap(r["b"]); time.sleep(1)   # collapse
            break  # re-dump after every share (layout moves)
        if new_here == 0:
            sh("input", "swipe", "540", "1700", "540", "700", "600"); time.sleep(1.5)
            fresh = [r for r in rows(dump()) if (r["sender"], r["date"], r["time"], r["dur"], r["kind"]) not in done]
            stale_scrolls = 0 if fresh else stale_scrolls + 1
print("done; manifest", MAN)

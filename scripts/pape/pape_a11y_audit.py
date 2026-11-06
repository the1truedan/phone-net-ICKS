#!/usr/bin/env python3
"""P.A.P.E. accessibility audit: every PDF under the given folders, all local, tools in tandem.

    ~/models/pape_tools/.venv/bin/python scripts/pape_a11y_audit.py <folder|pdf> ... [--out DIR] [--juj DIR]

Per unique PDF (sha256 dedupe):
  veraPDF PDF/UA-1     pass/fail, failed rules, failed checks (batched, one Java start per 40 files)
  structure (pikepdf)  tagged (StructTreeRoot + MarkInfo/Marked), /Lang, title + DisplayDocTitle, encrypted
  text (pdftotext)     chars per page, image-only pages (needs OCR), fonts not embedded (pdffonts)
  ada-doc-check        needs_ocr triage (fail-closed) on the extracted text
  origin               .gov domains and agency names found in the first pages + producer/creator, so received
                       agency/government documents can be told apart from our own drafts and printouts
Writes results.tsv, results.jsonl and REPORT.md (counts by origin; every government-sourced PDF that fails, by name).
Reads only. Nothing leaves the Mac. Text content is not copied into the report, only names, counts and domains.
"""
import argparse, hashlib, json, os, re, subprocess, sys, time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.expanduser("~/ada-doc-check"))
try:
    from ada_check.triage import needs_ocr
except Exception:  # ada-doc-check missing: audit still runs
    needs_ocr = None

GOV = re.compile(r"\b((?:[a-z0-9-]+\.)+gov)\b", re.I)
AGENCY = {
    "WI DHS / ForwardHealth": re.compile(r"dhs\.wisconsin\.gov|forwardhealth|wisconsin department of health services", re.I),
    "CMS / Medicare": re.compile(r"\bcms\.gov|medicare\.gov|centers for medicare", re.I),
}
# Your own sources (agencies, providers): ~/.config/pape/agencies.json = {"Name": "regex", ...}. Kept local, never in git.
try:
    _extra = json.load(open(os.path.expanduser("~/.config/pape/agencies.json")))
    AGENCY.update({k: re.compile(v, re.I) for k, v in _extra.items()})
except Exception:
    pass
GOV_AGENCIES = {"WI DHS / ForwardHealth", "CMS / Medicare"}
OWN = re.compile(r"skia|chrom|pandoc|img2pdf|ocrmypdf|wkhtml|brave|reportlab|typst|weasyprint", re.I)
SCANAPP = re.compile(r"camscanner|scansnap|scanner|adobe scan|genius scan|microsoft lens", re.I)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def structure(p):
    import pikepdf
    r = {"encrypted": False}
    try:
        with pikepdf.open(p) as d:
            root = d.Root
            r.update(pages=len(d.pages), tagged=("/StructTreeRoot" in root),
                     marked=bool(root.get("/MarkInfo", {}).get("/Marked", False)) if "/MarkInfo" in root else False,
                     lang=str(root.get("/Lang", "")) or None,
                     title=bool(str(d.docinfo.get("/Title", "")).strip()) if d.docinfo else False,
                     display_title=bool(root.get("/ViewerPreferences", {}).get("/DisplayDocTitle", False)) if "/ViewerPreferences" in root else False,
                     producer=str(d.docinfo.get("/Producer", ""))[:80] if d.docinfo else "",
                     creator=str(d.docinfo.get("/Creator", ""))[:80] if d.docinfo else "")
    except pikepdf.PasswordError:
        r.update(encrypted=True, pages=None)
    except Exception as e:
        r.update(error=f"pikepdf: {e.__class__.__name__}")
    return r


def text_checks(p, pages):
    per = []
    for i in range(1, (pages or 0) + 1):
        t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), p, "-"], capture_output=True, text=True, timeout=60).stdout
        per.append(t)
    chars = [len(t.strip()) for t in per]
    fonts = subprocess.run(["pdffonts", p], capture_output=True, text=True, timeout=60).stdout.splitlines()[2:]
    not_emb = sum(1 for l in fonts if len(l.split()) >= 5 and l.split()[-5] == "no")
    head = "\n".join(per[:3])
    return per, {"chars_per_page": round(sum(chars) / max(1, len(chars))), "image_only_pages": sum(c < 30 for c in chars),
                 "fonts_not_embedded": not_emb}, head


def _lum(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def color_checks(p, pages, maxpages=6):
    """Per page at 50 dpi: dark-background share, red text on it, and the WCAG contrast of that red vs the background.
    Also the lowest text/background contrast seen (median ink color vs median paper color)."""
    import tempfile, glob
    from PIL import Image
    out = {"dark_bg_pages": 0, "red_on_dark_pages": 0, "red_on_dark_min_ratio": None, "min_text_ratio": None}
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-r", "50", "-png", "-l", str(min(pages or 0, maxpages)), p, f"{d}/pg"], capture_output=True, timeout=120)
        for f in sorted(glob.glob(f"{d}/pg*.png")):
            im = Image.open(f).convert("RGB")
            px = list(im.getdata())
            n = len(px)
            dark = [q for q in px if sum(q) < 120]
            light = [q for q in px if sum(q) > 600]
            bg_dark = len(dark) / n > 0.5
            bg = tuple(sorted(c[i] for c in (dark if bg_dark else light or px))[len(dark if bg_dark else light or px) // 2] for i in range(3))
            reds = [q for q in px if q[0] > 110 and q[0] > 2 * q[1] + 20 and q[0] > 2 * q[2] + 20]
            ink = [q for q in px if (sum(q) > 240 if bg_dark else sum(q) < 450)]
            if ink:
                med = tuple(sorted(c[i] for c in ink)[len(ink) // 2] for i in range(3))
                r = round(contrast(med, bg), 2)
                out["min_text_ratio"] = r if out["min_text_ratio"] is None else min(out["min_text_ratio"], r)
            if bg_dark:
                out["dark_bg_pages"] += 1
                if len(reds) > 0.003 * n:
                    out["red_on_dark_pages"] += 1
                    med = tuple(sorted(c[i] for c in reds)[len(reds) // 2] for i in range(3))
                    r = round(contrast(med, bg), 2)
                    out["red_on_dark_min_ratio"] = r if out["red_on_dark_min_ratio"] is None else min(out["red_on_dark_min_ratio"], r)
                    out["red_rgb"] = "#%02x%02x%02x" % med
    return out


def origin(head, name, producer, creator):
    gov = sorted({g.lower() for g in GOV.findall(head + " " + name)})
    ag = [k for k, rx in AGENCY.items() if rx.search(head) or rx.search(name)]
    meta = f"{producer} {creator}"
    made = "scan app" if SCANAPP.search(meta) else ("our tools" if OWN.search(meta) else ("other" if meta.strip() else "unknown"))
    senders = [a for a in ag if a not in GOV_AGENCIES]
    if senders:  # an agency's own document that cites .gov (e.g. a hospice form quoting cms.gov) stays "agency"
        cls = "agency"
    elif gov or ag:
        cls = "government"
    elif made == "our tools":
        cls = "our drafts"
    else:
        cls = "other"
    return {"origin": cls, "gov_domains": gov, "agencies": ag, "made_with": made}


def verapdf_batch(paths):
    out = {}
    x = subprocess.run(["verapdf", "-f", "ua1", "--format", "xml", *paths], capture_output=True, text=True, timeout=3600).stdout
    for job in re.findall(r"<job>.*?</job>", x, re.S):
        nm = re.search(r"<item[^>]*>\s*<name>(.*?)</name>", job, re.S)
        if not nm:
            continue
        path = nm.group(1).strip()
        comp = re.search(r'isCompliant="(true|false)"', job)
        rules = re.findall(r'<rule [^>]*clause="([^"]+)"[^>]*testNumber="(\d+)"[^>]*status="failed"[^>]*failedChecks="(\d+)"', job)
        err = re.search(r"<taskException[^>]*>(.*?)</taskException>", job, re.S) or re.search(r"<exceptionMessage>(.*?)</", job, re.S)
        out[path] = {"ua1": None if comp is None else comp.group(1) == "true",
                     "ua1_failed_rules": [f"{c}-{n}" for c, n, _ in rules], "ua1_failed_checks": sum(int(k) for *_, k in rules),
                     "ua1_error": (err.group(1).strip()[:120] if (err and comp is None) else None)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", default=os.path.expanduser(os.environ.get("PAPE_OUT", "~/pape_scans")) + f"/_a11y_audit/{time.strftime('%Y-%m-%d_%H%M')}")
    ap.add_argument("--juj", help="J.U.J. job folder (pause / stop between batches)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    files = []
    for p in a.paths:
        if os.path.isfile(p):
            files.append(p)
        else:
            for root, _, fs in os.walk(p):
                files += [os.path.join(root, f) for f in fs if f.lower().endswith(".pdf") and not f.startswith("._")]
    seen, uniq, dupes = {}, [], 0
    for f in sorted(files):
        h = sha(f)
        if h in seen:
            dupes += 1; continue
        seen[h] = f; uniq.append((f, h))
    print(f"{len(files)} PDFs, {len(uniq)} unique ({dupes} duplicates skipped)", flush=True)
    J = None
    if a.juj:
        sys.path.insert(0, os.path.expanduser("~/juj")); import juj as J
        J.card(a.juj, f"P.A.P.E. accessibility audit of {len(uniq)} unique PDFs -> {a.out}", [f"batch{i}" for i in range(0, len(uniq), 40)],
               actions=("pause", "resume", "stop"))
    rows = []
    for i in range(0, len(uniq), 40):
        if J and J.steer(a.juj)["stop"]:
            break
        chunk = uniq[i:i + 40]
        vp = verapdf_batch([f for f, _ in chunk])
        for f, h in chunk:
            r = {"path": f, "sha256": h, "bytes": os.path.getsize(f)}
            r.update(structure(f))
            if not r.get("encrypted") and r.get("pages"):
                per, tc, head = text_checks(f, r["pages"])
                r.update(tc)
                try:
                    r.update(color_checks(f, r["pages"]))
                except Exception as e:
                    r["color_error"] = e.__class__.__name__
                r.update(origin(head, os.path.basename(f), r.get("producer", ""), r.get("creator", "")))
                if needs_ocr:
                    try:
                        n = needs_ocr(f, text="\n".join(per))
                        r["ada_needs_ocr"], r["ada_decidable"] = n.get("needs_ocr"), n.get("decidable")
                    except Exception as e:
                        r["ada_error"] = e.__class__.__name__
            else:
                r.update(origin("", os.path.basename(f), r.get("producer", ""), r.get("creator", "")))
            r.update(vp.get(f, {"ua1": None, "ua1_error": "no veraPDF result"}))
            rows.append(r)
        print(f"  {min(i + 40, len(uniq))}/{len(uniq)}", flush=True)
        if J:
            J.progress(a.juj, done=f"batch{i}")
    with open(f"{a.out}/results.jsonl", "w") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in rows)
    cols = ["origin", "ua1", "red_on_dark_pages", "red_on_dark_min_ratio", "dark_bg_pages", "min_text_ratio", "tagged", "lang", "title", "image_only_pages", "chars_per_page", "fonts_not_embedded",
            "ada_needs_ocr", "ua1_failed_checks", "gov_domains", "agencies", "made_with", "pages", "path"]
    with open(f"{a.out}/results.tsv", "w") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(",".join(v) if isinstance(v, list) else str(v) for v in (r.get(c) for c in cols)) + "\n")
    # report
    by = defaultdict(list)
    for r in rows:
        by[r.get("origin", "other")].append(r)
    L = [f"# ♿ P.A.P.E. accessibility audit · {time.strftime('%Y-%m-%d %H:%M')}", "",
         f"{len(files)} PDFs scanned · {len(uniq)} unique · {dupes} duplicates skipped · tools: veraPDF PDF/UA-1, pikepdf structure, "
         "pdftotext / pdffonts, ada-doc-check triage", "",
         "| Origin | PDFs | PDF/UA-1 pass | Tagged | Has /Lang | Has title | Needs OCR (image-only pages) | Fonts not embedded |",
         "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for k in ("government", "agency", "other", "our drafts"):
        rs = by.get(k, [])
        if not rs:
            continue
        L.append(f"| {k} | {len(rs)} | {sum(r.get('ua1') is True for r in rs)} | {sum(bool(r.get('tagged')) for r in rs)} | "
                 f"{sum(bool(r.get('lang')) for r in rs)} | {sum(bool(r.get('title')) for r in rs)} | "
                 f"{sum((r.get('image_only_pages') or 0) > 0 for r in rs)} | {sum((r.get('fonts_not_embedded') or 0) > 0 for r in rs)} |")
    rule_counts = Counter(x for r in rows for x in r.get("ua1_failed_rules", []))
    L += ["", "**Most-failed PDF/UA-1 rules** (ISO 14289-1 clause-test): " + ", ".join(f"{k} ×{v}" for k, v in rule_counts.most_common(8)), ""]
    gov = sorted(by.get("government", []), key=lambda r: r["path"])
    L += [f"## 🏛️ Government-sourced PDFs ({len(gov)})", "", "| File | .gov / agency | PDF/UA-1 | Tagged | Lang | Image-only pages | Failed checks |", "|---|---|---|---|---|---:|---:|"]
    for r in gov:
        L.append(f"| {os.path.basename(r['path'])[:70]} | {', '.join(r.get('gov_domains') or r.get('agencies') or [])[:60]} | "
                 f"{'✅' if r.get('ua1') else '❌' if r.get('ua1') is False else '—'} | {'yes' if r.get('tagged') else 'no'} | "
                 f"{r.get('lang') or '—'} | {r.get('image_only_pages', '—')} | {r.get('ua1_failed_checks', '—')} |")
    rod = [r for r in rows if r.get("red_on_dark_pages")]
    L += ["", f"## 🟥⬛ Red text on a dark background ({len(rod)} PDFs)", "",
          "WCAG 2.1 AA needs 4.5:1 for normal text (3:1 for large). Pure red #ff0000 on black is 5.25:1, so it can pass by the number,",
          "but darker reds fail, and for people with red-weak color vision (protanopia) red looks much darker, so red on black can",
          "nearly vanish. Best practice: light text on dark, or dark text on light; don't carry meaning by red alone (WCAG 1.4.1).", "",
          "| File | Origin | Pages red-on-dark | Red | Contrast | WCAG AA normal text |", "|---|---|---:|---|---:|---|"]
    for r in sorted(rod, key=lambda r: r.get("red_on_dark_min_ratio") or 0):
        ratio = r.get("red_on_dark_min_ratio") or 0
        L.append(f"| {os.path.basename(r['path'])[:60]} | {r.get('origin')} | {r['red_on_dark_pages']} | {r.get('red_rgb', '')} | {ratio}:1 | "
                 f"{'✅ passes 4.5:1' if ratio >= 4.5 else '⚠️ large text only (3:1)' if ratio >= 3 else '❌ fails'} |")
    ag = by.get("agency", [])
    L += ["", f"## 🏢 Agency PDFs ({len(ag)}): " + ", ".join(f"{k} {v}" for k, v in Counter(x for r in ag for x in r.get('agencies', [])).most_common()),
          f"PDF/UA-1 pass {sum(r.get('ua1') is True for r in ag)} of {len(ag)} · tagged {sum(bool(r.get('tagged')) for r in ag)} · "
          f"image-only (scans without text) {sum((r.get('image_only_pages') or 0) > 0 for r in ag)}", "",
          "Notes: a machine PASS is necessary, not sufficient (reading order, alt-text quality and meaning need a human). "
          "Our own scans and printouts are listed under 'other' / 'our drafts' and are fixed by the P.A.P.E. tagged-PDF step.", ""]
    open(f"{a.out}/REPORT.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L[:20])); print(a.out)


if __name__ == "__main__":
    main()

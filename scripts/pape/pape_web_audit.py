#!/usr/bin/env python3
"""P.A.P.E. website audit: public pages + the PDFs they link to, WCAG 2.1 AA, all local tools.

    ~/models/pape_tools/.venv/bin/python scripts/pape_web_audit.py https://www.example.org https://www.example.gov --out DIR

Per site: the home page plus up to --pages same-site links, preferring member / rights / grievance / appeal / contact /
accessibility / forms / caregiver / SDS / IRIS pages. Each page: pa11y with both engines (HTML_CodeSniffer + axe-core),
WCAG2AA. Each linked PDF (up to --pdfs): saved, then veraPDF PDF/UA-1 + structure + contrast (pape_a11y_audit).
Read-only: plain GETs, no forms, no logins. Writes pages.jsonl, pdfs.jsonl, REPORT.md.
"""
import argparse, html, json, os, re, subprocess, sys, time, urllib.parse, urllib.request
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util as _u
_s = _u.spec_from_file_location("audit", os.path.join(HERE, "pape_a11y_audit.py")); audit = _u.module_from_spec(_s); _s.loader.exec_module(audit)
NODE = os.path.expanduser("~/models/pape_tools/node")
UA = "Mozilla/5.0 (Macintosh; accessibility audit; P.A.P.E.)"
PRIORITY = re.compile(r"member|right|grievance|appeal|complain|contact|accessib|ada|nondiscrim|form|caregiver|self.?direct|sds|iris|provider|privacy|notice|handbook|pay|timesheet|enroll", re.I)
# WCAG success criteria for the codes pa11y / axe report most often, in plain words
PLAIN = {
    "1_1_1": "1.1.1 images need text alternatives", "1_3_1": "1.3.1 structure (headings, labels, tables) must be real markup",
    "1_4_3": "1.4.3 text contrast at least 4.5:1", "2_4_4": "2.4.4 link text must say where it goes",
    "4_1_2": "4.1.2 controls need a name and role", "2_4_2": "2.4.2 pages need a title", "3_1_1": "3.1.1 page language",
    "color-contrast": "1.4.3 text contrast at least 4.5:1", "image-alt": "1.1.1 images need text alternatives",
    "link-name": "2.4.4 / 4.1.2 links need readable names", "label": "1.3.1 / 4.1.2 form fields need labels",
    "button-name": "4.1.2 buttons need readable names", "html-has-lang": "3.1.1 page language", "frame-title": "4.1.2 frames need titles",
}


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        data = r.read()
        return r.geturl(), (data if binary else data.decode("utf-8", "replace"))


def links(base, page):
    out = set()
    for h in re.findall(r'href=["\']([^"\'#]+)', page, re.I):
        u = urllib.parse.urljoin(base, html.unescape(h).strip())
        if u.startswith("http"):
            out.add(u.split("#")[0])
    return out


def pa11y(url):
    r = subprocess.run(["npx", "--prefix", NODE, "pa11y", "--standard", "WCAG2AA", "--runner", "htmlcs", "--runner", "axe",
                        "--reporter", "json", "--timeout", "60000", url], capture_output=True, text=True, timeout=180, cwd=NODE)
    try:
        issues = json.loads(r.stdout or "[]")
    except ValueError:
        return {"error": (r.stderr or r.stdout)[-200:]}
    codes = Counter()
    for i in issues:
        c = i.get("code", "")
        m = re.search(r"Guideline\d_\d\.(\d_\d_\d)", c)
        codes[m.group(1) if m else c] += 1
    return {"issues": len(issues), "errors": sum(i.get("type") == "error" for i in issues), "codes": dict(codes.most_common(12))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sites", nargs="+"); ap.add_argument("--out", required=True)
    ap.add_argument("--pages", type=int, default=14); ap.add_argument("--pdfs", type=int, default=10)
    a = ap.parse_args()
    os.makedirs(f"{a.out}/pdfs", exist_ok=True)
    allpages, allpdfs = [], []
    for site in a.sites:
        host = urllib.parse.urlparse(site).netloc.replace("www.", "")
        try:
            final, home = get(site)
        except Exception as e:
            print(site, "unreachable", e); continue
        ls = links(final, home)
        same = [u for u in ls if host in urllib.parse.urlparse(u).netloc and not u.lower().endswith(".pdf")]
        same = sorted(set(same), key=lambda u: (not PRIORITY.search(u), len(u)))[: a.pages]
        pdfs = [u for u in ls if u.lower().split("?")[0].endswith(".pdf")]
        # one level deeper for PDFs (forms and notices usually sit on inner pages)
        for u in same:
            try:
                f2, p2 = get(u)
                pdfs += [x for x in links(f2, p2) if x.lower().split("?")[0].endswith(".pdf")]
            except Exception:
                pass
        pdfs = sorted(set(pdfs), key=lambda u: (not PRIORITY.search(u), u))[: a.pdfs]
        for u in [final] + [x for x in same if x != final]:
            r = {"site": host, "url": u, **pa11y(u)}
            allpages.append(r); print(f"page {r.get('issues', 'ERR'):>4} issues  {u[:90]}", flush=True)
            with open(f"{a.out}/pages.jsonl", "a") as fh:
                fh.write(json.dumps(r) + "\n")
        for u in pdfs:
            name = re.sub(r"[^\w.\-]+", "_", urllib.parse.unquote(u.split("/")[-1].split("?")[0]))[:90]
            p = f"{a.out}/pdfs/{host}__{name}"
            try:
                _, data = get(u, binary=True)
                open(p, "wb").write(data)
                s = audit.structure(p); r = {"site": host, "url": u, "file": p, **{k: s.get(k) for k in ("pages", "tagged", "lang", "title", "encrypted")}}
                if s.get("pages") and not s.get("encrypted"):
                    _, tc, _ = audit.text_checks(p, s["pages"]); r.update(tc)
                    try:
                        r.update(audit.color_checks(p, s["pages"]))
                    except Exception:
                        pass
                r.update(audit.verapdf_batch([p]).get(p, {}))
            except Exception as e:
                r = {"site": host, "url": u, "error": f"{e.__class__.__name__}"}
            allpdfs.append(r); print(f"pdf  {str(r.get('ua1')):>5}  {u[:90]}", flush=True)
            with open(f"{a.out}/pdfs.jsonl", "a") as fh:
                fh.write(json.dumps(r) + "\n")
    L = [f"# 🌐 P.A.P.E. website accessibility audit · {time.strftime('%Y-%m-%d %H:%M')}", "",
         "Standard: WCAG 2.1 Level AA (pages, via pa11y: HTML_CodeSniffer + axe-core) and PDF/UA-1 (linked PDFs, via veraPDF).",
         "Automated checks find a subset of barriers; a passing page still needs manual review (keyboard, screen reader).", ""]
    for site in sorted({p["site"] for p in allpages} | {p["site"] for p in allpdfs}):
        ps = [p for p in allpages if p["site"] == site and "issues" in p]
        ds = [p for p in allpdfs if p["site"] == site and "error" not in p]
        codes = Counter()
        for p in ps:
            codes.update(p["codes"])
        L += [f"## {site}", "", f"**Pages checked:** {len(ps)} · **issues found:** {sum(p['issues'] for p in ps)} "
              f"(errors {sum(p['errors'] for p in ps)}) · **pages with at least one error:** {sum(p['errors'] > 0 for p in ps)}", "",
              "| Most common problem | Count |", "|---|---:|"]
        L += [f"| {PLAIN.get(c, c)} | {n} |" for c, n in codes.most_common(8)]
        L += ["", "| Page | Issues | Errors |", "|---|---:|---:|"] + [f"| {p['url'][:80]} | {p['issues']} | {p['errors']} |" for p in ps]
        L += ["", f"**Linked PDFs checked:** {len(ds)} · PDF/UA-1 pass {sum(d.get('ua1') is True for d in ds)} · tagged {sum(bool(d.get('tagged')) for d in ds)} · "
              f"scans without text {sum((d.get('image_only_pages') or 0) > 0 for d in ds)}", "",
              "| PDF | PDF/UA-1 | Tagged | Language | Title | Lowest contrast |", "|---|---|---|---|---|---:|"]
        L += [f"| {d['url'].split('/')[-1][:60]} | {'✅' if d.get('ua1') else '❌'} ({d.get('ua1_failed_checks', '—')}) | {'yes' if d.get('tagged') else 'no'} | "
              f"{d.get('lang') or '—'} | {'yes' if d.get('title') else 'no'} | {d.get('min_text_ratio') or '—'} |" for d in ds]
        L.append("")
    open(f"{a.out}/REPORT.md", "w").write("\n".join(L) + "\n")
    print(f"{a.out}/REPORT.md")


if __name__ == "__main__":
    main()

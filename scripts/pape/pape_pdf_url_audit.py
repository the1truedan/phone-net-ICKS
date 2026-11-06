#!/usr/bin/env python3
"""P.A.P.E.: audit a list of public PDF URLs (official sources) for PDF/UA-1 + structure + contrast, citing each source.

    ~/models/pape_tools/.venv/bin/python scripts/pape_pdf_url_audit.py urls.txt --out DIR

urls.txt: one `label | url` per line (# comments ok). Plain GETs of public documents only. Writes pdfs.jsonl + REPORT.md.
"""
import argparse, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util as _u
_s = _u.spec_from_file_location("audit", os.path.join(HERE, "pape_a11y_audit.py")); audit = _u.module_from_spec(_s); _s.loader.exec_module(audit)
UA = "Mozilla/5.0 (Macintosh; accessibility audit; P.A.P.E.)"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("urls"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(f"{a.out}/pdfs", exist_ok=True)
    rows = []
    for line in open(a.urls):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        label, url = [x.strip() for x in line.split("|", 1)]
        p = f"{a.out}/pdfs/{re.sub(r'[^\w.-]+', '_', label)[:60]}.pdf"
        r = {"label": label, "url": url}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read(); r["final_url"] = resp.geturl()
            if not data.startswith(b"%PDF"):
                r["error"] = "not a PDF (moved or HTML page)"
            else:
                open(p, "wb").write(data); r["bytes"] = len(data)
                s = audit.structure(p); r.update({k: s.get(k) for k in ("pages", "tagged", "lang", "title", "producer")})
                if s.get("pages") and not s.get("encrypted"):
                    _, tc, _ = audit.text_checks(p, s["pages"]); r.update(tc)
                    try:
                        r.update(audit.color_checks(p, s["pages"]))
                    except Exception:
                        pass
                r.update(audit.verapdf_batch([p]).get(p, {}))
        except Exception as e:
            r["error"] = f"{e.__class__.__name__}: {str(e)[:80]}"
        rows.append(r)
        print(f"{str(r.get('ua1', 'ERR')):5} {r.get('ua1_failed_checks', ''):>7}  {label[:60]}  {r.get('error', '')}", flush=True)
    with open(f"{a.out}/pdfs.jsonl", "w") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in rows)
    ok = [r for r in rows if "error" not in r]
    L = [f"# ♿ Official caregiving / hospice PDFs: accessibility check · {time.strftime('%Y-%m-%d %H:%M')}", "",
         f"{len(ok)} PDFs checked (veraPDF PDF/UA-1, structure, contrast) · {sum(r.get('ua1') is True for r in ok)} pass · "
         f"{len(rows) - len(ok)} could not be fetched", "",
         "| Document | Source | PDF/UA-1 | Failed checks | Tagged | Language | Title | Lowest contrast |", "|---|---|---|---:|---|---|---|---:|"]
    for r in ok:
        L.append(f"| {r['label']} | [{re.sub(r'^https?://(www\\.)?', '', r['url']).split('/')[0]}]({r['url']}) | {'✅' if r.get('ua1') else '❌'} | "
                 f"{r.get('ua1_failed_checks', '—'):,} | {'yes' if r.get('tagged') else 'no'} | {r.get('lang') or '—'} | "
                 f"{'yes' if r.get('title') else 'no'} | {r.get('min_text_ratio') or '—'}:1 |" if isinstance(r.get('ua1_failed_checks'), int) else
                 f"| {r['label']} | [{r['url'].split('/')[2]}]({r['url']}) | {'✅' if r.get('ua1') else '❌'} | — | {'yes' if r.get('tagged') else 'no'} | {r.get('lang') or '—'} | {'yes' if r.get('title') else 'no'} | {r.get('min_text_ratio') or '—'}:1 |")
    bad = [r for r in rows if "error" in r]
    if bad:
        L += ["", "Could not fetch: " + "; ".join(f"{r['label']} ({r['error']})" for r in bad)]
    open(f"{a.out}/REPORT.md", "w").write("\n".join(L) + "\n")
    print(f"{a.out}/REPORT.md")


if __name__ == "__main__":
    main()

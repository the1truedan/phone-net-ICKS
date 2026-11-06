#!/usr/bin/env python3
"""P.A.P.E. full treatment (Paper Accessibility, Parsing & Evidence) with the A.I.D.A. greatest hits merged in.

    ~/models/pape_tools/.venv/bin/python scripts/pape_process.py <pdf|folder> ... --out DIR [--juj DIR] [--limit N]

Per PDF (sha256-deduped), into DIR/<sha12>_<name>/:
  original.pdf            byte copy (the evidence copy; never changed)
  searchable.pdf          ocrmypdf only when pages have no text layer (rotation threshold 1, deskew)
  accessible.pdf          tagged PDF/UA-1 copy (scripts/pape_tag_pdf.py: headings, lists, language, title)
  briefs/                 A.I.D.A. layman relay: caregiver brief (actions, dates, money) + gentle plain-language brief
  REPORT.md               before -> after: veraPDF PDF/UA-1, tags, language, title, scans without text, contrast, A.I.D.A. gate
Batch: DIR/INDEX.md, DIR/results.jsonl, DIR/SHA256SUMS.txt, DIR/custody_log.txt. All local; rule-based briefs, no LLM.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # repo root: optional A.I.D.A. agents (aida-complex-doc-lab); skipped if missing
import importlib.util as _u
_s = _u.spec_from_file_location("audit", os.path.join(HERE, "pape_a11y_audit.py")); audit = _u.module_from_spec(_s); _s.loader.exec_module(audit)
PY = os.path.expanduser("~/models/pape_tools/.venv/bin/python")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def check(pdf):
    s = audit.structure(pdf)
    r = {"tagged": s.get("tagged"), "lang": s.get("lang"), "title": s.get("title"), "pages": s.get("pages"), "encrypted": s.get("encrypted")}
    if s.get("pages") and not s.get("encrypted"):
        per, tc, _ = audit.text_checks(pdf, s["pages"])
        r.update(tc)
        try:
            r.update(audit.color_checks(pdf, s["pages"]))
        except Exception:
            pass
        r["text"] = "\n".join(per)
    r.update(audit.verapdf_batch([pdf]).get(pdf, {}))
    return r


def aida(text, label, outdir):
    out = {}
    try:
        from agents.aida.layman_relay import dual_audience_summary, write_dual_briefs
        dual = dual_audience_summary(text, source_label=label)
        out["briefs"] = write_dual_briefs(dual, os.path.join(outdir, "briefs"), "brief")
        out["doc_kind"] = dual.get("doc_kind") or dual.get("kind")
    except Exception as e:
        out["briefs_error"] = f"{e.__class__.__name__}: {e}"[:160]
    try:
        from agents.aida.document_accessibility_gate import accessibility_gate
        g = accessibility_gate(path=os.path.join(outdir, "accessible.pdf"))
        out["gate"] = {k: g.get(k) for k in ("ok", "wcag_score", "flags")}
    except Exception as e:
        out["gate_error"] = f"{e.__class__.__name__}"
    return out


def row(label, r):
    v = r.get("ua1")
    return (f"| {label} | {'✅ pass' if v else '❌ fail' if v is False else '—'} ({r.get('ua1_failed_checks', '—')} checks) | "
            f"{'yes' if r.get('tagged') else 'no'} | {r.get('lang') or '—'} | {'yes' if r.get('title') else 'no'} | "
            f"{r.get('image_only_pages', '—')} | {r.get('min_text_ratio') or '—'} |")


def treat(src, h, outroot):
    name = re.sub(r"[^\w.\-]+", "_", os.path.basename(src))[:80]
    d = os.path.join(outroot, f"{h[:12]}_{name[:-4] if name.lower().endswith('.pdf') else name}")
    os.makedirs(d, exist_ok=True)
    orig = os.path.join(d, "original.pdf")
    shutil.copy2(src, orig)
    before = check(orig)
    rec = {"source": src, "sha256": h, "dir": d, "before": {k: v for k, v in before.items() if k != "text"}}
    if before.get("encrypted"):
        rec["skipped"] = "encrypted"; return rec
    work, text = orig, before.get("text", "")
    if (before.get("image_only_pages") or 0) > 0 or len(text.strip()) < 100:
        sp = os.path.join(d, "searchable.pdf")
        r = subprocess.run(["ocrmypdf", "-q", "--skip-text", "--rotate-pages", "--rotate-pages-threshold", "1", "--deskew",
                            "--optimize", "1", "-l", "eng", orig, sp], capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(sp):
            work = sp
            text = subprocess.run(["pdftotext", sp, "-"], capture_output=True, text=True).stdout
            rec["ocr"] = "done"
        else:
            rec["ocr"] = f"failed: {r.stderr[-160:]}"
    title = re.sub(r"[_\-]+", " ", os.path.basename(src)[:-4]).strip()
    acc = os.path.join(d, "accessible.pdf")
    r = subprocess.run([PY, os.path.join(HERE, "pape_tag_pdf.py"), work, acc, "--title", title], capture_output=True, text=True, timeout=600)
    after = check(acc) if os.path.exists(acc) else {"ua1": None, "ua1_error": f"tag failed: {r.stderr[-160:]}"}
    rec["after"] = {k: v for k, v in after.items() if k != "text"}
    rec["aida"] = aida(text, os.path.basename(src), d)
    L = [f"# 📜 P.A.P.E. · {os.path.basename(src)}", "", f"sha256 `{h}` · source `{src}`", "",
         "| Copy | PDF/UA-1 | Tagged | Language | Title | Pages without text | Lowest contrast |", "|---|---|---|---|---|---:|---:|",
         row("original", before), row("accessible", after), "",
         f"- OCR: {rec.get('ocr', 'not needed')}",
         f"- A.I.D.A. kind: {rec['aida'].get('doc_kind', '—')} · gate: {rec['aida'].get('gate') or rec['aida'].get('gate_error')}",
         f"- Briefs: {', '.join(os.path.relpath(p, d) for p in (rec['aida'].get('briefs') or {}).values()) or rec['aida'].get('briefs_error', '—')}",
         "", "Machine pass = minimum. Reading order and meaning still need a human look."]
    open(os.path.join(d, "REPORT.md"), "w").write("\n".join(L) + "\n")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+"); ap.add_argument("--out", required=True)
    ap.add_argument("--juj"); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    files = []
    for p in a.paths:
        if os.path.isfile(p):
            files.append(p)
        else:
            for root, _, fs in os.walk(p):
                files += [os.path.join(root, f) for f in sorted(fs) if f.lower().endswith(".pdf") and not f.startswith("._")]
    seen, todo = set(), []
    for f in files:
        h = sha(f)
        if h not in seen:
            seen.add(h); todo.append((f, h))
    if a.limit:
        todo = todo[: a.limit]
    J = None
    if a.juj:
        sys.path.insert(0, os.path.expanduser("~/juj")); import juj as J
        J.card(a.juj, f"P.A.P.E. full treatment of {len(todo)} PDFs -> {a.out}", [os.path.basename(f) for f, _ in todo], actions=("pause", "resume", "stop", "skip"))
    print(f"{len(files)} PDFs, {len(todo)} unique", flush=True)
    done = []
    for i, (f, h) in enumerate(todo, 1):
        if J:
            s = J.steer(a.juj)
            if s["stop"]:
                break
            if os.path.basename(f) in s["skip"]:
                continue
        t0 = time.time()
        try:
            rec = treat(f, h, a.out)
        except Exception as e:
            rec = {"source": f, "sha256": h, "error": f"{e.__class__.__name__}: {e}"[:200]}
        rec["secs"] = round(time.time() - t0, 1)
        done.append(rec)
        with open(os.path.join(a.out, "results.jsonl"), "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        b, af = rec.get("before", {}), rec.get("after", {})
        print(f"{i}/{len(todo)} {rec['secs']:6.1f}s  {b.get('ua1')}->{af.get('ua1')}  {os.path.basename(f)[:60]}", flush=True)
        if J:
            J.progress(a.juj, done=os.path.basename(f))
    ok = [r for r in done if "after" in r]
    L = ["# 📜 P.A.P.E. full treatment", "", f"{time.strftime('%Y-%m-%d %H:%M')} · {len(done)} PDFs · tools: ocrmypdf, P.A.P.E. tagger, veraPDF, A.I.D.A. layman relay + gate", "",
         "| | Before | After |", "|---|---:|---:|",
         f"| ✅ PDF/UA-1 pass | {sum(r['before'].get('ua1') is True for r in ok)} | {sum(r['after'].get('ua1') is True for r in ok)} |",
         f"| 🏷️ Tagged | {sum(bool(r['before'].get('tagged')) for r in ok)} | {sum(bool(r['after'].get('tagged')) for r in ok)} |",
         f"| 🗣️ Language set | {sum(bool(r['before'].get('lang')) for r in ok)} | {sum(bool(r['after'].get('lang')) for r in ok)} |",
         f"| 🖼️ Pages without text | {sum(r['before'].get('image_only_pages') or 0 for r in ok)} | {sum(r['after'].get('image_only_pages') or 0 for r in ok)} |",
         f"| 📝 A.I.D.A. briefs written | — | {sum(bool(r.get('aida', {}).get('briefs')) for r in ok)} |",
         "", f"OCR run on {sum(r.get('ocr') == 'done' for r in ok)} · errors {sum('error' in r for r in done)} · encrypted skipped {sum(r.get('skipped') == 'encrypted' for r in done)}"]
    open(os.path.join(a.out, "INDEX.md"), "w").write("\n".join(L) + "\n")
    with open(os.path.join(a.out, "SHA256SUMS.txt"), "w") as fh:
        for root, _, fs in os.walk(a.out):
            for f in sorted(fs):
                if f not in ("SHA256SUMS.txt",):
                    p = os.path.join(root, f); fh.write(f"{sha(p)}  {os.path.relpath(p, a.out)}\n")
    with open(os.path.join(a.out, "custody_log.txt"), "a") as fh:
        fh.write(f"{time.strftime('%F %T %Z')} P.A.P.E. full treatment: {len(done)} PDFs (copies; originals untouched) -> {a.out}\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()

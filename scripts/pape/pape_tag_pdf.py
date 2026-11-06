#!/usr/bin/env python3
"""P.A.P.E. tagged-PDF step: searchable scan PDF -> accessible tagged PDF (PDF/UA-1 target). All local.

    ~/models/pape_tools/.venv/bin/python scripts/pape_tag_pdf.py in.pdf [out.tagged.pdf] [--title "…"] [--lang en-US]

1. text per page (pdftotext; the OCR layer ocrmypdf made)
2. structure: title (first strong line), headings (short ALL-CAPS lines, "Step N", "*QUESTION N", lines ending ':'),
   lists (bullet glyphs OCR makes: • ¢ « e * ° -), paragraphs (joined wrapped lines); one <section> per page with an
   "Page N of M" heading so page references still work
3. print a TAGGED PDF with headless Chromium (Brave): --export-tagged-pdf + document outline
4. pikepdf: XMP dc:title + pdfuaid:part=1, /Lang, ViewerPreferences/DisplayDocTitle, MarkInfo/Marked
5. veraPDF PDF/UA-1 check; the result is printed
The original scan PDF is never changed: the tagged PDF is the accessible copy, the scan stays the evidence copy.
"""
import argparse, html, os, re, subprocess, sys, tempfile

BRAVE = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
BULLET = re.compile(r"^\s*(?:[•¢«°*·\-–]|e(?=\s+[A-Z]))\s+")


def pages_text(pdf):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
    return [subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), pdf, "-"], capture_output=True, text=True).stdout for i in range(1, n + 1)]


def is_heading(line):
    s = line.strip()
    if not s or len(s) > 70:
        return False
    letters = [c for c in s if c.isalpha()]
    return (len(letters) >= 4 and sum(c.isupper() for c in letters) / len(letters) > 0.8) \
        or re.match(r"^(\*?QUESTION\s+\d+|Step\s+\d+\b|Details\s*-\s*Step)", s, re.I) is not None \
        or (s.endswith(":") and len(s.split()) <= 6)


def to_html(pages, title, lang):
    out = []
    for i, t in enumerate(pages, 1):
        out.append(f'<section aria-label="Page {i} of {len(pages)}"><h2 class="pg">Page {i} of {len(pages)}</h2>')
        para, items = [], []

        def flush():
            if para:
                out.append(f"<p>{html.escape(' '.join(para))}</p>"); para.clear()
            if items:
                out.append("<ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in items) + "</ul>"); items.clear()
        for line in t.splitlines():
            s = line.strip()
            if not s:
                flush(); continue
            if BULLET.match(s):
                if para:
                    out.append(f"<p>{html.escape(' '.join(para))}</p>"); para.clear()
                items.append(BULLET.sub("", s)); continue
            if is_heading(s):
                flush(); out.append(f"<h3>{html.escape(s.rstrip(':'))}</h3>"); continue
            if items:  # wrapped continuation of the last bullet
                items[-1] += " " + s; continue
            para.append(s)
        flush()
        out.append("</section>")
    css = ("body{font-family:Georgia,serif;font-size:12pt;line-height:1.45;margin:0}h1{font-size:18pt}"
           "h2.pg{font-size:10pt;color:#555;border-top:1px solid #999;padding-top:4pt;margin-top:18pt}"
           "h3{font-size:13pt;margin:12pt 0 4pt}@page{margin:0.8in}")
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
            f"<style>{css}</style></head><body><main><h1>{html.escape(title)}</h1>{''.join(out)}</main></body></html>")


def finish(pdf, title, lang):
    import pikepdf
    with pikepdf.open(pdf, allow_overwriting_input=True) as p:
        with p.open_metadata(set_pikepdf_as_editor=False) as m:
            m["dc:title"] = title
            m.register_xml_namespace("http://www.aiim.org/pdfua/ns/id/", "pdfuaid")
            m["pdfuaid:part"] = "1"
        p.Root.Lang = pikepdf.String(lang)
        p.Root.ViewerPreferences = pikepdf.Dictionary(DisplayDocTitle=True)
        p.Root.MarkInfo = pikepdf.Dictionary(Marked=True)
        # Chromium writes non-standard types (Strong, Em, ...): map them so PDF/UA 7.1-5 holds
        std = {"Document", "Part", "Art", "Sect", "Div", "BlockQuote", "Caption", "TOC", "TOCI", "Index", "NonStruct", "Private",
               "P", "H", "H1", "H2", "H3", "H4", "H5", "H6", "L", "LI", "Lbl", "LBody", "Table", "TR", "TH", "TD", "THead", "TBody",
               "TFoot", "Span", "Quote", "Note", "Reference", "BibEntry", "Code", "Link", "Annot", "Ruby", "RB", "RT", "RP",
               "Warichu", "WT", "WP", "Figure", "Formula", "Form"}
        seen, stack = set(), [p.Root.get("/StructTreeRoot")]
        while stack:
            n = stack.pop()
            if isinstance(n, pikepdf.Dictionary):
                if "/S" in n:
                    seen.add(str(n.S)[1:])
                k = n.get("/K")
                stack += list(k) if isinstance(k, pikepdf.Array) else ([k] if k is not None else [])
            elif isinstance(n, pikepdf.Array):
                stack += list(n)
        extra = {t: ("Div" if t in ("Section", "Aside", "Nav", "Main", "Header", "Footer") else "Span") for t in seen - std}
        if extra and "/StructTreeRoot" in p.Root:
            rm = p.Root.StructTreeRoot.get("/RoleMap", pikepdf.Dictionary())
            for t, m in extra.items():
                rm[pikepdf.Name("/" + t)] = pikepdf.Name("/" + m)
            p.Root.StructTreeRoot.RoleMap = rm
        p.docinfo["/Title"] = title
        p.save(pdf)


def verapdf(pdf):
    x = subprocess.run(["verapdf", "-f", "ua1", "--format", "xml", pdf], capture_output=True, text=True).stdout
    ok = 'isCompliant="true"' in x
    failed = re.findall(r'<rule [^>]*clause="([^"]+)"[^>]*testNumber="(\d+)"[^>]*status="failed"[^>]*failedChecks="(\d+)"', x)
    return ok, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("out", nargs="?")
    ap.add_argument("--title"); ap.add_argument("--lang", default="en-US")
    a = ap.parse_args()
    out = a.out or re.sub(r"\.pdf$", "", a.pdf) + ".tagged.pdf"
    pages = pages_text(a.pdf)
    first = next((l.strip() for t in pages for l in t.splitlines() if len(l.strip()) > 8 and sum(c.isalpha() for c in l) > 6), "")
    title = a.title or os.path.basename(a.pdf)[:-4].replace("_", " ")
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "doc.html")
        open(h, "w").write(to_html(pages, title, a.lang))
        subprocess.run([BRAVE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--export-tagged-pdf",
                        "--generate-pdf-document-outline", f"--print-to-pdf={out}", f"file://{h}"], capture_output=True)
    if not os.path.exists(out):
        sys.exit("print failed")
    finish(out, title, a.lang)
    ok, failed = verapdf(out)
    print(f"{out}\n  pages in: {len(pages)} · first line: {first[:60]!r}\n  PDF/UA-1: {'PASS' if ok else 'FAIL'}"
          + "".join(f"\n    rule {c}-{n}: {k} checks" for c, n, k in failed[:8]))


if __name__ == "__main__":
    main()

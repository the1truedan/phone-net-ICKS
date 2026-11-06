#!/usr/bin/env python3
"""Markdown -> tagged PDF that passes PDF/UA-1 (same route as pape_tag_pdf.py), for letters and applications.

    ~/models/pape_tools/.venv/bin/python scripts/pape_md_to_pdf.py IN.md [--title "…"] [--lang en-US] [--size 10.5]

Writes IN.pdf next to IN.md and prints the veraPDF result. Lists become plain paragraphs ("• " / bold numbers) because
Chromium's tagged lists with bold text fail PDF/UA-1 rule 7.2-20; no table borders (rule 7.1-3).
"""
import argparse, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pape_tag_pdf as tag  # noqa: E402
from pape_tag_pdf import BRAVE  # noqa: E402


def flatten_lists(md):
    out = []
    for line in md.splitlines():
        m = re.match(r"^(\s*)(\d+)\. (.*)", line)
        if m:
            out.append(f"**{m.group(2)}.** {m.group(3)}\n"); continue
        m = re.match(r"^(\s*)[-*] (.*)", line)
        if m:
            out.append(("    " if m.group(1) else "") + "• " + m.group(2) + "\n"); continue
        out.append(line)
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("md"); ap.add_argument("--title"); ap.add_argument("--lang", default="en-US")
    ap.add_argument("--size", type=float, default=10.5); a = ap.parse_args()
    src = open(a.md).read()
    src = re.sub(r"^<style>.*?</style>\s*", "", src, flags=re.S)
    title = a.title or (re.search(r"^# (.+)$", src, re.M) or [None, os.path.basename(a.md)])[1]
    out = os.path.splitext(a.md)[0] + ".pdf"
    with tempfile.TemporaryDirectory() as d:
        m, h = f"{d}/in.md", f"{d}/a.html"
        open(m, "w").write(flatten_lists(src))
        subprocess.run(["pandoc", m, "-s", "-o", h, "--metadata", f"title={title}", "-V", f"lang={a.lang}"], check=True)
        css = (f"<style>body{{font-family:Helvetica,Arial,sans-serif;font-size:{a.size}pt;line-height:1.3;max-width:none;margin:0;padding:0}}"
               "h1{font-size:16pt;margin:0 0 4pt}h2{font-size:12.5pt;margin:10pt 0 3pt}p{margin:3pt 0}header{display:none}"
               "table,thead,tbody,tr,th,td{border:none!important}td,th{padding:1pt 8pt 1pt 0;text-align:left;vertical-align:top}@page{size:letter;margin:0.7in}</style></head>")
        html = open(h).read()  # read first: open(h, "w") would empty the file
        open(h, "w").write(html.replace("</head>", css))
        tmp = f"{d}/out.pdf"
        subprocess.run([BRAVE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--export-tagged-pdf",
                        "--generate-pdf-document-outline", f"--print-to-pdf={tmp}", f"file://{h}"], capture_output=True, timeout=90)
        import time
        for _ in range(40):  # Brave can return before the PDF is fully written
            if os.path.exists(tmp) and subprocess.run(["pdftotext", tmp, "-"], capture_output=True, text=True).stdout.strip():
                break
            time.sleep(0.5)
        else:
            sys.exit(f"render failed: no text in {tmp} (HTML kept at {h})")
        os.replace(tmp, out) if os.stat(tmp).st_dev == os.stat(os.path.dirname(os.path.abspath(out))).st_dev else __import__("shutil").move(tmp, out)
    tag.finish(out, title, a.lang)
    ok, failed = tag.verapdf(out)
    pages = re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", out], capture_output=True, text=True).stdout).group(1)
    print(f"{out}  pages={pages}  PDF/UA-1={'PASS' if ok else 'FAIL ' + str(failed[:4])}")


if __name__ == "__main__":
    main()
